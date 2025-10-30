# SigmaSight Batch Processing Performance Optimization Plan

**Document Version**: 1.0
**Date**: October 29, 2025
**Status**: Planning Phase

---

## Executive Summary

**Current Performance**: 60 minutes for 3 portfolios × 87 trading days
**Projected at Scale**: 1000 portfolios would take ~333 hours (13.9 DAYS) - UNACCEPTABLE

**Target Performance**:
- **Backfill**: 1000 portfolios × 87 days in **< 12 hours** ⚠️ (requires **28x speedup**)
- **Daily Production**: 1000 portfolios in **< 5 hours** (achievable with parallelization)

**Strategy**: 4-phase approach over 7 months to achieve full architectural redesign

---

## Problem Analysis

### Root Causes Identified

1. **Sequential Portfolio Processing** (No parallelization)
   - Portfolios processed one-by-one
   - 7 analytics jobs run sequentially per portfolio
   - Single database session prevents concurrent operations

2. **Phase 3 Dominates Execution Time** (55-65% of total)
   - 7 sequential analytics jobs × 3 portfolios × 87 dates = 1,827 calculations
   - 90-day regressions for market beta and IR beta
   - Factor analysis with ridge regression
   - Correlation matrix calculations

3. **N+1 Query Patterns** in Phase 2 and 2.5
   - 2 queries per position for P&L (current + previous price)
   - 1 query per position for market value updates
   - 3 queries × 21,000 positions × 87 dates = **5.5 MILLION queries** at 1000 portfolio scale

### Time Breakdown (60 minutes for 3 portfolios × 87 dates)

| Phase | Time per Date | Total Time | % of Total |
|-------|--------------|------------|------------|
| **Phase 1: Market Data** | 5-10 sec | 10-15 min | 20-25% |
| **Phase 2: P&L & Snapshots** | 3-5 sec | 5-8 min | 10-15% |
| **Phase 2.5: Position Updates** | 2-3 sec | 3-5 min | 5-10% |
| **Phase 3: Risk Analytics** | 20-30 sec | **30-40 min** | **55-65%** |

---

## Current Architecture

```
BATCH ORCHESTRATOR V3
│
├─ OUTER LOOP: for calc_date in missing_dates (87 trading days)
│   │
│   ├─ PHASE 1: Market Data Collection ✅ SHARED ACROSS PORTFOLIOS
│   │   │   [RUNS ONCE PER DATE]
│   │   ├─ Get symbol universe (positions + factor ETFs)
│   │   ├─ Check cache for existing data
│   │   ├─ Fetch missing symbols (YFinance → FMP priority chain)
│   │   ├─ Store in market_data_cache (bulk upsert, 1000 records/batch)
│   │   └─ Fetch company profiles (shared)
│   │
│   ├─ PHASE 2: P&L Calculation ⚠️ SEQUENTIAL PORTFOLIO LOOP
│   │   │   for portfolio in portfolios (3 portfolios)
│   │   │       for position in positions (21 positions avg)
│   │   ├─ Calculate position-level P&L
│   │   ├─ Create portfolio snapshot
│   │   └─ Update equity rollforward
│   │
│   ├─ PHASE 2.5: Position Market Value Updates ⚠️ SEQUENTIAL POSITION LOOP
│   │   │   for position in all_active_positions (63 total)
│   │   ├─ Update position.last_price
│   │   └─ Update position.market_value
│   │
│   └─ PHASE 3: Risk Analytics ⚠️ SEQUENTIAL PORTFOLIO × JOBS
│       │   for portfolio in portfolios (3 portfolios)
│       │       7 SEQUENTIAL analytics jobs
│       ├─ Market beta (90-day regression)
│       ├─ IR beta (90-day regression)
│       ├─ Ridge factors (5 factors)
│       ├─ Spread factors (5 factors)
│       ├─ Sector analysis
│       ├─ Volatility analytics (21d, 63d, 252d)
│       └─ Correlations
│
└─ BATCH TRACKING: Store phase durations
```

### What's Already Optimized ✅

1. **Market Data Cache** - Shared across all portfolios (Phase 1)
2. **Bulk Upserts** - 1000 records per batch (10-20x faster than individual inserts)
3. **Bulk Cache Checks** - 2 queries instead of N queries (50x reduction in round trips)
4. **Incremental Processing** - Only processes missing dates (not full reprocessing)

### User Observation: CORRECT ✅

> "If we have S&P 500 + NASDAQ symbols in market_data_cache, why are we refetching for each portfolio?"

