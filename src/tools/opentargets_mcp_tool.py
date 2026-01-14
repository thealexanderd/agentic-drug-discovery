"""OpenTargets MCP tool using async MCP client with LLM-driven queries."""

import asyncio
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.models import SearchResult
from src.config import settings


class OpenTargetsMCPTool:
    """
    Tool for accessing OpenTargets via MCP (Model Context Protocol) over SSE.
    """
    
    MCP_SERVER_URL = "https://mcp.platform.opentargets.org/mcp"
    
    def __init__(self):
        """Initialize MCP tool."""
        self.available_tools = []
        
        # Initialize LLM - import here to avoid version conflicts
        if settings.llm_model.startswith("gpt"):
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.llm_model, 
                temperature=0,
                api_key=settings.openai_api_key
            )
        else:
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model=settings.llm_model, 
                temperature=0,
                api_key=settings.anthropic_api_key
            )
        
        print(f"OpenTargets MCP: Initialized (will connect on first use)")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, disease: str, proteins: list[str] = None) -> list[SearchResult]:
        """
        Search OpenTargets for target-disease associations.
        
        Args:
            disease: Disease name or EFO ID
            proteins: Optional list of specific protein/gene symbols to query
            
        Returns:
            List of SearchResult objects with OpenTargets evidence
        """
        try:
            # Run the async search in a new event loop
            return asyncio.run(self._async_search(disease, proteins))
        except Exception as e:
            print(f"OpenTargets MCP error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _async_search(self, disease: str, proteins: list[str] = None) -> list[SearchResult]:
        """Async implementation of search."""
        try:
            async with streamable_http_client(self.MCP_SERVER_URL) as (read, write, get_session_id):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    await session.initialize()
                    
                    # List available tools
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools]
                    print(f"OpenTargets MCP: Connected ({len(tool_names)} tools: {tool_names})")
                    
                    # Search for disease
                    disease_id = await self._search_disease_async(session, disease)
                    
                    if not disease_id:
                        print(f"OpenTargets MCP: Could not find disease ID for '{disease}'")
                        return []
                    
                    print(f"OpenTargets MCP: Found disease {disease_id}")
                    
                    # Get top targets using LLM to figure out the right tools/queries
                    targets = await self._get_targets_with_llm(session, disease_id, disease)
                    
                    print(f"OpenTargets MCP: Retrieved {len(targets)} associations")
                    return targets
                    
        except Exception as e:
            print(f"OpenTargets MCP async error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _search_disease_async(self, session: ClientSession, disease: str) -> str | None:
        """Search for disease using MCP."""
        try:
            # Use search_entities tool
            variations = [disease, disease.lower(), disease.title()]
            for suffix in [" Mellitus", " Disease", " Syndrome"]:
                if suffix in disease:
                    variations.append(disease.replace(suffix, "").strip())
            
            # Call search_entities with list of query strings
            result = await session.call_tool(
                "search_entities",
                arguments={"query_strings": variations[:5]}  # Limit to 5 variations
            )
            
            # Parse the result
            if result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        import json
                        data = json.loads(content.text)
                        
                        # Results are array with nested structure
                        for result_item in data.get("results", []):
                            result_data = result_item.get("result", {}).get("result", [[]])[0]
                            for entity in result_data:
                                if isinstance(entity, dict) and entity.get("entity") == "disease":
                                    disease_id = entity.get("id")
                                    query = result_item.get("key")
                                    print(f"OpenTargets MCP: Matched '{query}' → {disease_id}")
                                    return disease_id
            
            return None
            
        except Exception as e:
            print(f"Disease search error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _get_targets_with_llm(self, session: ClientSession, disease_id: str, disease_name: str) -> list[SearchResult]:
        """Query OpenTargets for targets - use hardcoded working query."""
        try:
            # Use the known-working query format
            graphql_query = f'''query {{
  disease(efoId: "{disease_id}") {{
    id
    associatedTargets(page: {{size: 50, index: 0}}) {{
      rows {{
        target {{
          id
          approvedSymbol
          approvedName
        }}
        score
        datatypeScores {{
          id
          score
        }}
      }}
    }}
  }}
}}'''
            
            print(f"OpenTargets MCP: Querying for {disease_id}")
            
            # Execute the query
            result = await session.call_tool(
                "query_open_targets_graphql",
                arguments={"query_string": graphql_query}
            )
            
            # Parse results
            results = []
            if result.content and not result.isError:
                for content in result.content:
                    if hasattr(content, 'text'):
                        import json
                        
                        # The response might be multiple JSON objects
                        text = content.text.strip()
                        data = None
                        
                        # Try to parse as single JSON
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            # Try splitting by newlines and parsing each
                            for line in text.split("\n"):
                                line = line.strip()
                                if line:
                                    try:
                                        data = json.loads(line)
                                        break
                                    except:
                                        continue
                        
                        if not data:
                            continue
                        
                        # MCP wraps response in {status, result, message}
                        if data.get("status") == "success":
                            data = data.get("result", {})
                        
                        # Navigate GraphQL response
                        disease_data = data.get("disease", {})
                        rows = disease_data.get("associatedTargets", {}).get("rows", [])
                        
                        for row in rows:
                            target = row.get("target", {})
                            gene_symbol = target.get("approvedSymbol")
                            if not gene_symbol:
                                continue
                            
                            score = row.get("score", 0)
                            
                            # Extract datatype scores
                            datatype_scores = {}
                            for dt in row.get("datatypeScores", []):
                                datatype_scores[dt["id"]] = dt["score"]
                            
                            results.append(SearchResult(
                                source="opentargets",
                                result_id=f"{gene_symbol}-{disease_id}",
                                title=f"{gene_symbol}: {target.get('approvedName', '')}",
                                relevance_score=min(score, 1.0),
                                metadata={
                                    "gene_symbol": gene_symbol,
                                    "ensembl_id": target.get("id"),
                                    "protein_name": target.get("approvedName", ""),
                                    "disease_id": disease_id,
                                    "overall_score": score,
                                    "genetic_score": datatype_scores.get("genetic_association", 0),
                                    "literature_score": datatype_scores.get("literature", 0),
                                    "pathways_score": datatype_scores.get("affected_pathway", 0),
                                    "animal_models_score": datatype_scores.get("animal_model", 0),
                                    "known_drugs_score": datatype_scores.get("known_drug", 0),
                                    "datatype_scores": datatype_scores
                                }
                            ))
            
            return results
            
        except Exception as e:
            print(f"Error getting targets with LLM: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _get_top_targets_async(self, session: ClientSession, disease_id: str, disease_name: str) -> list[SearchResult]:
        """Get top targets for disease using GraphQL."""
        try:
            # Use GraphQL query to get disease-target associations
            graphql_query = """
            query DiseaseTargets($efoId: String!) {
                disease(efoId: $efoId) {
                    id
                    name
                    associatedTargets(page: {size: 50, index: 0}) {
                        rows {
                            target {
                                id
                                approvedSymbol
                                approvedName
                            }
                            score
                            datatypeScores {
                                id
                                score
                            }
                        }
                    }
                }
            }
            """
            
            result = await session.call_tool(
                "query_open_targets_graphql",
                arguments={
                    "query_string": graphql_query,
                    "variables": {"efoId": disease_id}
                }
            )
            
            # Parse results
            results = []
            
            if result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        import json
                        data = json.loads(content.text)
                        
                        # Navigate GraphQL response structure
                        disease_data = data.get("data", {}).get("disease", {})
                        rows = disease_data.get("associatedTargets", {}).get("rows", [])
                        
                        for row in rows:
                            target = row.get("target", {})
                            gene_symbol = target.get("approvedSymbol")
                            if not gene_symbol:
                                continue
                            
                            score = row.get("score", 0)
                            
                            # Extract datatype scores
                            datatype_scores = {}
                            for dt in row.get("datatypeScores", []):
                                datatype_scores[dt["id"]] = dt["score"]
                            
                            results.append(SearchResult(
                                source="opentargets",
                                result_id=f"{gene_symbol}-{disease_id}",
                                title=f"{gene_symbol}: {target.get('approvedName', '')}",
                                relevance_score=min(score, 1.0),
                                metadata={
                                    "gene_symbol": gene_symbol,
                                    "ensembl_id": target.get("id"),
                                    "protein_name": target.get("approvedName", ""),
                                    "disease_id": disease_id,
                                    "overall_score": score,
                                    "genetic_score": datatype_scores.get("genetic_association", 0),
                                    "literature_score": datatype_scores.get("literature", 0),
                                    "pathways_score": datatype_scores.get("affected_pathway", 0),
                                    "animal_models_score": datatype_scores.get("animal_model", 0),
                                    "known_drugs_score": datatype_scores.get("known_drug", 0),
                                    "datatype_scores": datatype_scores
                                }
                            ))
            
            return results
            
        except Exception as e:
            print(f"Error getting targets: {e}")
            import traceback
            traceback.print_exc()
            return []


def create_opentargets_mcp_tool() -> OpenTargetsMCPTool:
    """Factory function to create OpenTargets MCP tool."""
    return OpenTargetsMCPTool()
