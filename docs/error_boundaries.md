# Error Boundaries & Structured Exception Handling

## Overview

**Foundation Layer #2** provides structured error types and automatic error-to-response conversion for production-grade error handling.

### Problem Solved
- No distinction between transient (retry-able) and permanent errors
- Generic exceptions hard to debug and don't guide retry decisions
- No automatic conversion of exceptions to HTTP responses
- No coordinated retry/backoff strategy

## Error Hierarchy

```
Exception
  └── SalesIntelligenceError (structured, application-level)
      ├── RetriableError (transient, safe to retry)
      │   └── Network timeout, DB pool busy, rate limit
      └── NonRetriableError (permanent, don't retry)
          └── Validation error, auth failed, not found
```

## Using Error Types

### Define Clear Error Codes

```python
from services.common.errors import RetriableError, NonRetriableError

# Transient error (retry-able)
raise RetriableError(
    code="DB_CONNECTION_TIMEOUT",
    message="Failed to connect to database after 3 attempts",
    context={"service": "pipeline", "operation": "bulk_insert", "retry_count": 2},
)

# Permanent error (don't retry)
raise NonRetriableError(
    code="INVALID_ACCOUNT_ID",
    message="Account ID must be a valid UUID",
    context={"provided_id": "not-a-uuid"},
)

# Preserve original exception as cause
try:
    db.connect()
except ConnectionError as e:
    raise RetriableError(
        code="DB_CONNECTION_FAILED",
        message=f"Database unavailable: {str(e)}",
        cause=e,
    )
```

## Error Handler Middleware

The middleware automatically converts errors to JSON responses:

| Error Type | HTTP Status | Client Action |
|-----------|------------|---------------|
| `RetriableError` | 429 (Too Many Requests) | Retry with backoff |
| `NonRetriableError` | 400 (Bad Request) | Don't retry, fix input |
| Other `Exception` | 500 (Internal Error) | Don't retry, report |

### Example Responses

**RetriableError:**
```json
HTTP/1.1 429 Too Many Requests

{
  "error": "DB_CONNECTION_TIMEOUT",
  "message": "Failed to connect to database after 3 attempts",
  "context": {
    "service": "pipeline",
    "retry_count": 2
  }
}
```

**NonRetriableError:**
```json
HTTP/1.1 400 Bad Request

{
  "error": "INVALID_ACCOUNT_ID",
  "message": "Account ID must be a valid UUID",
  "context": {
    "provided_id": "not-a-uuid"
  }
}
```

## Retry Strategies

### Decorator: Sync Functions

```python
from services.common.retry import retry_on_retriable_error
from services.common.errors import RetriableError

@retry_on_retriable_error(max_retries=3, initial_delay_ms=100)
def fetch_from_external_api():
    response = requests.get("https://api.example.com/data")
    if response.status_code == 429:
        raise RetriableError("RATE_LIMIT", "API rate limited, retry later")
    return response.json()

# On RetriableError: retries up to 3 times with exponential backoff
# Delays: 100ms, 200ms, 400ms (backoff_factor=2.0)
# On NonRetriableError: raises immediately, no retry
```

### Decorator: Async Functions

```python
from services.common.retry import async_retry_on_retriable_error

@async_retry_on_retriable_error(
    max_retries=5,
    initial_delay_ms=50,
    max_delay_ms=5000,
    backoff_factor=2.0,
)
async def enrich_account_with_llm(account_id: str):
    try:
        response = await llm_client.message(prompt)
        return response
    except Exception as e:
        raise RetriableError(
            code="LLM_UNAVAILABLE",
            message="LLM service temporarily unavailable",
            cause=e,
        )
```

### Configuration

```python
@retry_on_retriable_error(
    max_retries=3,           # Retry up to 3 times
    initial_delay_ms=100,    # Start with 100ms delay
    max_delay_ms=10000,      # Cap delay at 10 seconds
    backoff_factor=2.0,      # Double delay each time
)
def my_function():
    pass

# Delay sequence: 100ms → 200ms → 400ms (or until max_delay_ms)
# Total attempts: 4 (initial + 3 retries)
```

## Error Context Best Practices

### Include Relevant Data

```python
# ✅ Good: Include context for debugging
raise RetriableError(
    code="LLM_RATE_LIMIT",
    message="LLM API rate limited",
    context={
        "remaining_tokens": 0,
        "reset_at": "2026-09-10T15:32:50Z",
        "operation": "enrich_account",
        "account_id": "acc_123",
    },
)

# ❌ Bad: No context
raise RetriableError("ERROR", "Something failed")

# ❌ Bad: Sensitive data
raise NonRetriableError(
    code="AUTH_FAILED",
    message="Auth failed",
    context={"password": "secret123"},  # Never log passwords!
)
```

