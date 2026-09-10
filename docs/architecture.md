# Architecture: Microservices-First AI Sales Intelligence Platform

## Overview

**Microservices-first backend** for identifying businesses needing cybersecurity services from Shodan scan data. Each service is self-contained, independently deployable, and follows strict SOLID principles.

## Project Structure

```
/
├── services/                    [Microservices at root]
│   ├── storage/                [Shared data access layer]
│   ├── pipeline/               [Ingest service]
│   ├── aggregation/            [Aggregation service]
│   ├── scoring/                [Scoring service]
│   └── enrichment/             [Enrichment service]
│
├── config.py                   [Root configuration]
├── main.py                     [FastAPI application]
└── docs/                       [Documentation]
```

## Layering: API → Service → Storage

Each service strictly enforces three-tier architecture:

### 1. API Layer (api.py)
- FastAPI routers with dependency injection
- Receives HTTP requests
- Calls service layer ONLY (never direct storage access)
- Returns HTTP responses

```python
# services/pipeline/api.py
@router.post("/ingest")
def ingest_records(
    input_path: str,
    service: PipelineService = Depends(get_ingest_service),
) -> dict[str, Any]:
    return service.ingest(input_path)
```

### 2. Service Layer (service.py)
- Business logic orchestration
- Dependency-injected storage services
- Calls storage for data access
- No HTTP concerns
- Fully testable with mocked storage

```python
# services/pipeline/service.py
class PipelineService:
    def __init__(self, staging_storage: StagingStorageService):
        self.staging_storage = staging_storage
    
    def ingest(self, input_path: str) -> dict[str, Any]:
        for batch in iter_batches(input_path):
            normalized = [normalize_record(r) for r in batch]
            self.staging_storage.bulk_insert(normalized)
```

### 3. Storage Layer (services/storage/)
- Pure data access: CRUD + specialized queries
- Cannot be called from api.py directly
- Only called by service.py
- Abstraction-based (Protocol interfaces)
- Extensible backend support

```python
# services/storage/postgres_staging_storage.py
class StagingStorageService:
    def bulk_insert(self, records: list[dict]) -> int:
        # Pure data access via SQLAlchemy ORM
        session = self._get_session()
        for record in records:
            staging_record = StagingRecordSQL(**record)
            session.add(staging_record)
        session.commit()
```

## SOLID Principles

### Single Responsibility Principle (SRP)
- **Class Level:** Each class has one job
  - `StagingStorageService` → bulk insert + queries
  - `PipelineService` → orchestration
  
- **Module Level:** One file = one class
  - `account_storage.py` → AccountStorageService
  - `staging_storage.py` → StagingStorageService
  
- **Package Level:** Clean separation
  - `storage/` → data access only
  - `*/service.py` → business logic
  - `*/api.py` → HTTP handling

### Open/Closed Principle (OCP)
- Add new extractors without modifying existing
- Add new storage backends via StorageType enum
- New services extend without changing existing

### Liskov Substitution Principle (LSP)
- All storage services implement Protocol contracts
- All extractors implement FeatureExtractorInterface

### Interface Segregation Principle (ISP)
- Lean Protocol interfaces: only methods needed
- StorageService: get, list, create, update, delete, count
- NamesStorageService: store_name, get_name, list_by_pattern, clear_cache

### Dependency Inversion Principle (DIP)
- All clients depend on Protocols, not concrete classes
- Dependency injection via FastAPI Depends()
- Easy to mock in tests

## Services

### 1. Storage Service (services/storage/)
**Pure data access layer** - shared by all services

Files:
- `abstractions.py` - Protocol interfaces
- `enums.py` - StorageType, TableType
- `postgres_*.py` - PostgreSQL implementations (SQLModel ORM)
- `postgres_connection.py` - Connection pooling (SQLAlchemy)
- `sqlmodel_models.py` - SQLModel ORM models
- `models.py` - Pydantic domain models (Account, StagingRecord)
- `migrate.py` - Schema application
- `factory.py` - Backend factory (PostgreSQL-only)

Implementations:
- `PostgresAccountStorageService` - accounts table CRUD
- `PostgresStagingStorageService` - staging_records bulk insert
- `PostgresTraceStorageService` - trace_logs append + query
- `PostgresNamesStorageServiceImpl` - company name caching

### 2. Pipeline Service (services/pipeline/)
**Data ingestion and normalization**

