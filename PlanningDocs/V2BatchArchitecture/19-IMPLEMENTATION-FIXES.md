# 19: Implementation Fixes & Clarifications

## Overview

This document addresses gaps identified during architecture review and provides concrete solutions for:
1. Cache health check + cold start handling
2. Private positions (no market prices)
3. Options symbol handling
4. Symbol onboarding race condition
5. Dual database confirmation
6. Two cron job coordination

---

## 1. Cache Health Check & Cold Start Handling

### Problem

Railway deploys restart the app, losing the in-memory cache. During cold start:
- First analytics requests would all hit DB (slow)
- Could overwhelm connection pool if many users request simultaneously
- Health check would pass before cache is ready

### Solution: Readiness Probe + Background Initialization

#### 1.1 Cache State Tracking

```python
# backend/app/cache/symbol_cache.py

class SymbolCacheService:
    def __init__(self):
        self._cache: Dict[str, SymbolCache] = {}
        self._initialized: bool = False
        self._initializing: bool = False
        self._init_started_at: Optional[datetime] = None
        self._init_error: Optional[str] = None

    def is_ready(self) -> bool:
        """Check if cache is fully initialized and ready for fast queries."""
        return self._initialized and len(self._cache) > 0

    def is_initializing(self) -> bool:
        """Check if cache initialization is in progress."""
        return self._initializing

    def get_init_status(self) -> dict:
        """Get detailed initialization status for health checks."""
        return {
            "ready": self._initialized,
            "initializing": self._initializing,
            "symbols_loaded": len(self._cache),
            "started_at": self._init_started_at.isoformat() if self._init_started_at else None,
            "error": self._init_error
        }
```

#### 1.2 Two-Tier Health Endpoints

```python
# backend/app/api/v1/health.py

@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe - Is the app running?

    Railway uses this to know if container is alive.
    Returns 200 immediately - no cache check.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe - Is the app ready to serve traffic?

    Railway uses this to know when to route traffic after deploy.
    Returns 503 until cache is initialized OR timeout reached.
    """
    from app.cache.symbol_cache import symbol_cache

    cache_status = symbol_cache.get_init_status()

    # Ready if cache is initialized
    if cache_status["ready"]:
        return {
            "status": "ready",
            "cache_symbols": cache_status["symbols_loaded"],
            "mode": "cache"
        }

    # Still initializing - check timeout
    if cache_status["initializing"]:
        started = datetime.fromisoformat(cache_status["started_at"])
        elapsed = (datetime.utcnow() - started).total_seconds()

        # After 30 seconds, declare ready with DB fallback
        if elapsed > 30:
            return {
                "status": "ready",
                "cache_symbols": cache_status["symbols_loaded"],
                "mode": "db_fallback",
                "message": "Cache still loading, using DB fallback"
            }

        # Still loading, not ready yet
        raise HTTPException(
            status_code=503,
            detail={
                "status": "initializing",
                "elapsed_seconds": int(elapsed),
                "symbols_loaded": cache_status["symbols_loaded"]
            }
        )

    # Cache failed to initialize - still ready with DB fallback
    return {
        "status": "ready",
        "cache_symbols": 0,
        "mode": "db_fallback",
        "error": cache_status["error"]
    }
```

#### 1.3 Background Initialization on Startup

```python
# backend/app/main.py

from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    - Starts cache initialization in background (non-blocking)
    - App accepts requests immediately with DB fallback
    - Readiness probe gates traffic until cache is ready (max 30s)
    """
    # Start cache initialization in background
    asyncio.create_task(initialize_cache_background())

    yield

    # Shutdown - nothing to clean up (cache is in memory)


async def initialize_cache_background():
    """
    Initialize symbol cache in background.

    Non-blocking - analytics requests use DB fallback until ready.
    """
    from app.cache.symbol_cache import symbol_cache
    from app.database import get_async_session

    symbol_cache._initializing = True
    symbol_cache._init_started_at = datetime.utcnow()

    try:
        async with get_async_session() as db:
            await symbol_cache.initialize(db)

        symbol_cache._initialized = True
        logger.info(f"Cache initialized: {symbol_cache.symbols_in_cache()} symbols")

    except Exception as e:
        symbol_cache._init_error = str(e)
        logger.error(f"Cache initialization failed: {e}")
        # App continues with DB fallback

    finally:
        symbol_cache._initializing = False
```

