"""Tests for the target ranker."""

import pytest
from src.models import AgentState, SearchResult
from src.rankers import TargetRanker


def test_ranker_creation():
    """Test ranker can be created."""
    ranker = TargetRanker()
    assert ranker is not None


def test_ranker_with_empty_state():
    """Test ranker handles empty state."""
    ranker = TargetRanker()
    state = AgentState(disease_query="test")
    
    targets = ranker.rank_targets(state)
    assert targets == []


def test_ranker_with_gwas_results():
    """Test ranker processes GWAS results."""
    ranker = TargetRanker()
    state = AgentState(
        disease_query="test",
        gwas_results=[
            SearchResult(
                source="gwas",
                result_id="1",
                title="Test",
                relevance_score=0.9,
                metadata={"gene": "APOE", "pvalue": 1e-10}
            )
        ]
    )
    
    targets = ranker.rank_targets(state)
    assert len(targets) > 0
    assert targets[0].gene_symbol == "APOE"
    assert targets[0].genetic_score > 0


def test_ranker_sorting():
    """Test targets are sorted by overall score."""
    ranker = TargetRanker()
    state = AgentState(
        disease_query="test",
        gwas_results=[
            SearchResult(
                source="gwas",
                result_id="1",
                title="Low score",
                relevance_score=0.3,
                metadata={"gene": "GENE1", "pvalue": 1e-3}
            ),
            SearchResult(
                source="gwas",
                result_id="2",
                title="High score",
                relevance_score=0.9,
                metadata={"gene": "GENE2", "pvalue": 1e-10}
            )
        ]
    )
    
    targets = ranker.rank_targets(state)
    assert len(targets) == 2
    assert targets[0].overall_score >= targets[1].overall_score
