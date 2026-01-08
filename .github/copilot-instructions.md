# AI Agent Instructions for Agentic Protein Target Discovery

## Project Overview

This is a **LangGraph-based multi-agent system** that discovers and ranks protein targets for diseases by querying biomedical databases (PubMed, GWAS Catalog, UniProt, PDB, PubChem). The system aggregates evidence from multiple sources and produces a ranked list of therapeutic targets.

**Core workflow**: Disease Query → Database Search → Evidence Aggregation → Target Ranking

## Architecture

### Key Components

1. **LangGraph Agent** ([src/agents/target_agent.py](src/agents/target_agent.py))
   - Orchestrates the multi-step workflow using a state graph
   - Three main nodes: `normalize_disease` → `search_databases` → `rank_targets`
   - State is maintained in `AgentState` (Pydantic model) and passed between nodes

2. **Database Tools** ([src/tools/](src/tools/))
   - Each tool is a class with a `search()` method returning `list[SearchResult]`
   - Tools use `tenacity` for retry logic (3 attempts with exponential backoff)
   - All tools implement rate limiting and error handling
   - Key tools: `PubMedTool`, `GWASTool`, `UniProtTool`, `PDBTool`, `PubChemTool`

3. **Target Ranker** ([src/rankers/target_ranker.py](src/rankers/target_ranker.py))
   - Aggregates evidence by protein/gene symbol across all database results
   - Calculates four evidence scores: genetic (0.35 weight), literature (0.30), structural (0.20), druggability (0.15)
   - Returns sorted `list[ProteinTarget]` by `overall_score`

4. **Data Models** ([src/models.py](src/models.py))
   - `AgentState`: Workflow state with search results and control flow
   - `ProteinTarget`: Final output with scores and evidence metadata
   - `SearchResult`: Unified result format from all database tools

## Critical Conventions

### API Integration Patterns

- **PubMed/NCBI**: Uses Biopython's `Entrez` module. Always set `Entrez.email` and optionally `Entrez.api_key` (from config)
- **GWAS**: REST API at `ebi.ac.uk/gwas`. Extract genes from `loci[0].authorReportedGenes[0].geneName`
- **UniProt**: REST API at `rest.uniprot.org/uniprotkb`. Query format: `(disease:X) AND (reviewed:true)`
- **PDB**: GraphQL-style search at `search.rcsb.org/rcsbsearch/v2/query`. Match by `rcsb_gene_name.value`
- **PubChem**: PUG REST API at `pubchem.ncbi.nlm.nih.gov/rest/pug`. Search by compound/protein relationships

### Scoring Logic

All relevance scores are **normalized to 0-1 range**:
- GWAS: p-value based (p ≤ 5e-8 → 1.0, p ≤ 1e-5 → 0.8, etc.)
- PubMed: Keyword presence ("therapeutic target", "drug target" = high value)
- UniProt: Disease annotation presence + binding sites + PDB structures
- Multiple evidence pieces get a confidence boost: `+0.05` per additional result (max +0.2)

### LangGraph State Management

The `AgentState` model uses:
- `disease_query`: Original user input
- `candidate_proteins`: Accumulated gene/protein names from searches (used to guide subsequent searches)
- `searches_completed`: List of database names already queried (prevents duplicates)
- `next_action`: Controls workflow routing (`"search_databases"`, `"rank_targets"`, `"complete"`)

**Critical**: Candidate proteins are built incrementally—GWAS results populate initial candidates, then UniProt searches use those candidates and adds more.

## Development Workflows

### Running the Application

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your OPENAI_API_KEY or ANTHROPIC_API_KEY

# Basic usage
python main.py discover "Alzheimer's disease"

# With options
python main.py discover "Type 2 diabetes" --max-targets 20 --output results.csv --verbose

# Check configuration
python main.py config
```

### Testing

```bash
pytest tests/                    # Run all tests
pytest tests/test_ranker.py -v  # Specific test file
pytest -k "gwas" -v             # Tests matching pattern
```

Tests use mocking for API calls. Check [tests/conftest.py](tests/conftest.py) for shared fixtures.

### Adding New Database Tools

1. Create `src/tools/new_tool.py` implementing:
   ```python
   class NewTool:
       @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
       def search(self, disease: str) -> list[SearchResult]:
           # Query API, return SearchResult objects
   ```

2. Update `src/tools/__init__.py` to export the tool

3. Integrate in `src/agents/target_agent.py`:
   - Initialize tool in `create_agent()`
   - Add search logic in `search_databases()` node
   - Append to `state.searches_completed`

4. Update ranker in `src/rankers/target_ranker.py`:
   - Add evidence processing in `_aggregate_evidence()`
   - Update scoring weights if needed

## Configuration

Settings via [src/config.py](src/config.py) using `pydantic-settings`:
- Loads from `.env` file automatically
- Required: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- Optional: `NCBI_API_KEY` (recommended for PubMed rate limits)
- Access via `from src.config import settings`

## Common Pitfalls

1. **Rate Limiting**: All tools implement retry logic, but NCBI/PubMed has strict limits without an API key
2. **Gene Symbol Normalization**: Different databases use different conventions (HGNC vs UniProt). The system uses uppercase matching
3. **Empty Results**: Disease names must match database terminology. The LLM normalization step helps but may need manual adjustment
4. **LangGraph State**: Always return the modified `state` object from each node function

## Key Files Reference

- [main.py](main.py) - CLI entry point using Typer
- [src/agents/target_agent.py](src/agents/target_agent.py) - LangGraph workflow definition
- [src/rankers/target_ranker.py](src/rankers/target_ranker.py) - Evidence aggregation and scoring
- [src/models.py](src/models.py) - All Pydantic data models
- [src/config.py](src/config.py) - Configuration management
- [examples/basic_usage.py](examples/basic_usage.py) - Programmatic usage examples
