# Quick Reference: PubMed Improvements

## What Was Fixed

### ❌ Problem 1: "Lupus" searches failed
**Before**: Search for "Lupus" returned 0 results  
**After**: Automatically expands to medical terms (Systemic Lupus Erythematosus, SLE) + MeSH lookup

### ❌ Problem 2: Results not relevant  
**Before**: Simple keyword scoring (0.5-0.7), no quality assessment  
**After**: Multi-factor scoring considering:
- Publication type (clinical trials, meta-analyses get priority)
- Recency (last 3-10 years weighted)
- Therapeutic keywords presence
- Disease specificity in title

### ❌ Problem 3: Barely has title, truncated abstracts
**Before**: Title + 500 characters of abstract  
**After**: Full rich metadata:
- Complete abstracts
- Publication year
- Publication types (Clinical Trial, Review, etc.)
- MeSH subject headings
- Extracted protein/gene names
- Direct PubMed URLs

## How It Works Now

### Search Flow
```
User enters "Lupus"
    ↓
1. MeSH Term Lookup
   → Finds: "Lupus Erythematosus, Systemic"
    ↓
2. Generate Variations  
   → ["Lupus", "Systemic Lupus Erythematosus", "SLE"]
    ↓
3. Build Smart Query
   → (MeSH terms OR disease variations) 
     AND therapeutic keywords
     AND human studies
     AND last 10 years
    ↓
4. Fetch Results (XML format)
   → Parse full metadata
   → Extract proteins from text
    ↓
5. Score Each Article
   → Multi-factor relevance (0.3-1.0)
    ↓
6. Extract Candidate Proteins
   → ["IFNA", "TNF", "IL6", ...]
    ↓
7. Targeted Follow-up
   → Search "Lupus AND IFNA"
   → Search "Lupus AND TNF"
   → (for top 10 proteins)
```

### Relevance Scoring Breakdown

| Factor | Base Score | How Added |
|--------|-----------|-----------|
| Base | 0.3 | Always included |
| High-value publication | +0.2 | Clinical trial, Meta-analysis, RCT, Review |
| "therapeutic target" | +0.2 | Direct mention |
| "drug target" | +0.2 | Direct mention |
| Disease in title | +0.15 | Exact match in title |
| Recent (≤3 years) | +0.15 | Publication year |
| "clinical trial" keyword | +0.15 | In text |
| "treatment" | +0.1 | In text |
| "therapy" | +0.1 | In text |
| Recent (≤5 years) | +0.10 | Publication year |
| Mechanism terms | +0.05 | "pathogenesis", "biomarker", etc. |
| Recent (≤10 years) | +0.05 | Publication year |
| MeSH relevance | +0.03 | Per relevant MeSH term |
| **Maximum** | **1.0** | Capped |

### Protein Extraction Patterns

The system identifies proteins using:

1. **Gene Symbol Pattern**: `[A-Z][A-Z0-9]{1,5}`
   - Examples: TNF, IL6, IFNA2, CD20
   - Filters: Removes common words (THE, AND, DNA, etc.)

2. **Protein Name Pattern**: `[Name] protein|receptor|kinase|enzyme`
   - Examples: "TNF-alpha protein", "IL-6 receptor"
   - Extracts the name part and uppercases

3. **Limit**: Top 20 proteins per article

## Usage Examples

### Basic Search
```python
from src.tools.pubmed_tool import PubMedTool

tool = PubMedTool()
results = tool.search("Lupus")

for r in results:
    print(f"Title: {r.title}")
    print(f"Relevance: {r.relevance_score}")
    print(f"Year: {r.metadata['year']}")
    print(f"Proteins: {r.metadata['proteins_mentioned']}")
    print(f"URL: {r.metadata['url']}")
```

### Targeted Search with Protein
```python
results = tool.search("Lupus", "IFNA")
# Searches specifically for Lupus + Interferon Alpha
```

### Via Main CLI
```bash
# Now works with simple disease names!
python main.py discover "Lupus" --max-targets 10 --verbose

# Still works with full names
python main.py discover "Systemic Lupus Erythematosus" --output results.csv
```

## Adding More Disease Variations

Edit `src/tools/pubmed_tool.py`, method `_get_disease_variations()`:

```python
def _get_disease_variations(self, disease: str) -> list[str]:
    variations = [disease]
    disease_lower = disease.lower()
    
    # Add your pattern:
    if "your disease" in disease_lower:
        variations.extend(["Full Name", "Abbreviation"])
    
    return list(set(variations))
```

## Configuration

In `.env` file:
```bash
# Optional but recommended for higher rate limits
NCBI_API_KEY=your_api_key_here
NCBI_EMAIL=your@email.com

# Controls how many PubMed results to fetch (default: 50)
MAX_PUBMED_RESULTS=50
```

## Testing

Test the improvements:
```bash
python3 test_improvements.py
```

Expected output:
- ✓ "Lupus" search returns results
- ✓ Full metadata extracted
- ✓ Proteins identified
- ✓ Relevance scores calculated

## Files Changed

1. ✏️ `src/tools/pubmed_tool.py` - Complete rewrite with all improvements
2. ✏️ `src/rankers/target_ranker.py` - Better PubMed evidence processing
3. ✏️ `src/agents/target_agent.py` - Two-stage search + protein extraction
4. ✏️ `src/utils/display.py` - Show more findings and pathways
5. 📄 `test_improvements.py` - Test script (new)
6. 📄 `PUBMED_IMPROVEMENTS.md` - Detailed documentation (new)
7. 📄 `comparison.py` - Before/after visualization (new)

## Performance Impact

- **Query time**: +1-2 seconds (MeSH lookup + XML parsing)
- **API calls**: 11x more (1 initial + 10 targeted) but much better results
- **Memory**: Minimal impact (full abstracts ~1-2 KB each)
- **Rate limiting**: Respected (0.34s between calls)

## What's Next?

Consider these future enhancements:
1. Cache MeSH terms and disease variations
2. Use BioBERT or spaCy for better protein NER
3. Add citation count weighting
4. Implement abstract summarization with LLM
5. Integrate Disease Ontology databases
