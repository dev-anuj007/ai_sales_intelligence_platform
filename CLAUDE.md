# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start: Common Commands

### Setup & Dependencies
```bash
uv sync                          # Install all dependencies
```

### Running Tests
```bash
uv run pytest services/*/tests/ -v                    # All tests
uv run pytest services/pipeline/tests/ -v             # Single service tests
uv run pytest services/*/tests/ --cov=services/ --cov-report=html  # With coverage
```

### Type Checking
```bash
uv run mypy services/           # Strict mode (required before commit)
```

### Development: Ingest & Process Data
```bash
# 1. Ingest sample data
uv run python -m services.pipeline.run_pipeline \
  --input services/pipeline/data/fixtures/shodan_sample.jsonl \
  --db services/storage/db/sales_intel.duckdb \
  --limit 5000

# 2. Score accounts
uv run python -m services.scoring.score_accounts \
  --db services/storage/db/sales_intel.duckdb

# 3. Enrich top accounts (mock LLM)
uv run python -m services.enrichment.run_enrichment \
  --db services/storage/db/sales_intel.duckdb \
  --top-n 50 \
  --client mock
```

### Running the API Server
```bash
uv run uvicorn main:app --reload --port 8001  # Auto-reload on changes
curl http://localhost:8001/health             # Check health
curl http://localhost:8001/accounts?limit=10  # List accounts
```

### Evaluation & Evals
```bash
uv run python services/enrichment/evals/run_eval.py \
  --prompt-version v1 \
  --dataset services/enrichment/evals/datasets/signal_noise_v1.jsonl \
  --client mock
```

---

## Architecture Overview

**Microservices-first backend** with strict three-tier layering: **API → Service → Storage**.

### Core Services

1. **Pipeline** (`services/pipeline/`)
   - Streaming ingest from Shodan zstd files
   - Record normalization, domain extraction, noise filtering
   - Bulk insert into staging_records table

2. **Aggregation** (`services/aggregation/`)
   - GROUP BY root_domain to create accounts
   - Build top-20 records index per account
   - Honeypot-only account detection

3. **Scoring** (`services/scoring/`)
   - Rule-based deterministic risk scoring (0–100)
   - Composite score: vulnerabilities (35%) + exposure (25%) + TLS (15%) + EOL/legacy (15%) + attack surface (10%)
   - Explainable score breakdown with `signal_tags` + `score_explanation` JSON

4. **Enrichment** (`services/enrichment/`)
   - LLM orchestration via LangGraph
   - Haiku for classification, Sonnet for judgment
   - Mock-first design (swap via env var once Anthropic key available)

5. **Storage** (`services/storage/`)
   - Shared data access layer (DuckDB)
   - Protocol-based abstractions (extensible to Postgres, Redis)
   - Repositories: AccountStorageService, StagingStorageService, TraceStorageService

### Three-Tier Layering (Critical)

Each service strictly follows this pattern:

```
api.py          → FastAPI routers + HTTP handling (never touches storage directly)
   ↓
service.py      → Business logic + orchestration (zero HTTP concerns)
   ↓
storage/        → Data access: CRUD + queries
```

**Rule:** `api.py` NEVER directly accesses storage. Always call via `service.py`. This enables:
- 100% testable service layer (mocked storage)
- Loose coupling (storage backend swappable)
- Clear separation of concerns

---

## Engineering Principles (Non-Negotiable)

### 1. SOLID Principles Enforced
- **SRP:** One class per file, one file per class. Each class has exactly one reason to change.
- **OCP:** New features extend without modifying existing code (factory pattern for extractors).
- **LSP:** All implementations honor Protocol contracts.
- **ISP:** Lean Protocol interfaces (only methods implementers need).
- **DIP:** All clients depend on Protocols, not concrete classes.

### 2. Dependency Injection Everywhere
- **Zero global mutable state** (except immutable `config.py` singleton)
- All dependencies passed explicitly via function args or FastAPI `Depends()`
- Makes testing trivial (swap real storage with mock)

```python
# ✅ Correct
@router.post("/accounts")
def list_accounts(service = Depends(get_service)):
    return service.list_accounts()

def get_service() -> AccountService:
    pool = get_pool()
    storage = AccountStorageService(pool.get_connection())
    return AccountService(storage)

# ❌ Wrong: Global storage access
_storage = get_connection()  # Global mutable state
```

### 3. Mock-First Testing
- **90%+ coverage** on service layer with mocked storage
- Tests run offline (<1 second per test, no DB/Docker required)
- Integration tests (< 20) hit tmp DuckDB only
- Real storage tests separate from unit tests

### 4. Type Safety (mypy --strict)
- **100% type annotations** required
- All functions must have argument + return types
- Run `uv run mypy services/` before every commit
- No `Any` except in exceptional cases (document with comment)

