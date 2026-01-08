"""Target ranking and scoring logic."""

from collections import defaultdict
from src.models import ProteinTarget, SearchResult, AgentState


class TargetRanker:
    """Ranks protein targets based on multi-source evidence."""
    
    def rank_targets(self, state: AgentState) -> list[ProteinTarget]:
        """
        Rank protein targets based on evidence from all sources.
        
        Args:
            state: Current agent state with search results
            
        Returns:
            Sorted list of ProteinTarget objects
        """
        # Aggregate evidence by protein/gene
        protein_evidence = self._aggregate_evidence(state)
        
        # Create ProteinTarget objects with scores
        targets = []
        for protein_id, evidence in protein_evidence.items():
            target = self._create_target(protein_id, evidence)
            targets.append(target)
        
        # Sort by overall score
        targets.sort(key=lambda x: x.overall_score, reverse=True)
        
        return targets
    
    def _aggregate_evidence(self, state: AgentState) -> dict:
        """Aggregate evidence from all search results by protein."""
        evidence = defaultdict(lambda: {
            "genetic": [],
            "literature": [],
            "structural": [],
            "druggability": [],
            "sources": set(),
            "findings": [],
            "names": set(),
            "pathways": set()
        })
        
        # Process GWAS results for genetic evidence
        for result in state.gwas_results:
            gene = result.metadata.get("gene", "").upper()
            if gene and gene != "UNKNOWN":
                evidence[gene]["genetic"].append(result.relevance_score)
                evidence[gene]["sources"].add("GWAS Catalog")
                evidence[gene]["findings"].append(
                    f"Genetic association (p={result.metadata.get('pvalue', 'N/A')})"
                )
        
        # Process PubMed results for literature evidence
        for result in state.pubmed_results:
            # Use extracted proteins from metadata
            proteins_mentioned = result.metadata.get("proteins_mentioned", [])
            
            # Also check against candidate proteins
            all_proteins = set(proteins_mentioned + state.candidate_proteins)
            
            for protein in all_proteins:
                protein_upper = protein.upper()
                # Check if protein is mentioned in title or abstract
                title_abstract = f"{result.title} {result.metadata.get('abstract', '')}".upper()
                if protein_upper in title_abstract:
                    evidence[protein_upper]["literature"].append(result.relevance_score)
                    evidence[protein_upper]["sources"].add("PubMed")
                    
                    # Add key finding with publication info
                    year = result.metadata.get("year", "")
                    pmid = result.metadata.get("pmid", "")
                    pub_types = result.metadata.get("publication_types", [])
                    
                    finding_text = f"Referenced in: {result.title[:80]}..."
                    if year:
                        finding_text += f" ({year})"
                    if pub_types:
                        finding_text += f" [{pub_types[0] if pub_types else 'Article'}]"
                    
                    evidence[protein_upper]["findings"].append(finding_text)
        
        # Process UniProt results
        for result in state.uniprot_results:
            gene = result.metadata.get("gene", "").upper()
            if gene:
                evidence[gene]["literature"].append(result.relevance_score)
                evidence[gene]["sources"].add("UniProt")
                evidence[gene]["names"].add(result.title)
                if result.metadata.get("function"):
                    evidence[gene]["findings"].append(result.metadata["function"])
        
        # Process PDB results for structural evidence
        for result in state.pdb_results:
            protein = result.metadata.get("protein", "").upper()
            if protein:
                evidence[protein]["structural"].append(result.relevance_score)
                evidence[protein]["sources"].add("PDB")
                evidence[protein]["findings"].append(
                    f"3D structure available (PDB: {result.metadata.get('pdb_id')})"
                )
        
        # Process PubChem results for druggability
        for result in state.pubchem_results:
            protein = result.metadata.get("protein_target", "").upper()
            if protein:
                evidence[protein]["druggability"].append(result.relevance_score)
                evidence[protein]["sources"].add("PubChem")
        
        return evidence
    
    def _create_target(self, protein_id: str, evidence: dict) -> ProteinTarget:
        """Create a ProteinTarget from aggregated evidence."""
        # Calculate average scores for each category
        genetic_score = self._average_score(evidence["genetic"])
        literature_score = self._average_score(evidence["literature"])
        structural_score = self._average_score(evidence["structural"])
        druggability_score = self._average_score(evidence["druggability"])
        
        # Get protein name (use first name found or the ID)
        protein_name = list(evidence["names"])[0] if evidence["names"] else protein_id
        
        return ProteinTarget(
            protein_id=protein_id,
            protein_name=protein_name,
            gene_symbol=protein_id,
            genetic_score=genetic_score,
            literature_score=literature_score,
            structural_score=structural_score,
            druggability_score=druggability_score,
            evidence_sources=list(evidence["sources"]),
            key_findings=list(evidence["findings"])[:5],  # Top 5 findings
            related_pathways=list(evidence["pathways"])
        )
    
    def _average_score(self, scores: list[float]) -> float:
        """Calculate average score, with boosting for multiple evidence."""
        if not scores:
            return 0.0
        
        avg = sum(scores) / len(scores)
        
        # Boost score slightly for multiple pieces of evidence
        confidence_boost = min(len(scores) * 0.05, 0.2)
        
        return min(avg + confidence_boost, 1.0)


def create_ranker() -> TargetRanker:
    """Factory function to create target ranker."""
    return TargetRanker()
