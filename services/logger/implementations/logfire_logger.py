"""Logfire backend implementation for logger service."""

import logfire
from typing import Any

from services.logger.abstractions import Logger
from services.logger.context import TraceContext


class LogfireLogger(Logger):
    """Logfire-backed logger with automatic trace context injection."""

    def info(self, event: str, **context: Any) -> None:
        """Log info level event with context."""
        full_context = {**TraceContext.get_context(), **context}
        logfire.info(event, **full_context)

    def error(
        self, event: str, error: Exception | None = None, **context: Any
    ) -> None:
        """Log error level event with optional exception."""
        full_context = {**TraceContext.get_context(), **context}
        if error:
            full_context["error"] = str(error)
            full_context["error_type"] = type(error).__name__
        logfire.error(event, **full_context)

    def warning(self, event: str, **context: Any) -> None:
        """Log warning level event with context."""
        full_context = {**TraceContext.get_context(), **context}
        logfire.warning(event, **full_context)

    def debug(self, event: str, **context: Any) -> None:
        """Log debug level event with context."""
        full_context = {**TraceContext.get_context(), **context}
        logfire.debug(event, **full_context)
