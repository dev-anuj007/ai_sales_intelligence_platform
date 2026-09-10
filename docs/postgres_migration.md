# PostgreSQL Setup Guide

PostgreSQL is the sole database backend for the AI Sales Intelligence Platform. This guide explains how to set up PostgreSQL for local development and production.

## Overview

**Why PostgreSQL?**

- ✅ **Concurrent writes**: Multiple services can write simultaneously
- ✅ **Better scaling**: Handles 100+ requests/second
- ✅ **Production-ready**: ACID compliance, transactions, rollback
- ✅ **Monitoring**: Native observability via pgAdmin, logs
- ✅ **Backup/Restore**: Industry-standard tools (pg_dump, WAL archiving)
- ✅ **Type-safe ORM**: SQLAlchemy + SQLModel for Pythonic data access

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

**Docker (Recommended for Development):**
```bash
docker run --name sales-intel-postgres \
  -e POSTGRES_PASSWORD=admin \
  -p 5432:5432 \
  -d postgres:15
```

### 2. Configure Environment

Create `.env` in project root:
```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=sales_intel
POSTGRES_USER=postgres
POSTGRES_PASSWORD=admin          # Use secure password in production!
```

### 3. Initialize Database

Run the setup script:
```bash
uv run python scripts/setup_postgres.py
```

This creates:
- Database: `sales_intel`
- Tables: `staging_records`, `accounts`, `account_top_records`, `trace_logs`
- Indices: For efficient queries

### 4. Verify Connection

```bash
# Test connection
python -c "from services.storage import init_pool; pool = init_pool(); conn = pool.get_connection(); print('Connected!'); conn.close()"

# Or use psql CLI
psql -h localhost -U postgres -d sales_intel -c "SELECT 1;"
```

## Database Schema

The platform uses SQLModel ORM for type-safe data access. Tables are created automatically via SQLAlchemy.

### Tables

#### staging_records
Raw records from Shodan ingestion:
```sql
CREATE TABLE staging_records (
    record_id BIGINT PRIMARY KEY,
    root_domain VARCHAR(255),
    ip VARCHAR(15),
    port INT,
    ts TIMESTAMP,
    tags TEXT[],
    vuln_count INT,
    max_cvss FLOAT,
    max_epss FLOAT,
    ... (30+ fields)
);

CREATE INDEX idx_staging_root_domain ON staging_records(root_domain);
CREATE INDEX idx_staging_timestamp ON staging_records(ts);
```

#### accounts
Aggregated per-domain records:
```sql
CREATE TABLE accounts (
    root_domain VARCHAR(255) PRIMARY KEY,
    record_count INT,
    asset_count INT,
    distinct_ips INT,
    distinct_ports INT,
    port_list JSONB,
    countries JSONB,
    vuln_count_total INT,
    vuln_count_critical INT,
    max_cvss FLOAT,
    max_epss FLOAT,
    exposed_database_count INT,
    legacy_protocol_count INT,
    weak_tls_count INT,
    self_signed_cert_count INT,
    eol_product_count INT,
    iot_ot_device_count INT,
    honeypot_flagged BOOLEAN,
    excluded_as_honeypot BOOLEAN,
    risk_score FLOAT,
    score_version VARCHAR(10),
    signal_tags JSONB,
    score_explanation JSONB,
    scored_at TIMESTAMP,
    narrative TEXT,
    outreach_draft TEXT,
    enriched_at TIMESTAMP,
    ... (more fields)
);

CREATE INDEX idx_accounts_risk_score ON accounts(risk_score DESC);
CREATE INDEX idx_accounts_excluded ON accounts(excluded_as_honeypot);
```

#### account_top_records
Top 20 records per account for LLM grounding:
```sql
CREATE TABLE account_top_records (
    root_domain VARCHAR(255),
    record_id BIGINT,
    rank INT,
    PRIMARY KEY (root_domain, record_id)
);

CREATE INDEX idx_account_top_rank ON account_top_records(root_domain, rank);
```

#### trace_logs
LLM call tracing:
```sql
CREATE TABLE trace_logs (
    trace_id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    task VARCHAR(50),
    root_domain VARCHAR(255),
    model VARCHAR(50),
    prompt_name VARCHAR(100),
    prompt_version VARCHAR(10),
    input_tokens INT,
    output_tokens INT,
    cost_usd FLOAT,
    latency_ms INT,
    decision TEXT,
    success BOOLEAN,
    error TEXT,
    request_hash VARCHAR(64),
    llm_client_type VARCHAR(20)
);

CREATE INDEX idx_trace_timestamp ON trace_logs(timestamp DESC);
CREATE INDEX idx_trace_task ON trace_logs(task);
```

## Development Workflow

