# Roadmap: Future Phases

## Phase 2: Production Deployment ✅ (Partially Complete)

### Infrastructure
- Docker containerization (services + PostgreSQL)
- CI/CD pipeline (GitHub Actions)
- Staging/prod environments
- Monitoring dashboard (Logfire integration)

### Database
✅ **PostgreSQL** (concurrent writers, ACID transactions)
- Connection pooling via SQLAlchemy (thread-safe)
- Query optimization (indices, materialized views)
- Backup/restore strategies

## Phase 3: Concurrency & Multi-Writer ✅ (Built In)

**Current:** PostgreSQL supports concurrent writers natively
- No single-writer limitation
- ACID transactions ensure consistency
- Connection pooling for efficient resource usage

**Future:** Application-level optimizations
- Redis queue for long-running tasks
- Async task workers (Celery or similar)
- Rate limiting per writer

## Phase 4: Multi-Snapshot Signals

**Current:** Single snapshot (2026-09-07)

**Future:** Track changes across snapshots
```sql
SELECT 
  current_snapshot.root_domain,
  current_snapshot.risk_score - previous_snapshot.risk_score as score_delta,
  CASE 
    WHEN current_snapshot.vuln_count > previous_snapshot.vuln_count THEN 'NEW_VULNS'
    WHEN current_snapshot.is_legacy_protocol AND NOT previous_snapshot.is_legacy_protocol THEN 'NEW_EXPOSURE'
    ELSE 'NO_CHANGE'
  END as signal
FROM accounts current_snapshot
JOIN accounts_2026_09_01 previous_snapshot 
  ON current_snapshot.root_domain = previous_snapshot.root_domain
WHERE current_snapshot.risk_score > previous_snapshot.risk_score
```

**Value:** "Score went 45→72 in 3 days" is higher priority than absolute score

## Phase 5: CRM Integration

### Salesforce
- Map accounts → Leads
- Create/update opportunities for high-risk domains
- Sync signal_tags → custom fields
- Two-way sync (sales feedback → exclusion list)

### HubSpot
- Company database sync
- Contact association
- Deal pipeline automation

## Phase 6: UI/Frontend

### Dashboard (MVP)
- Account risk scorecard
- Filter by score, signal tags, industry, geography
- CSV export for sales
- Drill-down: account detail → top records → narrative

### Admin Panel
- Score model tuning (adjust weights)
- Rule tuning (adjust port lists, thresholds)
- Prompt versioning (A/B test enrichment prompts)
- Cost monitoring (real-time LLM spend)

## Phase 7: Advanced Analytics

### Cohort Analysis
- Industry-level risk distribution
- Geographic concentration
- Temporal trends (score drift over time)

### Predictive Models
- Breach likelihood (based on exposure + vulnerabilities)
- Time-to-compromise estimates
- Prioritization algorithms (ML, not rules)

## Phase 8: API Enhancements

### Rate Limiting & Auth
- API key authentication
- Rate limits (100 req/min for standard tier)
- Usage tracking per key

### Webhooks
- Real-time notifications for high-risk discoveries
- Signal-triggered alerts (NEW_VULNERABILITY, EXPOSED_DATABASE, etc.)
- Batch notifications (daily summary)

### Streaming API
- Server-sent events (SSE) for live enrichment progress
- WebSocket for real-time updates

## Phase 9: Quality & Scale

### Performance Tuning
- Full-file streaming (parallel processing)
- Query optimization (indices on scoring queries)
- Caching layer (Redis for hot accounts)

### Reliability
- Dead-letter queue for failed enrichments
- Automatic retries with exponential backoff
- Circuit breaker for LLM API failures

### Observability
- Distributed tracing (full request flow)
- Custom metrics (accounts processed/hour, LLM cost per account)
- SLO tracking (availability, latency percentiles)

## Phase 10: Commercial Readiness

### Compliance
- SOC 2 certification
- GDPR/CCPA compliance (data retention, right to be forgotten)
- PII scrubbing (remove customer data from logs)

### Documentation
- API reference (OpenAPI/Swagger)
- Integration guides (Salesforce, HubSpot, custom)
- Best practices (lead scoring, prioritization)

### Partnerships
- Shodan integration (direct data feed)
- LinkedIn enrichment (company details)
- Industry database (SIC codes, employee counts)

## Implementation Order

**Priority 1 (Months 1-2):**
1. Production deployment (Docker + basic CI/CD)
2. Postgres migration (concurrent writes)

**Priority 2 (Months 3-4):**
3. Multi-snapshot signals
4. Concurrency improvements

**Priority 3 (Months 5-6):**
5. CRM integration (Salesforce first)
6. UI/dashboard

**Priority 4 (Months 7+):**
7. Advanced analytics
8. API enhancements
9. Quality & scale
10. Commercial readiness

## Success Metrics (Post-MVP)

- **Adoption:** % of customer base using platform
- **Lead Quality:** % of leads that convert (vs. traditional ICP scoring)
- **Time-to-Value:** Days from signup to first qualified lead
- **Cost Efficiency:** LLM cost per qualified lead
- **Reliability:** 99.9% uptime, <1s p99 latency for account lookup
