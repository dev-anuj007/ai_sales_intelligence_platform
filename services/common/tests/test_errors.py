"""Tests for error types and error handling."""

import pytest
from services.common.errors import (
    SalesIntelligenceError,
    RetriableError,
    NonRetriableError,
)


def test_sales_intelligence_error_basic() -> None:
    """Base error should store code and message."""
    error = SalesIntelligenceError(
        code="TEST_ERROR",
        message="Test error message",
    )
    assert error.code == "TEST_ERROR"
    assert error.message == "Test error message"
    assert error.context == {}
    assert error.cause is None


def test_sales_intelligence_error_with_context() -> None:
    """Error should store context dict."""
    context = {"service": "pipeline", "operation": "ingest", "retry_count": 2}
    error = SalesIntelligenceError(
        code="DB_TIMEOUT",
        message="Database connection timeout",
        context=context,
    )
    assert error.context == context


def test_sales_intelligence_error_with_cause() -> None:
    """Error should preserve original exception as cause."""
    original = Exception("Original error")
    error = SalesIntelligenceError(
        code="WRAPPED_ERROR",
        message="Wrapped original error",
        cause=original,
    )
    assert error.cause is original


def test_sales_intelligence_error_to_dict() -> None:
    """Error should convert to dict for JSON response."""
    error = SalesIntelligenceError(
        code="API_ERROR",
        message="API call failed",
        context={"endpoint": "/accounts", "status_code": 500},
    )
    result = error.to_dict()
    assert result["error"] == "API_ERROR"
    assert result["message"] == "API call failed"
    assert result["context"]["endpoint"] == "/accounts"


def test_retriable_error_is_subclass() -> None:
    """RetriableError should be subclass of SalesIntelligenceError."""
    error = RetriableError(
        code="NETWORK_TIMEOUT",
        message="Request timed out",
    )
    assert isinstance(error, SalesIntelligenceError)
    assert error.code == "NETWORK_TIMEOUT"


def test_non_retriable_error_is_subclass() -> None:
    """NonRetriableError should be subclass of SalesIntelligenceError."""
    error = NonRetriableError(
        code="VALIDATION_ERROR",
        message="Invalid input",
    )
    assert isinstance(error, SalesIntelligenceError)
    assert error.code == "VALIDATION_ERROR"


def test_error_inheritance_chain() -> None:
    """Error hierarchy should be: Exception -> SalesIntelligenceError -> Specific."""
    retriable = RetriableError("CODE", "message")
    non_retriable = NonRetriableError("CODE", "message")

    assert isinstance(retriable, SalesIntelligenceError)
    assert isinstance(retriable, Exception)
    assert isinstance(non_retriable, SalesIntelligenceError)
    assert isinstance(non_retriable, Exception)

    assert not isinstance(retriable, NonRetriableError)
    assert not isinstance(non_retriable, RetriableError)
