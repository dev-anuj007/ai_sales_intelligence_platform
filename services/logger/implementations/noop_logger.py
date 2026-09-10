"""No-op logger for testing and silent operation."""

from typing import Any

from services.logger.abstractions import Logger


class NoopLogger(Logger):
    """No-operation logger that discards all events (for testing)."""

    def info(self, event: str, **context: Any) -> None:
        """Discard info event."""
        pass

    def error(
        self, event: str, error: Exception | None = None, **context: Any
    ) -> None:
        """Discard error event."""
        pass

    def warning(self, event: str, **context: Any) -> None:
        """Discard warning event."""
        pass

    def debug(self, event: str, **context: Any) -> None:
        """Discard debug event."""
        pass
