# PostgreSQL Migration: Complete Implementation

## Overview

Successfully migrated the AI Sales Intelligence Platform from **DuckDB-only** to support both **DuckDB** (development) and **PostgreSQL** (production) storage backends using **SQLModel** for ORM.

## What Changed

### 1. **New Dependencies** (pyproject.toml)
```toml
sqlmodel>=0.0.22              # SQLModel: Pydantic + SQLAlchemy
sqlalchemy>=2.0               # ORM layer
psycopg2-binary>=2.9          # PostgreSQL driver
alembic>=1.14                 # Schema migrations (optional)
```

### 2. **New Files Created**

#### PostgreSQL ORM & Connection
- `services/storage/sqlmodel_models.py` — SQLModel ORM definitions
- `services/storage/postgres_connection.py` — PostgreSQL connection pool
- `services/storage/factory.py` — Backend selection factory (DuckDB/PostgreSQL)

#### PostgreSQL Storage Services
- `services/storage/postgres_account_storage.py` — Account CRUD
- `services/storage/postgres_staging_storage.py` — Staging record bulk insert
- `services/storage/postgres_trace_storage.py` — Trace log storage
- `services/storage/postgres_names_storage.py` — Company name cache

#### Setup & Migration
- `scripts/setup_postgres.py` — One-command PostgreSQL setup
- `docs/postgres_migration.md` — Comprehensive migration guide

### 3. **Modified Files**

#### Configuration
- `config.py` — Added PostgreSQL connection settings (host, port, database, user, password)
- `pyproject.toml` — Added SQLModel, SQLAlchemy, psycopg2 dependencies

#### Storage Layer
- `services/storage/__init__.py` — Updated to use factory pattern
- `services/storage/factory.py` — **NEW**: Backend selection via DB_TYPE config
- `services/storage/migrate.py` — Updated to support both DuckDB and PostgreSQL

#### Initialization
- `main.py` — Added `apply_schema()` call to initialize database on startup

#### Documentation
- `CLAUDE.md` — Updated setup commands, environment variables, project structure
- `docs/postgres_migration.md` — **NEW**: Complete PostgreSQL migration guide

## Architecture: Factory Pattern

### Automatic Backend Selection
```
config.py (DB_TYPE setting)
    ↓
services/storage/factory.py
    ├─ if DB_TYPE="postgres":
    │   └─→ PostgresAccountStorageService (SQLModel ORM)
    ├─ if DB_TYPE="duckdb":
    │   └─→ DuckDBAccountStorageService (Raw queries)
    │
    ↓ (exports same interface)
    
AccountStorageService (Protocol)
    ↓ (api.py, service.py use this)
    
✅ Zero changes to application code
```

### Protocol-Based Design
All storage services implement a common Protocol interface:

```python
class StorageService(Protocol[T]):
    def get(self, id_value: Any) -> T | None: ...
    def list(self, limit: int = 100, offset: int = 0) -> list[T]: ...
    def create(self, entity: T) -> T: ...
    def update(self, entity: T) -> T: ...
    def delete(self, id_value: Any) -> bool: ...
    def count(self) -> int: ...
```

Both DuckDB and PostgreSQL implementations satisfy this interface.

## Usage

### Quick Start: PostgreSQL

```bash
# 1. Install dependencies
uv sync

# 2. Configure (create .env)
export DB_TYPE=postgres
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DATABASE=sales_intel
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres

# 3. Setup database
uv run python scripts/setup_postgres.py

# 4. Verify
uv run python -c "from services.storage import init_pool; init_pool(); print('✅ Connected')"

# 5. Run API
uv run uvicorn main:app --reload --port 8001
```

### Keep Using DuckDB (No Changes)

```bash
# Nothing changes!
export DB_TYPE=duckdb  # (or omit, it's the default)
uv run uvicorn main:app --reload --port 8001
```

## Implementation Details

### Pydantic → SQLModel Conversion

**Before (DuckDB):**
```python
class Account(BaseModel):
    root_domain: str
    risk_score: Optional[float] = None
```

**After (Both backends):**
```python
# Still use Pydantic for API contracts
class Account(BaseModel):
    root_domain: str
    risk_score: Optional[float] = None

# SQLModel ORM for database
class AccountSQL(SQLModel, table=True):
    root_domain: str = Field(primary_key=True)
    risk_score: Optional[float] = None
```

### Session Management (PostgreSQL Only)

```python
def get(self, root_domain: str) -> Account | None:
    session = self._get_session()  # Creates or reuses
    try:
        account_sql = session.query(AccountSQL).filter(...).first()
        return self._to_pydantic(account_sql) if account_sql else None
    finally:
        if self._owns_session:
            session.close()  # Clean up
```