### Local Development (Docker Recommended)

```bash
# 1. Start PostgreSQL in Docker
docker run --name sales-intel-postgres \
  -e POSTGRES_PASSWORD=admin \
  -p 5432:5432 \
  -d postgres:15

# 2. Initialize database
uv run python scripts/setup_postgres.py

# 3. Run pipeline
uv run python -m services.pipeline.run_pipeline \
  --input services/pipeline/data/fixtures/shodan_sample.jsonl \
  --limit 5000

# 4. Score and enrich
uv run python -m services.scoring.run_scoring
uv run python -m services.enrichment.run_enrichment --top-n 50

# 5. Start API server
uv run uvicorn main:app --reload

# 6. Query in another terminal
curl http://localhost:8001/accounts?limit=10
```

### Query Inspection

Use `psql` to inspect data:
```bash
# Connect to database
psql -h localhost -U postgres -d sales_intel

# List tables
\dt

# Query accounts
SELECT root_domain, risk_score, signal_tags FROM accounts LIMIT 5;

# Query by score range
SELECT root_domain, risk_score FROM accounts 
WHERE risk_score > 80 
ORDER BY risk_score DESC 
LIMIT 10;

# Query traces
SELECT task, model, cost_usd, latency_ms FROM trace_logs ORDER BY timestamp DESC LIMIT 5;

# Exit
\q
```

### Backup & Restore

```bash
# Backup database
pg_dump -h localhost -U postgres -d sales_intel > backup.sql

# Restore from backup
psql -h localhost -U postgres -d sales_intel < backup.sql

# Docker-specific backup
docker exec sales-intel-postgres pg_dump -U postgres sales_intel > backup.sql
```

## Production Deployment

### 1. RDS (AWS Recommended)

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier sales-intel-prod \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --master-username postgres \
  --master-user-password $(openssl rand -base64 32) \
  --allocated-storage 100
```

Update `.env` with RDS endpoint:
```bash
POSTGRES_HOST=sales-intel-prod.cxxxxxx.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DATABASE=sales_intel
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<generated-password>
```

### 2. Connection Pooling (PgBouncer)

For production, use PgBouncer for connection pooling:

```bash
# Install pgbouncer
brew install pgbouncer  # macOS
sudo apt-get install pgbouncer  # Ubuntu

# Configure pgbouncer.ini
[databases]
sales_intel = host=localhost port=5432 dbname=sales_intel

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25

# Start pgbouncer
pgbouncer -d /etc/pgbouncer/pgbouncer.ini
```

Update app to use pgbouncer port (6432):
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=6432
```

### 3. Monitoring

**pgAdmin (Web UI):**
```bash
docker run --name pgadmin -p 5050:80 \
  -e PGADMIN_DEFAULT_EMAIL=admin@example.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin \
  -d dpage/pgadmin4
```

Visit http://localhost:5050, login, add server with RDS endpoint.

**Query Logs:**
```bash
# Enable query logging
psql -h localhost -U postgres -d sales_intel -c "ALTER SYSTEM SET log_statement = 'all';"
psql -h localhost -U postgres -d sales_intel -c "SELECT pg_reload_conf();"

# View logs
tail -f /var/log/postgresql/postgresql.log  # Linux
```

## Troubleshooting

### Connection refused
```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Check port
lsof -i :5432

# Restart service
brew services restart postgresql@15  # macOS
sudo systemctl restart postgresql    # Linux
docker restart sales-intel-postgres  # Docker
```

### Out of connections
```sql
-- Check current connections
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

-- Increase max_connections in postgresql.conf
max_connections = 200

-- Reload config
SELECT pg_reload_conf();
```

### Slow queries
```sql
-- Enable query timing
EXPLAIN ANALYZE SELECT ... ;

-- Create indices for common queries
CREATE INDEX idx_accounts_risk_score ON accounts(risk_score DESC);
CREATE INDEX idx_staging_root_domain ON staging_records(root_domain);
```

## Migration from DuckDB (Legacy)

This section is for reference only. DuckDB is no longer supported.

**If you have existing DuckDB data:**

```python
import duckdb
import psycopg2

# Export from DuckDB
duckdb_conn = duckdb.connect('services/storage/db/sales_intel.duckdb')
df = duckdb_conn.execute("SELECT * FROM accounts").fetchdf()

# Import to PostgreSQL
from services.storage import AccountStorageService
storage = AccountStorageService()
for _, row in df.iterrows():
    storage.create(row.to_dict())
```

## Next Steps

- [Architecture Guide](architecture.md) - System design and layering
- [How You Build](how-you-build.md) - Design decisions and rationale
- [CLAUDE.md](../CLAUDE.md) - Development workflow and coding standards