#### 1.4 Railway Configuration

```yaml
# railway.json
{
  "deploy": {
    "healthcheckPath": "/health/ready",
    "healthcheckTimeout": 60,
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  }
}
```

#### 1.5 Analytics Fallback Pattern

All analytics endpoints use this pattern:

```python
async def get_portfolio_factors(portfolio_id: UUID, db: AsyncSession):
    """Get portfolio factors - uses cache with DB fallback."""
    from app.cache.symbol_cache import symbol_cache

    positions = await get_active_positions(db, portfolio_id)

    for pos in positions:
        # Try cache first
        factors = symbol_cache.get_factors(pos.symbol)

        if factors is None:
            # Cache miss - fall back to DB
            logger.debug(f"Cache miss for {pos.symbol}, using DB")
            factors = await get_factors_from_db(db, pos.symbol)

        # ... compute weighted factors ...
```

---

## 2. Private Positions Handling

### Problem

PRIVATE investment class positions have no market prices - they're manually valued.

### Solution: Explicit Skip in Symbol Batch, Manual Values in Portfolio Refresh

#### 2.1 Symbol Batch: Skip Private Symbols

```python
# backend/app/batch/v2/symbol_batch_runner.py

async def _get_symbols_to_process(db: AsyncSession) -> List[str]:
    """
    Get all symbols that need price/factor updates.

    EXCLUDES private positions - they have no market prices.
    """
    # Get symbols from PUBLIC and OPTIONS positions only
    query = select(Position.symbol).where(
        and_(
            Position.deleted_at.is_(None),
            Position.symbol.isnot(None),
            Position.investment_class.in_(['PUBLIC', 'OPTIONS'])  # Exclude PRIVATE
        )
    ).distinct()

    result = await db.execute(query)
    position_symbols = {row[0] for row in result.all()}

    # Add universe symbols (S&P 500, Nasdaq, etc.)
    universe_symbols = await get_universe_symbols(db)

    # Add factor ETFs
    factor_etfs = {'VUG', 'VTV', 'MTUM', 'QUAL', 'IWM', 'SPY', 'USMV', 'TLT'}

    return list(position_symbols.union(universe_symbols).union(factor_etfs))
```

#### 2.2 Portfolio Refresh: Use Manual Values for Private

```python
# backend/app/batch/v2/portfolio_refresh_runner.py

async def create_portfolio_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    snapshot_date: date
) -> PortfolioSnapshot:
    """
    Create snapshot using cached prices for PUBLIC/OPTIONS,
    and manual market_value for PRIVATE.
    """
    positions = await get_active_positions(db, portfolio_id)

    total_value = Decimal('0')
    total_cost = Decimal('0')
    positions_included = 0

    for position in positions:
        if position.investment_class == 'PRIVATE':
            # PRIVATE: Use manually-entered market_value
            # (Set by user in command center, not from market data)
            if position.market_value:
                total_value += position.market_value
                total_cost += position.quantity * position.entry_price
                positions_included += 1
            else:
                logger.warning(
                    f"Private position {position.id} has no market_value, "
                    f"excluding from snapshot"
                )
        else:
            # PUBLIC/OPTIONS: Get price from cache
            price = await get_cached_price(position.symbol, snapshot_date)

            if price:
                market_value = position.quantity * price
                total_value += market_value
                total_cost += position.quantity * position.entry_price
                positions_included += 1

                # Update position's market value
                position.market_value = market_value
                position.last_price = price
                position.last_price_date = snapshot_date

    # ... create snapshot ...
```

