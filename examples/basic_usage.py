"""Example usage of the agentic target discovery system."""

from src.agents import run_target_discovery
from src.utils import display_results

# Example 1: Basic usage
print("Example 1: Alzheimer's Disease")
print("=" * 50)
state = run_target_discovery("Alzheimer's disease", verbose=True)
display_results(state.ranked_targets, max_display=5)

# Example 2: Different disease
print("\n\nExample 2: Type 2 Diabetes")
print("=" * 50)
state = run_target_discovery("Type 2 diabetes", verbose=True)
display_results(state.ranked_targets, max_display=5)

# Example 3: Access individual scores
print("\n\nExample 3: Detailed Scoring")
print("=" * 50)
state = run_target_discovery("Parkinson's disease")
top_target = state.ranked_targets[0]

print(f"Top Target: {top_target.gene_symbol}")
print(f"  Genetic Evidence: {top_target.genetic_score:.3f}")
print(f"  Literature Evidence: {top_target.literature_score:.3f}")
print(f"  Structural Data: {top_target.structural_score:.3f}")
print(f"  Druggability: {top_target.druggability_score:.3f}")
print(f"  Overall Score: {top_target.overall_score:.3f}")
print(f"\nEvidence Sources: {', '.join(top_target.evidence_sources)}")
print(f"\nKey Findings:")
for finding in top_target.key_findings:
    print(f"  - {finding}")