### 5. Self-Documenting Code
- **Names are primary documentation.** Code should read like prose.
- Comments only for non-obvious **WHY**, never for **WHAT**.
- Avoid obvious docstrings; let code speak for itself.

```python
# ❌ Obvious comment (don't)
def get_root_domain(domain: str) -> str | None:
    """Extract root domain from a string."""
    return tldextract(domain)

# ✅ Self-documenting (do)
def extract_root_domain(domain: str) -> str | None:
    return tldextract(domain)

# ✅ Comment non-obvious logic
# tldextract needs both domain AND suffix to identify root domain.
# "192.168.1.1" → None (numeric-only, no suffix)
```

### 6. Rule-Based Scoring, Selective LLM Use
- **Scoring is deterministic** (rule-based, <1ms per account, free)
- **LLM for narrative only** (signal/noise re-classification, company inference, risk narratives, outreach drafts)
- Cost transparency: track $/token, enforce cost ceiling

### 7. Anthropic SDK (not LangChain)
- Use raw `anthropic.Anthropic()` API
- Full control over cost tracking (exact token counts)
- All features available, no abstraction overhead
- Easier to mock for testing

---

## Key Constraints & Patterns

### No Global State (except config.py)
Tests must not interfere with each other. Use instance state + dependency injection.

### No Hardcoded Constants
All configuration via `config.py` (Pydantic Settings) + enums. Tune for different deployments, A/B test, respond to production issues.

### No Dynamic SQL or Unsafe Queries
Use parameterized queries always. DuckDB uses ? placeholders, Postgres uses %s.

### Immutable Domain Models
Pydantic models with `frozen = True`. Prevents accidental mutations, makes data flow explicit.

### One Class Per File
Enforced naming: `account_storage.py` contains exactly `AccountStorageService`, `staging_storage.py` contains exactly `StagingStorageService`. Enables fast module navigation.

---

## Storage Backend Extensibility

Current: **DuckDB** (embedded, single-file, single-writer)

All storage services implement `Protocol` interfaces in `services/storage/abstractions.py`:

```python
class StorageService(Protocol[T]):
    def get(self, id_value: Any) -> T | None: ...
    def list(self, limit: int = 100, offset: int = 0) -> list[T]: ...
    def create(self, data: dict) -> T: ...
```

**Adding a new backend:**
1. Create `PostgresStorageService` implementing the Protocol
2. Inject into service: `ScoringService(postgres_storage)`
3. Zero changes to `api.py` or `service.py`

Future backends: PostgreSQL (concurrent writes), Redis (cache), S3 (file storage)

---

## Project Structure

```
/
├── services/                          # Microservices at root (independently deployable)
│   ├── storage/                       # Shared data access layer
│   │   ├── abstractions.py            # Protocol interfaces
│   │   ├── account_storage.py         # Account CRUD
│   │   ├── staging_storage.py         # Staging bulk insert
│   │   ├── trace_storage.py           # Trace logging
│   │   ├── names_storage.py           # Company name cache
│   │   ├── duckdb_connection.py       # Connection pooling
│   │   ├── models.py                  # Domain models (Pydantic)
│   │   ├── migrate.py                 # Schema application
│   │   ├── db/                        # DuckDB files (.gitignore)
│   │   └── tests/
│   │
│   ├── pipeline/                      # Ingest service
│   │   ├── service.py                 # Business logic
│   │   ├── api.py                     # FastAPI routes
│   │   ├── normalizer.py              # Record normalization
│   │   ├── domain_utils.py            # Domain extraction
│   │   ├── noise_filter.py            # Noise detection
│   │   ├── stream_reader.py           # zstd streaming
│   │   ├── data/
│   │   │   ├── fixtures/              # Test data (committed)
│   │   │   └── raw/                   # External input (.gitignore)
│   │   └── tests/
│   │
│   ├── aggregation/                   # Aggregation service
│   │   ├── service.py
│   │   ├── api.py
│   │   └── tests/
│   │
│   ├── scoring/                       # Scoring service
│   │   ├── service.py
│   │   ├── api.py
│   │   └── tests/
│   │
│   └── enrichment/                    # Enrichment service
│       ├── service.py
│       ├── api.py
│       ├── prompts/                   # Versioned prompt templates
│       ├── evals/                     # Eval datasets + results
│       ├── traces/                    # LLM trace logs (.gitignore)
│       └── tests/
│
├── config.py                          # Environment configuration (immutable singleton)
├── main.py                            # FastAPI entry point
├── docs/                              # Comprehensive documentation
│   ├── architecture.md                # Layering, SOLID, deployment
│   ├── how-you-build.md               # Design decisions & rationale
│   ├── planning.md                    # Goals, phases
│   ├── roadmap.md                     # Future phases
│   └── cost_model.md                  # LLM costs & token tracking
├── pyproject.toml                     # Dependencies, pytest config
├── README.md                          # Quick start guide
└── CLAUDE.md                          # This file
```

