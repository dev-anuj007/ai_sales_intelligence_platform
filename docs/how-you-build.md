# How You Build: Decisions & Rationale

## Architecture Decisions

### Decision 1: Microservices-First at Root Level

**Choice:** Services in `/services/` at root, not nested in `src/sales_intel/`

**Why:**
- Each service is independently deployable (extract `/services/pipeline` → new repo)
- Simpler imports: `from services.pipeline.service` vs `from sales_intel.services.pipeline.ingest_service`
- Scales: can become separate Docker containers, Lambda functions, etc.
- Clear boundaries: Service owns its service.py, api.py, tests/

**Trade-off:** Flatter structure (less hierarchy) vs traditional layered architecture

**Decision:** Flat wins for modern cloud-native development

### Decision 2: Service-Oriented Layering (API → Service → Storage)

**Pattern:**
```
api.py           [HTTP only - FastAPI routers]
   ↓
service.py       [Business logic - orchestration]
   ↓
storage/         [Data access - CRUD + queries]
```

**Why:**
- api.py NEVER directly accesses storage (enforced in code review)
- service.py is 100% testable with mocked storage (zero DB required)
- Easy to swap storage backend (DuckDB → Postgres → Redis)
- Clear separation of concerns (HTTP, logic, data)

**Example violation (DON'T):**
```python
# ❌ WRONG: api.py directly calls storage
@router.post("/accounts")
def get_accounts(storage = Depends(get_storage)):
    return storage.list_accounts()  # Direct storage access = tight coupling
```

**Correct pattern (DO):**
```python
# ✅ RIGHT: api.py calls service, service calls storage
@router.post("/accounts")
def get_accounts(service = Depends(get_service)):
    return service.list_accounts()  # Via service layer
```

### Decision 3: Protocol-Based Abstractions (not Concrete Classes)

**Choice:** All storage accessed via Protocol interfaces, not direct classes

```python
# abstractions.py
class StorageService(Protocol[T]):
    def get(self, id_value: Any) -> T | None: ...
    def list(self, limit: int = 100, offset: int = 0) -> list[T]: ...

# service.py
class ScoringService:
    def __init__(self, account_storage: StorageService[Account]):  # Protocol, not class!
        self.storage = account_storage
```

**Why:**
- Loose coupling: service doesn't care if storage is DuckDB, Postgres, or Redis
- Testing: inject MockStorageService (100% code path coverage without DB)
- Future backends: add PostgresStorageService without changing service.py
- SOLID: Dependency Inversion Principle

**Trade-off:** Slightly more code (protocol definition) vs type safety + extensibility

**Decision:** Extra code is worth it (future-proof)

### Decision 4: Dependency Injection Everywhere

**Pattern:**
```python
# services/pipeline/api.py
def get_ingest_service() -> PipelineService:
    pool = get_pool()
    conn = pool.get_connection()
    storage = StagingStorageService(conn)
    return PipelineService(storage)

@router.post("/ingest")
def ingest(service = Depends(get_ingest_service)):
    return service.ingest()
```

**Why:**
- Zero global state (except config.py singleton)
- Testable: replace storage with mock in tests
- No hidden dependencies (everything explicit)
- Easier to debug: control flow is clear

**Trade-off:** More boilerplate (Depends() factory functions) vs testability

**Decision:** Boilerplate is worth clean testability

### Decision 5: Rule-Based Scoring (not LLM)

**Choice:** Scoring is deterministic (rules), LLM for language only

**Scoring rules** (no LLM):
```python
vuln_score = 100 * (0.5 * max_cvss/10 + 0.5 * max_epss) + min(20, 4 * critical_count)
exposure_score = (35 if db_exposed else 0) + (30 if legacy else 0) + (25 if iot else 0)
composite_score = 0.35 * vuln_score + 0.25 * exposure_score + ...
```

**Why:**
- Deterministic: same input → same score (no randomness)
- Auditable: score explanation is JSON breakdown of rules
- Fast: <1ms per account
- Free: no LLM cost
- Explainable: sales can understand "you scored 75 because: 3 CVEs (9.2 CVSS) + exposed DB"

**LLM use cases** (selective):
- Signal/noise re-classification (is this really a threat?)
- Company name inference (from domain + titles)
- Risk narrative (business-friendly explanation)
- Outreach draft (personalized email)

**Decision:** Rules for scoring (repeatable), LLM for narrative (high-value)

### Decision 6: Mock-First Testing

**Pattern:**
```python
# services/pipeline/tests/conftest.py
@pytest.fixture
def mock_storage():
    return MockStagingStorageService()  # Zero DB calls

def test_ingest_normalizes():
    service = PipelineService(mock_storage)
    result = service.ingest("path/to/file.jsonl.zst")
    assert result["total_inserted"] > 0
    # Test runs in <100ms, zero infrastructure required
```

**Why:**
- Tests run offline (no Docker, no database)
- Tests are fast (<1s per test, 90%+ coverage)
- CI/CD pipeline is simple (just `pytest`)
- Developers can test locally without setup

**Real storage tests** (integration only):
- Separate from unit tests
- Run against tmp DuckDB (fast, ephemeral)
- Much smaller number (< 20)

**Decision:** 90% mocks, 10% integration = speed + confidence

### Decision 7: DuckDB (Embedded, Single-File)

**Choice:** DuckDB for MVP, not Postgres/MySQL

**Why:**
- Single file (db/sales_intel.duckdb) - easy to backup, version control
- No server to run (MVP constraint: "no deployment")
- Competitive performance (analytical queries are fast)
- Streaming COPY/INSERT (good for bulk data)
- Type safety (strong types, constraints)

**Limitation:** Single writer per process

**Solution:** For concurrency, queue-based pipeline (roadmap)

**Migration path:** When scaling, switch to Postgres (Protocol makes it easy)

**Decision:** DuckDB for MVP, Postgres later

### Decision 8: Anthropic SDK (not LangChain)

**Choice:** Raw `anthropic.Anthropic()` API, not LangChain abstractions

```python
# DON'T: LangChain
from langchain.llms import ChatAnthropic
llm = ChatAnthropic(model="claude-haiku")

# DO: Anthropic SDK
from anthropic import Anthropic
client = Anthropic(api_key=env["ANTHROPIC_API_KEY"])
response = client.messages.create(
    model="claude-haiku-4-5",
    messages=[{"role": "user", "content": "..."}],
)
```

**Why:**
- Full control over cost tracking (measure exact tokens)
- Full control over latency (measure exact ms)
- No abstraction overhead
- All features available (vision, batch API, etc.)
- Easier to mock for testing

**Trade-off:** More code vs transparency

**Decision:** Transparency matters (cost is critical for business model)

### Decision 9: SOLID Compliance as Non-Negotiable

**Why:**
- Each violation is technical debt
- Every "just this once" costs 10x later
- Reviewer job 1: check SOLID, everything else is secondary

**Enforcement:**
- ✅ SRP: one class per file, one file per class
- ✅ OCP: new extractors don't modify existing
- ✅ LSP: all implementations honor Protocol
- ✅ ISP: protocols are minimal (only methods implementers need)
- ✅ DIP: all clients depend on Protocols

**Example violation (caught in review):**
```python
# ❌ WRONG: utils.py with 5 different functions
def is_database_port(): ...
def extract_domain(): ...
def normalize_record(): ...
def detect_noise(): ...
def score_account(): ...

# ✅ RIGHT: One class per file
# database_exposure.py
class DatabaseExposureExtractor:
    def extract(): ...

# domain_utils.py
class DomainExtractor:
    def extract(): ...
```

**Decision:** Refactor everything until SOLID, no exceptions

### Decision 10: Self-Documenting Code

**Pattern:**
```python
# ❌ WRONG: Obvious comment
def get_root_domain(domain_str: str) -> str | None:
    """Extract root domain from a string."""  # Method name already says this
    return tldextract(domain_str)

# ✅ RIGHT: Code names itself
def extract_root_domain(domain_str: str) -> str | None:
    return tldextract(domain_str)

# ✅ RIGHT: Comment for non-obvious logic
def _extract_root_domain(domain_str: str) -> str | None:
    # tldextract needs both domain AND suffix for a valid root domain
    # e.g., "mail.gmail.com" → "gmail.com" (domain=gmail, suffix=com)
    # "192.168.1.1" → None (no suffix, numeric-only IPs excluded)
    result = self.extractor(domain_str)
    if result.domain and result.suffix:
        return f"{result.domain}.{result.suffix}"
    return None
```

**Why:**
- Code changes, comments don't (comments get stale)
- Names are searchable, comments aren't
- Future reader spends 10s on code, can't assume comments are right

**Decision:** Names must be clear, only comment non-obvious WHY

## Technical Constraints

### Constraint 1: No Global State (except config.py)

**Why:**
- Makes testing impossible (tests interfere with each other)
- Makes parallelization impossible (race conditions)

**Exception:** config.py singleton (immutable, safe to share)

```python
# ❌ WRONG
_connection = None
def get_connection():
    global _connection  # Global mutable state = bad

# ✅ RIGHT
class DuckDBConnectionPool:
    def __init__(self):
        self._conn = None
    def get_connection(self):
        # Instance state, explicit dependency injection
```

### Constraint 2: No Hardcoded Constants

**Why:**
- Can't tune for different deployments
- Can't run A/B tests
- Can't respond to production issues

**Solution:** All via config.py + enums

```python
# ❌ WRONG
WEAK_TLS_VERSIONS = {"SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"}

# ✅ RIGHT
# config.py
class WeakTLSVersionsConfig(BaseModel):
    versions: list[str] = Field(default_factory=lambda: [...])
    def as_set(self) -> frozenset[str]:
        return frozenset(self.versions)

# usage
config = get_pipeline_config()
weak = config.weak_tls_versions.as_set()  # Configured, not hardcoded
```

### Constraint 3: Type Annotations Everywhere

**Why:**
- mypy --strict catches bugs at edit time (not runtime)
- Self-documents function contracts
- IDE autocomplete works (helps productivity)

```python
# ❌ WRONG
def score_account(account):
    return account.risk_score

# ✅ RIGHT
def score_account(account: Account) -> float:
    return account.risk_score
```

### Constraint 4: Immutable Domain Models

**Why:**
- Prevents accidental mutation bugs
- Clear data flow (immutable = passed by value, conceptually)

```python
# ❌ WRONG
class Account(BaseModel):
    root_domain: str
    risk_score: float

account.risk_score = 75  # Oops, mutated

# ✅ RIGHT
class Account(BaseModel):
    root_domain: str
    risk_score: float
    
    class Config:
        frozen = True

account.risk_score = 75  # pydantic.ValidationError: frozen model
```

## Design Patterns

### Pattern 1: Factory (Feature Extraction)

**Why:** Many extractors, one factory

```python
# factory.py
class FeatureExtractorFactory:
    def extract(self, record: dict) -> ExtractedFeatures:
        database = DatabaseExposureExtractor().extract(record)
        legacy = LegacyProtocolExposureExtractor().extract(record)
        vulnerabilities = VulnerabilityExtractor().extract(record)
        return ExtractedFeatures(
            database=database,
            legacy_protocol=legacy,
            vulnerabilities=vulnerabilities,
            # ...
        )
```

### Pattern 2: Strategy (Storage Backends)

**Why:** Switch backends without changing clients

```python
# Current: DuckDB
storage = DuckDBStorageService(connection)

# Future: Postgres
storage = PostgresStorageService(connection)

# Both implement Protocol StorageService
# Client code doesn't change
```

### Pattern 3: Template Method (Pipeline)

**Why:** Standard flow, pluggable steps

```python
# pipeline/service.py
def ingest(self, input_path: str):
    for batch in self._read_batch(input_path):        # Pluggable
        normalized = self._normalize(batch)           # Pluggable
        self._store(normalized)                       # Pluggable
    self._aggregate()                                 # Pluggable
```

## Metrics That Matter

✅ **Code Quality:**
- SOLID violations (target: zero)
- Test coverage (target: 90% service layer)
- mypy errors (target: zero)
- Type annotation % (target: 100%)

✅ **Performance:**
- Ingest throughput (target: 10.6M records < 1 hour)
- Query latency (target: <100ms for top-N accounts)
- LLM cost/account (target: <$0.02)

✅ **Maintainability:**
- Cyclomatic complexity (target: <10 per function)
- Class size (target: <300 lines)
- File size (target: <200 lines)
- Comment ratio (target: <5%)

## Summary: Engineering Philosophy

1. **SOLID is non-negotiable** — every violation is debt
2. **Testability is a feature** — mock-first design
3. **Names are the best documentation** — clear naming beats comments
4. **Type safety at compile time** — catch bugs before runtime
5. **Explicit dependencies** — no hidden state, no magic
6. **Rules > LLM for determinism** — use AI for language, logic for logic
7. **Microservices-ready** — each service can be extracted and deployed
8. **Cost transparency** — measure and track everything (LLM cost matters)
