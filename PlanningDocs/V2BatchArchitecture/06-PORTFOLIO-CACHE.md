# 06: Symbol & Portfolio Cache

## Overview

In-memory cache for symbol-level data. Small enough (~65 MB) to hold entirely in memory. Refreshed daily during symbol batch, with new symbols added on-demand during onboarding.

---

## Cache Size Estimate

| Data Type | Per Symbol | 5,000 Symbols |
|-----------|------------|---------------|
| Latest prices | ~50 bytes | 250 KB |
| Factor exposures | ~100 bytes | 500 KB |
| Stress test data | ~200 bytes | 1 MB |
| 1-year price history | ~12 KB | 63 MB |
| **Total** | | **~65 MB** |

Railway provides 8 GB RAM. This cache uses < 1%.

---

## Cache Structure

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Dict, List, Optional
import asyncio

@dataclass
class SymbolPriceData:
    symbol: str
    close: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    volume: int
    price_date: date

@dataclass
class SymbolFactors:
    symbol: str
    market_beta: Decimal
    ir_beta: Decimal
    ridge_factors: Dict[str, Decimal]  # 6 factors
    spread_factors: Dict[str, Decimal]  # 4 factors
    factor_date: date

@dataclass
class SymbolStressData:
    symbol: str
    scenarios: Dict[str, Decimal]  # scenario_name -> impact

@dataclass
class SymbolCache:
    """Complete cache for a single symbol."""
    latest_price: SymbolPriceData
    price_history: List[SymbolPriceData]  # 1 year
    factors: SymbolFactors
    stress: SymbolStressData


