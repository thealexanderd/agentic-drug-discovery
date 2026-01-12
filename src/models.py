"""Shared data models for the application."""

from typing import Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# AGENTIC REASONING MODELS
# =============================================================================

class ToolDecision(BaseModel):
    """Represents a decision by the LLM about which tool to use."""
    
    tool_name: str = Field(description="Name of the tool to use")
    reasoning: str = Field(description="LLM's reasoning for why this tool should be used")
    priority: int = Field(default=1, description="Priority order (1=highest)")
    parameters: dict = Field(default_factory=dict, description="Parameters to pass to the tool")
    expected_outcome: str = Field(description="What the LLM expects to learn from this tool")


class ResearchPlan(BaseModel):
    """High-level research plan created by the LLM for a disease."""
    
    disease_name: str = Field(description="Normalized disease name")
    disease_type: str = Field(description="Type: genetic, autoimmune, infectious, metabolic, etc.")
    key_hypotheses: list[str] = Field(default_factory=list, description="Research hypotheses to test")
    priority_pathways: list[str] = Field(default_factory=list, description="Key biological pathways to investigate")
    search_strategy: str = Field(description="Overall strategy for this disease type")
    tool_sequence: list[ToolDecision] = Field(default_factory=list, description="Planned sequence of tools")
    rationale: str = Field(description="Overall rationale for the research plan")


class IntermediateAnalysis(BaseModel):
    """LLM's analysis of intermediate results after using a tool."""
    
    tool_used: str = Field(description="Which tool produced these results")
    timestamp: datetime = Field(default_factory=datetime.now)
    results_summary: str = Field(description="Summary of what was found")
    key_proteins_found: list[str] = Field(default_factory=list, description="Proteins/genes identified")
    confidence_level: str = Field(description="low, medium, high - confidence in results")
    gaps_identified: list[str] = Field(default_factory=list, description="What's still missing or unclear")
    next_steps: list[str] = Field(default_factory=list, description="Recommended next actions")
    should_continue: bool = Field(default=True, description="Whether to continue searching")
    reasoning: str = Field(description="LLM's reasoning about these results")


class EvidenceSynthesis(BaseModel):
    """LLM's synthesis of evidence from multiple sources for a target."""
    
    gene_symbol: str = Field(description="The target gene/protein")
    overall_assessment: str = Field(description="LLM's overall assessment of this target")
    strength_of_evidence: str = Field(description="weak, moderate, strong, very_strong")
    mechanistic_explanation: str = Field(description="How this target relates to disease mechanism")
    supporting_evidence: list[str] = Field(default_factory=list, description="Key supporting evidence")
    concerns_or_gaps: list[str] = Field(default_factory=list, description="Concerns or missing evidence")
    druggability_assessment: str = Field(description="Assessment of druggability potential")
    recommended_validation: list[str] = Field(default_factory=list, description="Experiments to validate")


class ReasoningStep(BaseModel):
    """A single step in the agent's reasoning process."""
    
    step_number: int
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: str = Field(description="plan, search, analyze, synthesize, decide")
    description: str = Field(description="What the agent is doing")
    input_context: str = Field(description="What information the agent is working with")
    output: str = Field(description="Result of this reasoning step")
    llm_prompt: str = Field(default="", description="The prompt sent to the LLM")
    llm_response: str = Field(default="", description="The LLM's response")


# =============================================================================
# PROTEIN TARGET MODEL
# =============================================================================

class ProteinTarget(BaseModel):
    """Represents a potential protein target for drug discovery."""
    
    protein_id: str = Field(description="UniProt ID or gene symbol")
    protein_name: str = Field(description="Human-readable protein name")
    gene_symbol: str = Field(description="Official gene symbol")
    
    # Evidence scores (traditional)
    genetic_score: float = Field(default=0.0, ge=0.0, le=1.0, description="GWAS/genetic evidence")
    literature_score: float = Field(default=0.0, ge=0.0, le=1.0, description="PubMed publication strength")
    structural_score: float = Field(default=0.0, ge=0.0, le=1.0, description="PDB structural data availability")
    druggability_score: float = Field(default=0.0, ge=0.0, le=1.0, description="PubChem druggability indicators")
    
    # New evidence scores from additional databases
    disgenet_score: float = Field(default=0.0, ge=0.0, le=1.0, description="DisGeNET gene-disease association")
    go_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Gene Ontology functional relevance")
    pathway_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Reactome pathway relevance")
    
    # Metadata
    evidence_sources: list[str] = Field(default_factory=list, description="Database sources providing evidence")
    key_findings: list[str] = Field(default_factory=list, description="Key research findings")
    related_pathways: list[str] = Field(default_factory=list, description="Biological pathways involved")
    go_terms: list[str] = Field(default_factory=list, description="Gene Ontology terms")
    
    # LLM-generated insights
    llm_synthesis: EvidenceSynthesis | None = Field(default=None, description="LLM's evidence synthesis")
    
    @property
    def overall_score(self) -> float:
        """Weighted overall score combining all evidence types."""
        weights = {
            "genetic": 0.25,
            "literature": 0.20,
            "structural": 0.10,
            "druggability": 0.10,
            "disgenet": 0.20,
            "go": 0.08,
            "pathway": 0.07,
        }
        return (
            self.genetic_score * weights["genetic"] +
            self.literature_score * weights["literature"] +
            self.structural_score * weights["structural"] +
            self.druggability_score * weights["druggability"] +
            self.disgenet_score * weights["disgenet"] +
            self.go_score * weights["go"] +
            self.pathway_score * weights["pathway"]
        )


