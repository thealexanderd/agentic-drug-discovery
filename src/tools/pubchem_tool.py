"""PubChem search tool for chemical compound information."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import SearchResult


class PubChemTool:
    """Tool for searching PubChem for compound and target information."""
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    def __init__(self):
        self.session = requests.Session()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, proteins: list[str]) -> list[SearchResult]:
        """
        Search PubChem for compounds targeting specific proteins.
        
        Args:
            proteins: List of protein/gene names to search
            
        Returns:
            List of SearchResult objects with compound information
        """
        if not proteins:
            return []
        
        results = []
        
        # Search for compounds targeting each protein
        for protein in proteins[:10]:
            try:
                # Search for compounds associated with the protein target
                response = self.session.get(
                    f"{self.BASE_URL}/compound/name/{protein}/cids/JSON",
                    params={"name_type": "word"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    cids = data.get("IdentifierList", {}).get("CID", [])[:5]
                    
                    for cid in cids:
                        # Get compound details
                        compound_info = self._get_compound_info(cid)
                        
                        if compound_info:
                            results.append(SearchResult(
                                source="pubchem",
                                result_id=str(cid),
                                title=f"{compound_info['name']} (CID: {cid})",
                                relevance_score=0.6,  # Default relevance
                                metadata={
                                    "cid": cid,
                                    "protein_target": protein,
                                    "molecular_formula": compound_info.get("formula", ""),
                                    "molecular_weight": compound_info.get("weight", ""),
                                }
                            ))
                
            except Exception as e:
                print(f"PubChem search error for {protein}: {e}")
                continue
        
        return results
    
    def _get_compound_info(self, cid: int) -> dict:
        """Get detailed information for a compound."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IUPACName/JSON",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
                
                return {
                    "name": props.get("IUPACName", f"Compound {cid}"),
                    "formula": props.get("MolecularFormula", ""),
                    "weight": props.get("MolecularWeight", ""),
                }
        except Exception:
            pass
        
        return {"name": f"Compound {cid}"}


def create_pubchem_tool() -> PubChemTool:
    """Factory function to create PubChem tool."""
    return PubChemTool()
