# AI Sales Intelligence Platform

A production-grade sales intelligence platform for cybersecurity teams to identify, prioritize, and target high-risk businesses based on real internet-exposure telemetry, not just firmographic data.

**Status:** Backend-only build, alpha phase. UI and deployment to follow in future phases.

## Quick Start

### Prerequisites
- Python 3.11+
- `uv` package manager (https://docs.astral.sh/uv/getting-started/)

### Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Ingest data (using the fixture for quick dev iteration):**
   ```bash
   uv run python -m services.pipeline.run_pipeline \
     --input services/pipeline/data/fixtures/shodan_sample.jsonl \
     --db services/storage/db/sales_intel.duckdb \
     --limit 5000
   ```

3. **Score accounts:**
   ```bash
   uv run python -m services.scoring.score_accounts \
     --db services/storage/db/sales_intel.duckdb
   ```

4. **Enrich top accounts (mock LLM):**
   ```bash
   uv run python -m services.enrichment.run_enrichment \
     --db services/storage/db/sales_intel.duckdb \
     --top-n 50 \
     --client mock
   ```

5. **Run the API server:**
   ```bash
   # Uses port 8001 if port 8000 is in use
   uv run uvicorn main:app --reload --port 8001
   ```

6. **Test it:**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/accounts?limit=10
   curl http://localhost:8001/accounts/{root_domain}
   ```

### Running Tests

```bash
# All tests across all services
uv run pytest services/*/tests/ -v

# Tests for a specific service
uv run pytest services/pipeline/tests/ -v

# With coverage report
uv run pytest services/*/tests/ --cov=services/ --cov-report=html

# Type checking (strict mode)
uv run mypy services/
```

### Evaluation

Run the signal/noise classification eval against the mock LLM:

```bash
uv run python services/enrichment/evals/run_eval.py \
  --prompt-version v1 \
  --dataset services/enrichment/evals/datasets/signal_noise_v1.jsonl \
  --client mock
```

## Architecture

**Microservices-first with strict three-tier layering:**

Each service is self-contained and independently deployable:

1. **API Layer** (`*/api.py`) — FastAPI routers, HTTP request/response handling
2. **Service Layer** (`*/service.py`) — Business logic, orchestration
3. **Storage Layer** (`services/storage/`) — DuckDB access, repositories, models

All services are dependency-injected. Services have zero knowledge of HTTP/FastAPI. API layer NEVER directly accesses storage.

**Services:**
- `services/pipeline/` — Streaming ingest, normalization, domain extraction, noise filtering
- `services/aggregation/` — SQL aggregation from staging to accounts
- `services/scoring/` — Rule-based risk scoring engine
- `services/enrichment/` — LLM orchestration (signal/noise, company inference, narrative, outreach)
- `services/storage/` — Shared data access layer (DuckDB, repositories, domain models)

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
/
├── services/                Self-contained microservices
│   ├── storage/             Shared data access layer
│   │   ├── abstractions.py  Protocol interfaces
│   │   ├── *_storage.py     DuckDB implementations
│   │   ├── models.py        Pydantic domain models
│   │   ├── db/              DuckDB files (.gitignore)
│   │   └── tests/           Storage layer tests
│   │
│   ├── pipeline/            Data ingestion service
│   │   ├── service.py       Business logic
│   │   ├── api.py           FastAPI routes
│   │   ├── data/
│   │   │   ├── fixtures/    Test data (committed)
│   │   │   └── raw/         External input (.gitignore)
│   │   └── tests/           Unit tests (90%+ coverage)
│   │
│   ├── aggregation/         Aggregation service
│   │   ├── service.py
│   │   ├── api.py
│   │   └── tests/
│   │
│   ├── scoring/             Scoring service
│   │   ├── service.py
│   │   ├── api.py
│   │   └── tests/
│   │
│   └── enrichment/          Enrichment service
│       ├── service.py
│       ├── api.py
│       ├── prompts/         Versioned prompt templates
│       ├── evals/           Evaluation datasets & results
│       ├── traces/          LLM trace logs (.gitignore)
│       └── tests/
│
├── config.py                Environment configuration (Pydantic Settings)
├── main.py                  FastAPI application entry point
├── docs/                    Comprehensive documentation
│   ├── architecture.md      Layering, SOLID, abstractions
│   ├── planning.md          Goals, phases, decisions
│   ├── roadmap.md           Future phases, timeline
│   ├── cost_model.md        LLM costs, token tracking
│   └── how-you-build.md     Design patterns, philosophy
├── pyproject.toml           Dependencies, project config
└── README.md                This file
```

**Key principles:**
- Each service owns its data (fixtures, evals, prompts, traces)
- Tests live with the service (`services/*/tests/`)
- Single responsibility per file (one class per file)
- API → Service → Storage layering (strict three-tier)
- Dependency injection everywhere (zero globals except config)

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