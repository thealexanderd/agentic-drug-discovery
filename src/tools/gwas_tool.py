"""GWAS Catalog search tool for genetic associations."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import SearchResult


class GWASTool:
    """Tool for searching GWAS Catalog for genetic associations."""
    
    BASE_URL = "https://www.ebi.ac.uk/gwas/rest/api"
    
    def __init__(self):
        self.max_results = settings.max_gwas_results
        self.session = requests.Session()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, disease: str) -> list[SearchResult]:
        """
        Search GWAS Catalog for genetic associations with disease.
        
        Args:
            disease: Disease name or trait
            
        Returns:
            List of SearchResult objects with GWAS associations
        """
        try:
            # Search for associations by trait
            response = self.session.get(
                f"{self.BASE_URL}/efoTraits/search/findByEfoTrait",
                params={"trait": disease},
                headers={"Accept": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            traits = response.json().get("_embedded", {}).get("efoTraits", [])
            
            if not traits:
                return []
            
            # Get associations for the most relevant trait
            trait_uri = traits[0]["_links"]["self"]["href"]
            associations = self._get_associations(trait_uri)
            
            results = []
            for assoc in associations[:self.max_results]:
                # Extract gene information
                genes = assoc.get("loci", [{}])[0].get("authorReportedGenes", [{}])
                gene_name = genes[0].get("geneName", "Unknown") if genes else "Unknown"
                
                # Calculate relevance based on p-value
                pvalue = assoc.get("pvalue", 1.0)
                relevance = self._pvalue_to_score(pvalue)
                
                results.append(SearchResult(
                    source="gwas",
                    result_id=assoc.get("id", ""),
                    title=f"Association: {gene_name} - {disease}",
                    relevance_score=relevance,
                    metadata={
                        "gene": gene_name,
                        "pvalue": pvalue,
                        "risk_allele": assoc.get("strongestAllele", ""),
                        "study": assoc.get("study", {}).get("publicationInfo", {}).get("pubmedId", "")
                    }
                ))
            
            return results
            
        except Exception as e:
            print(f"GWAS search error: {e}")
            return []
    
    def _get_associations(self, trait_uri: str) -> list[dict]:
        """Fetch associations for a given trait."""
        try:
            response = self.session.get(
                f"{trait_uri}/associations",
                headers={"Accept": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("_embedded", {}).get("associations", [])
        except Exception:
            return []
    
    def _pvalue_to_score(self, pvalue: float) -> float:
        """Convert p-value to relevance score (0-1)."""
        # Genome-wide significance threshold is 5e-8
        if pvalue <= 5e-8:
            score = 1.0
        elif pvalue <= 1e-5:
            score = 0.8
        elif pvalue <= 1e-3:
            score = 0.6
        else:
            score = 0.3
        return score


def create_gwas_tool() -> GWASTool:
    """Factory function to create GWAS tool."""
    return GWASTool()