#### 2.3 Analytics: Private Positions Have No Factor Exposure

```python
async def get_portfolio_factor_exposures(portfolio_id: UUID, db: AsyncSession):
    """
    Compute portfolio factor exposures.

    PRIVATE positions contribute to portfolio value but NOT to factor exposures
    (they have no market beta, no growth/value tilt, etc.)
    """
    positions = await get_active_positions(db, portfolio_id)

    # Separate public/options (have factors) from private (no factors)
    factored_positions = [p for p in positions if p.investment_class != 'PRIVATE']
    private_positions = [p for p in positions if p.investment_class == 'PRIVATE']

    # Calculate total portfolio value (including private)
    total_value = sum(p.market_value or 0 for p in positions)

    # Calculate factor exposures only from factored positions
    factored_value = sum(p.market_value or 0 for p in factored_positions)

    portfolio_factors = defaultdict(Decimal)

    for pos in factored_positions:
        factors = symbol_cache.get_factors(pos.symbol)
        if factors and pos.market_value and factored_value > 0:
            weight = pos.market_value / factored_value
            portfolio_factors['market_beta'] += weight * factors.market_beta
            # ... other factors ...

    return PortfolioFactorExposures(
        **portfolio_factors,
        private_allocation_pct=(
            (sum(p.market_value or 0 for p in private_positions) / total_value * 100)
            if total_value > 0 else 0
        ),
        note="Factor exposures based on PUBLIC/OPTIONS positions only"
    )
```

---

## 3. Options Symbol Handling

### Problem

Options symbols need prices but have different symbol formats (e.g., `AAPL240119C00150000`).

### Solution: Include Options in Symbol Batch, Use Polygon for Prices

#### 3.1 Symbol Batch: Detect and Route Options

```python
# backend/app/batch/v2/symbol_batch_runner.py

def is_options_symbol(symbol: str) -> bool:
    """
    Detect if symbol is an options contract.

    Options format: AAPL240119C00150000 (underlying + date + type + strike)
    """
    # Options symbols are typically 15-21 characters
    # and contain a date pattern
    if len(symbol) >= 15:
        # Check for date pattern (YYMMDD) starting at position of underlying
        # Simple heuristic: if it has numbers in the middle, it's likely options
        return any(c.isdigit() for c in symbol[4:10])
    return False


async def _run_price_phase(symbols: List[str], target_date: date):
    """Fetch prices for all symbols, routing to appropriate provider."""

    # Separate equities from options
    equity_symbols = [s for s in symbols if not is_options_symbol(s)]
    options_symbols = [s for s in symbols if is_options_symbol(s)]

    # Fetch equity prices from YFinance
    if equity_symbols:
        equity_prices = await yfinance_batch_fetch(equity_symbols, target_date)
        await bulk_upsert_prices(equity_prices)
        logger.info(f"Fetched {len(equity_prices)} equity prices from YFinance")

    # Fetch options prices from Polygon
    if options_symbols:
        options_prices = await polygon_options_fetch(options_symbols, target_date)
        await bulk_upsert_prices(options_prices)
        logger.info(f"Fetched {len(options_prices)} options prices from Polygon")
```

#### 3.2 Options Don't Get Factor Exposures

```python
# backend/app/batch/v2/symbol_batch_runner.py

async def _run_factor_phase(symbols: List[str], target_date: date):
    """Calculate factor exposures for equity symbols only."""

    # Options don't have factor exposures - skip them
    equity_symbols = [s for s in symbols if not is_options_symbol(s)]

    logger.info(f"Calculating factors for {len(equity_symbols)} equity symbols")
    logger.info(f"Skipping {len(symbols) - len(equity_symbols)} options symbols")

    # ... calculate factors for equity_symbols ...
```

---

## 4. Symbol Onboarding Race Condition Fix

### Problem

Race condition when:
1. User uploads portfolio with new symbol XYZ at 2 PM
2. Symbol onboarding starts processing XYZ in background
3. Nightly symbol batch runs at 9 PM (XYZ may or may not be complete)
4. Portfolio refresh at 9:30 PM - XYZ might have prices but no factors