class SymbolCacheService:
    """
    In-memory cache for all symbol data.

    Lifecycle:
    1. Load from DB on startup
    2. Refresh entirely during nightly symbol batch
    3. Add individual symbols during mid-day onboarding
    """

    def __init__(self):
        self._cache: Dict[str, SymbolCache] = {}
        self._lock = asyncio.Lock()
        self._last_refresh: Optional[date] = None

    async def initialize(self, db) -> None:
        """Load entire cache from database on startup."""
        async with self._lock:
            symbols = await self._load_all_symbols(db)
            for symbol_data in symbols:
                self._cache[symbol_data.symbol] = symbol_data
            self._last_refresh = date.today()
            logger.info(f"Cache initialized with {len(self._cache)} symbols")

    def get(self, symbol: str) -> Optional[SymbolCache]:
        """Get cached data for a symbol."""
        return self._cache.get(symbol.upper())

    def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest closing price for a symbol."""
        cached = self._cache.get(symbol.upper())
        return cached.latest_price.close if cached else None

    def get_factors(self, symbol: str) -> Optional[SymbolFactors]:
        """Get factor exposures for a symbol."""
        cached = self._cache.get(symbol.upper())
        return cached.factors if cached else None

    def get_price_history(self, symbol: str) -> Optional[List[SymbolPriceData]]:
        """Get 1-year price history for a symbol."""
        cached = self._cache.get(symbol.upper())
        return cached.price_history if cached else None

    async def refresh_all(self, db) -> None:
        """
        Full cache refresh. Called by nightly symbol batch.

        Overwrites entire cache with fresh data from DB.
        """
        async with self._lock:
            new_cache: Dict[str, SymbolCache] = {}
            symbols = await self._load_all_symbols(db)
            for symbol_data in symbols:
                new_cache[symbol_data.symbol] = symbol_data

            # Atomic swap
            self._cache = new_cache
            self._last_refresh = date.today()
            logger.info(f"Cache refreshed with {len(self._cache)} symbols")

    async def add_symbol(self, db, symbol: str) -> None:
        """
        Add a single symbol to cache. Called during mid-day onboarding.

        Does NOT remove other symbols - just adds/updates one.
        """
        async with self._lock:
            symbol_data = await self._load_symbol(db, symbol.upper())
            if symbol_data:
                self._cache[symbol.upper()] = symbol_data
                logger.info(f"Added {symbol} to cache")

    def get_latest_price_date(self) -> Optional[date]:
        """Get the most recent price date in cache."""
        if not self._cache:
            return None
        # All symbols should have same date after batch
        first_symbol = next(iter(self._cache.values()))
        return first_symbol.latest_price.price_date

    def symbols_in_cache(self) -> int:
        """Return count of symbols in cache."""
        return len(self._cache)

    async def _load_all_symbols(self, db) -> List[SymbolCache]:
        """Load all symbol data from database."""
        # Implementation: query symbol_prices_daily, symbol_factor_exposures
        # Join and build SymbolCache objects
        ...

    async def _load_symbol(self, db, symbol: str) -> Optional[SymbolCache]:
        """Load single symbol data from database."""
        ...


# Global singleton
symbol_cache = SymbolCacheService()
```

---

## Lifecycle

### 1. Application Startup

```python
# In app startup (main.py or lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with get_async_session() as db:
        await symbol_cache.initialize(db)

    yield

    # Shutdown (nothing to do - cache is in memory)
```

### 2. Nightly Refresh (Symbol Batch)

```python
# At end of symbol batch runner
async def run_symbol_batch():
    # ... fetch prices, calculate factors ...

    # Refresh in-memory cache
    async with get_async_session() as db:
        await symbol_cache.refresh_all(db)

    logger.info("V2_BATCH_STEP step=cache_refresh status=completed")
```

### 3. Mid-Day Symbol Onboarding

```python
# After symbol onboarding completes
async def _process_symbol(self, db, job):
    symbol = job.symbol

    # ... fetch prices, calculate factors, write to DB ...

    # Add to in-memory cache
    await symbol_cache.add_symbol(db, symbol)

    logger.info(f"V2_ONBOARDING step=cache_add symbol={symbol}")
```

---

## Portfolio Analytics

Portfolio-level analytics (factor exposures, stress tests, correlations) are **computed on-demand** using cached symbol data:

```python
async def compute_portfolio_factors(
    db: AsyncSession,
    portfolio_id: UUID
) -> PortfolioFactorExposures:
    """
    Compute portfolio factor exposures from cached symbol factors.

    Fast because all symbol data is in memory.
    """
    positions = await get_active_positions(db, portfolio_id)

    # Calculate total portfolio value
    total_value = Decimal('0')
    for pos in positions:
        price = symbol_cache.get_latest_price(pos.symbol)
        if price:
            total_value += pos.quantity * price

    # Weight-average the factor exposures
    portfolio_factors = defaultdict(Decimal)

    for pos in positions:
        price = symbol_cache.get_latest_price(pos.symbol)
        factors = symbol_cache.get_factors(pos.symbol)

        if price and factors and total_value > 0:
            weight = (pos.quantity * price) / total_value

            portfolio_factors['market_beta'] += weight * factors.market_beta
            portfolio_factors['ir_beta'] += weight * factors.ir_beta

            for name, value in factors.ridge_factors.items():
                portfolio_factors[name] += weight * value

            for name, value in factors.spread_factors.items():
                portfolio_factors[name] += weight * value

    return PortfolioFactorExposures(**portfolio_factors)
```

**Performance**: With cache in memory, this computation takes ~10-50ms for a 50-position portfolio.

---

## No Invalidation Needed

| Event | Action | Rationale |
|-------|--------|-----------|
| Nightly batch | `refresh_all()` | Overwrites entire cache |
| Symbol onboarded | `add_symbol()` | Adds to cache, doesn't invalidate |
| Position change | Nothing | Portfolio analytics computed on-demand |
| User requests analytics | Compute from cache | Always uses latest cached symbol data |

---

## Cache Health Check

```python
@router.get("/admin/cache/status")
async def get_cache_status() -> CacheStatusResponse:
    """Admin endpoint to check cache health."""
    return CacheStatusResponse(
        symbols_cached=symbol_cache.symbols_in_cache(),
        latest_price_date=symbol_cache.get_latest_price_date(),
        last_refresh=symbol_cache._last_refresh,
        memory_estimate_mb=symbol_cache.symbols_in_cache() * 350 / 1_000_000
    )
```

---

## Fallback: Cache Miss

If symbol not in cache (shouldn't happen, but defensive):

```python
def get_latest_price(self, symbol: str) -> Optional[Decimal]:
    """Get latest closing price for a symbol."""
    cached = self._cache.get(symbol.upper())

    if cached:
        return cached.latest_price.close

    # Cache miss - log warning, return None
    logger.warning(f"Cache miss for {symbol}")
    return None
```

Callers handle `None` gracefully (position shows "Data unavailable").
