from __future__ import annotations

import pytest

from services.llm.mock_client import MockLLMClient


@pytest.fixture
def mock_connection() -> None:
    pass


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Mock LLM client for enrichment tests (zero API calls, deterministic responses)."""
    return MockLLMClient()