### Error Code Naming

```python
# Prefix_Category format
# Prefix: Service/Component (DB_, LLM_, STORAGE_)
# Category: Type of error (TIMEOUT, RATE_LIMIT, NOT_FOUND)

RetriableError: DB_CONNECTION_TIMEOUT, LLM_RATE_LIMIT, NETWORK_TIMEOUT
NonRetriableError: INVALID_INPUT, ACCOUNT_NOT_FOUND, AUTH_FAILED
```

## Logging Integration

All errors are automatically logged with trace context:

```
[trace_a1b2c3d4e5f6] error.retriable
  code=DB_CONNECTION_TIMEOUT
  error=ConnectionError('connection refused')
  span_id=retry_attempt_xyz
  attempt=2
  max_retries=3
  next_delay_ms=200
```

## Common Error Scenarios

### Database Errors

```python
from services.common.errors import RetriableError, NonRetriableError

try:
    db.insert_records(records)
except asyncpg.TooManyConnectionsError:
    raise RetriableError(
        code="DB_POOL_EXHAUSTED",
        message="Database connection pool exhausted",
        context={"record_count": len(records)},
    )
except asyncpg.PostgresError as e:
    raise RetriableError(
        code="DB_ERROR",
        message="Database operation failed",
        cause=e,
    )
except ValueError as e:
    raise NonRetriableError(
        code="INVALID_RECORD_FORMAT",
        message="Record format validation failed",
        cause=e,
    )
```

### LLM Errors

```python
import anthropic

try:
    response = client.messages.create(model="claude-opus", messages=[...])
except anthropic.RateLimitError:
    raise RetriableError(
        code="LLM_RATE_LIMIT",
        message="LLM API rate limited",
    )
except anthropic.AuthenticationError:
    raise NonRetriableError(
        code="LLM_AUTH_FAILED",
        message="Invalid API key or authentication failed",
    )
except anthropic.APIError as e:
    raise RetriableError(
        code="LLM_API_ERROR",
        message="LLM API error",
        cause=e,
    )
```

### Input Validation

```python
from pydantic import ValidationError

try:
    account = Account(**data)
except ValidationError as e:
    raise NonRetriableError(
        code="VALIDATION_ERROR",
        message=f"Invalid account data: {e.error_count()} field(s) failed validation",
        context={"errors": e.errors()},
    )
```

## Testing Error Handling

```python
import pytest
from services.common.errors import RetriableError, NonRetriableError

def test_converts_db_timeout_to_retriable_error():
    with pytest.raises(RetriableError) as exc_info:
        my_service.bulk_insert(records)
    
    assert exc_info.value.code == "DB_CONNECTION_TIMEOUT"
    assert exc_info.value.context["retry_count"] == 2

def test_converts_validation_error_to_non_retriable():
    with pytest.raises(NonRetriableError) as exc_info:
        my_service.validate_account(invalid_data)
    
    assert exc_info.value.code == "VALIDATION_ERROR"
```

## Next: Resilience Patterns

Once error boundaries are solid, add:

1. **Circuit Breaker** — Stop retrying on repeated failures
2. **Bulkhead** — Isolate failures to specific resources
3. **Fallback** — Graceful degradation (rule-based scoring if LLM unavailable)
4. **Dead Letter Queue** — Persist failed operations for replay

Example:
```python
from services.common.resilience import circuit_breaker, bulkhead

@circuit_breaker(failure_threshold=5, timeout_ms=30000)
@bulkhead(max_concurrent=10)
@retry_on_retriable_error(max_retries=3)
async def call_external_service():
    pass
```

## File Structure

```
services/common/
├── __init__.py           # Public API
├── errors.py             # SalesIntelligenceError, RetriableError, NonRetriableError
├── error_handler.py      # ErrorResponseHandler (OOP design)
├── retry.py              # ExponentialBackoffRetry, AsyncExponentialBackoffRetry
└── tests/
    ├── test_errors.py    # Error type tests
    └── test_retry.py     # Retry logic tests (12 passing)
```

## Wired Into FastAPI

In `main.py`:
```python
from services.common.errors import RetriableError, NonRetriableError
from services.common.error_handler import error_handler

app.add_exception_handler(RetriableError, error_handler)
app.add_exception_handler(NonRetriableError, error_handler)
```

All unhandled errors automatically logged, traced, and returned as JSON.
