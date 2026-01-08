# Agentic Protein Target Discovery

An intelligent agent-based system using LangGraph to discover and rank protein targets for diseases by searching across multiple biochemical and medical databases.

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
# Basic usage
python main.py --disease "Alzheimer's disease"

# With custom parameters
python main.py --disease "Type 2 diabetes" --max-targets 10 --min-score 0.7
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

```bash
# Run tests
pytest tests/

# Run with verbose logging
python main.py --disease "Parkinson's disease" --verbose

# Format code
black src/ tests/
ruff check src/ tests/
```

## License

MIT
