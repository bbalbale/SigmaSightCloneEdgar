# Database Architecture Analysis: Separating Vector (RAG) from Numerical (Calculations)

**Created**: 2025-12-19
**Status**: Research & Recommendation
**Context**: Performance issues with pgvector impacting core calculation engine

---

## Executive Summary

SigmaSight's PostgreSQL database with pgvector is handling two fundamentally different workloads that compete for resources. This document recommends separating RAG/vector operations from numerical calculations using two PostgreSQL instances on Railway.

**Key Decision**: Keep market data WITH core database (not a third database).

---

## Current State

### Single Database Architecture (Problem)

```
┌─────────────────────────────────────────────────────────────────┐
│              PostgreSQL + pgvector (Single Instance)            │
│                                                                 │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐│
│  │  Numerical/OLTP         │    │  Vector/RAG                 ││
│  │  (Core Calculations)    │    │  (AI Engine)                ││
│  │                         │    │                             ││
│  │  • positions            │    │  • ai_kb_documents          ││
│  │  • portfolios           │    │  • ai_memories              ││
│  │  • position_greeks      │    │  • ai_feedback              ││
│  │  • factor_exposures     │    │                             ││
│  │  • correlations         │    │  1536-dim embeddings        ││
│  │  • snapshots            │    │  HNSW index traversal       ││
│  │  • market_data_cache    │    │  High memory consumption    ││
│  │  • company_profiles     │    │                             ││
│  └─────────────────────────┘    └─────────────────────────────┘│
│                                                                 │
│            ⚠️ RESOURCE CONTENTION - "Noisy Neighbor" Problem    │
└─────────────────────────────────────────────────────────────────┘
```

### Workload Characteristics

| Workload | Tables | Characteristics |
|----------|--------|-----------------|
| **RAG/Vector** | `ai_kb_documents`, `ai_memories`, `ai_feedback` | High memory, ANN graph traversal, 1536-dim embeddings |
| **Numerical/Transactional** | `positions`, `portfolios`, `position_greeks`, `factor_exposures`, `correlations`, `snapshots` | ACID transactions, complex joins, time-series aggregations |
| **Market Data** | `market_data_cache`, `company_profiles` | Read-heavy, shared across users, time-series |

---

## The "Noisy Neighbor" Problem

Vector similarity searches are **RAM-hungry** operations. Vector workloads act like "noisy neighbors" requiring gigabytes of memory for ANN (Approximate Nearest Neighbor) graph traversal.

When RAG queries run, they compete with batch calculations for:
- **Shared buffers** - Vector indexes need to stay in RAM
- **work_mem** - ANN searches are memory-intensive
- **I/O bandwidth** - Large embedding columns (6KB per row at 1536 dims)

This is why calculation engine slowdowns occur during AI chat activity.

---

## Market Data Separation Analysis

### Should Market Data Be Separate? **NO**

| Factor | Assessment |
|--------|------------|
| **Scale** | ~63 positions, 3 portfolios - market data volume is small |
| **Join complexity** | Portfolio views need prices + positions in single query |
| **API-first architecture** | You fetch from YFinance/FMP on-demand, not storing years of history |
| **Incremental complexity** | 3 DBs = 3x connection pools, 3x monitoring, 3x backups |
| **The actual bottleneck** | pgvector (solved by AI separation), not market data |

### Data Access Patterns

| Data Type | Access Pattern | Update Frequency | Shared Across Users? |
|-----------|---------------|------------------|---------------------|
| **User Data** | Transactional, joins with positions | On user action | No |
| **Portfolio/Positions** | Read-heavy, complex joins | On trades/imports | No |
| **Market Data (prices)** | Time-series queries, lookups by symbol | Daily batch + real-time | **Yes** |
| **Calculations** | Batch writes, analytical reads | Daily batch | No |

### When to Reconsider Market Data Separation

| Trigger | Threshold |
|---------|-----------|
| Historical price rows | > 10 million records |
| Symbols tracked | > 5,000 unique symbols |
| Real-time price updates | Sub-second requirements |
| Multi-tenant with isolation | Different clients need data isolation |

**Current recommendation**: Market data stays with core database.

---

## Recommendation: Dual PostgreSQL Architecture on Railway

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Railway Project                          │
│                                                                 │
│  ┌───────────────────────────────┐    ┌───────────────────────┐│
│  │  PostgreSQL (Core + Market)   │    │  PostgreSQL (AI/RAG)  ││
│  │  "sigmasight-core"            │    │  "sigmasight-ai"      ││
│  │                               │    │                       ││
│  │  USER DATA:                   │    │  • ai_kb_documents    ││
│  │  • users                      │    │  • ai_memories        ││
│  │  • portfolios                 │    │  • ai_feedback        ││
│  │  • positions                  │    │                       ││
│  │  • tags, position_tags        │    │  pgvector extension   ││
│  │                               │    │  HNSW index           ││
│  │  CALCULATIONS:                │    │  Vector workloads     ││
│  │  • position_greeks            │    │                       ││
│  │  • factor_exposures           │    │                       ││
│  │  • correlations               │    │                       ││
│  │  • snapshots                  │    │                       ││
│  │                               │    │                       ││
│  │  MARKET DATA:                 │    │                       ││
│  │  • market_data_cache          │    │                       ││
│  │  • company_profiles           │    │                       ││
│  │  (efficient joins with        │    │                       ││
│  │   positions table)            │    │                       ││
│  └───────────────────────────────┘    └───────────────────────┘│
│              │                              │                   │
│              └──────────┬───────────────────┘                   │
│                         │                                       │
│                    FastAPI Backend                              │
│                    (single service)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why Two PostgreSQL Databases (Not a Dedicated Vector DB)?

