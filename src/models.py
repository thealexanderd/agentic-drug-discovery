"""Shared data models for the application."""

from typing import Literal
from pydantic import BaseModel, Field


class ProteinTarget(BaseModel):
    """Represents a potential protein target for drug discovery."""
    
    protein_id: str = Field(description="UniProt ID or gene symbol")
    protein_name: str = Field(description="Human-readable protein name")
    gene_symbol: str = Field(description="Official gene symbol")
    
    # Evidence scores
    genetic_score: float = Field(default=0.0, ge=0.0, le=1.0, description="GWAS/genetic evidence")
    literature_score: float = Field(default=0.0, ge=0.0, le=1.0, description="PubMed publication strength")
    structural_score: float = Field(default=0.0, ge=0.0, le=1.0, description="PDB structural data availability")
    druggability_score: float = Field(default=0.0, ge=0.0, le=1.0, description="PubChem druggability indicators")
    
    # Metadata
    evidence_sources: list[str] = Field(default_factory=list, description="Database sources providing evidence")
    key_findings: list[str] = Field(default_factory=list, description="Key research findings")
    related_pathways: list[str] = Field(default_factory=list, description="Biological pathways involved")
    
    @property
    def overall_score(self) -> float:
        """Weighted overall score combining all evidence types."""
        weights = {
            "genetic": 0.35,
            "literature": 0.30,
            "structural": 0.20,
            "druggability": 0.15,
        }
        return (
            self.genetic_score * weights["genetic"] +
            self.literature_score * weights["literature"] +
            self.structural_score * weights["structural"] +
            self.druggability_score * weights["druggability"]
        )


class SearchResult(BaseModel):
    """Generic search result from a database."""
    
    source: Literal["pubmed", "pubchem", "gwas", "pdb", "uniprot"]
    result_id: str
    title: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)
    

class AgentState(BaseModel):
    """State passed between LangGraph nodes."""
    
    disease_query: str
    normalized_disease: str = ""
    
    # Search results from each database
    pubmed_results: list[SearchResult] = Field(default_factory=list)
    gwas_results: list[SearchResult] = Field(default_factory=list)
    uniprot_results: list[SearchResult] = Field(default_factory=list)
    pdb_results: list[SearchResult] = Field(default_factory=list)
    pubchem_results: list[SearchResult] = Field(default_factory=list)
    
    # Extracted protein targets
    candidate_proteins: list[str] = Field(default_factory=list)
    
    # Final ranked results
    ranked_targets: list[ProteinTarget] = Field(default_factory=list)
    
    # Workflow control
    searches_completed: list[str] = Field(default_factory=list)
    next_action: str = ""
    messages: list[str] = Field(default_factory=list)
