"""Tests for the PubMed tool."""

import pytest
from src.tools.pubmed_tool import PubMedTool


def test_pubmed_tool_creation():
    """Test PubMed tool can be created."""
    tool = PubMedTool()
    assert tool is not None
    assert tool.max_results > 0


def test_pubmed_search_returns_results():
    """Test PubMed search returns SearchResult objects."""
    tool = PubMedTool()
    results = tool.search("diabetes", "insulin")
    
    assert isinstance(results, list)
    # Results may be empty if API is unavailable, but should be a list
    if results:
        assert results[0].source == "pubmed"
        assert results[0].result_id
        assert 0 <= results[0].relevance_score <= 1


def test_pubmed_relevance_calculation():
    """Test relevance scoring logic."""
    tool = PubMedTool()
    
    high_relevance = tool._calculate_relevance(
        "Therapeutic target for diabetes treatment",
        "This protein is a drug target for clinical trials"
    )
    
    low_relevance = tool._calculate_relevance(
        "Generic title",
        "Generic abstract with no keywords"
    )
    
    assert high_relevance > low_relevance
    assert 0 <= high_relevance <= 1
    assert 0 <= low_relevance <= 1
