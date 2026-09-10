"""Python stdlib logging backend implementation."""

import json
import logging
from typing import Any

from services.logger.abstractions import Logger
from services.logger.context import TraceContext


class StdlibLogger(Logger):
    """Python stdlib logging backend with structured JSON output."""

    def __init__(self, name: str = "sales_intel") -> None:
        self.logger = logging.getLogger(name)

    def info(self, event: str, **context: Any) -> None:
        """Log info level event with context."""
        full_context = {**TraceContext.get_context(), **context}
        self.logger.info(f"{event} {json.dumps(full_context)}")

    def error(
        self, event: str, error: Exception | None = None, **context: Any
    ) -> None:
        """Log error level event with optional exception."""
        full_context = {**TraceContext.get_context(), **context}
        if error:
            full_context["error"] = str(error)
            full_context["error_type"] = type(error).__name__
        self.logger.error(f"{event} {json.dumps(full_context)}", exc_info=error)

    def warning(self, event: str, **context: Any) -> None:
        """Log warning level event with context."""
        full_context = {**TraceContext.get_context(), **context}
        self.logger.warning(f"{event} {json.dumps(full_context)}")

    def debug(self, event: str, **context: Any) -> None:
        """Log debug level event with context."""
        full_context = {**TraceContext.get_context(), **context}
        self.logger.debug(f"{event} {json.dumps(full_context)}")
