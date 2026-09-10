"""FastAPI middleware for automatic trace context propagation."""

import time
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from services.logger.context import TraceContext
from services.logger.factory import get_logger_sync

logger = get_logger_sync()


class TraceMiddleware(BaseHTTPMiddleware):
    """Middleware that captures/generates trace IDs and manages request context.

    - Extracts X-Trace-ID header or generates new trace ID
    - Extracts X-Request-ID header or generates new request ID
    - Sets up trace context for entire request lifecycle
    - Logs request start/completion with timing
    - Includes trace/request IDs in response headers
    - Cleans up context after request completes
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Extract or generate trace ID from headers
        trace_id = request.headers.get("X-Trace-ID", f"trace_{uuid4().hex[:12]}")
        request_id = request.headers.get(
            "X-Request-ID", f"req_{uuid4().hex[:8]}"
        )

        # Set context for this request (thread-safe via contextvars)
        TraceContext.set_trace_id(trace_id)
        TraceContext.set_request_id(request_id)
        TraceContext.new_span_id("http_request")

        start_time = time.time()

        try:
            logger.info(
                "http.request.start",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
            )

            response: Response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "http.request.complete",
                status_code=response.status_code,
                duration_ms=f"{duration_ms:.2f}",
            )

            # Add trace/request IDs to response headers for client correlation
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "http.request.failed",
                error=e,
                duration_ms=f"{duration_ms:.2f}",
            )
            raise

        finally:
            # Always cleanup context to prevent leaks
            TraceContext.clear()