Files:
- `service.py` - PipelineService (business logic)
- `api.py` - POST /pipeline/ingest route
- `ingest_service.py` - legacy compatibility
- `normalizer.py` - record normalization
- `domain_utils.py` - domain extraction
- `noise_filter.py` - tag-based noise detection
- `stream_reader.py` - zstd streaming

Flow:
1. Stream Shodan records from zstd file
2. Normalize each record (extract features, domain, etc.)
3. Bulk insert into staging_records table
4. Trigger aggregation

### 3. Aggregation Service (services/aggregation/)
**Group staging records into accounts**

Files:
- `service.py` - AggregationService (business logic)
- `api.py` - POST /aggregation/run route

Flow:
1. GROUP BY root_domain on staging_records
2. Create accounts table rows
3. Build account_top_records index (top 20 records per account)
4. Mark honeypot-only accounts

### 4. Scoring Service (services/scoring/)
**Rule-based risk scoring**

Files:
- `service.py` - ScoringService (business logic)
- `api.py` - POST /scoring/run route

Rules (0-100 composite score):
- Vulnerability score (35%) - CVSS × EPSS + critical count
- Exposure score (25%) - DB + legacy + IoT/OT presence
- TLS hygiene (15%) - self-signed / weak version ratio
- EOL/legacy (15%) - EOL-flagged assets ratio
- Attack surface (10%) - log2(asset_count+1)

### 5. Enrichment Service (services/enrichment/)
**LLM-powered enrichment (future)**

Files:
- `service.py` - EnrichmentService (business logic)
- `api.py` - POST /enrichment/run route

Future tasks (not implemented yet):
- Signal/noise re-classification (Haiku)
- Company name inference (Haiku)
- Risk narrative generation (Sonnet)
- Outreach draft generation (Sonnet)

## Storage Backend

**Current:** PostgreSQL 12+ (SQLAlchemy ORM via SQLModel)

**Features:**
- Concurrent writers
- Full ACID transactions
- Connection pooling (thread-safe)
- Type-safe ORM models (SQLModel)

**Future backends** via `StorageType` enum:
```python
class StorageType(Enum):
    DATABASE = "database"   # PostgreSQL (current)
    CACHE = "cache"         # Redis (future)
    FILE = "file"           # S3 (future)
```

**Adding new backend:**
1. Create `RedisStorageService` implementing Protocol
2. Inject into service: `ScoringService(redis_storage)`
3. Zero changes to api.py or service.py

## Testing Strategy

**Per-service unit tests with mocked storage**

Location:
```
services/pipeline/tests/
├── conftest.py          [Fixtures, mock storage]
├── test_service.py      [PipelineService logic]
├── test_api.py          [Routes and HTTP handling]
└── test_*.py            [Component tests]
```

Target: 90%+ coverage on service layer

Run tests:
```bash
pytest services/pipeline/tests/
pytest services/*/tests/                    # All services
pytest services/*/tests/ --cov=services/    # With coverage
```

## Deployment Readiness

Each service can be extracted and deployed independently:

```bash
# Extract pipeline service
mkdir -p api-service && cp -r services/pipeline api-service/
cd api-service
uv run uvicorn main:app --port 8001
```

Shared dependencies:
- `services/storage/` (all services depend on)
- `config.py` (shared configuration)

## Code Quality

✅ **Type Safety:** mypy strict mode on all services
✅ **Self-Documenting:** Clear naming, no obvious comments
✅ **Dependency Injection:** All dependencies explicitly passed
✅ **Protocol-Based:** Clients depend on abstractions
✅ **No Hardcoded Config:** All via config.py + enums
✅ **SOLID Compliant:** SRP, OCP, LSP, ISP, DIP

## What's NOT Here (Roadmap)

- ❌ UI/frontend (roadmap)
- ❌ Production hosting/CI-CD (roadmap)
- ❌ Multi-snapshot delta analysis (roadmap)
- ❌ CRM integration (roadmap)
- ❌ Authentication/authorization (roadmap)

## Next Steps

1. **M3+:** Implement scoring rules (deterministic, no LLM)
2. **M4+:** Wire LLM client (Anthropic SDK via mock-first)
3. **M5+:** Implement enrichment services
4. **M6+:** FastAPI full surface (accounts, traces, evals)
5. **M7+:** Test suite (90%+ coverage)
6. **M8+:** Documentation (planning, cost model, roadmap)
