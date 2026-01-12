"""DisGeNET tool for gene-disease associations."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import SearchResult


class DisGeNETTool:
    """Tool for searching DisGeNET for gene-disease associations.
    
    DisGeNET provides curated gene-disease associations with evidence scores,
    making it extremely valuable for target prioritization.
    """
    
    BASE_URL = "https://www.disgenet.org/api"
    
    def __init__(self):
        self.session = requests.Session()
        # DisGeNET requires an API key for authenticated access
        # Free tier allows limited queries
        self.api_key = getattr(settings, 'disgenet_api_key', None)
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, disease: str) -> list[SearchResult]:
        """
        Search DisGeNET for genes associated with a disease.
        
        Args:
            disease: Disease name or identifier
            
        Returns:
            List of SearchResult objects with gene-disease associations
        """
        results = []
        
        try:
            # First, search for the disease to get its CUI or ID
            disease_results = self._search_disease(disease)
            
            if not disease_results:
                print(f"No disease match found in DisGeNET for: {disease}")
                return []
            
            # Get top disease match
            disease_id = disease_results[0].get("diseaseId", "")
            disease_name = disease_results[0].get("diseaseName", disease)
            
            print(f"Found disease in DisGeNET: {disease_name} ({disease_id})")
            
            # Get gene-disease associations for this disease
            associations = self._get_disease_genes(disease_id)
            
            for assoc in associations[:50]:  # Limit to top 50
                gene_symbol = assoc.get("geneSymbol", "")
                gene_id = assoc.get("geneId", "")
                score = assoc.get("score", 0.0)  # DisGeNET score (0-1)
                evidence_index = assoc.get("ei", 0.0)  # Evidence index
                
                # Number of publications and sources
                n_pmids = assoc.get("nPmids", 0)
                n_snps = assoc.get("nSnps", 0)
                
                # Association type
                assoc_type = assoc.get("associationType", "")
                
                # Calculate relevance score based on DisGeNET metrics
                relevance = self._calculate_relevance(score, evidence_index, n_pmids, n_snps)
                
                if gene_symbol:
                    results.append(SearchResult(
                        source="disgenet",
                        result_id=f"{disease_id}_{gene_id}",
                        title=f"{gene_symbol} - {disease_name}",
                        relevance_score=relevance,
                        metadata={
                            "gene_symbol": gene_symbol,
                            "gene_id": gene_id,
                            "disease_id": disease_id,
                            "disease_name": disease_name,
                            "disgenet_score": score,
                            "evidence_index": evidence_index,
                            "n_publications": n_pmids,
                            "n_snps": n_snps,
                            "association_type": assoc_type,
                            "source_databases": assoc.get("sources", [])
                        }
                    ))
            
            print(f"Found {len(results)} gene-disease associations in DisGeNET")
            return results
            
        except Exception as e:
            print(f"DisGeNET search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def search_by_genes(self, genes: list[str], disease: str = "") -> list[SearchResult]:
        """
        Search DisGeNET for disease associations of specific genes.
        
        Args:
            genes: List of gene symbols to search
            disease: Optional disease context for filtering
            
        Returns:
            List of SearchResult objects
        """
        results = []
        
        try:
            for gene in genes[:20]:  # Limit to 20 genes
                gene_assocs = self._get_gene_diseases(gene)
                
                for assoc in gene_assocs[:10]:  # Top 10 diseases per gene
                    disease_name = assoc.get("diseaseName", "")
                    
                    # Filter by disease if provided
                    if disease and disease.lower() not in disease_name.lower():
                        continue
                    
                    score = assoc.get("score", 0.0)
                    evidence_index = assoc.get("ei", 0.0)
                    n_pmids = assoc.get("nPmids", 0)
                    
                    relevance = self._calculate_relevance(score, evidence_index, n_pmids, 0)
                    
                    results.append(SearchResult(
                        source="disgenet",
                        result_id=f"{gene}_{assoc.get('diseaseId', '')}",
                        title=f"{gene} - {disease_name}",
                        relevance_score=relevance,
                        metadata={
                            "gene_symbol": gene,
                            "disease_id": assoc.get("diseaseId", ""),
                            "disease_name": disease_name,
                            "disgenet_score": score,
                            "evidence_index": evidence_index,
                            "n_publications": n_pmids
                        }
                    ))
            
            return results
            
        except Exception as e:
            print(f"DisGeNET gene search error: {e}")
            return []
    
    def _search_disease(self, disease: str) -> list[dict]:
        """Search for a disease in DisGeNET."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/disease/search",
                params={"query": disease, "limit": 5},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                # Fallback: try using GDA endpoint with disease name
                return self._search_disease_fallback(disease)
                
        except Exception:
            return self._search_disease_fallback(disease)
    
    def _search_disease_fallback(self, disease: str) -> list[dict]:
        """Fallback disease search using the public gene-disease API."""
        try:
            # Use the open targets genetics API as fallback
            response = self.session.get(
                "https://www.disgenet.org/static/disgenet_ap1/files/downloads/all_gene_disease_pmid_associations.tsv.gz",
                timeout=30
            )
            # This is a large file, so we'll return empty and rely on other methods
            return []
        except Exception:
            return []
    
    def _get_disease_genes(self, disease_id: str) -> list[dict]:
        """Get genes associated with a disease."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/gda/disease/{disease_id}",
                params={"limit": 100, "min_score": 0.1},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
            
        except Exception:
            return []
    
    def _get_gene_diseases(self, gene: str) -> list[dict]:
        """Get diseases associated with a gene."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/gda/gene/{gene}",
                params={"limit": 50},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
            
        except Exception:
            return []
    
    def _calculate_relevance(self, score: float, evidence_index: float, n_pmids: int, n_snps: int) -> float:
        """Calculate relevance score from DisGeNET metrics."""
        # Base is the DisGeNET score (already 0-1)
        relevance = score * 0.6
        
        # Boost for evidence index
        relevance += min(evidence_index, 1.0) * 0.2
        
        # Boost for number of publications (capped at 20)
        pub_boost = min(n_pmids / 20, 1.0) * 0.1
        relevance += pub_boost
        
        # Boost for SNP associations (genetic evidence)
        if n_snps > 0:
            snp_boost = min(n_snps / 10, 1.0) * 0.1
            relevance += snp_boost
        
        return min(relevance, 1.0)


def create_disgenet_tool() -> DisGeNETTool:
    """Factory function to create DisGeNET tool."""
    return DisGeNETTool()
