"""
Agentic LangGraph workflow for protein target discovery.

This module implements a truly agentic approach where the LLM:
1. Creates a research plan based on disease characteristics
2. Dynamically decides which tools to use and in what order
3. Evaluates intermediate results and adjusts strategy
4. Synthesizes evidence with reasoning at each step
"""

import json
from typing import Any
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END

from src.config import settings
from src.models import (
    AgentState, 
    ResearchPlan, 
    ToolDecision, 
    IntermediateAnalysis,
    EvidenceSynthesis
)
from src.tools import TOOL_REGISTRY
from src.rankers import create_ranker


# =============================================================================
# SYSTEM PROMPTS FOR AGENTIC BEHAVIOR
# =============================================================================

RESEARCH_PLANNER_PROMPT = """You are an expert biomedical researcher specializing in drug target discovery.
Given a disease, create a research plan for identifying the best protein targets.

Consider:
1. Disease type (genetic, autoimmune, infectious, metabolic, neurodegenerative, etc.)
2. Known biology and mechanisms
3. What databases would be most valuable for THIS specific disease
4. What hypotheses to test

Available databases:
{tool_descriptions}

Respond in JSON format:
{{
    "disease_name": "standardized disease name",
    "disease_type": "category of disease",
    "key_hypotheses": ["hypothesis 1", "hypothesis 2", ...],
    "priority_pathways": ["pathway 1", "pathway 2", ...],
    "search_strategy": "overall strategy description",
    "tool_sequence": [
        {{"tool_name": "name", "reasoning": "why this tool", "priority": 1, "expected_outcome": "what to learn"}},
        ...
    ],
    "rationale": "overall rationale for this plan"
}}"""

TOOL_SELECTOR_PROMPT = """You are deciding which database to query next for protein target discovery.

Current research state:
{state_summary}

Tools already used: {tools_used}
Available tools: {available_tools}

Based on what you've learned so far, which tool should be used next and why?
Consider:
- What information gaps remain?
- What would provide the most value at this stage?
- Should you go deeper on current candidates or broaden the search?

Respond in JSON format:
{{
    "tool_name": "selected_tool",
    "reasoning": "detailed reasoning for this choice",
    "parameters": {{"key": "value"}},
    "expected_outcome": "what you expect to learn"
}}

If you have enough information, respond:
{{
    "tool_name": "DONE",
    "reasoning": "why no more searches are needed"
}}"""

RESULT_ANALYZER_PROMPT = """You are analyzing search results from {tool_name} for protein target discovery.

Disease: {disease}
Research hypotheses: {hypotheses}

Search results summary:
{results_summary}

Top results:
{top_results}

Analyze these results:
1. What key proteins/genes were identified?
2. How confident are you in these results?
3. What gaps remain?
4. What should be done next?

Respond in JSON format:
{{
    "results_summary": "brief summary of findings",
    "key_proteins_found": ["GENE1", "GENE2", ...],
    "confidence_level": "low|medium|high",
    "gaps_identified": ["gap 1", "gap 2", ...],
    "next_steps": ["step 1", "step 2", ...],
    "should_continue": true/false,
    "reasoning": "detailed reasoning about these results"
}}"""

EVIDENCE_SYNTHESIZER_PROMPT = """You are synthesizing evidence for protein target: {gene_symbol}

Disease: {disease}

Evidence from multiple sources:
{evidence_summary}

Synthesize this evidence into a comprehensive assessment:
1. Overall assessment of this target
2. Strength of evidence (weak/moderate/strong/very_strong)
3. Mechanistic explanation
4. Key supporting evidence
5. Concerns or gaps
6. Druggability assessment
7. Recommended validation experiments

Respond in JSON format:
{{
    "overall_assessment": "comprehensive assessment",
    "strength_of_evidence": "weak|moderate|strong|very_strong",
    "mechanistic_explanation": "how this target relates to disease",
    "supporting_evidence": ["evidence 1", "evidence 2", ...],
    "concerns_or_gaps": ["concern 1", "concern 2", ...],
    "druggability_assessment": "assessment of druggability",
    "recommended_validation": ["experiment 1", "experiment 2", ...]
}}"""

