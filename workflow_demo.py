#!/usr/bin/env python3
"""
Visual demonstration of the improved PubMed workflow
"""

def print_box(title, content, width=70):
    """Print content in a nice box."""
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│ {title:^{width-4}} │")
    print("├" + "─" * (width - 2) + "┤")
    for line in content:
        print(f"│ {line:<{width-4}} │")
    print("└" + "─" * (width - 2) + "┘")

print("\n" + "=" * 70)
print(" IMPROVED PUBMED WORKFLOW ".center(70, "="))
print("=" * 70 + "\n")

# Step 1
print_box("STEP 1: User Query", [
    "User enters: 'Lupus'",
    ""
], 70)
print("         ↓")

# Step 2
print_box("STEP 2: MeSH Term Lookup", [
    "Query NCBI MeSH database for 'Lupus'",
    "→ Found: 'Lupus Erythematosus, Systemic'",
    "→ Found: 'Lupus Erythematosus, Cutaneous'",
    ""
], 70)
print("         ↓")

# Step 3
print_box("STEP 3: Generate Disease Variations", [
    "Built-in patterns expand disease names:",
    "  • Lupus",
    "  • Systemic Lupus Erythematosus",
    "  • SLE",
    "  • Lupus Erythematosus",
    ""
], 70)
print("         ↓")

# Step 4
print_box("STEP 4: Build Smart PubMed Query", [
    '(("Lupus Erythematosus, Systemic"[MeSH] OR',
    ' "Lupus"[Title/Abstract] OR "SLE"[Title/Abstract])',
    'AND "humans"[MeSH Terms]',
    'AND ("therapeutic target" OR "drug target" OR "treatment")',
    'AND last 10 years)',
    ""
], 70)
print("         ↓")

# Step 5
print_box("STEP 5: Fetch & Parse Results (XML Format)", [
    "Fetch up to 50 articles from PubMed",
    "Extract for each article:",
    "  ✓ Full title and abstract",
    "  ✓ Publication year and types",
    "  ✓ MeSH subject headings",
    "  ✓ Identify proteins via regex patterns",
    ""
], 70)
print("         ↓")

# Step 6
print_box("STEP 6: Calculate Relevance Scores", [
    "Example article scoring:",
    "  Base score:              0.30",
    "  + Clinical trial type:  +0.20",
    "  + Recent (2023):        +0.15",
    "  + 'therapeutic target': +0.20",
    "  + Disease in title:     +0.15",
    "  + Mechanism keywords:   +0.05",
    "  --------------------------------",
    "  Final relevance:         1.05 → 1.00 (capped)",
    ""
], 70)
print("         ↓")

# Step 7
print_box("STEP 7: Extract Candidate Proteins", [
    "From all 50 articles, extract mentioned proteins:",
    "  • IFNA, IFNB, IFNAR (Interferons)",
    "  • TNF, TNFRSF (TNF family)",
    "  • IL6, IL10, IL17 (Interleukins)",
    "  • CD20, CD40 (Cell markers)",
    "  • BAFF, BLK (B-cell factors)",
    "",
    "Total: 47 unique protein candidates identified",
    ""
], 70)
print("         ↓")

# Step 8
print_box("STEP 8: Targeted Follow-up Searches", [
    "For top 10 candidate proteins, run specific searches:",
    "  1. 'Lupus AND IFNA' → 12 more results",
    "  2. 'Lupus AND TNF' → 15 more results",
    "  3. 'Lupus AND IL6' → 8 more results",
    "  ...",
    "  10. 'Lupus AND CD20' → 6 more results",
    "",
    "Total PubMed results: 50 + 87 = 137 articles",
    ""
], 70)
print("         ↓")

# Step 9
print_box("STEP 9: Integration with Other Databases", [
    "Use protein candidates to search:",
    "  • GWAS Catalog: genetic associations",
    "  • UniProt: protein information",
    "  • PDB: 3D structures",
    "  • PubChem: drug compounds",
    ""
], 70)
print("         ↓")

# Step 10
print_box("STEP 10: Evidence Aggregation & Ranking", [
    "For each protein, calculate scores:",
    "  • Genetic score (from GWAS): 0-1",
    "  • Literature score (from PubMed): 0-1",
    "  • Structural score (from PDB): 0-1",
    "  • Druggability score (from PubChem): 0-1",
    "",
    "Weighted overall score:",
    "  0.35×genetic + 0.30×literature +",
    "  0.20×structural + 0.15×druggability",
    ""
], 70)
print("         ↓")

# Step 11
print_box("STEP 11: Final Output", [
    "Top protein target: IFNA",
    "  Overall score: 0.87",
    "  Evidence sources: PubMed, GWAS, UniProt, PDB",
    "  Key findings:",
    "    • Ref in: Targeting type I interferon... (2023)",
    "    • Genetic association (p=2.3e-12)",
    "    • 3D structure available (PDB: 1ITF)",
    "  Related pathways:",
    "    • Type I interferon signaling",
    "    • Innate immune response",
    ""
], 70)

print("\n" + "=" * 70)
print(" KEY IMPROVEMENTS ".center(70, "="))
print("=" * 70)
print("""
✓ Disease name variations & MeSH lookup → Works with 'Lupus'
✓ Full abstracts & rich metadata → Not truncated anymore  
✓ Protein extraction from text → Automatic candidate discovery
✓ Multi-factor relevance scoring → More accurate results
✓ Two-stage search strategy → Broad + targeted queries
✓ Publication type awareness → Prioritize clinical trials
✓ Recency weighting → Recent research valued more
✓ Direct PubMed URLs → Easy access to sources
""")
print("=" * 70 + "\n")