### Solution: Portfolio Refresh Checks for Missing Factors

The cleanest solution is to have Portfolio Refresh ensure all required data exists before creating snapshots.

#### 4.1 Portfolio Refresh: Check for Missing Factors

```python
# backend/app/batch/v2/portfolio_refresh_runner.py

async def run_portfolio_refresh(target_date: date) -> Dict[str, Any]:
    """
    Portfolio refresh with symbol completeness check.

    Before creating snapshots, ensures all portfolio symbols have factors.
    Calculates missing factors inline if needed.
    """

    # Step 1: Wait for symbol batch completion
    if not await wait_for_symbol_batch(target_date, max_wait_minutes=60):
        return {"status": "aborted", "reason": "symbol_batch_timeout"}

    # Step 2: Check for pending symbol onboarding
    pending_symbols = await get_pending_onboarding_symbols()
    if pending_symbols:
        logger.info(f"Waiting for {len(pending_symbols)} pending symbol onboarding jobs")
        await wait_for_onboarding_completion(pending_symbols, max_wait_seconds=120)

    # Step 3: Get all portfolios needing snapshots
    portfolios = await get_portfolios_needing_snapshots(target_date)

    # Step 4: Process each portfolio
    for portfolio in portfolios:
        # Step 4a: Check for symbols missing factors
        missing_factors = await get_symbols_missing_factors(
            portfolio_id=portfolio.id,
            target_date=target_date
        )

        if missing_factors:
            logger.info(
                f"Portfolio {portfolio.id} has {len(missing_factors)} symbols "
                f"missing factors: {missing_factors}"
            )
            # Calculate factors inline for missing symbols
            await calculate_factors_for_symbols(missing_factors, target_date)

        # Step 4b: Create snapshot (now all symbols have data)
        await create_portfolio_snapshot(portfolio.id, target_date)

    return {"status": "complete", ...}


async def get_symbols_missing_factors(
    portfolio_id: UUID,
    target_date: date
) -> List[str]:
    """
    Find symbols in portfolio that don't have factor exposures.

    This catches:
    1. Newly onboarded symbols that completed after symbol batch
    2. Symbols where factor calculation failed
    3. Any other data gaps
    """
    async with get_async_session() as db:
        # Get all PUBLIC/OPTIONS symbols in portfolio
        portfolio_symbols = await db.execute(
            select(Position.symbol).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.deleted_at.is_(None),
                    Position.investment_class.in_(['PUBLIC', 'OPTIONS']),
                    ~is_options_symbol(Position.symbol)  # Exclude options
                )
            ).distinct()
        )
        symbols = {row[0] for row in portfolio_symbols.all()}

        # Get symbols that have factor exposures for target_date
        symbols_with_factors = await db.execute(
            select(SymbolFactorExposure.symbol).where(
                and_(
                    SymbolFactorExposure.symbol.in_(symbols),
                    SymbolFactorExposure.calculation_date == target_date
                )
            ).distinct()
        )
        have_factors = {row[0] for row in symbols_with_factors.all()}

        # Return symbols missing factors
        missing = symbols - have_factors
        return list(missing)


async def calculate_factors_for_symbols(
    symbols: List[str],
    target_date: date
) -> None:
    """
    Calculate factor exposures for specific symbols.

    Used to fill gaps for symbols that missed the nightly batch.
    """
    from app.calculations.symbol_factors import calculate_symbol_factors

    logger.info(f"Calculating factors inline for {len(symbols)} symbols")

    async with get_async_session() as db:
        for symbol in symbols:
            try:
                await calculate_symbol_factors(db, symbol, target_date)
                logger.info(f"Calculated factors for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to calculate factors for {symbol}: {e}")
                # Continue with other symbols - this one will have no factors
```

#### 4.2 Wait for Pending Onboarding