# =============================================================================
# SEARCH RESULT MODEL  
# =============================================================================

class SearchResult(BaseModel):
    """Generic search result from a database."""
    
    source: Literal["pubmed", "pubchem", "gwas", "pdb", "uniprot", "disgenet", "go", "reactome"]
    result_id: str
    title: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)
    

# =============================================================================
# AGENT STATE - CORE WORKFLOW STATE
# =============================================================================

class AgentState(BaseModel):
    """State passed between LangGraph nodes - enhanced for agentic workflow."""
    
    disease_query: str
    normalized_disease: str = ""
    
    # =========================================================================
    # AGENTIC REASONING STATE
    # =========================================================================
    research_plan: ResearchPlan | None = Field(default=None, description="LLM-generated research plan")
    reasoning_trace: list[ReasoningStep] = Field(default_factory=list, description="Full reasoning trace")
    intermediate_analyses: list[IntermediateAnalysis] = Field(default_factory=list, description="Analysis after each tool")
    current_hypotheses: list[str] = Field(default_factory=list, description="Active research hypotheses")
    
    # Tool decision tracking
    planned_tools: list[ToolDecision] = Field(default_factory=list, description="Tools planned to use")
    tools_executed: list[str] = Field(default_factory=list, description="Tools already executed")
    
    # Iteration control
    iteration_count: int = Field(default=0, description="Current iteration number")
    max_iterations: int = Field(default=5, description="Maximum reasoning iterations")
    should_continue_research: bool = Field(default=True, description="Whether to continue searching")
    
    # =========================================================================
    # SEARCH RESULTS FROM EACH DATABASE
    # =========================================================================
    pubmed_results: list[SearchResult] = Field(default_factory=list)
    gwas_results: list[SearchResult] = Field(default_factory=list)
    uniprot_results: list[SearchResult] = Field(default_factory=list)
    pdb_results: list[SearchResult] = Field(default_factory=list)
    pubchem_results: list[SearchResult] = Field(default_factory=list)
    
    # New database results
    disgenet_results: list[SearchResult] = Field(default_factory=list)
    go_results: list[SearchResult] = Field(default_factory=list)
    reactome_results: list[SearchResult] = Field(default_factory=list)
    
    # =========================================================================
    # EXTRACTED PROTEINS AND TARGETS
    # =========================================================================
    candidate_proteins: list[str] = Field(default_factory=list, description="Accumulated protein candidates")
    protein_evidence: dict = Field(default_factory=dict, description="Evidence per protein from LLM analysis")
    
    # Final ranked results with LLM synthesis
    ranked_targets: list[ProteinTarget] = Field(default_factory=list)
    final_synthesis: str = Field(default="", description="LLM's final synthesis of all findings")
    
    # =========================================================================
    # WORKFLOW CONTROL (kept for backward compatibility)
    # =========================================================================
    searches_completed: list[str] = Field(default_factory=list)
    next_action: str = ""
    messages: list[str] = Field(default_factory=list)
    
    def add_reasoning_step(self, action_type: str, description: str, input_context: str, output: str, 
                           llm_prompt: str = "", llm_response: str = "") -> None:
        """Add a new reasoning step to the trace."""
        step = ReasoningStep(
            step_number=len(self.reasoning_trace) + 1,
            action_type=action_type,
            description=description,
            input_context=input_context,
            output=output,
            llm_prompt=llm_prompt,
            llm_response=llm_response
        )
        self.reasoning_trace.append(step)
    
    def get_context_summary(self) -> str:
        """Get a summary of current state for LLM context."""
        return f"""
Disease: {self.normalized_disease or self.disease_query}
Iteration: {self.iteration_count}/{self.max_iterations}
Candidate proteins found: {len(self.candidate_proteins)}
Top candidates: {', '.join(self.candidate_proteins[:10]) if self.candidate_proteins else 'None yet'}
Tools executed: {', '.join(self.tools_executed) if self.tools_executed else 'None yet'}
Active hypotheses: {'; '.join(self.current_hypotheses[:3]) if self.current_hypotheses else 'None yet'}
"""
