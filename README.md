# Agentic Protein Target Discovery

An intelligent agent-based system using LangGraph to discover and rank protein targets for diseases by searching across multiple biochemical and medical databases.

> **🚀 Recent Improvements**: Enhanced PubMed integration with MeSH term lookup, full abstract extraction, automatic protein identification, and multi-factor relevance scoring. Now supports simplified disease names like "Lupus" or "Diabetes"! See [PUBMED_IMPROVEMENTS.md](PUBMED_IMPROVEMENTS.md) for details.

## Overview

This application uses LangGraph to orchestrate a multi-agent workflow that:
1. Searches biochemical/medical resources (PubMed, PubChem, GWAS Catalog, PDB, UniProt)
2. Analyzes relationships between diseases and proteins
3. Ranks potential protein targets based on evidence strength
4. Provides actionable insights for drug discovery

## Features

- **Multi-Database Search**: Queries PubMed, PubChem, GWAS Catalog, PDB, and UniProt
- **Intelligent Agent**: Uses LangGraph for decision-making and workflow orchestration
- **Evidence-Based Ranking**: Scores protein targets based on genetic, structural, and literature evidence
- **Smart Disease Matching**: Automatically expands disease names (e.g., "Lupus" → "Systemic Lupus Erythematosus") with MeSH term lookup
- **Rich PubMed Integration**: Extracts full abstracts, publication types, proteins mentioned, and more
- **Two-Stage Search**: Initial broad search followed by targeted protein-specific queries
- **Extensible Architecture**: Easy to add new data sources and ranking criteria

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Required API keys:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - For LLM reasoning
- `NCBI_API_KEY` (optional but recommended) - For PubMed rate limits

## Usage

```bash
# Basic usage - now works with simple disease names!
python main.py discover "Lupus"
python main.py discover "Alzheimer's disease"
python main.py discover "Type 2 Diabetes"

# With options
python main.py discover "Lupus" --max-targets 20 --verbose --output results.csv

# Show configuration
python main.py config
```

### Example Output

The system now provides rich results including:
- Ranked protein targets with multi-factor scores
- Full PubMed abstracts and publication metadata
- Extracted protein mentions from literature
- Direct links to source databases
- Key findings with publication details

## Testing

```bash
# Run all tests
pytest tests/

# Test PubMed improvements specifically
python test_improvements.py
```

## Project Structure

```
agentic/
├── src/
│   ├── agents/          # LangGraph agent definitions
│   ├── tools/           # Database API integrations
│   ├── rankers/         # Target scoring and ranking logic
│   └── utils/           # Helper functions
├── tests/               # Unit and integration tests
├── examples/            # Example queries and outputs
├── main.py             # CLI entry point
└── requirements.txt    # Python dependencies
```

## Architecture

The system uses LangGraph to create a stateful agent that:
1. **Planning**: Breaks down the disease query into searchable components
2. **Search**: Queries multiple databases in parallel
3. **Integration**: Combines and deduplicates results
4. **Analysis**: Scores targets based on evidence quality and relevance
5. **Ranking**: Orders targets by potential therapeutic value

## Development


## License

MIT