```python
async def get_pending_onboarding_symbols() -> List[str]:
    """Get symbols currently being onboarded."""
    from app.batch.v2.symbol_onboarding import symbol_onboarding_queue

    pending = await symbol_onboarding_queue.get_pending()
    processing = [
        s for s, j in symbol_onboarding_queue._jobs.items()
        if j.status == 'processing'
    ]
    return pending + processing


async def wait_for_onboarding_completion(
    symbols: List[str],
    max_wait_seconds: int = 120
) -> bool:
    """
    Wait for specific symbols to complete onboarding.

    Returns True if all completed, False if timeout.
    """
    from app.batch.v2.symbol_onboarding import symbol_onboarding_queue

    start = datetime.utcnow()
    check_interval = 5  # seconds

    while (datetime.utcnow() - start).total_seconds() < max_wait_seconds:
        # Check if all symbols are done
        still_pending = []
        for symbol in symbols:
            job = await symbol_onboarding_queue.get_status(symbol)
            if job and job.status in ('pending', 'processing'):
                still_pending.append(symbol)

        if not still_pending:
            logger.info("All pending symbol onboarding completed")
            return True

        logger.info(f"Waiting for {len(still_pending)} symbols to complete onboarding")
        await asyncio.sleep(check_interval)

    logger.warning(f"Timeout waiting for symbol onboarding: {symbols}")
    return False
```

---

## 5. Dual Database Confirmation

### Clarification

**All V2 batch processing uses the Core database only.**

| Table | Database | Used By |
|-------|----------|---------|
| `market_data_cache` | Core (gondola) | Symbol Batch, Portfolio Refresh |
| `symbol_universe` | Core (gondola) | Symbol Batch, Onboarding |
| `symbol_factor_exposures` | Core (gondola) | Symbol Batch, Analytics |
| `portfolio_snapshots` | Core (gondola) | Portfolio Refresh |
| `positions` | Core (gondola) | All |
| `portfolios` | Core (gondola) | All |
| `batch_run_tracking` | Core (gondola) | Batch History |
| `ai_kb_documents` | AI (metro) | NOT used by batch |
| `ai_memories` | AI (metro) | NOT used by batch |
| `ai_feedback` | AI (metro) | NOT used by batch |

### Session Usage

```python
# All V2 batch code uses Core database session
from app.database import get_async_session  # Core DB

async def run_symbol_batch():
    async with get_async_session() as db:  # Core DB
        # All queries here hit Core (gondola)
        symbols = await db.execute(select(Position.symbol)...)
        await db.execute(insert(MarketDataCache).values(...))
```

**AI database is NEVER accessed by batch processing.**

---

## 6. Two Cron Job Coordination

### Approach: Database Completion Flag with Polling

Since you want two separate cron jobs, we need reliable coordination:

#### 6.1 Symbol Batch Writes Completion Flag

```python
# backend/app/batch/v2/symbol_batch_runner.py

async def run_symbol_batch(target_date: date = None) -> Dict[str, Any]:
    """Run symbol batch and record completion."""
    target_date = target_date or get_effective_trading_date()

    # Record start
    await record_batch_run(
        batch_type='symbol_batch',
        batch_date=target_date,
        status='running'
    )

    try:
        # ... run all phases ...

        # Record completion
        await record_batch_run(
            batch_type='symbol_batch',
            batch_date=target_date,
            status='completed',
            completed_at=datetime.utcnow()
        )

        return {"success": True, "date": target_date.isoformat()}

    except Exception as e:
        await record_batch_run(
            batch_type='symbol_batch',
            batch_date=target_date,
            status='failed',
            error_message=str(e)
        )
        raise


async def record_batch_run(
    batch_type: str,
    batch_date: date,
    status: str,
    **kwargs
):
    """Record batch run status to database."""
    async with get_async_session() as db:
        # Upsert - update if exists, insert if not
        existing = await db.execute(
            select(BatchRunTracking).where(
                and_(
                    BatchRunTracking.batch_type == batch_type,
                    BatchRunTracking.batch_date == batch_date
                )
            )
        )
        record = existing.scalar_one_or_none()

        if record:
            record.status = status
            for key, value in kwargs.items():
                setattr(record, key, value)
        else:
            record = BatchRunTracking(
                batch_type=batch_type,
                batch_date=batch_date,
                status=status,
                **kwargs
            )
            db.add(record)

        await db.commit()
```

