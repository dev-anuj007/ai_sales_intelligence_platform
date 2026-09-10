"""Fixtures for logger tests."""

import pytest
from services.logger.context import TraceContext


@pytest.fixture(autouse=True)
def clear_context() -> None:
    """Auto-clear trace context before and after each test."""
    TraceContext.clear()
    yield
    TraceContext.clear()
