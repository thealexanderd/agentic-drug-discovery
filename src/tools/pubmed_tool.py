"""PubMed search tool using NCBI Entrez."""

import time
import re
from datetime import datetime
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
        # First, find MeSH terms for the disease
        mesh_terms = self._get_mesh_terms(disease)
        
        # Build search query with multiple strategies
        query_parts = []
        
        # Strategy 1: MeSH terms (most precise)
        if mesh_terms:
            mesh_query = " OR ".join([f'"{term}"[MeSH Terms]' for term in mesh_terms[:3]])
            query_parts.append(f"({mesh_query})")
        
        # Strategy 2: Disease name variations
        disease_variations = self._get_disease_variations(disease)
        disease_query = " OR ".join([f'"{var}"[Title/Abstract]' for var in disease_variations])
        query_parts.append(f"({disease_query})")
        
        # Combine disease queries with OR
        disease_part = " OR ".join(query_parts) if query_parts else f'"{disease}"[Title/Abstract]'
        
        # Build final query
        final_parts = [f"({disease_part})"]
        
        if protein_context:
            final_parts.append(f'("{protein_context}"[Title/Abstract] OR "{protein_context}"[Gene Name])')
        
        # Add filters for relevance and quality
        final_parts.extend([
            '"humans"[MeSH Terms]',
            '("therapeutic target"[Text] OR "drug target"[Text] OR "protein target"[Text] OR "treatment"[Title/Abstract] OR "therapy"[Title/Abstract] OR "pathogenesis"[Title/Abstract])'
        ])
        
        query = " AND ".join(final_parts)
        
        try:
            # Search PubMed
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=self.max_results,
                sort="relevance",
                usehistory="y",
                datetype="pdat",
                reldate=3650  # Last 10 years
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            
            id_list = search_results["IdList"]
            
            if not id_list:
                print(f"No PubMed results for query: {query}")
                return []
            
            print(f"Found {len(id_list)} PubMed articles, fetching details...")
            
            # Fetch article details in XML format for better parsing
            time.sleep(0.34)  # Rate limiting
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=id_list,
                rettype="xml",
                retmode="xml"
            )
            articles = Entrez.read(fetch_handle)
            fetch_handle.close()
            
            # Parse results
            results = self._parse_pubmed_xml(articles, disease)
            
            return results
            
        except Exception as e:
            print(f"PubMed search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_pubmed_xml(self, articles_data: dict, disease: str) -> list[SearchResult]:
        """Parse PubMed XML format into SearchResult objects with full metadata."""
        results = []
        
        for article in articles_data.get('PubmedArticle', []):
            try:
                medline = article.get('MedlineCitation', {})
                pmid = str(medline.get('PMID', ''))
                
                article_data = medline.get('Article', {})
                title = article_data.get('ArticleTitle', '')
                
                # Get full abstract
                abstract_data = article_data.get('Abstract', {})
                abstract_texts = abstract_data.get('AbstractText', [])
                if isinstance(abstract_texts, list):
                    abstract = ' '.join([str(text) for text in abstract_texts])
                else:
                    abstract = str(abstract_texts) if abstract_texts else ''
                
                # Get publication date
                pub_date = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
                year = pub_date.get('Year', '')
                
                # Get publication types
                pub_types = [pt for pt in article_data.get('PublicationType', [])]
                
                # Get MeSH terms
                mesh_headings = medline.get('MeshHeadingList', [])
                mesh_terms = [mh.get('DescriptorName', '') for mh in mesh_headings if mh.get('DescriptorName')]
                
                if title:
                    # Extract proteins/genes mentioned
                    proteins_mentioned = self._extract_proteins(title, abstract)
                    
                    # Calculate relevance score
                    relevance = self._calculate_relevance(
                        title, abstract, pub_types, mesh_terms, year, disease
                    )
                    
                    results.append(SearchResult(
                        source="pubmed",
                        result_id=pmid,
                        title=title,
                        relevance_score=relevance,
                        metadata={
                            "abstract": abstract,
                            "pmid": pmid,
                            "year": year,
                            "publication_types": [str(pt) for pt in pub_types],
                            "mesh_terms": [str(mt) for mt in mesh_terms],
                            "proteins_mentioned": proteins_mentioned,
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                        }
                    ))
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue
        
        print(f"Parsed {len(results)} PubMed articles successfully")
        return results
    
    def _calculate_relevance(
        self, title: str, abstract: str, pub_types: list, 
        mesh_terms: list, year: str, disease: str
    ) -> float:
        """Advanced relevance scoring based on multiple factors."""
        text = f"{title} {abstract}".lower()
        score = 0.3  # Base score
        
        # High-value publication types
        high_value_pubs = ["Clinical Trial", "Randomized Controlled Trial", "Meta-Analysis", "Review"]
        for pub_type in pub_types:
            if any(hvp.lower() in str(pub_type).lower() for hvp in high_value_pubs):
                score += 0.2
                break
        
        # Therapeutic relevance keywords
        therapeutic_terms = {
            "therapeutic target": 0.20,
            "drug target": 0.20,
            "clinical trial": 0.15,
            "treatment": 0.10,
            "therapy": 0.10,
            "pharmacological": 0.10,
            "intervention": 0.08
        }
        
        for term, value in therapeutic_terms.items():
            if term in text:
                score += value
        
        # Disease-specific terms in title (high value)
        if disease.lower() in title.lower():
            score += 0.15
        
        # Molecular mechanism keywords
        mechanism_terms = ["pathogenesis", "etiology", "biomarker", "protein", "gene", 
                          "pathway", "mechanism", "molecular", "signaling"]
        for term in mechanism_terms:
            if term in text:
                score += 0.05
                break
        
        # Recency bonus (more recent = more relevant)
        if year:
            try:
                year_int = int(year)
                current_year = datetime.now().year
                if year_int >= current_year - 3:
                    score += 0.15
                elif year_int >= current_year - 5:
                    score += 0.10
                elif year_int >= current_year - 10:
                    score += 0.05
            except:
                pass
        
        # MeSH term relevance
        relevant_mesh = ["Protein", "Gene", "Therapeutic", "Drug", "Target", "Pathway"]
        mesh_str = " ".join([str(m) for m in mesh_terms]).lower()
        for term in relevant_mesh:
            if term.lower() in mesh_str:
                score += 0.03
        
        return min(score, 1.0)
    
    def _extract_proteins(self, title: str, abstract: str) -> list[str]:
        """Extract protein/gene names from text using pattern matching."""
        text = f"{title} {abstract}"
        proteins = set()
        
        # Pattern 1: Gene symbols (2-6 uppercase letters/numbers)
        gene_pattern = r'\b([A-Z][A-Z0-9]{1,5})\b'
        matches = re.findall(gene_pattern, text)
        
        # Filter out common words and short matches
        common_words = {'THE', 'AND', 'FOR', 'WITH', 'FROM', 'RNA', 'DNA', 'ATP', 
                       'GTP', 'USA', 'UK', 'VS', 'OR', 'NOT', 'ALL', 'NEW'}
        
        for match in matches:
            if match not in common_words and len(match) >= 2:
                proteins.add(match)
        
        # Pattern 2: Protein names with "protein" or "receptor"
        protein_pattern = r'\b([A-Z][A-Za-z0-9-]+)\s+(protein|receptor|kinase|enzyme)\b'
        protein_matches = re.findall(protein_pattern, text, re.IGNORECASE)
        for match, _ in protein_matches:
            if len(match) > 2:
                proteins.add(match.upper())
        
        return list(proteins)[:20]  # Limit to top 20
    
    def _get_mesh_terms(self, disease: str) -> list[str]:
        """Get MeSH terms for a disease to improve search accuracy."""
        try:
            handle = Entrez.esearch(db="mesh", term=disease, retmax=5)
            record = Entrez.read(handle)
            handle.close()
            
            mesh_ids = record.get('IdList', [])
            if not mesh_ids:
                return []
            
            time.sleep(0.34)
            handle = Entrez.efetch(db="mesh", id=mesh_ids[:3], rettype="full", retmode="xml")
            
            # Read raw XML content (not using Entrez.read for MeSH XML)
            xml_content = handle.read()
            handle.close()
            
            # Parse XML manually
            import xml.etree.ElementTree as ET
            
            terms = []
            try:
                # Ensure content is bytes for XML parser
                if isinstance(xml_content, str):
                    xml_content = xml_content.encode('utf-8')
                
                root = ET.fromstring(xml_content)
                
                # Navigate MeSH XML structure: DescriptorRecord -> DescriptorName -> String
                for descriptor in root.findall('.//DescriptorRecord'):
                    desc_name = descriptor.find('.//DescriptorName/String')
                    if desc_name is not None and desc_name.text:
                        terms.append(desc_name.text)
                
            except ET.ParseError as e:
                print(f"MeSH XML parsing error: {e}")
            
            return terms
        except Exception as e:
            print(f"Error fetching MeSH terms: {e}")
            return []
    
    def _get_disease_variations(self, disease: str) -> list[str]:
        """Generate common variations of disease names for better matching."""
        variations = [disease]
        disease_lower = disease.lower()
        
        # Common patterns
        if "lupus" in disease_lower and "systemic" not in disease_lower:
            variations.extend(["Systemic Lupus Erythematosus", "SLE"])
        elif "systemic lupus" in disease_lower:
            variations.extend(["Lupus", "SLE", "Lupus Erythematosus"])
        
        if "diabetes" in disease_lower:
            if "type 2" in disease_lower or "type ii" in disease_lower:
                variations.extend(["Type 2 Diabetes Mellitus", "T2DM", "Diabetes Mellitus Type 2"])
            elif "type 1" in disease_lower or "type i" in disease_lower:
                variations.extend(["Type 1 Diabetes Mellitus", "T1DM", "Diabetes Mellitus Type 1"])
            else:
                variations.extend(["Diabetes Mellitus"])
        
        if "alzheimer" in disease_lower:
            variations.extend(["Alzheimer Disease", "AD", "Alzheimer's"])
        
        if "rheumatoid arthritis" in disease_lower or "ra" == disease_lower:
            variations.extend(["Rheumatoid Arthritis", "RA", "Arthritis, Rheumatoid"])
        
        return list(set(variations))  # Remove duplicates


def create_pubmed_tool() -> PubMedTool:
    """Factory function to create PubMed tool."""
    return PubMedTool()
