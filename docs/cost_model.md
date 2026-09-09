# Cost Model: Token Usage & LLM Expenses

## Overview

**Only LLM phase incurs recurring cost.** All other phases (pipeline, aggregation, scoring) are free.

Pricing (as of Sept 2026):
- Claude Haiku: $1/M input tokens, $5/M output tokens
- Claude Sonnet: $2/M input tokens, $10/M output tokens

## Task Breakdown

### Task 1: Signal/Noise Re-Classification (Haiku)

**When:** Enrichment phase, ambiguous records only
**Why:** Distinguish genuine vulnerabilities from honeypots
**Model:** Haiku (cheap, high-volume)

Per account:
- Input: Top 20 records (filtered) + text description
- Context: ~500-1000 tokens per record
- Output: Classification (20-50 tokens)
- **Estimated:** 15,000 input tokens + 500 output tokens per account

**Cost per account:** (15k × $1 + 500 × $5) / 1M = $0.019

### Task 2: Company Name Inference (Haiku)

**When:** Enrichment phase, all top-N accounts
**Why:** Infer company from domain + HTTP titles
**Model:** Haiku

Per account:
- Input: Root domain + sample HTTP titles + products
- Context: ~200-300 tokens
- Output: Company name + confidence (30-50 tokens)
- **Estimated:** 2,000 input tokens + 100 output tokens per account

**Cost per account:** (2k × $1 + 100 × $5) / 1M = $0.0025

### Task 3: Risk Narrative (Sonnet)

**When:** Enrichment phase, final narrative for sales
**Why:** Human-readable explanation for account risk
**Model:** Sonnet (sophisticated reasoning, lower volume)

Per account:
- Input: Account summary + rule signals + top records + risk score + score explanation
- Context: ~2,000-3,000 tokens
- Output: 200-word narrative (300-500 tokens)
- **Estimated:** 2,500 input tokens + 400 output tokens per account

**Cost per account:** (2.5k × $2 + 400 × $10) / 1M = $0.009

### Task 4: Outreach Draft (Sonnet)

**When:** Enrichment phase, email draft for sales
**Why:** Personalized cold-email skeleton
**Model:** Sonnet

Per account:
- Input: Company name + inferred industry + key signals + risk score
- Context: ~500-1,000 tokens
- Output: Email draft (200-300 tokens)
- **Estimated:** 750 input tokens + 250 output tokens per account

**Cost per account:** (750 × $2 + 250 × $10) / 1M = $0.0035

## Daily Cost (Full Enrichment Run)

### Scenario: Enrich Top 50 Accounts Daily

| Task | Accounts | Cost/Account | Subtotal |
|------|----------|--------------|----------|
| Signal/Noise (Haiku) | 50 | $0.019 | $0.95 |
| Company Inference (Haiku) | 50 | $0.0025 | $0.13 |
| Risk Narrative (Sonnet) | 50 | $0.009 | $0.45 |
| Outreach Draft (Sonnet) | 50 | $0.0035 | $0.18 |
| **TOTAL PER DAY** | | | **$1.71** |

### Monthly Cost

- **Daily:** $1.71
- **Monthly (30 days):** $51.30
- **Quarterly:** $153.90
- **Annually:** $615.60

### Cost Ceiling Justification

**Why $0.02 per account?**
- Enrichment is for TOP accounts only (top 50-100)
- Lower-ranked accounts = lower priority (skip LLM)
- Haiku covers 95% of cases (cheap re-classification + inference)
- Sonnet used only for narrative + outreach (high value)

## Scaling Scenarios

### Conservative: Top 20 Accounts Daily
- Daily: $0.68
- Monthly: $20.40
- Annually: $244.80

### Growth: Top 100 Accounts Daily
- Daily: $3.42
- Monthly: $102.60
- Annually: $1,231.20

### Aggressive: Top 500 Accounts Daily
- Daily: $17.10
- Monthly: $513.00
- Annually: $6,156.00

## Comparison: Rule-Based vs LLM