### Type Safety with SQLAlchemy

```python
# ✅ Type-safe, IDE autocomplete
accounts = session.query(AccountSQL).filter(
    AccountSQL.risk_score >= 80,
    AccountSQL.excluded_as_honeypot == False
).order_by(AccountSQL.risk_score.desc()).limit(10).all()

# ✅ No SQL injection
# ✅ Automatic parameterization
```

## Testing

### Unit Tests (Unchanged)
```bash
uv run pytest services/*/tests/ -v
# Still uses mocked storage (no database needed)
```

### Integration Tests (Now PostgreSQL-Aware)
```bash
# Run with PostgreSQL
export DB_TYPE=postgres
uv run pytest services/*/tests/ -m integration -v

# OR run with DuckDB
export DB_TYPE=duckdb
uv run pytest services/*/tests/ -m integration -v
```

## Migration Path: Existing DuckDB → PostgreSQL

1. **Export from DuckDB:**
   ```bash
   duckdb services/storage/db/sales_intel.duckdb \
     "COPY accounts TO '/tmp/accounts.parquet' (FORMAT PARQUET)"
   ```

2. **Setup PostgreSQL** (see Quick Start above)

3. **Import to PostgreSQL:**
   ```python
   df = pd.read_parquet('/tmp/accounts.parquet')
   for _, row in df.iterrows():
       account = AccountSQL(**row.to_dict())
       session.add(account)
   session.commit()
   ```

4. **Switch config:**
   ```bash
   export DB_TYPE=postgres
   ```

Full guide: [docs/postgres_migration.md](docs/postgres_migration.md)

## Validation

### Type Checking
```bash
uv run mypy services/ --strict
# All PostgreSQL code is 100% type-safe
```

### Schema Coverage

**DuckDB** → Uses existing `schema.sql` (unchanged)
**PostgreSQL** → Uses SQLModel auto-generated schema
- All tables created automatically
- Indexes on primary keys
- JSON columns for list types
- Timestamps with UTC precision

### Connection Pool

**PostgreSQL** (`postgres_connection.py`):
- SQLAlchemy connection pooling
- Configurable pool size (default: 10, overflow: 20)
- Health check on every connection
- Auto-reconnect on stale connections

## Future Work

### Phase 2: Observability (Post-Migration)
- Structured logging (logfire integration)
- SQL query tracing
- Connection pool metrics
- Slow query logging

### Phase 3: Advanced Features
- Read replicas (PostgreSQL streaming replication)
- Sharding for scale-out
- Connection pooling with PgBouncer
- Automated backups with WAL archiving

### Phase 4: Other Backends
- Redis cache layer
- S3 file storage
- MongoDB for documents
- Elasticsearch for full-text search

## Files Changed Summary

```
Modified:
  config.py                              (+9 lines: DB config)
  pyproject.toml                         (+5 deps)
  services/storage/__init__.py           (refactored to factory)
  services/storage/migrate.py            (split DuckDB/Postgres)
  main.py                                (+1 line: apply_schema)
  CLAUDE.md                              (docs updated)

Created:
  services/storage/sqlmodel_models.py    (SQLModel ORM, 138 lines)
  services/storage/postgres_connection.py (Connection pool, 148 lines)
  services/storage/factory.py            (Backend selection, 35 lines)
  services/storage/postgres_account_storage.py     (308 lines)
  services/storage/postgres_staging_storage.py     (115 lines)
  services/storage/postgres_trace_storage.py       (109 lines)
  services/storage/postgres_names_storage.py       (97 lines)
  scripts/setup_postgres.py              (Setup helper, 82 lines)
  docs/postgres_migration.md             (Comprehensive guide, 380 lines)
  MIGRATION_SUMMARY.md                   (This file)

Total Lines Added: ~1,400
Breaking Changes: None (backward compatible)
API Changes: None (services/api.py unchanged)
```

## Production Readiness Checklist

- ✅ SQLModel ORM with type safety
- ✅ Connection pooling with health checks
- ✅ Parameterized queries (no SQL injection)
- ✅ Transaction support (auto rollback on error)
- ✅ Schema auto-creation
- ✅ Factory pattern for backend selection
- ✅ No changes to application code
- ✅ Backward compatible with DuckDB
- ✅ Comprehensive setup guide
- ⚠️ (TODO) SSL/TLS support
- ⚠️ (TODO) Monitoring/observability
- ⚠️ (TODO) Automated backups
