"""Tests for retry logic with exponential backoff."""

import pytest
import asyncio
from services.common.errors import RetriableError, NonRetriableError
from services.common.retry import (
    retry_on_retriable_error,
    async_retry_on_retriable_error,
)


def test_retry_succeeds_on_first_attempt() -> None:
    """Function should return immediately if no error."""
    call_count = 0

    @retry_on_retriable_error(max_retries=3)
    def succeed_immediately():
        nonlocal call_count
        call_count += 1
        return "success"

    result = succeed_immediately()
    assert result == "success"
    assert call_count == 1


def test_retry_succeeds_on_second_attempt() -> None:
    """Function should retry once and succeed."""
    call_count = 0

    @retry_on_retriable_error(max_retries=3, initial_delay_ms=1)
    def fail_once():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RetriableError("TEMP_ERROR", "Temporary failure")
        return "success"

    result = fail_once()
    assert result == "success"
    assert call_count == 2


def test_retry_exhausts_after_max_attempts() -> None:
    """Function should raise after exhausting retries."""
    call_count = 0

    @retry_on_retriable_error(max_retries=2, initial_delay_ms=1)
    def always_fail():
        nonlocal call_count
        call_count += 1
        raise RetriableError("TEMP_ERROR", "Always fails")

    with pytest.raises(RetriableError):
        always_fail()

    assert call_count == 3  # Initial + 2 retries


def test_retry_does_not_catch_non_retriable_error() -> None:
    """Retry should not catch NonRetriableError."""
    call_count = 0

    @retry_on_retriable_error(max_retries=3)
    def fail_with_non_retriable():
        nonlocal call_count
        call_count += 1
        raise NonRetriableError("INVALID_INPUT", "Bad input")

    with pytest.raises(NonRetriableError):
        fail_with_non_retriable()

    assert call_count == 1  # No retries


def test_retry_backoff_increases_delay() -> None:
    """Delay should increase exponentially between retries."""
    import time

    call_times: list[float] = []

    @retry_on_retriable_error(
        max_retries=2, initial_delay_ms=10, backoff_factor=2.0
    )
    def track_timing():
        call_times.append(time.time())
        if len(call_times) < 3:
            raise RetriableError("TEMP_ERROR", "Retry me")
        return "success"

    result = track_timing()
    assert result == "success"
    assert len(call_times) == 3

    # Check delays are increasing (with some tolerance for system variation)
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]
    assert delay2 > delay1  # Second delay should be longer
