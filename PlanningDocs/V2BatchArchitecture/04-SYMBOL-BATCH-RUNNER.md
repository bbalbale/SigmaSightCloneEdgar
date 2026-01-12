# 04: Symbol Batch Runner

## Purpose

Daily cron job that processes ALL symbols in the universe, independent of portfolios.

**Key Insight**: Symbol data (prices, betas, factors) is the same regardless of which portfolio holds the symbol. Process once, use everywhere.

---

## Job Specification

```python
class SymbolBatchRunner:
    """
    Daily batch for symbol-level data.

    - Does NOT use portfolio watermarks
    - Does NOT depend on any portfolio state
    - Runs at fixed time daily
    """

    async def run_daily_symbol_batch(
        self,
        target_date: date = None,
        symbols: Optional[List[str]] = None  # Override for testing
    ) -> Dict[str, Any]:
        target_date = target_date or date.today()

        # Get all active symbols (if not overridden)
        if symbols is None:
            symbols = await self._get_active_symbols()

        logger.info(f"Processing {len(symbols)} symbols for {target_date}")

        # Phase tracking (reuse Phase 7.x infrastructure)
        batch_run_tracker.start(CurrentBatchRun(
            batch_run_id=f"symbol_batch_{target_date.isoformat()}",
            started_at=utc_now(),
            triggered_by="cron"
        ))

        try:
            # Phase 1: Fetch and store prices
            await self._run_price_phase(symbols, target_date)

            # Phase 2: Calculate Market Beta (OLS vs SPY)
            await self._run_market_beta_phase(symbols, target_date)

            # Phase 3: Calculate IR Beta (OLS vs TLT)
            await self._run_ir_beta_phase(symbols, target_date)

            # Phase 4: Calculate Ridge factors (6 factors)
            await self._run_ridge_factor_phase(symbols, target_date)

            # Phase 5: Calculate Spread factors (4 factors)
            await self._run_spread_factor_phase(symbols, target_date)

            # Phase 6: Update denormalized metrics
            await self._run_metrics_phase(symbols, target_date)

            batch_run_tracker.complete(success=True)
            return results

        except Exception as e:
            batch_run_tracker.complete(success=False)
            raise
```

---

## Phase Details

### Phase 1: Price Collection

```python
async def _run_price_phase(
    self,
    symbols: List[str],
    target_date: date
) -> Dict[str, Any]:
    batch_run_tracker.start_phase(
        "prices",
        "Daily Price Collection",
        len(symbols),
        "symbols"
    )

    # Batch fetch from YFinance (more efficient than per-symbol)
    prices = await yfinance_batch_fetch(symbols, target_date)

    # Bulk upsert to market_data_cache (existing table)
    await bulk_upsert_prices(prices)

    batch_run_tracker.complete_phase("prices", success=True)

    return {'symbols_updated': len(prices)}
```

### Phase 2: Market Beta (OLS vs SPY)

```python
async def _run_market_beta_phase(
    self,
    symbols: List[str],
    target_date: date
) -> Dict[str, Any]:
    batch_run_tracker.start_phase(
        "market_beta",
        "Market Beta Calculation",
        len(symbols),
        "symbols"
    )

    # Fetch SPY returns once (shared across all symbols)
    spy_returns = await self._get_returns(['SPY'], target_date, window=90)

    success = 0
    failed = 0

    # Process in batches of 10 (Railway safe)
    for batch in self._batch_symbols(symbols, batch_size=10):
        tasks = [
            self._calc_market_beta(symbol, target_date, spy_returns)
            for symbol in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failed += 1
            else:
                success += 1

        # Rate limiting
        await asyncio.sleep(0.5)

    batch_run_tracker.complete_phase("market_beta", success=True)

    return {'success': success, 'failed': failed}
```

### Phases 3-6: Similar Pattern

Each phase follows the same pattern:
1. Start phase tracking
2. Process symbols in batches of 10
3. Rate limit between batches
4. Complete phase tracking

---

## Scheduling

**Railway Cron**: 9:00 PM ET (after market close)

```python
# In scheduler_config.py
scheduler.add_job(
    func=self._run_symbol_batch,
    trigger=CronTrigger(hour=21, minute=0, timezone="America/New_York"),
    id="symbol_daily_batch",
    name="Daily Symbol Batch",
    max_instances=1,
    coalesce=True
)
```

**Why 9 PM ET?**
- Market closes at 4 PM ET
- Allow time for after-hours data to settle
- Complete before midnight for same-day processing

---

## Railway Constraints

| Constraint | Limit | Our Design |
|------------|-------|------------|
| vCPU | 8 | 10 concurrent tasks max |
| RAM | 8 GB | ~200MB peak expected |
| Dyno timeout | 30 min | Target 15 min, warn at 20 |
| DB connections | ~30 | Pool size 20 |

**Concurrency Design**:
```python
RAILWAY_BATCH_SIZE = 10  # Conservative for Railway

for batch in self._batch_symbols(symbols, batch_size=RAILWAY_BATCH_SIZE):
    tasks = [self._calculate_beta(s) for s in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0.5)  # Rate limiting
```

---

## Performance Estimate

| Phase | ~5,000 Symbols | Notes |
|-------|----------------|-------|
| Price Collection | 2-3 min | Batch YFinance call |
| Market Beta | 3-4 min | 10 concurrent |
| IR Beta | 3-4 min | 10 concurrent |
| Ridge Factors | 3-4 min | Reuse existing code |
| Spread Factors | 3-4 min | Reuse existing code |
| Metrics Update | 1 min | Denormalized upsert |
| **Total** | **12-15 min** | Fixed regardless of users |

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Single symbol fails | Log, continue, mark in metrics |
| YFinance rate limit | Backoff, retry |
| YFinance down | Fall back to FMP |
| > 10% symbols fail | Alert, but continue |
| Database error | Retry 3x, then fail phase |
| Timeout approaching | Log warning at 20 min |

---

## Telemetry

```python
# At end of batch
record_metric("symbol_batch.duration_seconds", duration)
record_metric("symbol_batch.symbols_processed", total_symbols)
record_metric("symbol_batch.symbols_failed", failed_count)
record_metric("symbol_batch.phase_1_duration", phase_1_time)
# ... per-phase metrics
```

---

## Integration with Portfolio Refresh

After symbol batch completes successfully:

```python
async def run_daily_symbol_batch(...):
    # ... all phases ...

    batch_run_tracker.complete(success=True)

    # Trigger portfolio refresh
    from app.batch.portfolio_refresh_runner import portfolio_refresh_runner
    await portfolio_refresh_runner.run_daily_portfolio_refresh(target_date)

    return results
```
