"""Test configuration and fixtures."""

import pytest
from unittest.mock import patch
import os


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "NCBI_EMAIL": "test@example.com",
        "LLM_MODEL": "gpt-4o",
    }):
        yield


@pytest.fixture
def sample_disease():
    """Sample disease query for testing."""
    return "Alzheimer's disease"


@pytest.fixture
def sample_proteins():
    """Sample protein list for testing."""
    return ["APOE", "APP", "PSEN1", "MAPT"]