**Answer**: We're NOT refetching market data (Phase 1 is shared). BUT we ARE inefficiently querying the cache in Phase 2 and 2.5 with N+1 patterns.

---

## Optimization Roadmap

### Phase 1: Foundation & Quick Wins (3-4 weeks)
**Goal**: 2-3x speedup → 165 hours for 1000 portfolios

#### 1.1 Query Optimization
- **Problem**: N+1 queries in Phase 2 and 2.5
- **Solution**: Bulk price fetching
  - Current: 2 queries per position (current + previous price)
  - Optimized: 2 bulk queries for all positions
  - **Impact**: 2-3x speedup for Phase 2/2.5

#### 1.2 Database Infrastructure
- **Problem**: Connection pool too small for parallelization
- **Solution**: Scale infrastructure
  - Increase connection pool from ~20 to 100-150 connections
  - Add read replicas for analytics queries (if needed)
  - Configure separate pools for batch vs API
  - **Impact**: Enable parallelization

#### 1.3 Instrumentation
- Add detailed timing metrics per phase per portfolio
- Add query profiling and slow query logging
- Add memory profiling
- **Impact**: Identify actual bottlenecks with data

**Deliverable**: Baseline metrics + 2-3x speedup

---

### Phase 2: Portfolio Parallelization (4-5 weeks)
**Goal**: Additional 3-5x speedup → 33-55 hours for 1000 portfolios

#### 2.1 Portfolio-Level Concurrency
- **Problem**: Portfolios processed sequentially
- **Solution**: Parallel processing with asyncio
  - Refactor batch orchestrator to use `asyncio.TaskGroup`
  - Process 20-50 portfolios concurrently (tuned to DB connections)
  - Each portfolio gets independent DB session
  - **Impact**: 3-5x speedup

#### 2.2 Analytics Job Parallelization
- **Problem**: 7 analytics jobs run sequentially per portfolio
- **Solution**: Parallelize independent jobs
  - Independent: market_beta, ir_beta, ridge_factors, spread_factors, sector, volatility
  - Dependent: correlations (needs position data first)
  - Run independent jobs in parallel per portfolio
  - **Impact**: 1.5-2x speedup for Phase 3

#### 2.3 Batch Size Tuning
- Tune portfolio batch size vs connection pool size
- Add backpressure handling
- Monitor connection utilization

**Deliverable**: 6-10x total speedup from Phase 1 baseline

---

### Phase 3: Distributed Architecture (8-12 weeks) 🚀
**Goal**: Additional 4-6x speedup → **8-12 hours for 1000 portfolios** ✅ TARGET

#### 3.1 Message Queue Architecture

**Technology Options:**

| Option | Pros | Cons | Best For |
|--------|------|------|----------|
| **Celery + Redis** | Full control, lower cost, Python-native | Need to manage infrastructure | On-prem or self-hosted cloud |
| **AWS SQS + Lambda** | Zero infrastructure, auto-scaling, pay-per-use | Higher per-task cost, cold starts | Cloud-native, variable workload |
| **AWS Batch + ECS** | Managed infrastructure, Docker-based | More complex setup | Large scale, predictable workload |

**Task Types:**
- `fetch_market_data_task(date)` - Phase 1, single task per date
- `calculate_portfolio_pnl_task(portfolio_id, date)` - Phase 2
- `update_position_values_task(portfolio_id, date)` - Phase 2.5
- `run_portfolio_analytics_task(portfolio_id, date, analytics_job)` - Phase 3

#### 3.2 Worker Pool
- Deploy 10-20 worker nodes (or serverless functions)
- Each worker processes portfolios independently
- Horizontal scaling based on queue depth

#### 3.3 Batch Orchestration Service
Coordinator service that:
- Distributes work to queue
- Monitors task completion
- Aggregates results
- Handles failures and retries

#### 3.4 New Architecture Flow

```
Batch Coordinator Service
│
├─ Phase 1: Fetch Market Data (SINGLE TASK per date)
│   └─ Result: market_data_cache populated for all symbols
│   └─ Blocks until complete
│
├─ Phase 2-3: Enqueue 87,000 Portfolio Tasks (1000 portfolios × 87 dates)
│   │
│   │   [DISTRIBUTED ACROSS WORKERS]
│   ├─ Worker 1 → Portfolio A, Date 1 (P&L + Analytics)
│   ├─ Worker 2 → Portfolio B, Date 1 (P&L + Analytics)
│   ├─ Worker 3 → Portfolio C, Date 1 (P&L + Analytics)
│   ├─ Worker 4 → Portfolio D, Date 1 (P&L + Analytics)
│   ├─ ...
│   ├─ Worker N → Portfolio Z, Date 87 (P&L + Analytics)
│   │
│   │   [EACH WORKER RUNS INDEPENDENTLY]
│   │   - Calculate P&L
│   │   - Update position values
│   │   - Run 7 analytics jobs (parallelized within worker)
│   │   - Write results to database
│   │
│   └─ All 87,000 tasks complete in parallel
│
└─ Phase 4: Aggregate Results
    └─ Update batch_run_tracking
    └─ Generate summary reports
```

