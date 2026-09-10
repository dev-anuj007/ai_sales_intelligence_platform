# PostgreSQL Migration Guide

This document explains how to migrate from DuckDB to PostgreSQL in the AI Sales Intelligence Platform.

## Overview

The platform now supports both **DuckDB** (default, single-file, single-writer) and **PostgreSQL** (production-ready, concurrent writes, scalable) as storage backends.

### Why PostgreSQL?

- ✅ **Concurrent writes**: Multiple services can write simultaneously
- ✅ **Better scaling**: Handles 100+ requests/second
- ✅ **Production-ready**: ACID compliance, transactions, rollback
- ✅ **Monitoring**: Native observability via pgAdmin, logs
- ✅ **Backup/Restore**: Industry-standard tools (pg_dump, WAL archiving)

### Why Keep DuckDB?

- ✅ **Zero setup**: Single file, no server needed
- ✅ **Fast**: Optimized for analytics queries
- ✅ **Development**: Perfect for local iteration

## Quick Start: PostgreSQL Setup

### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
- Download from https://www.postgresql.org/download/windows/
- Run installer, note the password you set for `postgres` user

**Docker:**
```bash
docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15
```

### 2. Configure Environment

Create `.env` in project root:
```bash
# Database Configuration
DB_TYPE=postgres                    # Change from 'duckdb' to 'postgres'
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=sales_intel
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres          # Use secure password in production!
```

### 3. Install Dependencies

```bash
uv sync                             # Install sqlmodel, sqlalchemy, psycopg2
```

### 4. Create Database and Tables

```bash
uv run python scripts/setup_postgres.py
```

Output should show:
```
✓ Database 'sales_intel' created
✓ Connection pool initialized
✓ Database connection successful
✓ All tables created successfully
✅ Setup complete!
```

### 5. Verify Connection

```bash
uv run python -c "
from services.storage import init_pool, get_pool
init_pool()
print('✅ PostgreSQL connected successfully!')
"
```

## Migration: DuckDB → PostgreSQL

### Step 1: Export Data from DuckDB

```bash
# Create backup
uv run python -c "
import duckdb
from pathlib import Path

# Connect to DuckDB
conn = duckdb.connect('services/storage/db/sales_intel.duckdb')

# Export tables
for table in ['staging_records', 'accounts', 'account_top_records', 'trace_logs']:
    conn.execute(f\"COPY {table} TO 'db_backup/{table}.parquet' (FORMAT PARQUET)\")
    print(f'✓ Exported {table}')
"
```

### Step 2: Setup PostgreSQL

Follow "Quick Start" above (steps 1-4).

### Step 3: Import Data to PostgreSQL

```bash
# Set environment to use PostgreSQL
export DB_TYPE=postgres

uv run python -c "
import pandas as pd
from pathlib import Path
from services.storage import init_pool, get_pool
from services.storage.sqlmodel_models import (
    StagingRecordSQL, AccountSQL, AccountTopRecordSQL, TraceRecordSQL
)
from sqlmodel import Session

init_pool()
session: Session = get_pool().get_connection()

# Import staging_records
df = pd.read_parquet('db_backup/staging_records.parquet')
for _, row in df.iterrows():
    record = StagingRecordSQL(**row.to_dict())
    session.add(record)
session.commit()
print(f'✓ Imported {len(df)} staging records')

# ... repeat for other tables
"
```

### Step 4: Update Config & Restart

In `.env`, set:
```bash
DB_TYPE=postgres
```

Restart the API server:
```bash
uv run uvicorn main:app --reload --port 8001
```

## Storage Service Factory Pattern

The platform uses **factory pattern** to automatically select the correct storage backend:

```python
# services/storage/factory.py
if settings.db_type == "postgres":
    AccountStorageService = PostgresAccountStorageService
    StagingStorageService = PostgresStagingStorageService
    TraceStorageService = PostgresTraceStorageService
else:
    AccountStorageService = DuckDBAccountStorageService  # Fallback
    # ... etc
```

**No changes needed to API or service layers** — they work with both backends transparently.

## Comparison: DuckDB vs PostgreSQL

| Feature | DuckDB | PostgreSQL |
|---------|--------|------------|
| Concurrent writes | ❌ Single writer | ✅ Multiple writers |
| Transactions | ⚠️ Limited | ✅ Full ACID |
| Query performance | ✅ Fast (OLAP) | ✅ Fast (OLTP) |
| Setup complexity | ✅ None | ⚠️ Medium (requires server) |
| Scalability | ❌ Single machine | ✅ Sharding, replication |
| Backup/Restore | ✅ File copy | ✅ pg_dump, WAL archiving |
| Monitoring | ⚠️ Logs only | ✅ pgAdmin, native metrics |
| Development | ✅ Perfect | ⚠️ More setup |
| Production | ❌ No | ✅ Recommended |