| Approach | Cost | Latency | Accuracy |
|----------|------|---------|----------|
| **Rules only** | $0 | <1ms | 70-80% (deterministic) |
| **Rules + LLM (hybrid)** | $0.02/account | 2-5s | 90-95% (augmented) |
| **LLM only** | $0.10/account | 5-10s | 85-92% (hallucination risk) |

**Decision:** Rules + selective LLM (production strategy)

## Cost Tracking Implementation

### Per-Request Tracing

All LLM calls logged to `trace_logs.jsonl`:

```json
{
  "trace_id": "uuid",
  "timestamp": "2026-09-10T12:34:56Z",
  "task": "signal_noise_classify",
  "root_domain": "example.com",
  "model": "claude-haiku-4-5",
  "prompt_version": "v1",
  "input_tokens": 15000,
  "output_tokens": 500,
  "cost_usd": 0.019,
  "latency_ms": 1200,
  "success": true
}
```

### Dashboard Query

```sql
SELECT
  task,
  COUNT(*) as calls,
  AVG(input_tokens) as avg_input,
  AVG(output_tokens) as avg_output,
  AVG(latency_ms) as avg_latency_ms,
  SUM(cost_usd) as total_cost_usd
FROM read_json_auto('trace_logs.jsonl')
WHERE timestamp >= NOW() - INTERVAL 1 DAY
GROUP BY task
ORDER BY total_cost_usd DESC;
```

### Example Output

```
Task                      | Calls | Avg Input | Avg Output | Avg Latency | Total Cost
--------------------------|-------|-----------|------------|-------------|----------
risk_narrative            | 50    | 2,500     | 400        | 1500ms      | $0.45
signal_noise_classify     | 50    | 15,000    | 500        | 2000ms      | $0.95
company_infer             | 50    | 2,000     | 100        | 800ms       | $0.13
outreach_draft            | 50    | 750       | 250        | 1200ms      | $0.18
--------------------------|-------|-----------|------------|-------------|----------
TOTAL                     | 200   |           |            |             | $1.71
```

## Optimization Strategies

### 1. Batch Processing
- Group similar companies (same industry) for inference
- Reuse company names across domains (cache NamesStorageService)
- Expected savings: 30-40% on company inference

### 2. Prompt Versioning
- v1: Full context (baseline)
- v2: Minimal context (faster, cheaper)
- A/B test on 10% of accounts
- Expected savings: 20% token reduction

### 3. Conditional Enrichment
- Skip enrichment for low-risk accounts (< 30 score)
- Skip narrative for medium-risk (< 60 score) if budget low
- Prioritize Sonnet for top 20 only
- Expected savings: 40-50% on large scales

### 4. Caching
- Store company inferences (rarely changes)
- Store narratives by risk score bracket (reuse patterns)
- Cache busted on new snapshot or rule version
- Expected savings: 60-70% on repeat enrichments

## Cost Control: Hard Limits

Recommended implementation:
```python
MAX_COST_PER_DAY = 2.50  # Stop enrichment if exceeded
MAX_COST_PER_ACCOUNT = 0.05  # Skip expensive accounts
MAX_ACCOUNTS_PER_RUN = 100  # Never enrich > 100/day

if total_cost_today > MAX_COST_PER_DAY:
    log.warning("Daily budget exceeded, pausing enrichment")
    return {"status": "paused", "reason": "budget_exceeded"}
```

## Forecasting Revenue

If SaaS model (per-lead or per-account):

**Example pricing:** $0.50 per qualified lead

| Scenario | Accounts/Day | Enrichment Cost | Revenue (50% conversion) | Margin |
|----------|--------------|-----------------|--------------------------|---------|
| Conservative | 20 | $0.34 | $5.00 | 93% |
| Growth | 100 | $1.71 | $25.00 | 93% |
| Aggressive | 500 | $8.55 | $125.00 | 93% |

**Viable at any scale** (LLM cost is <7% of revenue at reasonable pricing)
