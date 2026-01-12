# 16: Parallelism & Idempotency

## Overview

Concurrency limits, rate limiting for external APIs, and idempotency guarantees for V2 batch operations.

---

## API Rate Limits (Free Plans)

| Provider | Rate Limit | Priority | Notes |
|----------|------------|----------|-------|
| YFinance | ~2000 req/hour | Primary | Unofficial, be conservative |
| YahooQuery | ~2000 req/hour | Secondary | Same underlying API |
| FMP | 250 req/day | Tertiary | Very limited on free plan |
| Polygon | 5 req/minute | Last resort | Very limited on free plan |

**Strategy**: YFinance handles 99% of requests. FMP/Polygon only for fallback when YFinance fails.

Sources:
- [FMP Pricing](https://site.financialmodelingprep.com/pricing-plans)
- [Polygon Rate Limits](https://polygon.io/knowledge-base/article/what-is-the-request-limit-for-polygons-restful-apis)

---

## Concurrency Settings

```python
# backend/app/config.py

class Settings(BaseSettings):
    # ... existing ...

    # V2 Concurrency limits
    price_fetch_concurrency: int = 5
    factor_calc_concurrency: int = 10
    portfolio_refresh_concurrency: int = 10
    symbol_onboarding_concurrency: int = 3
    symbol_onboarding_max_queue: int = 50
```

### Symbol Batch

```python
import asyncio
from app.config import settings

async def fetch_all_prices(symbols: List[str], target_date: date) -> Dict[str, Decimal]:
    """Fetch prices with concurrency limit."""
    semaphore = asyncio.Semaphore(settings.price_fetch_concurrency)
    results = {}

    async def fetch_one(symbol: str):
        async with semaphore:
            price = await fetch_symbol_price_with_fallback(symbol, target_date)
            if price:
                results[symbol] = price

    await asyncio.gather(*[fetch_one(s) for s in symbols])
    return results


async def calculate_all_factors(symbols: List[str]) -> Dict[str, SymbolFactors]:
    """Calculate factors with concurrency limit."""
    semaphore = asyncio.Semaphore(settings.factor_calc_concurrency)
    results = {}

    async def calc_one(symbol: str):
        async with semaphore:
            factors = await calculate_symbol_factors(symbol)
            if factors:
                results[symbol] = factors

    await asyncio.gather(*[calc_one(s) for s in symbols])
    return results
```

### Portfolio Refresh

```python
async def refresh_all_portfolios(portfolios: List[Portfolio], target_date: date):
    """Refresh portfolios with concurrency limit."""
    semaphore = asyncio.Semaphore(settings.portfolio_refresh_concurrency)

    async def refresh_one(portfolio: Portfolio):
        async with semaphore:
            return await refresh_portfolio(portfolio, target_date)

    results = await asyncio.gather(*[refresh_one(p) for p in portfolios])
    return results
```

---

## Rate Limiting Implementation

```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = datetime.min
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if needed to respect rate limit."""
        async with self._lock:
            now = datetime.now()
            elapsed = (now - self.last_call).total_seconds()

            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)

            self.last_call = datetime.now()


# Rate limiters for each provider
yfinance_limiter = RateLimiter(calls_per_minute=30)  # Conservative
fmp_limiter = RateLimiter(calls_per_minute=1)  # 250/day = ~0.17/min, be safe
polygon_limiter = RateLimiter(calls_per_minute=4)  # 5/min limit, leave buffer


async def fetch_from_fmp(symbol: str, date: date) -> Optional[Decimal]:
    """Fetch from FMP with rate limiting."""
    await fmp_limiter.acquire()
    # ... actual API call ...
```

---

## Idempotency

### Portfolio Refresh

**Rule**: Skip portfolios that already have today's snapshot.

```python
async def get_portfolios_without_snapshot(target_date: date) -> List[Portfolio]:
    """
    Get portfolios needing refresh.

    Idempotent: If run twice, second run finds no portfolios to process.
    """
    query = """
        SELECT p.id, p.name, p.user_id
        FROM portfolios p
        WHERE p.deleted_at IS NULL
        AND EXISTS (
            SELECT 1 FROM positions pos
            WHERE pos.portfolio_id = p.id
            AND pos.exit_date IS NULL
        )
        AND NOT EXISTS (
            SELECT 1 FROM portfolio_snapshots ps
            WHERE ps.portfolio_id = p.id
            AND ps.snapshot_date = :target_date
        )
    """
    result = await db.execute(text(query), {"target_date": target_date})
    return result.all()
```

**Behavior on re-run:**
- First run: Creates snapshots for 150 portfolios
- Second run (same day): Finds 0 portfolios, completes immediately

### Symbol Batch

**Rule**: Overwrite prices/factors for the date. Safe to re-run.

```python
async def upsert_symbol_price(symbol: str, date: date, price: Decimal):
    """Upsert price - safe to run multiple times."""
    stmt = insert(MarketDataCache).values(
        symbol=symbol,
        date=date,
        close=price
    ).on_conflict_do_update(
        index_elements=['symbol', 'date'],
        set_={'close': price, 'updated_at': func.now()}
    )
    await db.execute(stmt)
```

### Symbol Onboarding

**Rule**: Deduplicate at queue time using in-memory queue.

```python
async def enqueue_symbol(symbol: str, requested_by: Optional[UUID] = None) -> bool:
    """
    Add symbol to in-memory onboarding queue.

    Idempotent: If symbol already queued/processing, returns False.
    """
    symbol = symbol.upper()

    # Check if already in queue (in-memory check)
    if symbol in symbol_onboarding_queue._jobs:
        logger.info(f"Symbol {symbol} already in queue, skipping")
        return False

    # Check if already in universe (database check)
    async with get_async_session() as db:
        in_universe = await db.execute(
            select(SymbolUniverse)
            .where(
                SymbolUniverse.symbol == symbol,
                SymbolUniverse.is_active == True
            )
        )

        if in_universe.scalar_one_or_none():
            logger.info(f"Symbol {symbol} already in universe, skipping")
            return False

    # Add to in-memory queue
    return await symbol_onboarding_queue.enqueue(symbol, requested_by)
```

---

## Queue Backpressure

Backpressure is built into the in-memory queue:

```python
class SymbolOnboardingQueue:
    def __init__(self, max_queue_depth: int = 50, max_concurrent: int = 3):
        self.max_queue_depth = max_queue_depth
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def enqueue(self, symbol: str, ...) -> bool:
        # Check queue depth
        pending_count = sum(1 for j in self._jobs.values()
                          if j.status in ('pending', 'processing'))
        if pending_count >= self.max_queue_depth:
            raise QueueFullError(f"Queue full ({self.max_queue_depth} max)")

        # Add to queue...
```

---

## Summary

| Operation | Concurrency | Idempotency | Rate Limit |
|-----------|-------------|-------------|------------|
| Price fetch (YFinance) | 5 | Upsert | 30/min |
| Price fetch (FMP) | 1 | Upsert | 1/min |
| Price fetch (Polygon) | 1 | Upsert | 4/min |
| Factor calculation | 10 | Upsert | N/A (local) |
| Portfolio refresh | 10 | Skip if exists | N/A |
| Symbol onboarding | 3 | In-memory dedupe | N/A |
