from __future__ import annotations

import pytest

from services.llm.cost_model import CostTracker


@pytest.fixture
def cost_tracker() -> CostTracker:
    """Fresh cost tracker for each test."""
    return CostTracker()
