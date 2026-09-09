# AI Sales Intelligence Platform

A production-grade sales intelligence platform for cybersecurity teams to identify, prioritize, and target high-risk businesses based on real internet-exposure telemetry, not just firmographic data.

**Status:** Backend-only build, alpha phase. UI and deployment to follow in future phases.

## Quick Start

### Prerequisites
- Python 3.11+
- `uv` package manager (https://docs.astral.sh/uv/getting-started/)

### Setup

1. **Clone and install dependencies:**
   ```bash
   uv sync
   uv pip install -e ".[dev]"
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings, especially RAW_DATA_PATH and LLM_CLIENT
   ```

3. **Ingest data (using the fixture for quick dev iteration):**
   ```bash
   uv run python -m sales_intel.services.pipeline.run_pipeline \
     --input data/fixtures/shodan_sample.jsonl \
     --db db/sales_intel.duckdb \
     --limit 5000
   ```

4. **Score accounts:**
   ```bash
   uv run python -m sales_intel.services.scoring.score_accounts \
     --db db/sales_intel.duckdb
   ```

5. **Enrich top accounts (mock LLM):**
   ```bash
   uv run python -m sales_intel.services.enrichment.run_enrichment \
     --db db/sales_intel.duckdb \
     --top-n 50 \
     --client mock
   ```

6. **Run the API server:**
   ```bash
   uv run uvicorn main:app --reload
   ```

7. **Test it:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/accounts?limit=10
   curl http://localhost:8000/accounts/example.com
   ```

### Running Tests

```bash
# Unit tests only
uv run pytest -v -m "not slow"

# Full test suite including integration
uv run pytest -v

# With coverage report
uv run pytest --cov=src/sales_intel --cov-report=html

# Type checking
uv run mypy src/
```

### Evaluation

Run the signal/noise classification eval against the mock LLM:

```bash
uv run python evals/signal_noise/run_eval.py \
  --prompt-version v1 \
  --dataset evals/signal_noise/dataset_v1.jsonl \
  --client mock
```

Compare v1 vs v2:

```bash
uv run python evals/signal_noise/run_eval.py \
  --prompt-version v2 \
  --compare-to v1 \
  --dataset evals/signal_noise/dataset_v1.jsonl \
  --client mock
```

## Architecture

**Layered SOA (Service-Oriented Architecture):**

- **Data Layer** (`src/sales_intel/data/`): DuckDB repositories, models, schema
- **Service Layer** (`src/sales_intel/services/`): Business logic (pipeline, scoring, enrichment, aggregation)
- **API Layer** (`src/sales_intel/api/`): FastAPI routers and HTTP schemas

All services are dependency-injected into routers. Services have zero knowledge of HTTP/FastAPI.

## Key Features

### Scoring
- **Rule-based, deterministic scoring** (0–100): weighted composite of vulnerability severity, exposable attack surface, TLS hygiene, EOL/legacy product prevalence, and raw asset count
- **Explainable signals**: each account gets a `signal_tags` list and a `score_explanation` JSON documenting the sub-score breakdown
- **Honeypot exclusion**: accounts whose only assets are honeypots are excluded from scoring

### LLM Orchestration (LangGraph)
- **Haiku for cost-effective classification**: signal/noise re-review, company/industry inference
- **Sonnet for judgment**: risk narratives, personalized outreach drafts
- **Mock client first**: all LLM code works with a deterministic mock client; swap to real Anthropic API via a single env var once a key is available

### Production-grade practices
- **Strict type annotations** with mypy strict mode
- **90%+ unit test coverage** on service layer (with mocked repositories and LLM)
- **Comprehensive tracing**: every LLM call logged to a JSONL trace file queryable via DuckDB
- **Cost awareness**: explicit $/token model cost calculations, cost ceiling enforced at runtime
- **Prompt versioning**: all prompts versioned as Markdown files; eval harness compares v1 vs v2 metrics

## Project Structure

```
src/sales_intel/
  config.py                  Pydantic Settings, all env-driven config
  data/                      Data layer: repositories, models, DuckDB schema
  services/
    pipeline/                Streaming ingest, domain extraction, noise filtering
    scoring/                 Rule-based risk scoring engine
    llm/                     LLM client abstraction (mock + Anthropic), pricing, tracing
    enrichment/              LangGraph orchestration (signal/noise, company infer, narrative, outreach)
    aggregation/             SQL aggregation from staging to accounts
  api/                       FastAPI routers, HTTP schemas, dependency injection
prompts/                     Versioned prompt files (v1.md, v2.md, ...)
skills/                      Reusable skill definitions (account-risk-triage)
evals/                       Hand-labeled evaluation sets, eval harness, results
data/
  fixtures/                  Committed sample data for testing (5K records)
  raw/                       gitignored: real raw data (env: RAW_DATA_PATH)
db/                          gitignored: DuckDB database file
traces/                      gitignored: LLM telemetry JSONL
tests/
  unit/                      Unit tests, mocked dependencies
  integration/               Integration tests, real tmp DuckDB
```

## Roadmap (Future Phases)

- **Phase 2: Frontend** — React/Next.js or Streamlit dashboard for sales reps to browse/filter accounts and view enriched narratives
- **Phase 3: Deployment** — Docker, cloud hosting (Fly.io / Railway / AWS), CI/CD pipeline
- **Phase 4: Multi-snapshot deltas** — Track "new exposure since last scan", enable historical trends
- **Phase 5: CRM integration** — Salesforce/HubSpot sync of scored accounts and outreach drafts
- **Phase 6: Auth & RBAC** — User management, role-based access control
- **Phase 7: Performance tuning** — Parallel zstd parsing, Postgres for accounts if concurrent writes needed

## Cost Model (Mock Scenario)

Top 50 accounts/day across all 4 LLM tasks (mock client = $0):
- Once Anthropic key is added: ~$0.01–0.02/account/day = under $1/day, under $30/month hard ceiling

See `docs/cost_model.md` for the full worksheet.

## Documentation

- `docs/planning.md` — use cases and why we chose them
- `docs/architecture.md` — component diagram, design decisions, rule-vs-LLM split, concurrency model
- `docs/cost_model.md` — pricing, token estimates, cost ceiling
- `docs/roadmap.md` — phased plan including UI/deployment
- `docs/how-you-build.md` — dev loop reflection

## Questions?

File an issue or reach out. This is a take-home assignment for Firmable; feedback welcome.