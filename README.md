# Agentic Protein Target Discovery

A **truly agentic** AI system using LangGraph that intelligently discovers and ranks protein targets for diseases. Unlike simple automation, this system features an LLM that **reasons about disease characteristics, dynamically selects databases, evaluates intermediate results, and adjusts its search strategy** in real-time.

## 🧠 What Makes It Agentic?

This isn't just a pipeline—it's an AI researcher that:

1. **Creates Research Plans**: Analyzes the disease type (genetic, autoimmune, metabolic, etc.) and creates a tailored research strategy
2. **Makes Dynamic Decisions**: The LLM decides which database to query next based on what it has learned
3. **Evaluates Results**: After each search, the LLM analyzes findings and identifies gaps
4. **Adjusts Strategy**: Changes its approach based on intermediate results
5. **Synthesizes Evidence**: Provides reasoned explanations for why targets are promising

## 🔬 Databases & Resources

### Core (Mandatory)

| Database | Purpose | Why It's Essential |
|----------|---------|-------------------|
| **PubMed** | Mechanistic & experimental evidence | Functional evidence, PMIDs for justification |
| **UniProt** | Protein identity & function | Canonical definitions, cross-references |
| **DisGeNET** | Gene-disease associations | Curated scores, evidence counts |
| **Gene Ontology** | Biological function validation | Verify mechanism relevance |

### Strongly Recommended

| Database | Purpose | Why It's Valuable |
|----------|---------|------------------|
| **GWAS Catalog** | Genetic associations | Causal evidence, avoids literature bias |
| **Reactome** | Pathway context | Mechanistic explanations, target clustering |

### Supplementary

| Database | Purpose |
|----------|---------|
| **PDB** | 3D structure availability for druggability |
| **PubChem** | Existing compounds, druggability validation |

## 🚀 Quick Start

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys

# Run agentic discovery
python main.py discover "Alzheimer's disease" --verbose --show-plan

# See available tools
python main.py tools

# Check configuration
python main.py config
```

## 📖 Usage Examples

```bash
# Basic discovery
python main.py discover "Type 2 Diabetes"

# Verbose mode shows agent reasoning
python main.py discover "Systemic Lupus Erythematosus" --verbose

# Show research plan
python main.py discover "Parkinson's disease" --show-plan

# Export results
python main.py discover "Breast Cancer" --max-targets 20 --output results.csv
```

### Example Output (Verbose Mode)

```
🔬 Agentic Protein Target Discovery
Disease: Systemic Lupus Erythematosus

🎯 Research Plan
  Disease    Systemic Lupus Erythematosus
  Type       autoimmune
  Strategy   Focus on immune system genes, interferon signaling...
  Hypotheses • Type I interferon pathway dysregulation
             • B cell hyperactivity
             • Complement system abnormalities

🔍 Database Search Results
  ■ DISGENET
     Found 45 gene-disease associations with strong evidence...
     Proteins: STAT4, IRF5, TNFSF4, PTPN22, ITGAM
  
  ■ GWAS
     Strong genetic associations for immune-related genes...
     Proteins: BLK, BANK1, TNFAIP3
  
  ■ PUBMED
     Literature confirms therapeutic relevance...
  
🎯 Top Protein Targets

#1. STAT4 - Signal transducer and activator of transcription 4
    Score: [████████████████░░░░] 0.82
    Sources: DisGeNET, GWAS, PubMed, Gene Ontology
    Evidence strength: strong
    
#2. IRF5 - Interferon regulatory factor 5
    Score: [███████████████░░░░░] 0.78
    ...
