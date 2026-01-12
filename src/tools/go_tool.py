"""Gene Ontology tool using QuickGO API."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import SearchResult


class GOTool:
    """Tool for searching Gene Ontology via QuickGO API.
    
    Gene Ontology provides biological process, molecular function, and cellular
    component annotations for genes/proteins. This is crucial for validating
    whether a protein makes biological sense as a target for a disease.
    """
    
    QUICKGO_URL = "https://www.ebi.ac.uk/QuickGO/services"
    UNIPROT_URL = "https://rest.uniprot.org/uniprotkb"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, genes: list[str], disease_context: str = "") -> list[SearchResult]:
        """
        Get Gene Ontology annotations for a list of genes.
        
        Args:
            genes: List of gene symbols to search
            disease_context: Disease context to help filter relevant GO terms
            
        Returns:
            List of SearchResult objects with GO annotations
        """
        results = []
        
        # Keywords related to disease mechanisms (for relevance scoring)
        mechanism_keywords = self._get_mechanism_keywords(disease_context)
        
        for gene in genes[:30]:  # Limit to 30 genes
            try:
                # Get GO annotations for this gene via UniProt
                annotations = self._get_go_annotations(gene)
                
                if not annotations:
                    continue
                
                # Group by GO aspect (Biological Process, Molecular Function, Cellular Component)
                bp_terms = []  # Biological Process
                mf_terms = []  # Molecular Function
                cc_terms = []  # Cellular Component
                
                for ann in annotations:
                    go_id = ann.get("id", "")
                    go_name = ann.get("term", "")
                    aspect = ann.get("aspect", "")
                    
                    if aspect == "P":
                        bp_terms.append({"id": go_id, "name": go_name})
                    elif aspect == "F":
                        mf_terms.append({"id": go_id, "name": go_name})
                    elif aspect == "C":
                        cc_terms.append({"id": go_id, "name": go_name})
                
                # Calculate relevance based on GO terms matching disease mechanisms
                relevance = self._calculate_relevance(bp_terms, mf_terms, mechanism_keywords)
                
                # Create a summary result for this gene
                results.append(SearchResult(
                    source="go",
                    result_id=f"GO_{gene}",
                    title=f"GO Annotations: {gene}",
                    relevance_score=relevance,
                    metadata={
                        "gene_symbol": gene,
                        "biological_processes": [t["name"] for t in bp_terms[:10]],
                        "molecular_functions": [t["name"] for t in mf_terms[:10]],
                        "cellular_components": [t["name"] for t in cc_terms[:5]],
                        "total_annotations": len(annotations),
                        "mechanism_matches": self._get_mechanism_matches(bp_terms + mf_terms, mechanism_keywords)
                    }
                ))
                
            except Exception as e:
                print(f"Error getting GO annotations for {gene}: {e}")
                continue
        
        print(f"Retrieved GO annotations for {len(results)} genes")
        return results
    
    def search_by_go_term(self, go_term: str) -> list[SearchResult]:
        """
        Search for genes annotated with a specific GO term.
        
        Args:
            go_term: GO term ID or name
            
        Returns:
            List of SearchResult objects with genes
        """
        results = []
        
        try:
            # Search QuickGO for annotations with this term
            response = self.session.get(
                f"{self.QUICKGO_URL}/annotation/search",
                params={
                    "goId": go_term,
                    "taxonId": 9606,  # Human
                    "limit": 100
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                annotations = data.get("results", [])
                
                # Group by gene
                genes = {}
                for ann in annotations:
                    gene_id = ann.get("geneProductId", "")
                    if gene_id not in genes:
                        genes[gene_id] = {
                            "annotations": [],
                            "evidence": []
                        }
                    genes[gene_id]["annotations"].append(ann)
                    genes[gene_id]["evidence"].append(ann.get("evidenceCode", ""))
                
                for gene_id, data in genes.items():
                    results.append(SearchResult(
                        source="go",
                        result_id=f"{go_term}_{gene_id}",
                        title=f"{gene_id} - {go_term}",
                        relevance_score=0.7,  # High relevance for direct GO term matches
                        metadata={
                            "gene_id": gene_id,
                            "go_term": go_term,
                            "annotation_count": len(data["annotations"]),
                            "evidence_codes": list(set(data["evidence"]))
                        }
                    ))
                
        except Exception as e:
            print(f"Error searching GO term {go_term}: {e}")
        
        return results
    
    def validate_target(self, gene: str, disease_mechanisms: list[str]) -> dict:
        """
        Validate whether a gene/protein makes biological sense for a disease.
        
        Args:
            gene: Gene symbol
            disease_mechanisms: List of expected biological mechanisms
            
        Returns:
            Validation result with score and explanation
        """
        annotations = self._get_go_annotations(gene)
        
        if not annotations:
            return {
                "gene": gene,
                "valid": False,
                "score": 0.0,
                "reason": "No GO annotations found"
            }
        
        # Get all GO term names
        go_terms = [ann.get("term", "").lower() for ann in annotations]
        
        # Check for mechanism matches
        matches = []
        for mechanism in disease_mechanisms:
            mechanism_lower = mechanism.lower()
            for term in go_terms:
                if mechanism_lower in term or any(word in term for word in mechanism_lower.split()):
                    matches.append((mechanism, term))
        
        if matches:
            return {
                "gene": gene,
                "valid": True,
                "score": min(len(matches) / len(disease_mechanisms), 1.0),
                "reason": f"Found {len(matches)} mechanism matches",
                "matches": matches[:5]
            }
        else:
            return {
                "gene": gene,
                "valid": True,  # Still valid, just lower confidence
                "score": 0.3,
                "reason": "No direct mechanism matches, but gene is annotated"
            }
    
    def _get_go_annotations(self, gene: str) -> list[dict]:
        """Get GO annotations for a gene from UniProt."""
        try:
            # Search UniProt for the gene
            response = self.session.get(
                f"{self.UNIPROT_URL}/search",
                params={
                    "query": f"gene:{gene} AND organism_id:9606 AND reviewed:true",
                    "format": "json",
                    "size": 1,
                    "fields": "accession,go"
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return []
            
            results = response.json().get("results", [])
            if not results:
                return []
            
            # Extract GO annotations
            entry = results[0]
            go_annotations = []
            
            # Parse GO cross-references
            for xref in entry.get("uniProtKBCrossReferences", []):
                if xref.get("database") == "GO":
                    go_id = xref.get("id", "")
                    properties = {p.get("key"): p.get("value") for p in xref.get("properties", [])}
                    
                    go_annotations.append({
                        "id": go_id,
                        "term": properties.get("GoTerm", ""),
                        "aspect": self._get_aspect(properties.get("GoTerm", "")),
                        "evidence": properties.get("GoEvidenceType", "")
                    })
            
            return go_annotations
            
        except Exception as e:
            print(f"Error getting GO annotations for {gene}: {e}")
            return []
    
    def _get_aspect(self, go_term: str) -> str:
        """Determine GO aspect from term prefix."""
        if go_term.startswith("P:"):
            return "P"  # Biological Process
        elif go_term.startswith("F:"):
            return "F"  # Molecular Function
        elif go_term.startswith("C:"):
            return "C"  # Cellular Component
        return ""
    
    def _get_mechanism_keywords(self, disease_context: str) -> list[str]:
        """Get relevant mechanism keywords based on disease context."""
        # Base keywords applicable to most diseases
        base_keywords = [
            "signaling", "signal transduction", "immune", "inflammation",
            "apoptosis", "cell death", "proliferation", "metabolism",
            "transport", "binding", "catalytic", "kinase", "receptor"
        ]
        
        # Disease-specific keywords
        disease_lower = disease_context.lower()
        
        if "alzheimer" in disease_lower or "neurodegener" in disease_lower:
            base_keywords.extend([
                "amyloid", "tau", "neuronal", "synaptic", "cognitive",
                "phosphorylation", "aggregation", "proteolysis"
            ])
        elif "diabetes" in disease_lower:
            base_keywords.extend([
                "insulin", "glucose", "glycolysis", "pancrea", "beta cell",
                "gluconeogenesis", "lipid metabolism"
            ])
        elif "cancer" in disease_lower or "tumor" in disease_lower:
            base_keywords.extend([
                "cell cycle", "tumor suppressor", "oncogene", "metastasis",
                "angiogenesis", "dna repair", "checkpoint"
            ])
        elif "autoimmune" in disease_lower or "lupus" in disease_lower:
            base_keywords.extend([
                "autoimmunity", "t cell", "b cell", "cytokine", "interferon",
                "complement", "antibody", "lymphocyte"
            ])
        elif "heart" in disease_lower or "cardiac" in disease_lower or "cardiovascular" in disease_lower:
            base_keywords.extend([
                "cardiac", "heart", "vascular", "blood pressure", "atherosclerosis",
                "cholesterol", "lipid", "coagulation"
            ])
        
        return base_keywords
    
    def _calculate_relevance(self, bp_terms: list[dict], mf_terms: list[dict], 
                             mechanism_keywords: list[str]) -> float:
        """Calculate relevance score based on GO term matches."""
        if not bp_terms and not mf_terms:
            return 0.2
        
        all_terms = [t["name"].lower() for t in bp_terms + mf_terms]
        
        # Count mechanism matches
        matches = 0
        for keyword in mechanism_keywords:
            for term in all_terms:
                if keyword.lower() in term:
                    matches += 1
                    break
        
        # Base score for having annotations
        score = 0.3
        
        # Add score for mechanism matches (up to 0.5)
        match_score = min(matches / max(len(mechanism_keywords), 1), 1.0) * 0.5
        score += match_score
        
        # Bonus for having both BP and MF annotations
        if bp_terms and mf_terms:
            score += 0.1
        
        # Bonus for druggability-relevant functions
        druggable_functions = ["kinase", "receptor", "channel", "transporter", "enzyme"]
        for func in druggable_functions:
            if any(func in term.lower() for term in all_terms):
                score += 0.05
                break
        
        return min(score, 1.0)
    
    def _get_mechanism_matches(self, terms: list[dict], keywords: list[str]) -> list[str]:
        """Get list of matched mechanisms."""
        matches = []
        term_names = [t["name"].lower() for t in terms]
        
        for keyword in keywords:
            for term in term_names:
                if keyword.lower() in term:
                    matches.append(keyword)
                    break
        
        return matches[:10]


def create_go_tool() -> GOTool:
    """Factory function to create Gene Ontology tool."""
    return GOTool()