**Parallelization Math:**
- 87,000 portfolio-date combinations
- 20 workers running concurrently
- Each task takes ~30-40 seconds (after Phase 1+2 optimizations)
- Total time: 87,000 / 20 × 35 sec = **42 hours / 20 = ~2 hours** 🚀

**With More Workers:**
- 50 workers: **~1 hour**
- 100 workers: **~30 minutes**

**Deliverable**: < 12 hour backfill at 1000 portfolio scale ✅

---

### Phase 4: Advanced Optimizations (Ongoing)
**Goal**: Handle growth to 5000-10000+ portfolios

#### 4.1 Precomputed Analytics Cache
- Cache factor returns, correlation matrices
- Incremental updates instead of full recalculation
- **Impact**: 2-3x speedup for repeated calculations

#### 4.2 Approximate Analytics
- Use sampling for large portfolios (>1000 positions)
- Monte Carlo for stress tests
- **Impact**: Maintain sub-second response times at scale

#### 4.3 Time-Series Database
- Consider TimescaleDB for market_data_cache
- Optimize time-series queries with native time-series indexes
- **Impact**: 5-10x faster historical queries

#### 4.4 CDC Pipeline
- Change Data Capture for real-time updates
- Stream processing for incremental analytics
- **Impact**: Near real-time analytics without batch runs

---

## Implementation Timeline

### Months 1-2: Quick Wins + Foundation
**Focus**: Query optimization, connection pool tuning, instrumentation

**Activities:**
- Refactor Phase 2 to bulk price fetching
- Refactor Phase 2.5 to bulk price fetching
- Increase database connection pool to 100-150
- Add timing instrumentation to all phases
- Add query profiling

**Outcome**: 2-3x speedup
- Current: 60 min for 3 portfolios
- Target: 20-30 min for 3 portfolios
- Projected for 1000: ~165 hours

---

### Months 2-4: Parallelization
**Focus**: Portfolio concurrency, analytics parallelization

**Activities:**
- Refactor batch orchestrator to use `asyncio.TaskGroup`
- Implement portfolio batching (20-50 concurrent)
- Parallelize independent analytics jobs
- Tune connection pool and batch sizes
- Monitor database load and connection utilization

**Outcome**: 6-10x total speedup
- Current baseline: 60 min for 3 portfolios
- Target: 6-10 min for 3 portfolios
- Projected for 1000: ~33-55 hours

---

### Months 4-7: Distributed Architecture
**Focus**: Message queue, worker pool, orchestration service

**Activities:**
- Choose technology stack (Celery vs AWS vs hybrid)
- Implement message queue architecture
- Deploy worker pool (10-20 workers initially)
- Build batch orchestration service
- Implement retry logic and error handling
- Add monitoring and alerting

**Outcome**: 20-30x total speedup ✅ TARGET MET
- Current baseline: 60 min for 3 portfolios
- Target: 2-3 min per date for all portfolios
- Projected for 1000: **8-12 hours** ✅

---

### Months 7+: Scale & Polish
**Focus**: Advanced optimizations, monitoring, cost optimization

**Activities:**
- Implement precomputed analytics cache
- Add approximate analytics for large portfolios
- Evaluate TimescaleDB for time-series
- Build CDC pipeline for real-time updates
- Optimize costs (worker count, instance types)
- Add comprehensive monitoring and alerting

**Outcome**: Ready for 5000-10000+ portfolios
- Daily production: 1000 portfolios in **< 1 hour**
- Backfill: 1000 portfolios in **< 4 hours**

---

## Success Metrics

### Phase 1 Targets (Months 1-2)
- ✅ 3 portfolios in 20-30 min (current: 60 min)
- ✅ Bulk query implementation complete
- ✅ Connection pool scaled to 100-150
- ✅ Timing instrumentation in place

### Phase 2 Targets (Months 2-4)
- ✅ 3 portfolios in 6-10 min
- ✅ 1000 portfolios projected at 33-55 hours
- ✅ 20-50 portfolios processed concurrently
- ✅ Analytics jobs parallelized per portfolio

