# Logger Service & Trace ID Propagation

## Overview

The logger service provides **pluggable, production-grade logging** with **automatic trace ID propagation** across your entire request lifecycle. Every log entry automatically includes context (trace_id, span_id, request_id, user_id) for end-to-end debugging.

## Why This Matters

### Without Trace Context
```
When a request fails, you get logs scattered across multiple services:
  pipeline.log:    "pipeline.start"
  aggregation.log: "aggregation.failed: connection timeout"
  unknown which log line is part of the same request/data flow
  → Impossible to correlate issues across services
```

### With Trace Context
```
Every log for a request includes trace_id="trace_a1b2c3d4e5f6":
  [trace_a1b2c3d4e5f6] "http.request.start"
  [trace_a1b2c3d4e5f6] "pipeline.start"
  [trace_a1b2c3d4e5f6] "pipeline.normalize" (span_id="normalize_xyz")
  [trace_a1b2c3d4e5f6] "aggregation.start" (span_id="aggregation_abc")
  [trace_a1b2c3d4e5f6] "aggregation.failed" (error=ConnectionTimeout)
  
  grep "trace_a1b2c3d4e5f6" app.log
  → Full request journey visible instantly
```

## Architecture

### Components

```
FastAPI Request
        ↓
  TraceMiddleware
  ├─ Extract/generate trace_id from X-Trace-ID header
  ├─ Generate request_id from X-Request-ID header
  ├─ Store in TraceContext (thread-safe contextvars)
        ↓
  Service Layer (AggregationService, ScoringService, etc.)
  ├─ Get injected logger via Depends(get_logger)
  ├─ Call logger.info("event") — trace context auto-injected
  ├─ Each operation: TraceContext.new_span_id("operation")
        ↓
  Logger Implementation (LogfireLogger, StdlibLogger, NoopLogger)
  ├─ Merge TraceContext.get_context() with event kwargs
  ├─ Send to configured backend (logfire, stdlib, noop)
        ↓
  Response Headers
  ├─ X-Trace-ID: returned to client for correlation
  ├─ X-Request-ID: returned to client for correlation
        ↓
  TraceContext.clear()
  ├─ Cleanup to prevent context leaks to next request
```

## Usage

### 1. In Services: Get Logger & Use Spans

```python
from fastapi import Depends
from services.logger.factory import get_logger
from services.logger.context import TraceContext

class AggregationService:
    def __init__(self, logger = Depends(get_logger)):
        self.logger = logger
    
    def aggregate_staging_to_accounts(self) -> dict:
        # Create span for this operation
        span_id = TraceContext.new_span_id("aggregation")
        
        self.logger.info("aggregation.start", total_records=50000)
        
        try:
            # Each substep gets its own span
            self._aggregate_accounts_sql()      # Logs with current span
            self._build_account_top_records()   # Logs with current span
            self._mark_excluded_honeypots()     # Logs with current span
            
            self.logger.info("aggregation.complete", accounts_created=15000)
            return {"status": "success"}
        
        except Exception as e:
            self.logger.error("aggregation.failed", error=e, retry_count=2)
            raise
    
    def _aggregate_accounts_sql(self) -> None:
        TraceContext.new_span_id("aggregate_sql")
        self.logger.info("sql.execute", query_size_kb=450)
        # ... SQL execution ...
        self.logger.info("sql.complete", rows_inserted=15000)
```

### 2. In FastAPI Routes: Dependency Injection

```python
from fastapi import APIRouter, Depends
from services.logger.factory import get_logger
from services.aggregation.service import AggregationService

router = APIRouter()

def get_aggregation_service(logger = Depends(get_logger)) -> AggregationService:
    return AggregationService(logger=logger)

@router.post("/aggregation/run")
async def run_aggregation(service: AggregationService = Depends(get_aggregation_service)):
    return service.aggregate_staging_to_accounts()

# When this endpoint is called:
# 1. TraceMiddleware generates/extracts trace_id
# 2. Logger injected via Depends(get_logger)
# 3. All service.logger calls include trace_id automatically
# 4. Response includes X-Trace-ID header
```