#### 6.2 Portfolio Refresh Polls for Completion

```python
# backend/app/batch/v2/portfolio_refresh_runner.py

async def wait_for_symbol_batch(
    target_date: date,
    max_wait_minutes: int = 60
) -> bool:
    """
    Wait for symbol batch to complete for target_date.

    Polls database every 5 minutes.
    Returns True if completed, False if timeout.
    """
    check_interval = 300  # 5 minutes
    max_attempts = max_wait_minutes // 5

    for attempt in range(max_attempts):
        status = await get_symbol_batch_status(target_date)

        if status == 'completed':
            logger.info(f"Symbol batch complete for {target_date} (attempt {attempt + 1})")
            return True

        if status == 'failed':
            logger.error(f"Symbol batch failed for {target_date}, aborting portfolio refresh")
            return False

        logger.info(
            f"Symbol batch not complete for {target_date}, "
            f"waiting 5 min (attempt {attempt + 1}/{max_attempts})"
        )
        await asyncio.sleep(check_interval)

    logger.error(f"Timeout waiting for symbol batch after {max_wait_minutes} minutes")
    return False


async def get_symbol_batch_status(target_date: date) -> Optional[str]:
    """Check symbol batch completion status from database."""
    async with get_async_session() as db:
        result = await db.execute(
            select(BatchRunTracking.status).where(
                and_(
                    BatchRunTracking.batch_type == 'symbol_batch',
                    BatchRunTracking.batch_date == target_date
                )
            )
        )
        return result.scalar_one_or_none()
```

#### 6.3 Railway Cron Configuration

```yaml
# railway.json
{
  "crons": [
    {
      "name": "symbol-batch",
      "schedule": "0 2 * * 1-5",
      "command": "python scripts/batch_processing/run_symbol_batch.py"
    },
    {
      "name": "portfolio-refresh",
      "schedule": "30 2 * * 1-5",
      "command": "python scripts/batch_processing/run_portfolio_refresh.py"
    }
  ]
}
```

**Notes**:
- Times in UTC: 2:00 AM UTC = 9:00 PM ET (EST)
- Portfolio refresh starts 30 min after symbol batch
- Portfolio refresh will wait up to 60 min for symbol batch
- If symbol batch takes 45 min, portfolio refresh waits ~15 min then runs
- If symbol batch fails, portfolio refresh aborts (no partial data)

---

## 7. Greeks Clarification

**Greeks are NOT being tracked in V2.**

Per your confirmation, options Greeks (delta, gamma, theta, vega) are not calculated in the batch system. Options positions:
- ✅ Get prices from Polygon
- ✅ Contribute to portfolio value
- ❌ Don't have factor exposures
- ❌ Don't have Greeks calculations

If Greeks tracking is needed in the future, it would be a separate phase that runs on OPTIONS positions only.

---

## Summary of Changes

| Issue | Solution | Files Affected |
|-------|----------|----------------|
| Cache cold start | Readiness probe + 30s timeout + DB fallback | `main.py`, `health.py`, `symbol_cache.py` |
| Private positions | Skip in symbol batch, use manual values | `symbol_batch_runner.py`, `portfolio_refresh_runner.py` |
| Options symbols | Route to Polygon, skip factor calc | `symbol_batch_runner.py` |
| Race condition | Portfolio refresh checks for missing factors | `portfolio_refresh_runner.py` |
| Dual DB | Confirmed: all V2 uses Core DB only | N/A (documentation) |
| Two cron jobs | DB completion flag + polling | `symbol_batch_runner.py`, `portfolio_refresh_runner.py` |
