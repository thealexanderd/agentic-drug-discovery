"""Target ranking and scoring logic with enhanced evidence aggregation."""

from collections import defaultdict
from src.models import ProteinTarget, SearchResult, AgentState


class TargetRanker:
    """Ranks protein targets based on multi-source evidence.
    
    This ranker aggregates evidence from all database sources:
    - Core: PubMed, UniProt, DisGeNET, Gene Ontology
    - Recommended: GWAS, Reactome
    - Supplementary: PDB, PubChem
    """
    
    # Evidence weights for scoring
    WEIGHTS = {
        "disgenet": 0.20,    # Gene-disease associations (high confidence)
        "genetic": 0.20,     # GWAS genetic evidence
        "literature": 0.18,  # PubMed publications
        "uniprot": 0.12,     # UniProt disease annotations
        "go": 0.10,          # Gene Ontology functional relevance
        "pathway": 0.08,     # Reactome pathway context
        "structural": 0.07,  # PDB structural availability
        "druggability": 0.05 # PubChem druggability
    }
    
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
            if target.overall_score > 0.1:  # Filter out very low scoring targets
                targets.append(target)
        
        # Sort by overall score
        targets.sort(key=lambda x: x.overall_score, reverse=True)
        
        return targets
    
    def _aggregate_evidence(self, state: AgentState) -> dict:
        """Aggregate evidence from all search results by protein."""
        evidence = defaultdict(lambda: {
            "disgenet": [],
            "genetic": [],
            "literature": [],
            "uniprot": [],
            "go": [],
            "pathway": [],
            "structural": [],
            "druggability": [],
            "opentargets": [],
            "sources": set(),
            "findings": [],
            "names": set(),
            "pathways": set(),
            "go_terms": set()
        })
        
        # =====================================================================
        # CORE DATABASES
        # =====================================================================
        
        # Process DisGeNET results (gene-disease associations)
        for result in state.disgenet_results:
            gene = result.metadata.get("gene_symbol", "").upper()
            if gene:
                evidence[gene]["disgenet"].append(result.relevance_score)
                evidence[gene]["sources"].add("DisGeNET")
                
                score = result.metadata.get("disgenet_score", "N/A")
                n_pubs = result.metadata.get("n_publications", 0)
                evidence[gene]["findings"].append(
                    f"DisGeNET: disease association score={score}, {n_pubs} publications"
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
                    
                    finding_text = f"PubMed: {result.title[:80]}..."
                    if year:
                        finding_text += f" ({year})"
                    if pub_types:
                        finding_text += f" [{pub_types[0] if pub_types else 'Article'}]"
                    
                    evidence[protein_upper]["findings"].append(finding_text)
        
        # Process UniProt results
        for result in state.uniprot_results:
            gene = result.metadata.get("gene", "").upper()
            if gene:
                evidence[gene]["uniprot"].append(result.relevance_score)
                evidence[gene]["sources"].add("UniProt")
                evidence[gene]["names"].add(result.title)
                if result.metadata.get("function"):
                    evidence[gene]["findings"].append(
                        f"UniProt function: {result.metadata['function'][:150]}..."
                    )
        
        # Process Gene Ontology results
        for result in state.go_results:
            gene = result.metadata.get("gene_symbol", "").upper()
            if gene:
                evidence[gene]["go"].append(result.relevance_score)
                evidence[gene]["sources"].add("Gene Ontology")
                
                # Add GO terms
                bps = result.metadata.get("biological_processes", [])
                mfs = result.metadata.get("molecular_functions", [])
                for term in bps[:5] + mfs[:5]:
                    evidence[gene]["go_terms"].add(term)
                
                # Add mechanism matches as findings
                matches = result.metadata.get("mechanism_matches", [])
                if matches:
                    evidence[gene]["findings"].append(
                        f"GO mechanisms: {', '.join(matches[:3])}"
                    )
        
        # =====================================================================
        # STRONGLY RECOMMENDED DATABASES
        # =====================================================================
        
        # Process GWAS results for genetic evidence
        for result in state.gwas_results:
            gene = result.metadata.get("gene", "").upper()
            if gene and gene != "UNKNOWN":
                evidence[gene]["genetic"].append(result.relevance_score)
                evidence[gene]["sources"].add("GWAS Catalog")
                evidence[gene]["findings"].append(
                    f"GWAS: genetic association (p={result.metadata.get('pvalue', 'N/A')})"
                )
        
        # Process Reactome pathway results
        for result in state.reactome_results:
            pathway_name = result.metadata.get("pathway_name", "")
            genes_in_pathway = result.metadata.get("genes_in_pathway", [])
            
            for gene in genes_in_pathway:
                gene_upper = gene.upper()
                evidence[gene_upper]["pathway"].append(result.relevance_score)
                evidence[gene_upper]["sources"].add("Reactome")
                evidence[gene_upper]["pathways"].add(pathway_name)
        
        # =====================================================================
        # SUPPLEMENTARY DATABASES
        # =====================================================================
        
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
        
        # =====================================================================
        # OPENTARGETS MCP - COMPREHENSIVE MULTI-SOURCE EVIDENCE
        # =====================================================================
        
        # Process OpenTargets results (comprehensive evidence)
        for result in state.opentargets_results:
            gene = result.metadata.get("gene_symbol", "").upper()
            if gene:
                # OpenTargets provides a comprehensive overall score
                overall = result.metadata.get("overall_score", result.relevance_score)
                evidence[gene]["opentargets"].append(overall)
                evidence[gene]["sources"].add("OpenTargets")
                
                # Also incorporate specific datatype scores
                genetic_ot = result.metadata.get("genetic_score", 0)
                literature_ot = result.metadata.get("literature_score", 0)
                pathways_ot = result.metadata.get("pathways_score", 0)
                animal_models = result.metadata.get("animal_models_score", 0)
                known_drugs = result.metadata.get("known_drugs_score", 0)
                
                # Boost other evidence categories with OpenTargets data
                if genetic_ot > 0:
                    evidence[gene]["genetic"].append(genetic_ot)
                if literature_ot > 0:
                    evidence[gene]["literature"].append(literature_ot)
                if pathways_ot > 0:
                    evidence[gene]["pathway"].append(pathways_ot)
                
                # Add comprehensive finding
                datatype_scores = result.metadata.get("datatype_scores", {})
                if datatype_scores:
                    top_datatypes = sorted(datatype_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                    finding_text = f"OpenTargets: overall={overall:.2f}, top evidence: " + \
                                   ", ".join([f"{dt}={sc:.2f}" for dt, sc in top_datatypes])
                    evidence[gene]["findings"].append(finding_text)
                
                # Add known drugs info if available
                if known_drugs > 0.5:
                    evidence[gene]["findings"].append(
                        f"Known drug target (OpenTargets known_drug score={known_drugs:.2f})"
                    )
        
        return evidence
    
    def _create_target(self, protein_id: str, evidence: dict) -> ProteinTarget:
        """Create a ProteinTarget from aggregated evidence."""
        # Calculate average scores for each category with confidence boosting
        disgenet_score = self._calculate_score(evidence["disgenet"])
        genetic_score = self._calculate_score(evidence["genetic"])
        literature_score = self._calculate_score(evidence["literature"])
        uniprot_score = self._calculate_score(evidence["uniprot"])
        go_score = self._calculate_score(evidence["go"])
        pathway_score = self._calculate_score(evidence["pathway"])
        structural_score = self._calculate_score(evidence["structural"])
        druggability_score = self._calculate_score(evidence["druggability"])
        opentargets_score = self._calculate_score(evidence["opentargets"])
        
        # Get protein name (use first name found or the ID)
        protein_name = list(evidence["names"])[0] if evidence["names"] else protein_id
        
        return ProteinTarget(
            protein_id=protein_id,
            protein_name=protein_name,
            gene_symbol=protein_id,
            # Traditional scores (mapped to new schema)
            genetic_score=genetic_score,
            literature_score=literature_score,
            structural_score=structural_score,
            druggability_score=druggability_score,
            # New evidence scores
            disgenet_score=disgenet_score,
            go_score=go_score,
            pathway_score=pathway_score,
            opentargets_score=opentargets_score,
            # Metadata
            evidence_sources=list(evidence["sources"]),
            key_findings=list(evidence["findings"])[:8],  # Top 8 findings
            related_pathways=list(evidence["pathways"])[:5],
            go_terms=list(evidence["go_terms"])[:10]
        )
    
    def _calculate_score(self, scores: list[float]) -> float:
        """Calculate average score with boosting for multiple evidence pieces."""
        if not scores:
            return 0.0
        
        # Base average
        avg = sum(scores) / len(scores)
        
        # Boost score for multiple pieces of evidence (more confidence)
        # Each additional piece adds 0.03, max boost of 0.15
        confidence_boost = min((len(scores) - 1) * 0.03, 0.15)
        
        return min(avg + confidence_boost, 1.0)


def create_ranker() -> TargetRanker:
    """Factory function to create target ranker."""
    return TargetRanker()