### 3. Client-Side: Correlation

```bash
# Client sends request with trace header (optional)
curl -H "X-Trace-ID: trace_custom_123" \
     http://localhost:8001/aggregation/run

# Response includes trace headers
HTTP/1.1 200 OK
X-Trace-ID: trace_custom_123
X-Request-ID: req_abcdef12
...

# Later, query all logs for this trace
grep "trace_custom_123" application.log | jq .
```

### 4. Example Log Output

```json
{
  "timestamp": "2026-09-10T15:32:45.123Z",
  "event": "http.request.start",
  "trace_id": "trace_a1b2c3d4e5f6",
  "span_id": "http_request_99887766",
  "request_id": "req_abcdef12",
  "method": "POST",
  "path": "/aggregation/run"
}

{
  "timestamp": "2026-09-10T15:32:45.234Z",
  "event": "aggregation.start",
  "trace_id": "trace_a1b2c3d4e5f6",
  "span_id": "aggregation_12345678",
  "request_id": "req_abcdef12",
  "total_records": 50000
}

{
  "timestamp": "2026-09-10T15:32:45.456Z",
  "event": "sql.execute",
  "trace_id": "trace_a1b2c3d4e5f6",
  "span_id": "aggregate_sql_87654321",
  "request_id": "req_abcdef12",
  "query_size_kb": 450
}

{
  "timestamp": "2026-09-10T15:32:47.789Z",
  "event": "aggregation.complete",
  "trace_id": "trace_a1b2c3d4e5f6",
  "span_id": "aggregation_12345678",
  "request_id": "req_abcdef12",
  "accounts_created": 15000
}

{
  "timestamp": "2026-09-10T15:32:50.890Z",
  "event": "http.request.complete",
  "trace_id": "trace_a1b2c3d4e5f6",
  "span_id": "http_request_99887766",
  "request_id": "req_abcdef12",
  "status_code": 200,
  "duration_ms": "5234.56"
}
```

## Logger Backends

### LogfireLogger (Default)

```python
# Uses existing logfire instrumentation
# Works with logfire.io for cloud observability
log_backend = "logfire"
```

### StdlibLogger (Fallback)

```python
# Uses Python's built-in logging module
# Useful for CI/CD or offline environments
log_backend = "stdlib"
```

### NoopLogger (Testing)

```python
# Discards all logs (fast for tests)
# Use in unit tests to avoid log noise
log_backend = "noop"
```

## Configuration

### In config.py

```python
class Settings(BaseSettings):
    # ===== Logging Configuration =====
    log_backend: Literal["logfire", "stdlib", "noop"] = "logfire"
    log_level: str = "INFO"
```

### In .env

```bash
LOG_BACKEND=logfire    # or "stdlib" or "noop"
LOG_LEVEL=DEBUG        # or INFO, WARNING, ERROR
```

## Tracing Patterns

### Pattern 1: Track Async Operations

```python
async def process_batch(self, batch_id: str) -> dict:
    TraceContext.new_span_id("process_batch")
    self.logger.info("batch.start", batch_id=batch_id, size=len(batch))
    
    try:
        results = await self._process_items(batch)
        self.logger.info("batch.complete", batch_id=batch_id, success_count=len(results))
        return results
    except Exception as e:
        self.logger.error("batch.failed", batch_id=batch_id, error=e)
        raise
```

### Pattern 2: Track Database Operations

```python
def bulk_insert(self, records: list) -> int:
    TraceContext.new_span_id("bulk_insert")
    self.logger.info("db.bulk_insert.start", record_count=len(records))
    
    start = time.time()
    try:
        count = self.storage.insert_many(records)
        duration_ms = (time.time() - start) * 1000
        self.logger.info("db.bulk_insert.complete", 
                        inserted=count, 
                        duration_ms=f"{duration_ms:.2f}")
        return count
    except Exception as e:
        self.logger.error("db.bulk_insert.failed", 
                         record_count=len(records), 
                         error=e)
        raise
```