## Running Tests with PostgreSQL

Tests now work with PostgreSQL:

```bash
# Unit tests (mocked storage)
uv run pytest services/*/tests/ -v

# Integration tests (real PostgreSQL)
uv run pytest services/*/tests/ -m integration -v
```

To use DuckDB for tests instead:
```bash
export DB_TYPE=duckdb
uv run pytest services/*/tests/ -v
```

## API Differences

### DuckDB (Manual Query Handling)
```python
# Old DuckDB-only code
def get(self, root_domain: str) -> Account | None:
    row = self._fetch_one(
        "SELECT * FROM accounts WHERE root_domain = ?",
        {"root_domain": root_domain}
    )
    return Account(**row) if row else None
```

### PostgreSQL (SQLModel ORM)
```python
# New SQLModel code (works with both backends)
def get(self, root_domain: str) -> Account | None:
    session = self._get_session()
    account_sql = session.query(AccountSQL).filter(
        AccountSQL.root_domain == root_domain
    ).first()
    return self._to_pydantic(account_sql) if account_sql else None
```

Benefits:
- **Type-safe**: No string concatenation, IDE autocomplete
- **Parameterized**: Automatic SQL injection prevention
- **Testable**: Easy to mock with SQLAlchemy fixtures

## Performance Tuning

### PostgreSQL Configuration

For development (`.env`):
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=sales_intel
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

For production, consider:
```bash
# Connection pooling (recommended with PgBouncer or pgpool)
# See https://wiki.postgresql.org/wiki/Number_Of_Database_Connections

# Enable WAL archiving for backups
# See https://www.postgresql.org/docs/current/continuous-archiving.html

# Configure replication for high availability
# See https://www.postgresql.org/docs/current/warm-standby.html
```

### Indexes (Auto-created by SQLModel)

Primary keys are automatically indexed:
- `accounts.root_domain` (string PK)
- `trace_logs.trace_id` (string PK)
- `account_top_records (root_domain, record_id)` (composite PK)

Add custom indexes for frequent queries:
```python
# In sqlmodel_models.py
class AccountSQL(SQLModel, table=True):
    root_domain: str = Field(primary_key=True, index=True)
    risk_score: Optional[float] = Field(None, index=True)  # ← Add this
    excluded_as_honeypot: bool = Field(default=False, index=True)
```

## Monitoring & Debugging

### Check PostgreSQL Status

```bash
# Via psql
psql -h localhost -U postgres -d sales_intel

# Inside psql
\dt                              # List tables
SELECT COUNT(*) FROM accounts;   # Count records
\q                               # Exit
```

### View Connection Pool Stats

```python
from services.storage import get_pool

pool = get_pool()
print(f"Pool size: {pool.pool_size}")
print(f"Max overflow: {pool.max_overflow}")
print(f"Engine: {pool.engine}")
```

### Enable SQL Query Logging

In `.env`:
```bash
LOG_LEVEL=DEBUG
```

This logs all SQL queries to logfire.

## Troubleshooting

### "Connection refused" Error

```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Try connecting manually
psql -h localhost -U postgres -d sales_intel

# If not running, start it
# macOS: brew services start postgresql@15
# Linux: sudo systemctl start postgresql
# Docker: docker start postgres
```

### "Database does not exist" Error

```bash
# Create it manually
psql -h localhost -U postgres -c "CREATE DATABASE sales_intel;"

# Or run setup script
uv run python scripts/setup_postgres.py
```

### "Permission denied" Error

Check PostgreSQL user credentials in `.env`:
```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-password-here>
```

### Connection Pool Exhausted

If you see "QueuePool limit of size 10 overflow 20 reached", increase pool size:
```python
# In config.py or environment
pool = PostgresConnectionPool(pool_size=20, max_overflow=40)
```

## Next Steps

1. **Enable SSL/TLS**: In production, use SSL for PostgreSQL connections
   ```python
   database_url = f"postgresql+psycopg2://...?sslmode=require"
   ```

2. **Setup backup strategy**: Use `pg_dump` or WAL archiving
   ```bash
   pg_dump -h localhost -U postgres sales_intel > backup.sql
   ```

3. **Configure monitoring**: Use pgAdmin or Grafana to monitor performance
   ```bash
   # Docker pgAdmin
   docker run -d -p 5050:80 dpage/pgadmin4
   ```

4. **Scale with replication**: Setup read replicas for high-traffic deployments
   ```bash
   # See: https://www.postgresql.org/docs/current/warm-standby.html
   ```

## References

- SQLModel docs: https://sqlmodel.tiangolo.com/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/en/20/orm/
- PostgreSQL docs: https://www.postgresql.org/docs/
- Connection pooling: https://www.postgresql.org/docs/current/sql-createuser.html
