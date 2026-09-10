"""Logger protocol interface for pluggable implementations."""

from typing import Any, Protocol


class Logger(Protocol):
    """Pluggable logger interface - implement for different backends."""

    def info(self, event: str, **context: Any) -> None:
        """Log info level event with context."""
        ...

    def error(
        self, event: str, error: Exception | None = None, **context: Any
    ) -> None:
        """Log error level event with optional exception."""
        ...

    def warning(self, event: str, **context: Any) -> None:
        """Log warning level event with context."""
        ...

    def debug(self, event: str, **context: Any) -> None:
        """Log debug level event with context."""
        ...
