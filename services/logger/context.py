"""Trace context management for request lifecycle and distributed tracing."""

import contextvars
from typing import Any
from uuid import uuid4


trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)
span_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "span_id", default=""
)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)


class TraceContext:
    """Thread-safe context management for trace IDs and request metadata."""

    @staticmethod
    def set_trace_id(trace_id: str) -> None:
        """Set trace ID (correlates entire request flow)."""
        trace_id_var.set(trace_id)

    @staticmethod
    def get_trace_id() -> str:
        """Get current trace ID or empty string if not set."""
        return trace_id_var.get()

    @staticmethod
    def new_trace_id() -> str:
        """Generate and set new trace ID."""
        trace_id = f"trace_{uuid4().hex[:12]}"
        trace_id_var.set(trace_id)
        return trace_id

    @staticmethod
    def set_span_id(span_id: str) -> None:
        """Set span ID (correlates single operation)."""
        span_id_var.set(span_id)

    @staticmethod
    def get_span_id() -> str:
        """Get current span ID or empty string if not set."""
        return span_id_var.get()

    @staticmethod
    def new_span_id(operation: str) -> str:
        """Generate and set new span ID for operation."""
        span_id = f"{operation}_{uuid4().hex[:8]}"
        span_id_var.set(span_id)
        return span_id

    @staticmethod
    def set_request_id(request_id: str) -> None:
        """Set HTTP request ID."""
        request_id_var.set(request_id)

    @staticmethod
    def get_request_id() -> str:
        """Get current request ID or empty string if not set."""
        return request_id_var.get()

    @staticmethod
    def set_user_id(user_id: str | None) -> None:
        """Set authenticated user ID."""
        user_id_var.set(user_id)

    @staticmethod
    def get_user_id() -> str | None:
        """Get current user ID or None if not set."""
        return user_id_var.get()

    @staticmethod
    def get_context() -> dict[str, Any]:
        """Return all context as dict for automatic injection into logs."""
        context: dict[str, Any] = {
            "trace_id": TraceContext.get_trace_id(),
            "span_id": TraceContext.get_span_id(),
            "request_id": TraceContext.get_request_id(),
        }
        user_id = TraceContext.get_user_id()
        if user_id:
            context["user_id"] = user_id
        return context

    @staticmethod
    def clear() -> None:
        """Clear all context (cleanup after request)."""
        trace_id_var.set("")
        span_id_var.set("")
        request_id_var.set("")
        user_id_var.set(None)