FINAL_SYNTHESIS_PROMPT = """You are providing a final synthesis of the protein target discovery for: {disease}

Research journey:
{reasoning_trace}

Top targets identified:
{top_targets}

Provide a final synthesis that:
1. Summarizes the key findings
2. Explains why the top targets were selected
3. Discusses the biological rationale
4. Notes any limitations or caveats
5. Suggests next steps for validation

Write a comprehensive but concise summary (2-3 paragraphs)."""


class AgenticTargetDiscovery:
    """
    Agentic workflow for protein target discovery.
    
    Unlike a simple automation, this agent:
    - Reasons about the disease and creates a tailored research plan
    - Dynamically selects tools based on intermediate results
    - Evaluates results and adjusts strategy
    - Provides reasoning at each step
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose or settings.verbose_reasoning
        self.llm = self._initialize_llm()
        self.tools = self._initialize_tools()
        self.ranker = create_ranker()
    
    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        if settings.get_llm_provider() == "openai":
            return ChatOpenAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature
            )
        else:
            return ChatAnthropic(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                api_key=settings.anthropic_api_key
            )
    
    def _initialize_tools(self) -> dict:
        """Initialize all available tools."""
        tools = {}
        for tool_id, tool_info in TOOL_REGISTRY.items():
            try:
                tools[tool_id] = tool_info["factory"]()
            except Exception as e:
                print(f"Warning: Could not initialize {tool_id}: {e}")
        return tools
    
    def _get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for prompts."""
        descriptions = []
        for tool_id, info in TOOL_REGISTRY.items():
            descriptions.append(f"""
- **{info['name']}** (priority: {info['priority']})
  Purpose: {info['purpose']}
  Best for: {', '.join(info['best_for'])}
  Provides: {', '.join(info['provides'])}
  Limitations: {', '.join(info['limitations'])}
""")
        return "\n".join(descriptions)
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"  🤖 {message}")
    
    def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Call the LLM with a prompt."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        response = self.llm.invoke(messages)
        return response.content
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Clean up response
        text = response.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return {}
    
    # =========================================================================
    # AGENTIC WORKFLOW NODES
    # =========================================================================
    
    def create_research_plan(self, state: AgentState) -> AgentState:
        """
        Create a research plan for the disease.
        
        The LLM analyzes the disease and creates a tailored strategy.
        """
        self._log(f"Creating research plan for: {state.disease_query}")
        
        prompt = f"""Create a research plan for discovering protein targets for: {state.disease_query}

{RESEARCH_PLANNER_PROMPT.format(tool_descriptions=self._get_tool_descriptions())}"""
        
        response = self._call_llm(prompt)
        plan_data = self._parse_json_response(response)
        
        if plan_data:
            # Create ResearchPlan object
            tool_sequence = []
            for tool in plan_data.get("tool_sequence", []):
                tool_sequence.append(ToolDecision(
                    tool_name=tool.get("tool_name", ""),
                    reasoning=tool.get("reasoning", ""),
                    priority=tool.get("priority", 1),
                    parameters=tool.get("parameters", {}),
                    expected_outcome=tool.get("expected_outcome", "")
                ))
            
            state.research_plan = ResearchPlan(
                disease_name=plan_data.get("disease_name", state.disease_query),
                disease_type=plan_data.get("disease_type", "unknown"),
                key_hypotheses=plan_data.get("key_hypotheses", []),
                priority_pathways=plan_data.get("priority_pathways", []),
                search_strategy=plan_data.get("search_strategy", ""),
                tool_sequence=tool_sequence,
                rationale=plan_data.get("rationale", "")
            )
            
            state.normalized_disease = plan_data.get("disease_name", state.disease_query)
            state.current_hypotheses = plan_data.get("key_hypotheses", [])
            state.planned_tools = tool_sequence
            
            # Add reasoning step
            state.add_reasoning_step(
                action_type="plan",
                description=f"Created research plan for {state.normalized_disease}",
                input_context=state.disease_query,
                output=plan_data.get("rationale", ""),
                llm_prompt=prompt[:500] + "...",
                llm_response=response[:500] + "..."
            )
            
            self._log(f"Disease type: {state.research_plan.disease_type}")
            self._log(f"Strategy: {state.research_plan.search_strategy}")
            self._log(f"Planned tools: {[t.tool_name for t in tool_sequence]}")
        
        state.next_action = "execute_search"
        state.messages.append(f"Created research plan for {state.normalized_disease}")
        
        return state
    
    def select_next_tool(self, state: AgentState) -> AgentState:
        """
        Dynamically select the next tool to use based on current state.
        
        The LLM evaluates what has been learned and decides what to do next.
        """
        self._log("Selecting next tool based on current findings...")
        
        # Get list of available and used tools
        used = state.tools_executed
        available = [t for t in self.tools.keys() if t not in used]
        
        if not available or state.iteration_count >= state.max_iterations:
            state.should_continue_research = False
            state.next_action = "synthesize"
            return state
        
        prompt = TOOL_SELECTOR_PROMPT.format(
            state_summary=state.get_context_summary(),
            tools_used=", ".join(used) if used else "None",
            available_tools=", ".join(available)
        )
        
        response = self._call_llm(prompt)
        decision = self._parse_json_response(response)
        
        if decision.get("tool_name") == "DONE":
            self._log(f"Deciding to stop: {decision.get('reasoning', 'sufficient evidence')}")
            state.should_continue_research = False
            state.next_action = "synthesize"
        elif decision.get("tool_name") in self.tools:
            tool_name = decision["tool_name"]
            self._log(f"Selected tool: {tool_name}")
            self._log(f"Reasoning: {decision.get('reasoning', '')}")
            
            state.planned_tools.insert(0, ToolDecision(
                tool_name=tool_name,
                reasoning=decision.get("reasoning", ""),
                priority=1,
                parameters=decision.get("parameters", {}),
                expected_outcome=decision.get("expected_outcome", "")
            ))
            state.next_action = "execute_search"
        else:
            # Default to next planned tool or first available
            if state.planned_tools:
                next_tool = state.planned_tools[0].tool_name
            else:
                next_tool = available[0]
            
            if next_tool not in used:
                state.next_action = "execute_search"
            else:
                state.should_continue_research = False
                state.next_action = "synthesize"
        
        return state
    
    def execute_search(self, state: AgentState) -> AgentState:
        """
        Execute the selected tool and analyze results.
        """
        state.iteration_count += 1
        
        # Determine which tool to use
        if state.planned_tools:
            tool_decision = state.planned_tools.pop(0)
            tool_name = tool_decision.tool_name
        else:
            # Find first unused tool
            for t in ["disgenet", "pubmed", "gwas", "uniprot", "go", "reactome", "pdb", "pubchem"]:
                if t not in state.tools_executed and t in self.tools:
                    tool_name = t
                    break
            else:
                state.should_continue_research = False
                state.next_action = "synthesize"
                return state
        
        if tool_name in state.tools_executed:
            state.next_action = "select_tool"
            return state
        
        self._log(f"Executing: {tool_name}")
        
        tool = self.tools.get(tool_name)
        if not tool:
            self._log(f"Tool not available: {tool_name}")
            state.next_action = "select_tool"
            return state
        
        # Execute the tool based on its type
        results = self._execute_tool(tool_name, tool, state)
        
        # Store results in state
        self._store_results(tool_name, results, state)
        
        state.tools_executed.append(tool_name)
        state.searches_completed.append(tool_name)
        
        # Analyze results with LLM
        analysis = self._analyze_results(tool_name, results, state)
        if analysis:
            state.intermediate_analyses.append(analysis)
            
            # Update candidate proteins
            for protein in analysis.key_proteins_found:
                if protein.upper() not in [p.upper() for p in state.candidate_proteins]:
                    state.candidate_proteins.append(protein.upper())
            
            # Check if we should continue
            if not analysis.should_continue and state.iteration_count >= 3:
                state.should_continue_research = False
        
        self._log(f"Found {len(results)} results, {len(state.candidate_proteins)} total candidates")
        state.messages.append(f"Searched {tool_name}: found {len(results)} results")
        
        # Decide next action
        if state.should_continue_research and state.iteration_count < state.max_iterations:
            state.next_action = "select_tool"
        else:
            state.next_action = "synthesize"
        
        return state
    
    def _execute_tool(self, tool_name: str, tool: Any, state: AgentState) -> list:
        """Execute a specific tool with appropriate parameters."""
        disease = state.normalized_disease or state.disease_query
        candidates = state.candidate_proteins[:20]  # Top 20 candidates
        
        try:
            if tool_name == "pubmed":
                # For PubMed, use disease and optionally top protein
                if candidates and len(state.tools_executed) > 2:
                    # Targeted search with top proteins
                    all_results = []
                    for protein in candidates[:5]:
                        results = tool.search(disease, protein)
                        all_results.extend(results)
                    return all_results
                else:
                    return tool.search(disease)
            
            elif tool_name == "gwas":
                return tool.search(disease)
            
            elif tool_name == "disgenet":
                return tool.search(disease)
            
            elif tool_name == "uniprot":
                return tool.search(disease, candidates)
            
            elif tool_name == "go":
                if candidates:
                    return tool.search(candidates, disease)
                return []
            
            elif tool_name == "reactome":
                if candidates:
                    return tool.search(candidates, disease)
                # Also search for disease pathways
                pathway_results = tool.search_disease_pathways(disease)
                return pathway_results
            
            elif tool_name == "pdb":
                if candidates:
                    return tool.search(candidates)
                return []
            
            elif tool_name == "pubchem":
                if candidates:
                    return tool.search(candidates)
                return []
            
            else:
                return []
                
        except Exception as e:
            self._log(f"Error executing {tool_name}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _store_results(self, tool_name: str, results: list, state: AgentState):
        """Store results in the appropriate state field."""
        result_map = {
            "pubmed": "pubmed_results",
            "gwas": "gwas_results",
            "uniprot": "uniprot_results",
            "pdb": "pdb_results",
            "pubchem": "pubchem_results",
            "disgenet": "disgenet_results",
            "go": "go_results",
            "reactome": "reactome_results"
        }
        
        field = result_map.get(tool_name)
        if field:
            current = getattr(state, field, [])
            setattr(state, field, current + results)
    
    def _analyze_results(self, tool_name: str, results: list, state: AgentState) -> IntermediateAnalysis:
        """Use LLM to analyze results from a tool."""
        if not results:
            return IntermediateAnalysis(
                tool_used=tool_name,
                results_summary=f"No results found from {tool_name}",
                key_proteins_found=[],
                confidence_level="low",
                gaps_identified=[f"No data from {tool_name}"],
                next_steps=["Try other databases"],
                should_continue=True,
                reasoning="Empty results, should continue with other tools"
            )
        
        # Prepare results summary for LLM
        top_results = []
        proteins_found = set()
        
        for r in results[:10]:  # Top 10 results
            top_results.append({
                "title": r.title,
                "score": r.relevance_score,
                "key_info": {k: v for k, v in r.metadata.items() if k in [
                    "gene", "gene_symbol", "pvalue", "disgenet_score", 
                    "biological_processes", "pathway_name"
                ]}
            })
            
            # Extract proteins
            gene = r.metadata.get("gene") or r.metadata.get("gene_symbol", "")
            if gene:
                proteins_found.add(gene.upper())
        
        prompt = RESULT_ANALYZER_PROMPT.format(
            tool_name=tool_name,
            disease=state.normalized_disease or state.disease_query,
            hypotheses=", ".join(state.current_hypotheses[:3]),
            results_summary=f"Found {len(results)} results with relevance scores ranging from {min(r.relevance_score for r in results):.2f} to {max(r.relevance_score for r in results):.2f}",
            top_results=json.dumps(top_results, indent=2)
        )
        
        response = self._call_llm(prompt)
        analysis_data = self._parse_json_response(response)
        
        if analysis_data:
            # Add reasoning step
            state.add_reasoning_step(
                action_type="analyze",
                description=f"Analyzed {len(results)} results from {tool_name}",
                input_context=f"Tool: {tool_name}, Results: {len(results)}",
                output=analysis_data.get("results_summary", ""),
                llm_response=response[:500] + "..."
            )
            
            return IntermediateAnalysis(
                tool_used=tool_name,
                results_summary=analysis_data.get("results_summary", ""),
                key_proteins_found=analysis_data.get("key_proteins_found", list(proteins_found)),
                confidence_level=analysis_data.get("confidence_level", "medium"),
                gaps_identified=analysis_data.get("gaps_identified", []),
                next_steps=analysis_data.get("next_steps", []),
                should_continue=analysis_data.get("should_continue", True),
                reasoning=analysis_data.get("reasoning", "")
            )
        
        # Fallback if parsing fails
        return IntermediateAnalysis(
            tool_used=tool_name,
            results_summary=f"Found {len(results)} results",
            key_proteins_found=list(proteins_found),
            confidence_level="medium",
            gaps_identified=[],
            next_steps=["Continue with next tool"],
            should_continue=True,
            reasoning="Analysis parsing failed, using fallback"
        )
    
    def synthesize_and_rank(self, state: AgentState) -> AgentState:
        """
        Synthesize all evidence and create final rankings.
        """
        self._log("Synthesizing evidence and ranking targets...")
        
        # Use the ranker to get base rankings
        state.ranked_targets = self.ranker.rank_targets(state)
        
        # For top targets, get LLM synthesis
        for target in state.ranked_targets[:10]:
            synthesis = self._synthesize_target_evidence(target, state)
            if synthesis:
                target.llm_synthesis = synthesis
        
        # Generate final synthesis narrative
        state.final_synthesis = self._generate_final_synthesis(state)
        
        state.add_reasoning_step(
            action_type="synthesize",
            description=f"Synthesized evidence for {len(state.ranked_targets)} targets",
            input_context=f"Candidates: {len(state.candidate_proteins)}",
            output=f"Ranked {len(state.ranked_targets)} targets"
        )
        
        state.next_action = "complete"
        state.messages.append(f"Ranked {len(state.ranked_targets)} protein targets")
        
        return state
    
    def _synthesize_target_evidence(self, target, state: AgentState) -> EvidenceSynthesis | None:
        """Get LLM synthesis for a specific target."""
        # Gather evidence summary
        evidence_parts = []
        
        # DisGeNET evidence
        for r in state.disgenet_results:
            if r.metadata.get("gene_symbol", "").upper() == target.gene_symbol.upper():
                evidence_parts.append(f"DisGeNET: score={r.metadata.get('disgenet_score', 'N/A')}, publications={r.metadata.get('n_publications', 0)}")
        
        # GWAS evidence
        for r in state.gwas_results:
            if r.metadata.get("gene", "").upper() == target.gene_symbol.upper():
                evidence_parts.append(f"GWAS: p-value={r.metadata.get('pvalue', 'N/A')}")
        
        # PubMed mentions
        pubmed_count = sum(1 for r in state.pubmed_results if target.gene_symbol.upper() in r.title.upper())
        if pubmed_count:
            evidence_parts.append(f"PubMed: {pubmed_count} publications mentioning this target")
        
        # GO annotations
        for r in state.go_results:
            if r.metadata.get("gene_symbol", "").upper() == target.gene_symbol.upper():
                bps = r.metadata.get("biological_processes", [])[:3]
                if bps:
                    evidence_parts.append(f"GO biological processes: {', '.join(bps)}")
        
        # Pathway info
        pathways = []
        for r in state.reactome_results:
            if target.gene_symbol.upper() in [g.upper() for g in r.metadata.get("genes_in_pathway", [])]:
                pathways.append(r.metadata.get("pathway_name", ""))
        if pathways:
            evidence_parts.append(f"Reactome pathways: {', '.join(pathways[:3])}")
        
        if not evidence_parts:
            return None
        
        prompt = EVIDENCE_SYNTHESIZER_PROMPT.format(
            gene_symbol=target.gene_symbol,
            disease=state.normalized_disease,
            evidence_summary="\n".join(f"- {e}" for e in evidence_parts)
        )
        
        response = self._call_llm(prompt)
        data = self._parse_json_response(response)
        
        if data:
            return EvidenceSynthesis(
                gene_symbol=target.gene_symbol,
                overall_assessment=data.get("overall_assessment", ""),
                strength_of_evidence=data.get("strength_of_evidence", "moderate"),
                mechanistic_explanation=data.get("mechanistic_explanation", ""),
                supporting_evidence=data.get("supporting_evidence", []),
                concerns_or_gaps=data.get("concerns_or_gaps", []),
                druggability_assessment=data.get("druggability_assessment", ""),
                recommended_validation=data.get("recommended_validation", [])
            )
        
        return None
    
    def _generate_final_synthesis(self, state: AgentState) -> str:
        """Generate a final narrative synthesis."""
        # Prepare reasoning trace summary
        trace_summary = []
        for step in state.reasoning_trace[-5:]:  # Last 5 steps
            trace_summary.append(f"Step {step.step_number} ({step.action_type}): {step.description}")
        
        # Prepare top targets
        top_targets = []
        for t in state.ranked_targets[:5]:
            top_targets.append({
                "gene": t.gene_symbol,
                "score": t.overall_score,
                "sources": t.evidence_sources
            })
        
        prompt = FINAL_SYNTHESIS_PROMPT.format(
            disease=state.normalized_disease,
            reasoning_trace="\n".join(trace_summary),
            top_targets=json.dumps(top_targets, indent=2)
        )
        
        response = self._call_llm(prompt)
        return response


def create_agent(verbose: bool = False):
    """Create the agentic target discovery workflow."""
    agent = AgenticTargetDiscovery(verbose=verbose)
    
    # Build the state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("plan", agent.create_research_plan)
    workflow.add_node("select_tool", agent.select_next_tool)
    workflow.add_node("execute_search", agent.execute_search)
    workflow.add_node("synthesize", agent.synthesize_and_rank)
    
    # Define routing
    def route_after_plan(state: AgentState) -> str:
        return "execute_search" if state.next_action == "execute_search" else "synthesize"
    
    def route_after_select(state: AgentState) -> str:
        if state.next_action == "execute_search":
            return "execute_search"
        return "synthesize"
    
    def route_after_search(state: AgentState) -> str:
        if state.next_action == "select_tool":
            return "select_tool"
        return "synthesize"
    
    def route_after_synthesis(state: AgentState) -> str:
        return END
    
    # Set entry point
    workflow.set_entry_point("plan")
    
    # Add conditional edges
    workflow.add_conditional_edges("plan", route_after_plan, {
        "execute_search": "execute_search",
        "synthesize": "synthesize"
    })
    
    workflow.add_conditional_edges("select_tool", route_after_select, {
        "execute_search": "execute_search",
        "synthesize": "synthesize"
    })
    
    workflow.add_conditional_edges("execute_search", route_after_search, {
        "select_tool": "select_tool",
        "synthesize": "synthesize"
    })
    
    workflow.add_conditional_edges("synthesize", route_after_synthesis, {
        END: END
    })
    
    return workflow.compile()


def run_target_discovery(disease: str, verbose: bool = False) -> AgentState:
    """
    Run the agentic target discovery workflow.
    
    Args:
        disease: Disease name to search for
        verbose: Whether to print detailed reasoning
        
    Returns:
        Final AgentState with ranked targets and reasoning trace
    """
    workflow = create_agent(verbose=verbose)
    
    initial_state = AgentState(
        disease_query=disease,
        max_iterations=settings.max_iterations
    )
    
    # Run the workflow
    final_state = workflow.invoke(initial_state)
    
    if verbose:
        print("\n📋 Reasoning Trace:")
        for step in final_state["reasoning_trace"]:
            print(f"  [{step.action_type}] {step.description}")
    
    return final_state
