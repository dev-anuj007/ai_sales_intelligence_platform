from __future__ import annotations

import pytest

from services.llm.cost_model import CostTracker
from services.llm.mock_client import MockLLMClient


@pytest.fixture
def cost_tracker() -> CostTracker:
    """Fresh cost tracker for each test."""
    return CostTracker()


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Mock LLM client for testing (zero API calls)."""
    return MockLLMClient()
