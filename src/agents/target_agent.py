"""LangGraph agent for coordinating target discovery workflow."""

from typing import Annotated
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.config import settings
from src.models import AgentState
from src.tools import (
    create_pubmed_tool,
    create_gwas_tool,
    create_uniprot_tool,
    create_pdb_tool,
    create_pubchem_tool
)
from src.rankers import create_ranker


def create_agent():
    """Create the LangGraph agent for target discovery."""
    
    # Initialize LLM
    if settings.get_llm_provider() == "openai":
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature
        )
    else:
        llm = ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key
        )
    
    # Initialize tools
    pubmed = create_pubmed_tool()
    gwas = create_gwas_tool()
    uniprot = create_uniprot_tool()
    pdb = create_pdb_tool()
    pubchem = create_pubchem_tool()
    ranker = create_ranker()
    
    # Define workflow nodes
    def normalize_disease(state: AgentState) -> AgentState:
        """Normalize and understand the disease query."""
        state.messages.append(f"Normalizing disease query: {state.disease_query}")
        
        # Use LLM to normalize disease name
        prompt = f"""Given the disease query: "{state.disease_query}"
        
Provide:
1. The standardized medical name for this disease
2. 3-5 key synonyms or related terms
3. 3-5 relevant biological pathways or systems

Format your response as:
DISEASE: <standardized name>
SYNONYMS: <synonym1>, <synonym2>, ...
PATHWAYS: <pathway1>, <pathway2>, ..."""

        response = llm.invoke([HumanMessage(content=prompt)])
        state.normalized_disease = response.content.split("DISEASE:")[1].split("\n")[0].strip()
        state.next_action = "search_databases"
        
        return state
    
    def search_databases(state: AgentState) -> AgentState:
        """Search multiple databases in parallel."""
        state.messages.append("Searching databases...")
        
        disease = state.normalized_disease or state.disease_query
        
        # Search PubMed
        if "pubmed" not in state.searches_completed:
            state.pubmed_results = pubmed.search(disease)
            state.searches_completed.append("pubmed")
            state.messages.append(f"Found {len(state.pubmed_results)} PubMed articles")
            
            # Extract protein candidates from PubMed results
            for result in state.pubmed_results:
                proteins = result.metadata.get("proteins_mentioned", [])
                for protein in proteins:
                    if protein not in state.candidate_proteins:
                        state.candidate_proteins.append(protein)
        
        # Search GWAS
        if "gwas" not in state.searches_completed:
            state.gwas_results = gwas.search(disease)
            state.searches_completed.append("gwas")
            state.messages.append(f"Found {len(state.gwas_results)} GWAS associations")
            
            # Extract candidate proteins from GWAS
            for result in state.gwas_results:
                gene = result.metadata.get("gene", "")
                if gene and gene != "Unknown":
                    state.candidate_proteins.append(gene)
        
        # Search UniProt with candidate proteins
        if "uniprot" not in state.searches_completed:
            state.uniprot_results = uniprot.search(disease, state.candidate_proteins)
            state.searches_completed.append("uniprot")
            state.messages.append(f"Found {len(state.uniprot_results)} UniProt entries")
            
            # Add more candidates from UniProt
            for result in state.uniprot_results:
                gene = result.metadata.get("gene", "")
                if gene and gene not in state.candidate_proteins:
                    state.candidate_proteins.append(gene)
        
        # Search PDB with candidates
        if "pdb" not in state.searches_completed and state.candidate_proteins:
            state.pdb_results = pdb.search(state.candidate_proteins[:20])
            state.searches_completed.append("pdb")
            state.messages.append(f"Found {len(state.pdb_results)} PDB structures")
        
        # Search PubChem with candidates
        if "pubchem" not in state.searches_completed and state.candidate_proteins:
            state.pubchem_results = pubchem.search(state.candidate_proteins[:20])
            state.searches_completed.append("pubchem")
            state.messages.append(f"Found {len(state.pubchem_results)} PubChem compounds")
        
        # Do a second targeted PubMed search with top candidate proteins
        if "pubmed_targeted" not in state.searches_completed and state.candidate_proteins:
            top_proteins = state.candidate_proteins[:10]  # Top 10 candidates
            for protein in top_proteins:
                try:
                    targeted_results = pubmed.search(disease, protein)
                    state.pubmed_results.extend(targeted_results)
                except Exception as e:
                    print(f"Error in targeted PubMed search for {protein}: {e}")
            state.searches_completed.append("pubmed_targeted")
            state.messages.append(f"Completed targeted PubMed search for {len(top_proteins)} proteins")
        
        state.next_action = "rank_targets"
        return state
    
    def rank_targets(state: AgentState) -> AgentState:
        """Rank protein targets based on aggregated evidence."""
        print("Ranking targets...")
        state.messages.append("Ranking protein targets...")
        
        state.ranked_targets = ranker.rank_targets(state)
        state.messages.append(f"Ranked {len(state.ranked_targets)} protein targets")
        print(state.ranked_targets)
        
        state.next_action = "complete"
        return state
    
    def should_continue(state: AgentState) -> str:
        """Determine next step in workflow."""
        if state.next_action == "search_databases":
            return "search"
        elif state.next_action == "rank_targets":
            return "rank"
        else:
            return "end"
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("normalize", normalize_disease)
    workflow.add_node("search", search_databases)
    workflow.add_node("rank", rank_targets)
    
    # Add edges
    workflow.set_entry_point("normalize")
    workflow.add_conditional_edges(
        "normalize",
        should_continue,
        {
            "search": "search",
            "end": END
        }
    )
    workflow.add_conditional_edges(
        "search",
        should_continue,
        {
            "rank": "rank",
            "end": END
        }
    )
    workflow.add_conditional_edges(
        "rank",
        should_continue,
        {
            "end": END
        }
    )
    
    return workflow.compile()


def run_target_discovery(disease: str, verbose: bool = False) -> AgentState:
    """
    Run the target discovery workflow.
    
    Args:
        disease: Disease name to search for
        verbose: Whether to print progress messages
        
    Returns:
        Final AgentState with ranked targets
    """
    agent = create_agent()
    
    initial_state = AgentState(disease_query=disease)
    
    # Run the agent
    final_state = agent.invoke(initial_state)
    
    if verbose:
        for msg in final_state.messages:
            print(f"  {msg}")
    
    return final_state
