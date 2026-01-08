"""PubMed search tool using NCBI Entrez."""

import time
from typing import Any
from Bio import Entrez
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import SearchResult


class PubMedTool:
    """Tool for searching PubMed/NCBI literature database."""
    
    def __init__(self):
        Entrez.email = settings.ncbi_email
        if settings.ncbi_api_key:
            Entrez.api_key = settings.ncbi_api_key
        self.max_results = settings.max_pubmed_results
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, disease: str, protein_context: str = "") -> list[SearchResult]:
        """
        Search PubMed for articles related to disease and optionally protein.
        
        Args:
            disease: Disease name to search
            protein_context: Optional protein/gene context to narrow search
            
        Returns:
            List of SearchResult objects with PubMed articles
        """
        # Build search query
        query_parts = [f'"{disease}"[Title/Abstract]']
        
        if protein_context:
            query_parts.append(f'"{protein_context}"[Title/Abstract]')
        
        # Add filters for relevance
        query_parts.extend([
            '"humans"[MeSH Terms]',
            '"therapeutic target"[Text Word] OR "drug target"[Text Word] OR "protein target"[Text Word]'
        ])
        
        query = " AND ".join(query_parts)
        
        try:
            # Search PubMed
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=self.max_results,
                sort="relevance",
                usehistory="y"
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            
            id_list = search_results["IdList"]
            
            if not id_list:
                return []
            
            # Fetch article details
            time.sleep(0.34)  # Rate limiting
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=id_list,
                rettype="medline",
                retmode="text"
            )
            articles = fetch_handle.read()
            fetch_handle.close()
            
            # Parse results
            results = self._parse_medline(articles, id_list)
            
            return results
            
        except Exception as e:
            print(f"PubMed search error: {e}")
            return []
    
    def _parse_medline(self, medline_text: str, pmids: list[str]) -> list[SearchResult]:
        """Parse MEDLINE format text into SearchResult objects."""
        results = []
        articles = medline_text.split("\n\n")
        
        for idx, article in enumerate(articles):
            if not article.strip() or idx >= len(pmids):
                continue
                
            title = ""
            abstract = ""
            
            lines = article.split("\n")
            for line in lines:
                if line.startswith("TI  -"):
                    title = line[5:].strip()
                elif line.startswith("AB  -"):
                    abstract = line[5:].strip()
            
            if title:
                # Calculate simple relevance score based on keyword presence
                relevance = self._calculate_relevance(title, abstract)
                
                results.append(SearchResult(
                    source="pubmed",
                    result_id=pmids[idx],
                    title=title,
                    relevance_score=relevance,
                    metadata={
                        "abstract": abstract[:500],  # Truncate for brevity
                        "pmid": pmids[idx]
                    }
                ))

        print(results)
        # exit()
        
        return results
    
    def _calculate_relevance(self, title: str, abstract: str) -> float:
        """Simple relevance scoring based on keyword presence."""
        text = f"{title} {abstract}".lower()
        
        high_value_terms = ["therapeutic target", "drug target", "clinical trial", "treatment"]
        medium_value_terms = ["protein", "gene", "pathway", "mechanism"]
        
        score = 0.5  # Base score
        
        for term in high_value_terms:
            if term in text:
                score += 0.15
        
        for term in medium_value_terms:
            if term in text:
                score += 0.05
        
        return min(score, 1.0)


def create_pubmed_tool() -> PubMedTool:
    """Factory function to create PubMed tool."""
    return PubMedTool()
