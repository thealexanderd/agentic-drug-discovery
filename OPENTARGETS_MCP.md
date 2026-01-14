# OpenTargets MCP Integration

This project now integrates with [OpenTargets](https://platform.opentargets.org/) via their **Model Context Protocol (MCP) server** at `https://mcp.platform.opentargets.org/mcp`.

## What is OpenTargets?

OpenTargets is a comprehensive platform that aggregates evidence for target-disease associations from multiple sources:

- **Genetics**: GWAS, rare diseases, somatic mutations
- **Literature**: Text-mined evidence from publications
- **Pathways**: Reactome, CRISPR screens, sysbio
- **Animal Models**: MGI, ortholog mappings
- **Drugs**: Known drug-target relationships, clinical trials
- **Expression**: Differential expression, baseline expression

## Integration via MCP

The integration uses the **Model Context Protocol (MCP)**, which allows the LLM agent to:

1. **Call MCP tools** directly via JSON-RPC
2. **Fallback to GraphQL API** if MCP endpoints are unavailable
3. **Get comprehensive scores** for target-disease associations
4. **Access datatype-specific evidence** (genetics, literature, pathways, etc.)

## How It Works

### Tool: `OpenTargetsMCPTool`

Location: [`src/tools/opentargets_mcp_tool.py`](src/tools/opentargets_mcp_tool.py)

**Capabilities:**

1. **Disease Search**: Maps disease names to EFO IDs
2. **Target-Disease Associations**: Gets evidence scores for specific protein-disease pairs
3. **Top Targets**: Retrieves top-ranked targets for a disease
4. **Datatype Scores**: Breaks down evidence by type (genetic, literature, pathways, animal models, known drugs)

### MCP Endpoint

```
POST https://mcp.platform.opentargets.org/mcp
```

**Example MCP Call:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_disease_targets",
    "arguments": {
      "disease_id": "EFO_0000685",
      "size": 50
    }
  }
}
```

### GraphQL Fallback

If MCP endpoints fail, the tool automatically falls back to OpenTargets GraphQL API:

```
POST https://api.platform.opentargets.org/api/v4/graphql
```

## Usage

### In Agent Workflow

The agent can dynamically select OpenTargets when it needs comprehensive evidence:

```python
from src.agents.target_agent import create_agent

agent = create_agent(verbose=True)
state = agent.invoke({"disease_query": "Type 1 Diabetes"})

# OpenTargets will be selected if the agent determines it's valuable
# Results appear in state.opentargets_results
```

### Direct Tool Usage

```python
from src.tools import create_opentargets_mcp_tool

tool = create_opentargets_mcp_tool()

# Search for top targets for a disease
results = tool.search("Type 1 Diabetes")

for r in results:
    print(f"Gene: {r.metadata['gene_symbol']}")
    print(f"Overall Score: {r.metadata['overall_score']}")
    print(f"Genetic Evidence: {r.metadata['genetic_score']}")
    print(f"Literature Evidence: {r.metadata['literature_score']}")
    print(f"Known Drugs: {r.metadata.get('known_drugs_score', 0)}")