```

## 🏗️ Architecture

### Agentic Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC TARGET DISCOVERY                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   PLAN      │───▶│   EXECUTE    │───▶│    ANALYZE       │   │
│  │             │    │   SEARCH     │    │                  │   │
│  │ LLM creates │    │              │    │ LLM evaluates    │   │
│  │ research    │    │ Query        │    │ results, finds   │   │
│  │ strategy    │    │ selected     │    │ gaps, decides    │   │
│  └─────────────┘    │ database     │    │ next steps       │   │
│                     └──────────────┘    └────────┬─────────┘   │
│                            ▲                     │              │
│                            │    ┌────────────────┘              │
│                            │    │                               │
│                     ┌──────┴────▼──────┐                       │
│                     │   SELECT TOOL    │                        │
│                     │                  │                        │
│                     │ LLM dynamically  │                        │
│                     │ chooses next     │                        │
│                     │ database based   │                        │
│                     │ on current state │                        │
│                     └──────────────────┘                        │
│                            │                                    │
│                            ▼                                    │
│                     ┌──────────────────┐                       │
│                     │   SYNTHESIZE     │                        │
│                     │                  │                        │
│                     │ LLM creates      │                        │
│                     │ evidence summary │                        │
│                     │ for each target  │                        │
│                     └──────────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **AgenticTargetDiscovery** | `src/agents/target_agent.py` | Main agentic workflow with LLM reasoning |
| **ResearchPlan** | `src/models.py` | LLM-generated research strategy |
| **ToolDecision** | `src/models.py` | Dynamic tool selection decisions |
| **IntermediateAnalysis** | `src/models.py` | LLM analysis of search results |
| **EvidenceSynthesis** | `src/models.py` | Per-target evidence synthesis |
| **TOOL_REGISTRY** | `src/tools/__init__.py` | Tool metadata for agentic selection |

## 🔧 Configuration

### Environment Variables

```bash
# Required: One LLM API key
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

# Recommended: For better PubMed rate limits
NCBI_API_KEY=...
NCBI_EMAIL=your@email.com

# Optional: For full DisGeNET access
DISGENET_API_KEY=...

# Agentic settings
MAX_ITERATIONS=5          # Maximum reasoning iterations
VERBOSE_REASONING=false   # Show LLM reasoning by default
```

### Config File Settings

```python
# src/config.py
llm_model: str = "gpt-4o"       # LLM model to use
llm_temperature: float = 0.1    # Lower = more focused
max_iterations: int = 5         # Reasoning iterations
max_pubmed_results: int = 50
max_gwas_results: int = 100
```

## 📊 Evidence Scoring

Targets are ranked using weighted evidence from multiple sources:

| Evidence Type | Weight | Source |
|---------------|--------|--------|
| DisGeNET score | 20% | Gene-disease association database |
| Genetic evidence | 20% | GWAS Catalog |
| Literature | 18% | PubMed publications |
| UniProt annotations | 12% | Disease annotations |
| GO relevance | 10% | Functional validation |
| Pathway context | 8% | Reactome pathways |
| Structural | 7% | PDB availability |
| Druggability | 5% | PubChem compounds |

## 🧪 Testing

```bash
pytest tests/                    # All tests
pytest tests/test_ranker.py -v  # Specific test
pytest -k "gwas" -v             # Pattern matching
```

## 📁 Project Structure

```
agentic/
├── src/
│   ├── agents/
│   │   └── target_agent.py    # 🧠 Agentic workflow with LLM reasoning
│   ├── tools/
│   │   ├── pubmed_tool.py     # Core: Literature search
│   │   ├── uniprot_tool.py    # Core: Protein information
│   │   ├── disgenet_tool.py   # Core: Gene-disease associations
│   │   ├── go_tool.py         # Core: Gene Ontology
│   │   ├── gwas_tool.py       # Recommended: Genetic associations
│   │   ├── reactome_tool.py   # Recommended: Pathways
│   │   ├── pdb_tool.py        # Supplementary: Structures
│   │   └── pubchem_tool.py    # Supplementary: Compounds
│   ├── rankers/
│   │   └── target_ranker.py   # Multi-source evidence ranking
│   ├── models.py              # Pydantic models including agentic types
│   └── config.py              # Configuration management
├── tests/
├── examples/
├── main.py                    # CLI with reasoning visualization
└── requirements.txt
```

## 🆚 Automation vs Agentic

| Aspect | Previous (Automation) | Now (Agentic) |
|--------|----------------------|---------------|
| Strategy | Fixed sequence | LLM-planned per disease |
| Tool Selection | All tools, always | Dynamic based on findings |
| Intermediate Results | Stored, not analyzed | LLM evaluates each step |
| Error Handling | Skip and continue | Reason about gaps |
| Output | Scores only | Scores + reasoning + synthesis |

## 📄 License

MIT
