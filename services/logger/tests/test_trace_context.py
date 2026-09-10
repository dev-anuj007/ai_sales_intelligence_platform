"""Tests for trace context propagation and logger integration."""

import pytest
from services.logger.context import TraceContext
from services.logger.factory import create_logger
from services.logger.implementations.noop_logger import NoopLogger


def test_trace_context_generates_unique_trace_ids() -> None:
    """Trace IDs should be unique on each generation."""
    TraceContext.clear()
    trace_id_1 = TraceContext.new_trace_id()
    trace_id_2 = TraceContext.new_trace_id()
    assert trace_id_1.startswith("trace_")
    assert trace_id_2.startswith("trace_")
    assert trace_id_1 != trace_id_2


def test_trace_context_persists_within_request() -> None:
    """Trace ID should persist across multiple operations."""
    TraceContext.clear()
    trace_id = TraceContext.new_trace_id()

    # Simulate multiple service calls within single request
    assert TraceContext.get_trace_id() == trace_id
    assert TraceContext.get_trace_id() == trace_id


def test_span_id_tracks_operation() -> None:
    """Each operation should get unique span ID while maintaining trace ID."""
    TraceContext.clear()
    trace_id = TraceContext.new_trace_id()

    span_1 = TraceContext.new_span_id("operation_1")
    assert TraceContext.get_span_id() == span_1
    assert TraceContext.get_trace_id() == trace_id

    span_2 = TraceContext.new_span_id("operation_2")
    assert TraceContext.get_span_id() == span_2
    assert TraceContext.get_trace_id() == trace_id  # Unchanged

    assert span_1 != span_2


def test_context_cleared_after_request() -> None:
    """Context should be cleared to prevent leaks between requests."""
    TraceContext.set_trace_id("trace_123")
    TraceContext.set_request_id("req_456")
    TraceContext.set_user_id("user_789")

    assert TraceContext.get_trace_id() != ""
    assert TraceContext.get_request_id() != ""
    assert TraceContext.get_user_id() is not None

    TraceContext.clear()

    assert TraceContext.get_trace_id() == ""
    assert TraceContext.get_request_id() == ""
    assert TraceContext.get_user_id() is None


def test_get_context_returns_all_fields() -> None:
    """get_context should return all active context fields."""
    TraceContext.clear()
    TraceContext.set_trace_id("trace_abc")
    TraceContext.set_request_id("req_xyz")
    TraceContext.set_span_id("span_123")
    TraceContext.set_user_id("user_alice")

    context = TraceContext.get_context()

    assert context["trace_id"] == "trace_abc"
    assert context["request_id"] == "req_xyz"
    assert context["span_id"] == "span_123"
    assert context["user_id"] == "user_alice"


def test_user_id_optional_in_context() -> None:
    """User ID should be omitted from context if not set."""
    TraceContext.clear()
    TraceContext.set_trace_id("trace_xyz")

    context = TraceContext.get_context()

    assert "trace_id" in context
    assert "user_id" not in context  # Omitted if None


def test_noop_logger_discards_logs() -> None:
    """NoopLogger should discard all logs without error."""
    logger = NoopLogger()

    # Should not raise
    logger.info("test.event", key="value")
    logger.warning("test.warning")
    logger.debug("test.debug")
    logger.error("test.error", error=Exception("test"))


def test_logger_factory_creates_noop() -> None:
    """Factory should create NoopLogger when backend is 'noop'."""
    logger = create_logger("noop")
    assert isinstance(logger, NoopLogger)


def test_logger_context_injection() -> None:
    """Logger implementation should inject trace context automatically."""
    TraceContext.clear()
    TraceContext.set_trace_id("trace_test_123")
    TraceContext.set_request_id("req_test_456")

    logger = NoopLogger()
    # Should not raise even though noop discards it
    logger.info("test.event", extra_field="value")
