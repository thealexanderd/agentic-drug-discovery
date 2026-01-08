"""UniProt search tool for protein information."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import SearchResult


class UniProtTool:
    """Tool for searching UniProt protein database."""
    
    BASE_URL = "https://rest.uniprot.org/uniprotkb"
    
    def __init__(self):
        self.session = requests.Session()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, disease: str, proteins: list[str] = None) -> list[SearchResult]:
        """
        Search UniProt for proteins associated with disease.
        
        Args:
            disease: Disease name
            proteins: Optional list of specific proteins/genes to search
            
        Returns:
            List of SearchResult objects with UniProt entries
        """
        try:
            # Build query
            if proteins:
                # Search for specific proteins
                gene_query = " OR ".join([f"gene:{p}" for p in proteins[:10]])
                query = f"({gene_query}) AND (disease:{disease}) AND (reviewed:true)"
            else:
                # General disease search
                query = f"(disease:{disease}) AND (reviewed:true)"
            
            response = self.session.get(
                f"{self.BASE_URL}/search",
                params={
                    "query": query,
                    "format": "json",
                    "size": 50
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for entry in data.get("results", []):
                protein_name = entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "Unknown")
                accession = entry.get("primaryAccession", "")
                genes = entry.get("genes", [])
                gene_name = genes[0].get("geneName", {}).get("value", "") if genes else ""
                
                # Calculate relevance based on evidence and disease annotation
                relevance = self._calculate_relevance(entry, disease)
                
                # Extract key information
                function = entry.get("comments", [])
                function_text = ""
                for comment in function:
                    if comment.get("commentType") == "FUNCTION":
                        function_text = comment.get("texts", [{}])[0].get("value", "")[:200]
                        break
                
                results.append(SearchResult(
                    source="uniprot",
                    result_id=accession,
                    title=f"{protein_name} ({gene_name})",
                    relevance_score=relevance,
                    metadata={
                        "accession": accession,
                        "gene": gene_name,
                        "function": function_text,
                        "organism": entry.get("organism", {}).get("scientificName", "")
                    }
                ))
            
            return results
            
        except Exception as e:
            print(f"UniProt search error: {e}")
            return []
    
    def _calculate_relevance(self, entry: dict, disease: str) -> float:
        """Calculate relevance score based on entry quality and disease involvement."""
        score = 0.5  # Base score for reviewed entries
        
        # Check for disease annotations
        comments = entry.get("comments", [])
        for comment in comments:
            if comment.get("commentType") == "DISEASE":
                if disease.lower() in str(comment).lower():
                    score += 0.3
                else:
                    score += 0.1
        
        # Check for drug/ligand binding
        if any(feat.get("type") == "BINDING" for feat in entry.get("features", [])):
            score += 0.1
        
        # Check for 3D structure
        if entry.get("uniProtKBCrossReferences", []):
            for xref in entry.get("uniProtKBCrossReferences", []):
                if xref.get("database") == "PDB":
                    score += 0.1
                    break
        
        return min(score, 1.0)


def create_uniprot_tool() -> UniProtTool:
    """Factory function to create UniProt tool."""
    return UniProtTool()