---

## Testing Strategy

### Unit Tests (Mock-First)
- **Location:** `services/*/tests/`
- **Pattern:** Service layer logic with mocked storage
- **Setup:** `conftest.py` provides mock repositories
- **Target:** 90%+ coverage, <100ms per test
- **Run:** `uv run pytest services/*/tests/ --cov=services/`

### Test Fixtures (Conftest)
```python
# services/pipeline/tests/conftest.py
@pytest.fixture
def mock_staging_storage() -> StagingStorageService:
    return MockStagingStorageService()

def test_ingest_normalizes(mock_staging_storage):
    service = PipelineService(mock_staging_storage)
    result = service.ingest("path/to/file")
    assert result["total_inserted"] > 0
```

### Integration Tests (Rare)
- Only for storage layer
- Hit ephemeral tmp DuckDB
- Marked with `@pytest.mark.integration`
- Run separately: `uv run pytest -m integration`

### Type Checking
- **Strict mode required:** `uv run mypy services/`
- **Before commit:** No warnings, no errors
- **Target:** 100% of codebase, zero Any types

---

## Common Refactoring Patterns

### Adding a New Service

1. Create `services/your_service/` directory
2. Add files: `service.py`, `api.py`, `__init__.py`
3. Create `tests/` with `conftest.py`, `test_service.py`, `test_api.py`
4. Define business logic in `service.py` (zero HTTP knowledge)
5. Define routes in `api.py` with dependency injection
6. Inject into `main.py` router registration
7. Run: `uv run mypy services/` + `uv run pytest services/your_service/tests/`

### Adding a New Storage Backend

1. Create `PostgresStorageService` in `services/storage/postgres_storage.py`
2. Implement Protocol from `abstractions.py`
3. Inject into service: `ScoringService(postgres_storage)`
4. No changes to existing code (open/closed principle)

### Adding a New Feature Extractor

1. Create class (e.g., `VulnerabilityExtractor`)
2. One file per class: `vulnerability_extractor.py`
3. Implement extractor interface: `def extract(record: dict) -> Features`
4. Register in factory if needed
5. Add unit test: `services/pipeline/tests/test_vulnerability_extractor.py`

---

## Code Review Checklist

Before committing, verify:

- [ ] **SOLID:** No SRP violations (one class per file)
- [ ] **Types:** `uv run mypy services/` passes (zero errors)
- [ ] **Tests:** `uv run pytest services/*/tests/ -v` passes
- [ ] **Coverage:** Service layer > 90% coverage
- [ ] **API → Service → Storage:** No shortcuts (api.py never touches storage)
- [ ] **Naming:** Code reads like prose, comments only for non-obvious WHY
- [ ] **No hardcoded constants:** All config via `config.py`
- [ ] **Immutable models:** Domain models use `frozen = True`
- [ ] **Dependency injection:** All dependencies explicit, no globals

---

## Documentation References

- **Quick start:** [README.md](README.md)
- **Architecture deep-dive:** [docs/architecture.md](docs/architecture.md)
- **Design decisions & rationale:** [docs/how-you-build.md](docs/how-you-build.md)
- **Planning & goals:** [docs/planning.md](docs/planning.md)
- **Future roadmap:** [docs/roadmap.md](docs/roadmap.md)
- **LLM costs & token tracking:** [docs/cost_model.md](docs/cost_model.md)

---

## Environment Variables

Configure via `.env` file or CLI. Key variables:

```bash
LLM_CLIENT=mock              # "mock" or "anthropic"
ANTHROPIC_API_KEY=...        # Required if llm_client="anthropic"
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
DUCKDB_PATH=...              # Custom DB path (default: services/storage/db/sales_intel.duckdb)
```

See `config.py` for complete settings list.

---

## Tips for Productivity

1. **Fast iteration:** Use `--reload` flag on uvicorn: `uv run uvicorn main:app --reload`
2. **Single test:** `uv run pytest services/pipeline/tests/test_service.py::test_ingest -v`
3. **Avoid DB setup:** Use mocked storage in tests
4. **Check types early:** Run `mypy` after each file edit
5. **IDE support:** Full type hints enable autocomplete in VS Code, PyCharm
6. **Trace LLM calls:** Check `services/enrichment/traces/llm_traces.jsonl` after enrichment runs

---

## Known Gotchas

- **DuckDB single-writer:** Only one process can write at a time. For concurrent writes, use queue-based pipeline (roadmap) or migrate to Postgres.
- **Protocol vs Concrete:** Always depend on `Protocol[T]`, never `ConcreteStorageService`. This enables swappable backends.
- **Fixtures commit-ready:** Test fixtures in `services/pipeline/data/fixtures/` are committed to git; use small zstd files.
- **Mock-first design:** If a test needs real DuckDB, it should be marked `@pytest.mark.integration` and separated.
