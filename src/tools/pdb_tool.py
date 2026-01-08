"""PDB (Protein Data Bank) search tool for structural data."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import SearchResult


class PDBTool:
    """Tool for searching Protein Data Bank for structural data."""
    
    SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
    
    def __init__(self):
        self.session = requests.Session()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, proteins: list[str]) -> list[SearchResult]:
        """
        Search PDB for structural data on proteins.
        
        Args:
            proteins: List of protein/gene names to search
            
        Returns:
            List of SearchResult objects with PDB structures
        """
        if not proteins:
            return []
        
        results = []
        
        # Search for each protein (limit to avoid too many requests)
        for protein in proteins[:10]:
            try:
                query = {
                    "query": {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "rcsb_entity_source_organism.rcsb_gene_name.value",
                            "operator": "exact_match",
                            "value": protein
                        }
                    },
                    "return_type": "entry",
                    "request_options": {
                        "return_all_hits": False,
                        "results_content_type": ["experimental"],
                        "sort": [{"sort_by": "score", "direction": "desc"}]
                    }
                }
                
                response = self.session.post(
                    self.SEARCH_URL,
                    json=query,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for hit in data.get("result_set", [])[:5]:  # Top 5 structures per protein
                        pdb_id = hit.get("identifier", "")
                        score = hit.get("score", 0)
                        
                        # Normalize score to 0-1
                        relevance = min(score / 100.0, 1.0)
                        
                        results.append(SearchResult(
                            source="pdb",
                            result_id=pdb_id,
                            title=f"Structure {pdb_id} for {protein}",
                            relevance_score=relevance,
                            metadata={
                                "pdb_id": pdb_id,
                                "protein": protein,
                                "structure_url": f"https://www.rcsb.org/structure/{pdb_id}"
                            }
                        ))
                
            except Exception as e:
                print(f"PDB search error for {protein}: {e}")
                continue
        
        return results


def create_pdb_tool() -> PDBTool:
    """Factory function to create PDB tool."""
    return PDBTool()