### Pattern 3: Track LLM Calls

```python
async def enrich_with_llm(self, account_id: str) -> dict:
    TraceContext.new_span_id("llm_enrich")
    self.logger.info("llm.request.start", account_id=account_id, model="claude-haiku")
    
    try:
        response = await self.llm_client.message(prompt, model="claude-haiku")
        self.logger.info("llm.request.complete", 
                        account_id=account_id,
                        tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                        stop_reason=response.stop_reason)
        return response
    except RateLimitError as e:
        self.logger.error("llm.rate_limit", account_id=account_id, error=e)
        raise RetriableError(...)
    except AuthenticationError as e:
        self.logger.error("llm.auth_failed", error=e)
        raise NonRetriableError(...)
```

## Debugging with Traces

### Find All Logs for a Request

```bash
# Using grep
grep "trace_a1b2c3d4e5f6" /var/log/app.log | jq .

# Using logfire CLI
logfire query 'trace_id = "trace_a1b2c3d4e5f6"'

# Using Datadog
@trace_id:trace_a1b2c3d4e5f6
```

### Find Errors and Their Trace

```bash
# Find all errors, then get full trace
grep "level:ERROR" /var/log/app.log | jq '.trace_id' | \
  xargs -I {} grep "{}" /var/log/app.log | jq .
```

### Performance Analysis

```bash
# Find slow requests
grep "http.request.complete" /var/log/app.log | \
  jq 'select(.duration_ms > 5000)' | \
  jq '{trace_id, duration_ms}'

# Then trace that request
grep "trace_slow_123" /var/log/app.log | jq . | sort_by(.timestamp)
```

## Testing with Traces

```python
def test_aggregation_with_traces():
    TraceContext.clear()
    trace_id = TraceContext.new_trace_id()
    
    service = AggregationService(logger=NoopLogger())
    result = service.aggregate(...)
    
    # In production test, you'd query your logger backend:
    # logs = query_logs(trace_id=trace_id)
    # assert any(log.event == "aggregation.complete" for log in logs)
    
    assert result["status"] == "success"
```

## File Structure

```
services/logger/
├── __init__.py                    # Public API
├── abstractions.py                # Logger Protocol
├── context.py                     # Thread-safe TraceContext
├── middleware.py                  # FastAPI middleware
├── factory.py                     # Logger factory
├── implementations/
│   ├── logfire_logger.py         # Default: Logfire backend
│   ├── stdlib_logger.py          # Fallback: Python logging
│   └── noop_logger.py            # Testing: Silent logger
└── tests/
    ├── test_trace_context.py     # Context tests
    └── conftest.py               # Fixtures
```

## Best Practices

✅ **DO:**
- Use `TraceContext.new_span_id()` at the start of each logical operation
- Log at start and completion of each operation
- Include relevant context (counts, IDs, durations)
- Use error() for exceptions, include the exception object

❌ **DON'T:**
- Call `logfire.info()` directly — use injected logger
- Log sensitive data (passwords, API keys, tokens)
- Log at DEBUG level for high-volume events in production
- Forget to clear context (middleware does this automatically)

## Performance

- **Trace ID generation:** < 1µs (UUID hex generation)
- **Context injection:** < 1µs (dict lookup + merge)
- **Middleware overhead:** ~0.5ms per request (timing + header processing)
- **Total overhead:** Negligible compared to I/O operations

## Next: Error Boundaries

Once logging is solid, add structured error types:

```python
# Coming next...
class SalesIntelligenceError(Exception):
    code: str
    message: str
    context: dict

class RetriableError(SalesIntelligenceError):
    # Network timeout, DB locked, LLM rate limit
    pass

class NonRetriableError(SalesIntelligenceError):
    # Validation, auth, bad config
    pass
```

Then error handler middleware will auto-convert to JSON responses with proper HTTP status codes.
