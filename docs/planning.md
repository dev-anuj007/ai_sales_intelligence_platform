# Planning: AI Sales Intelligence Platform

## Project Goal

Build a **sales intelligence backend** that identifies businesses needing cybersecurity services from Shodan internet scan data. Demonstrate **AI-native engineering practices** at production grade:
- Skills: SOLID architecture, dependency injection, proper abstraction layers
- Evals: Prompt versioning, cost monitoring, LLM tracing
- Tests: 90%+ service layer coverage with mocks
- Type Safety: mypy strict mode across codebase
- Self-Documenting: Code should name itself, minimal comments

## Key Decisions (Locked In)

✅ **Backend only** (no UI, no hosting/deployment this phase)
✅ **Microservices-first** (each service independently deployable)
✅ **Service-Oriented Layering** (API → Service → Storage)
✅ **PostgreSQL** (concurrent writers, ACID transactions, production-ready)
✅ **Rule-based scoring** (deterministic, auditable, free)
✅ **LLM for language tasks only** (Haiku for classification, Sonnet for narrative)
✅ **Mock-first development** (100% testability before real API integration)
✅ **Anthropic SDK** (not LangChain - full control over usage/cost/latency)
✅ **Protocol-based abstractions** (Clients depend on Protocols, not concrete classes)
✅ **Strict SOLID** (Every violation becomes technical debt)

## Dataset

**Shodan internet scan snapshot** (~88GB decompressed, ~10.6M records):
- Dates: 2026-09-07
- Fields: ip, port, hostnames, domains, org, isp, asn, location, tags, vulns, ssl, http, cpe, protocols, products
- Coverage: 70% have domains, 1.85% have vulnerabilities, 8.9% have SSL, 16.9% have HTTP titles
- Key insight: NO firmographic data (name, industry, size) - signals come purely from internet exposure

## Architecture Phases

### M0: Scaffold + Fixtures
- FastAPI app with Logfire
- PostgreSQL schema (staging_records, accounts, account_top_records, trace_logs)
- 5,000-record test fixture from real data
- pytest setup (90%+ coverage target)

### M1: Data Layer
- PostgreSQL connection pooling (SQLAlchemy)
- Domain models (Account, StagingRecord via SQLModel ORM)
- Storage service abstractions via Protocol interfaces

### M2: Pipeline Service ✅ (COMPLETE)
- Stream zstd-compressed JSONL
- Normalize records (extract domain, features, flags)
- Bulk insert staging_records
- Aggregate → accounts via SQL
- Build top-records index

**Strict SOLID:**
- ✅ SRP: One file = one service class
- ✅ ISP: Protocols for storage abstraction
- ✅ DIP: Dependency injection everywhere
- ✅ Module-level SRP: extractors/ → one class per file
- ✅ Self-documenting: Code names itself

### M3: Scoring Service
- Fetch unscored accounts
- Apply rule-based composite scoring
- Store risk_score, signal_tags, score_explanation
- Deterministic, auditable (JSON explanation per account)

### M4: LLM Client + Prompts
- Protocol-based LLMClient (MockLLMClient first)
- Prompt versioning (v1, v2, ... per task)
- Cost tracking (usage → $usd)
- Latency tracing (trace_logs.jsonl)

### M5: Enrichment Service
- Top-N selection (top 50 accounts by risk_score)
- LangGraph orchestration:
  1. Signal/noise re-classification (Haiku - ambiguous records only)
  2. Company name inference (Haiku)
  3. Risk narrative (Sonnet - grounded in rule outputs)
  4. Outreach draft (Sonnet)
- LLM calls traced to trace_logs.jsonl

### M6: FastAPI Surface
- GET /accounts (filter, sort, paginate)
- GET /accounts/{root_domain} (full detail + top records + narrative)
- POST /pipeline/runs (trigger ingest)
- POST /scoring/runs (trigger scoring)
- POST /enrichment/runs (trigger enrichment, top-n parameter)
- GET /traces (LLM tracing dashboard)
- GET /evals (signal-noise eval harness results)

### M7: Test Suite Green
- 90%+ unit test coverage (service layer)
- All tests use mocked storage
- Integration test (full pipeline → scoring → enrichment)
- mypy --strict passes

### M8: Documentation
- architecture.md (see docs/architecture.md)
- cost_model.md (token volume × frequency × pricing)
- roadmap.md (future: UI, hosting, concurrency, CRM)
- how-you-build.md (decisions and rationale)

## Roadmap (Not This Phase)

❌ **UI:** Web dashboard for lead scoring, filtering, export
❌ **Hosting:** Containerization, CI/CD, staging/prod infrastructure
❌ **Multi-Snapshot:** Track deltas between scan dates (signal of change)
❌ **CRM Integration:** Salesforce, HubSpot sync
❌ **Auth:** API keys, role-based access control
❌ **Performance Tuning:** Full-file streaming, incremental indexing
❌ **Horizontal Scaling:** Read replicas, connection pooling (pgBouncer)

## Technical Constraints

### PostgreSQL
- Connection pooling via SQLAlchemy (thread-safe, efficient)
- ACID transactions ensure data consistency
- Concurrent writers supported (no single-writer limitation)

### LLM Cost Control
- Top-N selection (only enrich top 50 accounts/day, not 10.6M)
- Cost ceiling documented: ~$1/day for production usage
- Mock client for dev/testing (zero cost)

### Type Safety
- mypy --strict on all services
- No Any without justification
- Protocols for all abstractions

## Metrics & Success Criteria

✅ **Code Quality**
- 90%+ coverage (service layer unit tests)
- Zero SOLID violations (each violation reviewed + fixed)
- mypy --strict passing

✅ **Architecture**
- Each service ≤ 10 classes (stay focused)
- No circular dependencies
- Clear data flow (API → Service → Storage)

✅ **Performance**
- Pipeline: ingest 10.6M records in < 1 hour
- Scoring: score 100K accounts in < 5 minutes
- Enrichment: enrich 50 accounts in < 5 minutes (LLM bottleneck)

✅ **Cost**
- Rule-based scoring: free
- LLM enrichment: < $0.01 per account (Haiku) + $0.10 (Sonnet)
- Daily enrichment budget: ~$30/month for top-50 accounts/day