| Factor | Two PostgreSQL DBs | Dedicated Vector DB (Pinecone/Qdrant) |
|--------|-------------------|---------------------------------------|
| **Complexity** | Low - same tech stack | Medium - new SDK, different patterns |
| **Cost** | ~$5-10/mo extra on Railway | $25-100+/mo for managed vector DB |
| **Data Consistency** | Easy - same SQL patterns | Requires sync logic |
| **Scaling Path** | Clear - add resources as needed | Different scaling model |
| **Your Scale** | pgvector handles <100M vectors well | Overkill unless billions of vectors |

### pgvector Performance (2024-2025 Benchmarks)

- pgvector 0.8.0 offers up to **9× faster query processing**
- **100× more relevant results** with improved algorithms
- **40-80% cost reduction** compared to specialized vector DBs for <100M vectors
- HNSW index build speeds **30× faster** in recent versions
- Scalar quantization saves **50% memory** while maintaining quality

---

## Complete Table Inventory

### Tables Staying in Core Database (sigmasight-core)

**User & Portfolio Data:**
- `users`
- `portfolios`
- `positions`
- `tags` / `tags_v2`
- `position_tags`
- `portfolio_target_prices`

**Calculation Results:**
- `position_greeks`
- `position_factor_exposures`
- `position_market_betas`
- `position_volatility`
- `position_interest_rate_betas`
- `correlation_calculations`
- `pairwise_correlations`
- `correlation_clusters`
- `correlation_cluster_positions`
- `factor_correlations`
- `factor_exposures`
- `factor_definitions`
- `portfolio_snapshots`
- `stress_test_scenarios`
- `stress_test_results`
- `market_risk_scenarios`

**Market Data:**
- `market_data_cache`
- `company_profiles`
- `benchmarks_sector_weights`
- `fund_holdings`

**System:**
- `batch_jobs`
- `batch_job_schedules`
- `batch_run_tracking`
- `export_history`
- `modeling_session_snapshots`
- `equity_changes`
- `position_realized_events`

**Fundamentals:**
- `income_statements`
- `balance_sheets`
- `cash_flows`

### Tables Moving to AI Database (sigmasight-ai)

- `ai_kb_documents` (with vector embeddings)
- `ai_memories`
- `ai_feedback`

---

## Cost Analysis (Railway)

| Configuration | Monthly Cost |
|--------------|--------------|
| Current (single DB) | ~$5-20/mo |
| Dual PostgreSQL | ~$10-30/mo |
| Triple PostgreSQL (with market) | ~$15-45/mo |
| PostgreSQL + Pinecone | ~$30-120/mo |

**Recommendation**: Dual PostgreSQL provides the best cost/performance balance.

---

## Monitoring & Success Metrics

### Before Migration (Baseline)
- Batch calculation time for all portfolios
- RAG query latency (p50, p95, p99)
- Database CPU/memory during batch runs
- Database CPU/memory during AI chat

### After Migration (Target)
- Batch calculation time: **< 50% of current** (no vector contention)
- RAG query latency: **unchanged or better**
- Core DB: stable during AI chat activity
- AI DB: stable during batch calculations

---

## References

- [Crunchy Data - pgvector Performance Tips](https://www.crunchydata.com/blog/pgvector-performance-for-developers)
- [Instaclustr - pgvector 2025 Guide](https://www.instaclustr.com/education/vector-database/pgvector-key-features-tutorial-and-pros-and-cons-2026-guide/)
- [The Lean Product Studio - RAG Architecture](https://theleanproduct.studio/blog/rag-architecture-vector-database-selection)
- [DigitalOcean - Choosing Vector Databases](https://www.digitalocean.com/community/conceptual-articles/how-to-choose-the-right-vector-database)
- [Railway PostgreSQL Docs](https://docs.railway.com/guides/postgresql)
- [ZenML - Vector Databases for RAG](https://www.zenml.io/blog/vector-databases-for-rag)
- [AWS - pgvector Performance](https://aws.amazon.com/blogs/database/load-vector-embeddings-up-to-67x-faster-with-pgvector-and-amazon-aurora/)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-19 | Dual PostgreSQL over dedicated vector DB | Same tech stack, lower cost, sufficient for scale |
| 2025-12-19 | Railway deployment | Already using Railway, simple to add second instance |
| 2025-12-19 | Keep pgvector (not switch to Pinecone) | <100M vectors, pgvector 0.8.0 performance is excellent |
| 2025-12-19 | Keep market data with core | Join complexity, scale doesn't warrant separation |
| 2025-12-19 | Two fresh databases (not migrate-in-place) | Clean slate, optimal tuning, no legacy cruft |
