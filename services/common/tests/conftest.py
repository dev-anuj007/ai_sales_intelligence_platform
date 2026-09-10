"""Fixtures for common service tests."""

from typing import Generator
import pytest
from services.logger.context import TraceContext


@pytest.fixture(autouse=True)
def clear_context() -> Generator[None, None, None]:
    """Auto-clear trace context before and after each test."""
    TraceContext.clear()
    yield
    TraceContext.clear()