### Phase 3 Targets (Months 4-7) 🎯 PRIMARY GOAL
- ✅ **1000 portfolios × 87 days in < 12 hours**
- ✅ 10-20 worker nodes deployed
- ✅ Message queue architecture operational
- ✅ Retry and error handling working

### Phase 4 Targets (Months 7+)
- ✅ 1000 portfolios × 87 days in < 4 hours
- ✅ Daily production in < 1 hour
- ✅ Ready for 5000+ portfolio scale

---

## Risks & Mitigation

### Risk 1: Database Overload
**Risk**: 100-150 concurrent connections may overwhelm PostgreSQL

**Mitigation:**
- Add read replicas for analytics queries
- Use connection pooling with PgBouncer
- Monitor database CPU, memory, I/O
- Scale database instance if needed

### Risk 2: Task Failures in Distributed System
**Risk**: Worker failures may leave incomplete data

**Mitigation:**
- Implement idempotent tasks (can be retried safely)
- Add dead letter queues for failed tasks
- Implement retry logic with exponential backoff
- Add task timeout monitoring

### Risk 3: Cost Overruns
**Risk**: 50-100 workers may be expensive

**Mitigation:**
- Start with 10-20 workers, scale up gradually
- Use spot instances or serverless (pay per use)
- Implement auto-scaling based on queue depth
- Monitor cost per portfolio-date calculation

### Risk 4: Complexity and Debugging
**Risk**: Distributed system harder to debug

**Mitigation:**
- Comprehensive logging and tracing
- Add distributed tracing (OpenTelemetry)
- Implement health checks and monitoring
- Feature flags for incremental rollout

### Risk 5: Data Consistency
**Risk**: Concurrent writes may cause race conditions

**Mitigation:**
- Use proper transaction boundaries
- Implement row-level locking where needed
- Use PostgreSQL advisory locks for coordination
- Ensure idempotent operations

---

## Cost Estimates

### Phase 1+2: Parallelization (AWS RDS + EC2)
- PostgreSQL RDS (db.r5.2xlarge): $1,200/month
- API Server (t3.medium): $30/month
- **Total**: ~$1,230/month

### Phase 3: Distributed Architecture

#### Option A: Celery + Redis + EC2
- PostgreSQL RDS (db.r5.4xlarge): $2,400/month
- Redis (cache.r5.xlarge): $200/month
- 20 Worker Nodes (t3.large spot): $300/month
- API Server (t3.medium): $30/month
- **Total**: ~$2,930/month (~2.4x increase)

#### Option B: AWS SQS + Lambda
- PostgreSQL RDS (db.r5.4xlarge): $2,400/month
- SQS: $0.40 per 1M requests
- Lambda: $0.20 per 1M requests × 100ms avg
- For 1000 portfolios × 87 dates daily: ~$50/month
- API Server (t3.medium): $30/month
- **Total**: ~$2,480/month (~2x increase)

**Recommendation**: Start with Option A (Celery) for cost control, migrate to Lambda if usage spikes.

---

## Next Steps

1. **Immediate (Week 1-2)**:
   - Review and approve optimization plan
   - Allocate engineering resources (1-2 developers)
   - Set up project tracking and milestones

2. **Phase 1 Kickoff (Week 3-4)**:
   - Implement bulk price fetching in Phase 2
   - Increase connection pool to 100
   - Add timing instrumentation
   - Run benchmark tests

3. **Phase 1 Validation (Week 5-6)**:
   - Measure actual speedup (target: 2-3x)
   - Identify remaining bottlenecks with profiling
   - Adjust Phase 2 plan based on results

4. **Phase 2 Planning (Week 7)**:
   - Detailed design for portfolio parallelization
   - Connection pool tuning strategy
   - Risk assessment and mitigation planning

---

## References

### Code Files
- `backend/app/batch/batch_orchestrator_v3.py` - Main orchestration
- `backend/app/batch/market_data_collector.py` - Phase 1 implementation
- `backend/app/batch/pnl_calculator.py` - Phase 2 implementation
- `backend/app/batch/analytics_runner.py` - Phase 3 implementation

### Related Documents
- `backend/CLAUDE.md` - Project overview and architecture
- `backend/TODO3.md` - Current Phase 3 API development status
- `backend/_docs/requirements/` - Product requirements and specifications

### Performance Analysis
- Current reseed log: `backend/reseed_fixed_commit.log`
- Batch processing analysis: October 29, 2025 session

---

**Document Owner**: Engineering Team
**Last Updated**: October 29, 2025
**Next Review**: After Phase 1 completion (Month 2)
