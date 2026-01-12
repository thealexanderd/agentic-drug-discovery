"""Reactome pathway tool for biological pathway context."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import SearchResult


class ReactomeTool:
    """Tool for searching Reactome pathway database.
    
    Reactome provides curated biological pathway information. This is crucial for:
    1. Understanding the mechanistic context of potential targets
    2. Clustering targets by biological pathways
    3. Identifying pathway-level therapeutic opportunities
    """
    
    BASE_URL = "https://reactome.org/ContentService"
    ANALYSIS_URL = "https://reactome.org/AnalysisService"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "text/plain"
        })
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, genes: list[str], disease_context: str = "") -> list[SearchResult]:
        """
        Get Reactome pathway information for a list of genes.
        
        Args:
            genes: List of gene symbols to search
            disease_context: Disease context for pathway relevance
            
        Returns:
            List of SearchResult objects with pathway information
        """
        results = []
        pathway_genes = {}  # pathway_id -> genes in that pathway
        
        # Get pathways for each gene
        for gene in genes[:30]:  # Limit to 30 genes
            try:
                pathways = self._get_gene_pathways(gene)
                
                for pathway in pathways:
                    pathway_id = pathway.get("stId", "")
                    pathway_name = pathway.get("displayName", "")
                    
                    if pathway_id not in pathway_genes:
                        pathway_genes[pathway_id] = {
                            "name": pathway_name,
                            "genes": [],
                            "is_disease": pathway.get("isInDisease", False)
                        }
                    pathway_genes[pathway_id]["genes"].append(gene)
                    
            except Exception as e:
                print(f"Error getting pathways for {gene}: {e}")
                continue
        
        # Create results for pathways with multiple genes (more interesting)
        for pathway_id, data in pathway_genes.items():
            num_genes = len(data["genes"])
            
            # Calculate relevance based on number of genes and disease relevance
            relevance = self._calculate_relevance(num_genes, data["is_disease"], data["name"], disease_context)
            
            results.append(SearchResult(
                source="reactome",
                result_id=pathway_id,
                title=data["name"],
                relevance_score=relevance,
                metadata={
                    "pathway_id": pathway_id,
                    "pathway_name": data["name"],
                    "genes_in_pathway": data["genes"],
                    "gene_count": num_genes,
                    "is_disease_pathway": data["is_disease"],
                    "url": f"https://reactome.org/content/detail/{pathway_id}"
                }
            ))
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        print(f"Found {len(results)} Reactome pathways for input genes")
        return results[:50]  # Top 50 pathways
    
    def search_disease_pathways(self, disease: str) -> list[SearchResult]:
        """
        Search for pathways directly associated with a disease.
        
        Args:
            disease: Disease name
            
        Returns:
            List of SearchResult objects with disease-associated pathways
        """
        results = []
        
        try:
            # Search Reactome for disease-related content
            response = self.session.get(
                f"{self.BASE_URL}/search/query",
                params={
                    "query": disease,
                    "species": "Homo sapiens",
                    "types": "Pathway",
                    "cluster": True
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            entries = data.get("results", [])
            
            for entry in entries[:30]:
                pathway_id = entry.get("stId", "")
                pathway_name = entry.get("name", "")
                
                results.append(SearchResult(
                    source="reactome",
                    result_id=pathway_id,
                    title=pathway_name,
                    relevance_score=0.8,  # High relevance for direct disease match
                    metadata={
                        "pathway_id": pathway_id,
                        "pathway_name": pathway_name,
                        "species": entry.get("species", ""),
                        "url": f"https://reactome.org/content/detail/{pathway_id}"
                    }
                ))
                
        except Exception as e:
            print(f"Error searching disease pathways: {e}")
        
        return results
    
    def get_pathway_genes(self, pathway_id: str) -> list[str]:
        """
        Get all genes/proteins in a pathway.
        
        Args:
            pathway_id: Reactome pathway stable ID
            
        Returns:
            List of gene symbols
        """
        genes = []
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/data/participants/{pathway_id}/participatingPhysicalEntities",
                timeout=30
            )
            
            if response.status_code != 200:
                return []
            
            entities = response.json()
            
            for entity in entities:
                # Extract gene name from entity
                gene_name = entity.get("geneName", [])
                if gene_name:
                    genes.extend(gene_name if isinstance(gene_name, list) else [gene_name])
                    
        except Exception as e:
            print(f"Error getting pathway genes: {e}")
        
        return list(set(genes))
    
    def analyze_gene_list(self, genes: list[str]) -> dict:
        """
        Perform pathway enrichment analysis on a list of genes.
        
        Args:
            genes: List of gene symbols
            
        Returns:
            Enrichment analysis results
        """
        try:
            # Submit gene list for analysis
            gene_string = "\n".join(genes)
            
            response = self.session.post(
                f"{self.ANALYSIS_URL}/identifiers/projection",
                params={
                    "interactors": False,
                    "pageSize": 50,
                    "page": 1,
                    "sortBy": "ENTITIES_FDR",
                    "order": "ASC",
                    "resource": "TOTAL",
                    "pValue": 0.05,
                    "includeDisease": True
                },
                data=gene_string,
                timeout=60
            )
            
            if response.status_code != 200:
                return {"error": "Analysis failed", "pathways": []}
            
            data = response.json()
            
            # Parse results
            pathways = []
            for pathway in data.get("pathways", []):
                pathways.append({
                    "pathway_id": pathway.get("stId", ""),
                    "name": pathway.get("name", ""),
                    "p_value": pathway.get("entities", {}).get("pValue", 1.0),
                    "fdr": pathway.get("entities", {}).get("fdr", 1.0),
                    "found_genes": pathway.get("entities", {}).get("found", 0),
                    "total_genes": pathway.get("entities", {}).get("total", 0),
                    "is_disease": pathway.get("inDisease", False)
                })
            
            return {
                "summary": data.get("summary", {}),
                "pathways": pathways
            }
            
        except Exception as e:
            print(f"Error in pathway analysis: {e}")
            return {"error": str(e), "pathways": []}
    
    def _get_gene_pathways(self, gene: str) -> list[dict]:
        """Get pathways containing a gene."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/data/query/{gene}/pathways",
                timeout=30
            )
            
            if response.status_code != 200:
                return []
            
            return response.json()
            
        except Exception:
            return []
    
    def _calculate_relevance(self, num_genes: int, is_disease: bool, 
                             pathway_name: str, disease_context: str) -> float:
        """Calculate pathway relevance score."""
        score = 0.3  # Base score
        
        # Boost for multiple genes in pathway (suggests coherent mechanism)
        gene_boost = min(num_genes / 5, 1.0) * 0.3
        score += gene_boost
        
        # Boost for disease-associated pathways
        if is_disease:
            score += 0.2
        
        # Check for disease-relevant terms in pathway name
        disease_lower = disease_context.lower()
        pathway_lower = pathway_name.lower()
        
        # General therapeutic pathway keywords
        therapeutic_keywords = [
            "signaling", "immune", "inflammation", "apoptosis", "cell cycle",
            "metabolism", "receptor", "kinase", "cytokine", "interleukin"
        ]
        
        for keyword in therapeutic_keywords:
            if keyword in pathway_lower:
                score += 0.05
        
        # Disease-specific matches
        if disease_lower:
            disease_words = disease_lower.split()
            for word in disease_words:
                if len(word) > 3 and word in pathway_lower:
                    score += 0.1
                    break
        
        return min(score, 1.0)


def create_reactome_tool() -> ReactomeTool:
    """Factory function to create Reactome tool."""
    return ReactomeTool()