```

### With Specific Proteins

```python
# Check specific proteins against a disease
candidates = ["INS", "PTPN22", "HLA-DRB1", "IL2RA"]
results = tool.search("Type 1 Diabetes", proteins=candidates)
```

## Data Returned

Each `SearchResult` from OpenTargets includes:

```python
{
    "source": "opentargets",
    "result_id": "INS-EFO_0000685",
    "title": "INS: Insulin",
    "relevance_score": 0.95,  # Overall association score
    "metadata": {
        "gene_symbol": "INS",
        "ensembl_id": "ENSG00000254647",
        "protein_name": "Insulin",
        "disease_id": "EFO_0000685",
        "overall_score": 0.95,
        "genetic_score": 0.88,         # GWAS, rare disease evidence
        "literature_score": 0.92,       # Text-mined publications
        "pathways_score": 0.75,         # Reactome, CRISPR
        "animal_models_score": 0.68,    # MGI, orthologs
        "known_drugs_score": 0.85,      # Known drug targets
        "datatype_scores": {
            "genetic_association": 0.88,
            "literature": 0.92,
            "affected_pathway": 0.75,
            "animal_model": 0.68,
            "known_drug": 0.85,
            "somatic_mutation": 0.45,
            # ... more datatypes
        }
    }
}
```

## Evidence Weighting

OpenTargets evidence is incorporated into the overall target ranking with a **20% weight**:

```python
overall_score = (
    0.20 * genetic_score +
    0.15 * literature_score +
    0.08 * structural_score +
    0.08 * druggability_score +
    0.15 * disgenet_score +
    0.07 * go_score +
    0.07 * pathway_score +
    0.20 * opentargets_score  # High weight for comprehensive data
)
```

OpenTargets also **boosts** other categories:
- Genetic score boosted by OpenTargets `genetic_association` datatype
- Literature score boosted by OpenTargets `literature` datatype
- Pathway score boosted by OpenTargets `affected_pathway` datatype

## Agent Decision Making

The agent knows to use OpenTargets when:

1. **Comprehensive evidence needed**: When initial searches yield weak results
2. **Known drug repurposing**: Looking for existing therapeutics
3. **Multi-source validation**: Cross-checking findings from other databases
4. **Genetic diseases**: Prioritizing genetic evidence

**Example agent reasoning:**

```
🤖 Selected tool: opentargets
🤖 Reasoning: Initial DisGeNET and GWAS searches identified candidate 
   genes but lack comprehensive evidence. OpenTargets will provide 
   multi-source validation including literature, pathways, and known 
   drug information to strengthen target selection.
```

## Tool Priority

In `TOOL_REGISTRY`:

```python
"opentargets": {
    "name": "OpenTargets (MCP)",
    "purpose": "Comprehensive multi-source target-disease evidence",
    "priority": 2,  # Strongly recommended
    "provides": [
        "target_disease_scores",
        "evidence_by_datatype",
        "drug_info",
        "genetics",
        "pathways"
    ],
    "best_for": [
        "comprehensive evidence",
        "target prioritization",
        "multi-source integration",
        "known drugs"
    ],
    "limitations": [
        "may be slower",
        "requires disease ID mapping"
    ]
}
```

## Error Handling

The tool includes robust error handling:

1. **MCP call fails** → Falls back to GraphQL API
2. **Disease ID not found** → Returns empty results with warning
3. **Network timeout** → Retries with exponential backoff (3 attempts)
4. **Rate limiting** → Handled via httpx client with 60s timeout

## Performance

- **Typical response time**: 2-5 seconds per query
- **Batch queries**: Can process up to 20 proteins in one search
- **Caching**: Results cached in agent state for the session
- **Parallel execution**: Can run alongside other database searches

## MCP Server Documentation

For more details on the OpenTargets MCP server:

- **Spec**: [Model Context Protocol](https://modelcontextprotocol.io/)
- **OpenTargets Platform**: https://platform.opentargets.org/
- **GraphQL API Docs**: https://platform-docs.opentargets.org/data-access/graphql-api

## Debugging

Enable verbose mode to see MCP interactions:

```bash
python main.py discover "Type 1 Diabetes" --verbose
```

Output will show:
```
🤖 Executing: opentargets
OpenTargets: Found disease EFO_0000685
OpenTargets: Retrieved 47 associations
```

## Future Enhancements

Potential improvements:

1. **Batch MCP calls**: Combine multiple queries into one request
2. **Caching disease IDs**: Cache EFO ID lookups to reduce API calls
3. **Evidence details**: Fetch detailed evidence (publications, SNPs, etc.)
4. **Drug information**: Extract specific drug molecules and clinical trial data
5. **Target safety**: Add safety liability information from OpenTargets
