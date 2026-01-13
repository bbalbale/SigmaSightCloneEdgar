# 22: V2 Batch Architecture - Onboarding Integration Plan

## Overview

This document outlines the integration of the V2 batch architecture with the user onboarding flow. The goal is to enable **fast portfolio setup** by leveraging pre-computed symbol-level data from the nightly V2 batch, while handling new symbols on-demand.

**Status**: Planning
**Target**:
- Known symbols: <10 seconds
- With unknown symbols: 30-60 seconds
**Dependencies**: 21-IMPLEMENTATION-PLAN.md (V2 Batch Architecture)

---

## Design Principles

1. **No no-ops** - Every endpoint does real work, just faster with V2 caches
2. **Reuse V2 batch phases** - Don't reinvent, parameterize existing code
3. **Scope to what's needed** - Only process new symbols, only process one portfolio
4. **Cache-first** - Use `symbol_cache` for prices and factors whenever possible

---

## Architecture

### V2 Onboarding Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    V2 ONBOARDING FLOW                                   │
│                                                                          │
│  POST /api/v1/onboarding/create-portfolio                               │
│       │                                                                   │
│       └─► Create Portfolio + Positions from CSV (unchanged)             │
│           Returns: portfolio_id                                          │
│                                                                          │
│  POST /api/v1/portfolios/{id}/calculate                                 │
│       │                                                                   │
│       ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   STEP 1: CLASSIFY SYMBOLS                        │   │
│  │                                                                    │   │
│  │  Get portfolio symbols from positions table                       │   │
│  │  Check against symbol_universe + symbol_factor_exposures          │   │
│  │                                                                    │   │
│  │  known_symbols: Have recent factors in cache/DB                   │   │
│  │  unknown_symbols: Need on-demand processing                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│       │                                                                   │
│       ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │          STEP 2: PROCESS UNKNOWN SYMBOLS (if any)                 │   │
│  │                                                                    │   │
│  │  For unknown_symbols only (scoped batch):                         │   │
│  │                                                                    │   │
│  │  Phase 0: Daily Valuations (yahooquery batch API)                 │   │
│  │     └─ PE, beta, 52-week range, market cap                        │   │
│  │                                                                    │   │
│  │  Phase 1: Market Data Collection (365-day lookback)               │   │
│  │     └─ YFinance primary, Polygon for options                      │   │
│  │                                                                    │   │
│  │  Phase 3: Factor Calculations                                     │   │
│  │     ├─ Ridge Factors (6): Value, Growth, Momentum, etc.           │   │
│  │     ├─ Spread Factors (4): Growth-Value, Momentum, etc.           │   │
│  │     └─ OLS Factors (3): Market Beta, IR Beta, Provider Beta       │   │
│  │                                                                    │   │
│  │  Add to symbol_universe, refresh factor cache                     │   │
│  │                                                                    │   │
│  │  Time: ~30-60s depending on symbol count                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│       │                                                                   │
│       ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │            STEP 3: PORTFOLIO CALCULATIONS (always)                │   │
│  │                                                                    │   │
│  │  Using V2 caches (symbol_cache._price_cache, _factor_cache):      │   │
│  │                                                                    │   │
│  │  Phase 4: P&L Calculations                                        │   │
│  │     └─ Position market values using cached prices                 │   │
│  │     └─ Portfolio snapshot creation                                │   │
│  │                                                                    │   │
│  │  Phase 5: Factor Aggregation                                      │   │
│  │     └─ Load symbol factors from cache                             │   │
│  │     └─ Equity-weighted aggregation to portfolio level             │   │
│  │                                                                    │   │
│  │  Phase 6: Stress Testing                                          │   │
│  │     └─ Calculate stress scenarios using aggregated factors        │   │
│  │                                                                    │   │
│  │  Time: ~5-10s (all from cache)                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│       │                                                                   │
│       ▼                                                                   │
│  Return: { status: "completed", portfolio_id, ... }                     │
│                                                                          │
│  GET /api/v1/onboarding/status/{portfolio_id}                           │
│       │                                                                   │
│       └─► Returns real-time progress during processing                  │
│           (existing batch_run_tracker integration)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Timeline Comparison

| Scenario | V1 (Current) | V2 (New) |
|----------|--------------|----------|
| All symbols known | 15-20 min | **5-10 seconds** |
| 1-5 unknown symbols | 15-20 min | **30-60 seconds** |
| 10+ unknown symbols | 15-20 min | **60-90 seconds** |

---

## Multi-Portfolio Handling

### Approach: Sequential Processing (Simple)

Multi-portfolio accounts are processed **sequentially** using the same V2 flow. This is intentionally simple because V2's speed makes batching unnecessary.

### Why Sequential Works Well

**Natural deduplication across portfolios**: When Portfolio 1 processes an unknown symbol, it gets added to `symbol_factor_exposures` and the cache is refreshed. Portfolio 2 will see that symbol as "known" - no duplicate processing.

```
Portfolio 1: AAPL, MSFT, GOOGL, NEWSTOCK1
    │
    ├─► Classify: NEWSTOCK1 = unknown
    ├─► Process NEWSTOCK1 (30-60s)
    ├─► Phases 4-6 (5-10s)
    └─► NEWSTOCK1 now in cache ✓

Portfolio 2: AAPL, TSLA, NEWSTOCK1, NEWSTOCK2
    │
    ├─► Classify: NEWSTOCK1 = known (!), NEWSTOCK2 = unknown
    ├─► Process only NEWSTOCK2 (30-60s)
    └─► Phases 4-6 (5-10s)

Portfolio 3: AAPL, MSFT, AMZN
    │
    ├─► Classify: All known ✓
    └─► Phases 4-6 only (5-10s)
```

### Multi-Portfolio Timeline

| Portfolios | V1 (Current) | V2 Sequential |
|------------|--------------|---------------|
| 2 portfolios (overlapping symbols) | 30-40 min | **10-70 sec** |
| 3 portfolios (all known) | 45-60 min | **15-30 sec** |
| 3 portfolios (3 unique unknown each) | 45-60 min | **~3 min** |

**Worst case** (3 portfolios, each with unique unknown symbols): ~3 minutes vs V1's ~1 hour.

### Frontend Integration

The existing multi-portfolio session management (implemented Dec 2025) works unchanged:

1. User uploads Portfolio 1 → V2 processes (5-60s) → Success screen
2. User clicks "Add Another Portfolio"
3. User uploads Portfolio 2 → V2 processes (5-60s) → Cumulative success screen
4. User clicks "Continue to Dashboard"

**No changes needed** to frontend session management, `portfolioStore`, or progress tracking.

---

## Implementation Plan

### Phase 1: Create Scoped Symbol Batch Function

**File**: `app/batch/v2/symbol_batch_runner.py`

Add a new function that runs Phases 0, 1, 3 for specific symbols only:

```python
async def run_symbol_batch_for_symbols(
    symbols: List[str],
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Run symbol batch phases for specific symbols only.

    Used during onboarding when portfolio contains unknown symbols.
    Runs Phase 0 (valuations), Phase 1 (prices), Phase 3 (factors).

    Args:
        symbols: List of symbols to process
        target_date: Calculation date (defaults to most recent trading day)

    Returns:
        Dict with processing results per symbol
    """
    if target_date is None:
        target_date = get_most_recent_completed_trading_day()

    logger.info(f"{V2_LOG_PREFIX} Processing {len(symbols)} symbols for onboarding")

    result = {
        "success": True,
        "symbols_processed": 0,
        "errors": [],
    }

    # Filter out private assets (HOME_EQUITY, FO_*, etc.)
    public_symbols, private_symbols = filter_private_assets(symbols)

    if private_symbols:
        logger.info(f"{V2_LOG_PREFIX} Skipping {len(private_symbols)} private assets")

    if not public_symbols:
        return result

    # Phase 0: Daily valuations (batch via yahooquery)
    await _run_phase_0_for_symbols(public_symbols, target_date)

    # Phase 1: Market data collection
    await _run_phase_1_for_symbols(public_symbols, target_date)

    # Phase 3: Factor calculations
    await _run_phase_3_for_symbols(public_symbols, target_date)

    # Add to symbol_universe
    await _add_symbols_to_universe(public_symbols)

    # Refresh factor cache so Phase 5 sees new factors
    await symbol_cache.refresh_factors(target_date)

    result["symbols_processed"] = len(public_symbols)
    return result
```

**Tasks**:
- [ ] Add `run_symbol_batch_for_symbols()` function
- [ ] Extract Phase 0 logic into `_run_phase_0_for_symbols()`
- [ ] Extract Phase 1 logic into `_run_phase_1_for_symbols()`
- [ ] Extract Phase 3 logic into `_run_phase_3_for_symbols()`
- [ ] Add `_add_symbols_to_universe()` helper

### Phase 2: Create Scoped Portfolio Refresh Function

**File**: `app/batch/v2/portfolio_refresh_runner.py`

Add a function that runs Phases 4-6 for a single portfolio:

```python
async def run_portfolio_refresh_for_portfolio(
    portfolio_id: UUID,
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Run portfolio refresh phases for a single portfolio.

    Used during onboarding after symbol processing is complete.
    Runs Phase 4 (P&L), Phase 5 (factor aggregation), Phase 6 (stress tests).

    Leverages V2 caches for fast execution:
    - symbol_cache._price_cache for P&L calculations
    - symbol_cache._factor_cache for factor aggregation

    Args:
        portfolio_id: Portfolio to refresh
        target_date: Calculation date (defaults to most recent trading day)

    Returns:
        Dict with processing results
    """
    if target_date is None:
        target_date = get_most_recent_completed_trading_day()

    logger.info(f"{V2_LOG_PREFIX} Refreshing portfolio {portfolio_id}")

    result = {
        "success": True,
        "phases": {},
        "errors": [],
    }

    # Ensure cache is initialized
    if not symbol_cache._initialized:
        await symbol_cache.initialize_async(target_date)

    # Phase 4: P&L calculations using price cache
    phase_4_result = await _run_phase_4_for_portfolio(portfolio_id, target_date)
    result["phases"]["phase_4_pnl"] = phase_4_result

    # Phase 5: Factor aggregation using factor cache
    phase_5_result = await _run_phase_5_for_portfolio(portfolio_id, target_date)
    result["phases"]["phase_5_factors"] = phase_5_result

    # Phase 6: Stress tests
    phase_6_result = await _run_phase_6_for_portfolio(portfolio_id, target_date)
    result["phases"]["phase_6_stress"] = phase_6_result

    result["success"] = all(
        p.get("success", False) for p in result["phases"].values()
    )

    return result


async def _run_phase_4_for_portfolio(
    portfolio_id: UUID,
    target_date: date,
) -> Dict[str, Any]:
    """Run P&L calculations for single portfolio using price cache."""
    from app.batch.pnl_calculator import pnl_calculator

    return await pnl_calculator.calculate_all_portfolios_pnl(
        calculation_date=target_date,
        db=None,
        portfolio_ids=[str(portfolio_id)],  # Single portfolio
        price_cache=symbol_cache._price_cache,  # Use V2 cache
    )


async def _run_phase_5_for_portfolio(
    portfolio_id: UUID,
    target_date: date,
) -> Dict[str, Any]:
    """Run factor aggregation for single portfolio using factor cache."""
    # Reuse existing _aggregate_portfolio_factors with single-item list
    return await _aggregate_portfolio_factors(
        portfolio_ids=[portfolio_id],
        target_date=target_date,
    )


async def _run_phase_6_for_portfolio(
    portfolio_id: UUID,
    target_date: date,
) -> Dict[str, Any]:
    """Run stress tests for single portfolio."""
    # Reuse existing _run_stress_tests_for_all_portfolios with single-item list
    return await _run_stress_tests_for_all_portfolios(
        portfolio_ids=[portfolio_id],
        target_date=target_date,
    )
```

**Tasks**:
- [ ] Add `run_portfolio_refresh_for_portfolio()` function
- [ ] Add `_run_phase_4_for_portfolio()` helper
- [ ] Add `_run_phase_5_for_portfolio()` helper
- [ ] Add `_run_phase_6_for_portfolio()` helper
- [ ] Ensure all phases use `symbol_cache` for data access

### Phase 3: Create V2 Onboarding Orchestrator

**File**: `app/services/v2_onboarding_service.py` (NEW)

```python
"""
V2 Onboarding Service

Orchestrates fast portfolio onboarding using V2 batch architecture.
Handles both known and unknown symbols efficiently.
"""

from datetime import date
from typing import Dict, List, Set, Tuple, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.trading_calendar import get_most_recent_completed_trading_day
from app.database import get_async_session
from app.models.positions import Position
from app.models.symbol_analytics import SymbolUniverse, SymbolFactorExposure
from app.cache.symbol_cache import symbol_cache

logger = get_logger(__name__)

V2_LOG_PREFIX = "[V2_ONBOARDING]"


class V2OnboardingService:
    """
    Fast-path onboarding using V2 batch architecture.

    Flow:
    1. Classify portfolio symbols (known vs unknown)
    2. Process unknown symbols (Phases 0, 1, 3) - scoped batch
    3. Run portfolio calculations (Phases 4, 5, 6) - using caches
    """

    async def run_onboarding_calculations(
        self,
        portfolio_id: UUID,
        calculation_date: date = None,
    ) -> Dict[str, Any]:
        """
        Run V2 onboarding calculations for a portfolio.

        Args:
            portfolio_id: Portfolio to process
            calculation_date: Date for calculations

        Returns:
            Dict with processing results and timing
        """
        import time
        start_time = time.time()

        if calculation_date is None:
            calculation_date = get_most_recent_completed_trading_day()

        logger.info(
            f"{V2_LOG_PREFIX} Starting onboarding for portfolio {portfolio_id} "
            f"(calc_date={calculation_date})"
        )

        result = {
            "success": True,
            "portfolio_id": str(portfolio_id),
            "calculation_date": calculation_date.isoformat(),
            "symbols": {},
            "phases": {},
            "errors": [],
        }

        try:
            # Step 1: Classify symbols
            known, unknown = await self._classify_symbols(portfolio_id, calculation_date)
            result["symbols"] = {
                "total": len(known) + len(unknown),
                "known": len(known),
                "unknown": len(unknown),
                "unknown_list": list(unknown),
            }

            logger.info(
                f"{V2_LOG_PREFIX} Symbol classification: "
                f"{len(known)} known, {len(unknown)} unknown"
            )

            # Step 2: Process unknown symbols (if any)
            if unknown:
                from app.batch.v2.symbol_batch_runner import run_symbol_batch_for_symbols

                symbol_result = await run_symbol_batch_for_symbols(
                    symbols=list(unknown),
                    target_date=calculation_date,
                )
                result["phases"]["symbol_processing"] = symbol_result

                if not symbol_result.get("success", False):
                    result["errors"].extend(symbol_result.get("errors", []))

            # Step 3: Run portfolio calculations (Phases 4-6)
            from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh_for_portfolio

            portfolio_result = await run_portfolio_refresh_for_portfolio(
                portfolio_id=portfolio_id,
                target_date=calculation_date,
            )
            result["phases"]["portfolio_refresh"] = portfolio_result

            if not portfolio_result.get("success", False):
                result["errors"].extend(portfolio_result.get("errors", []))
                result["success"] = False

        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} Onboarding failed: {e}", exc_info=True)
            result["success"] = False
            result["errors"].append(str(e))

        result["duration_seconds"] = round(time.time() - start_time, 2)

        logger.info(
            f"{V2_LOG_PREFIX} Onboarding complete: success={result['success']}, "
            f"duration={result['duration_seconds']}s"
        )

        return result

    async def _classify_symbols(
        self,
        portfolio_id: UUID,
        calculation_date: date,
    ) -> Tuple[Set[str], Set[str]]:
        """
        Classify portfolio symbols as known or unknown.

        Known = in symbol_universe AND has factors for calculation_date
        Unknown = needs on-demand processing

        Args:
            portfolio_id: Portfolio to check
            calculation_date: Date to check factors for

        Returns:
            (known_symbols, unknown_symbols)
        """
        async with get_async_session() as db:
            # Get portfolio symbols
            result = await db.execute(
                select(Position.symbol)
                .where(
                    Position.portfolio_id == portfolio_id,
                    Position.exit_date.is_(None),  # Active positions only
                )
                .distinct()
            )
            portfolio_symbols = {row[0].upper() for row in result.all()}

            if not portfolio_symbols:
                return set(), set()

            # Check which symbols have factors for this date
            result = await db.execute(
                select(SymbolFactorExposure.symbol)
                .where(
                    SymbolFactorExposure.symbol.in_(portfolio_symbols),
                    SymbolFactorExposure.calculation_date == calculation_date,
                )
                .distinct()
            )
            symbols_with_factors = {row[0] for row in result.all()}

            known = portfolio_symbols & symbols_with_factors
            unknown = portfolio_symbols - symbols_with_factors

            return known, unknown


# Global instance
v2_onboarding_service = V2OnboardingService()
```

**Tasks**:
- [ ] Create `app/services/v2_onboarding_service.py`
- [ ] Implement `run_onboarding_calculations()`
- [ ] Implement `_classify_symbols()`
- [ ] Add progress tracking integration with `batch_run_tracker`

### Phase 4: Update Calculate Endpoint

**File**: `app/api/v1/portfolios.py`

Update `trigger_portfolio_calculations()` to use V2 when enabled:

```python
@router.post("/{portfolio_id}/calculate", response_model=TriggerCalculationsResponse)
async def trigger_portfolio_calculations(
    portfolio_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_validated_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger batch calculations for user's portfolio.

    V2 Mode (BATCH_V2_ENABLED=true):
    - Uses pre-computed symbol data from nightly batch
    - Processes unknown symbols on-demand (Phases 0, 1, 3)
    - Runs portfolio calculations using V2 caches (Phases 4, 5, 6)
    - Typical time: 5-60 seconds depending on unknown symbols

    V1 Mode (BATCH_V2_ENABLED=false):
    - Full batch backfill for portfolio
    - Typical time: 15-20 minutes
    """
    # ... existing validation code ...

    # Create batch run for tracking
    batch_run_id = str(uuid4())
    run = CurrentBatchRun(
        batch_run_id=batch_run_id,
        started_at=utc_now(),
        triggered_by=current_user.email,
        portfolio_id=str(portfolio_id)
    )
    batch_run_tracker.start(run)

    calculation_date = get_most_recent_trading_day()

    if settings.BATCH_V2_ENABLED:
        # V2 Fast Path: Use caches + scoped symbol processing
        logger.info(
            f"[V2] User {current_user.email} triggered V2 calculations for "
            f"portfolio {portfolio_id} (batch_run_id: {batch_run_id})"
        )

        background_tasks.add_task(
            _run_v2_onboarding_with_tracking,
            portfolio_id=str(portfolio_id),
            calculation_date=calculation_date,
        )
    else:
        # V1 Fallback: Full batch
        logger.info(
            f"[V1] User {current_user.email} triggered V1 calculations for "
            f"portfolio {portfolio_id} (batch_run_id: {batch_run_id})"
        )

        background_tasks.add_task(
            batch_orchestrator.run_portfolio_onboarding_backfill,
            str(portfolio_id),
            calculation_date
        )

    return TriggerCalculationsResponse(
        portfolio_id=str(portfolio_id),
        batch_run_id=batch_run_id,
        status="started",
        message=f"Calculations started. Poll status at /api/v1/onboarding/status/{portfolio_id}"
    )


async def _run_v2_onboarding_with_tracking(
    portfolio_id: str,
    calculation_date: date,
):
    """
    V2 onboarding wrapper with batch_run_tracker integration.
    """
    from app.services.v2_onboarding_service import v2_onboarding_service
    from app.batch.batch_run_tracker import batch_run_tracker

    try:
        result = await v2_onboarding_service.run_onboarding_calculations(
            portfolio_id=UUID(portfolio_id),
            calculation_date=calculation_date,
        )

        batch_run_tracker.complete(success=result.get("success", False))

    except Exception as e:
        logger.error(f"[V2] Onboarding failed for {portfolio_id}: {e}", exc_info=True)
        batch_run_tracker.complete(success=False)
        raise
```

**Tasks**:
- [ ] Add V2 conditional in `trigger_portfolio_calculations()`
- [ ] Create `_run_v2_onboarding_with_tracking()` wrapper
- [ ] Update logging to distinguish V1 vs V2 paths
- [ ] Test feature flag switching

### Phase 5: Update Status Endpoint for V2 Progress

**File**: `app/api/v1/onboarding_status.py`

The existing status endpoint already uses `batch_run_tracker`, which will work with V2. Minor updates needed for V2-specific phase names:

```python
# V2 phase definitions for progress display
V2_PHASES = [
    {"phase_id": "classify", "phase_name": "Analyzing Portfolio", "unit": "symbols"},
    {"phase_id": "symbol_processing", "phase_name": "Processing New Symbols", "unit": "symbols"},
    {"phase_id": "phase_4", "phase_name": "Calculating P&L", "unit": "positions"},
    {"phase_id": "phase_5", "phase_name": "Aggregating Factors", "unit": "factors"},
    {"phase_id": "phase_6", "phase_name": "Running Stress Tests", "unit": "scenarios"},
]
```

**Tasks**:
- [ ] Add V2 phase definitions
- [ ] Update progress calculation for V2 flow
- [ ] Ensure `batch_run_tracker` integration works for both V1 and V2

---

## V2 Cache Utilization Summary

| Cache | Location | Used In | Purpose |
|-------|----------|---------|---------|
| `symbol_cache._price_cache` | `app/cache/symbol_cache.py` | Phase 4 (P&L) | 365 days of prices, DB fallback |
| `symbol_cache._factor_cache` | `app/cache/symbol_cache.py` | Phase 5 (Aggregation) | Symbol factors, refreshed after Phase 3 |
| `market_data_cache` table | Database | Phase 1 backup | Persistent price storage |
| `symbol_factor_exposures` table | Database | Phase 3 output, Phase 5 input | Persistent factor storage |
| `symbol_universe` table | Database | Symbol classification | Track known symbols |

### Cache Flow During Onboarding

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        V2 CACHE FLOW                                     │
│                                                                          │
│  Symbol Classification                                                   │
│       │                                                                   │
│       ├─► Query symbol_factor_exposures for portfolio symbols           │
│       │   └─► Returns known vs unknown                                   │
│       │                                                                   │
│  Unknown Symbol Processing (if needed)                                   │
│       │                                                                   │
│       ├─► Phase 0: yahooquery API → company_profiles table              │
│       ├─► Phase 1: YFinance API → market_data_cache table               │
│       │                          → symbol_cache._price_cache (refresh)  │
│       ├─► Phase 3: Calculate factors → symbol_factor_exposures table    │
│       │                              → symbol_cache._factor_cache (refresh)
│       │                                                                   │
│  Portfolio Calculations (always)                                         │
│       │                                                                   │
│       ├─► Phase 4: symbol_cache._price_cache → position market values   │
│       │           └─► DB fallback if cache miss                          │
│       │                                                                   │
│       ├─► Phase 5: symbol_cache._factor_cache → portfolio factors       │
│       │           └─► DB fallback if cache miss                          │
│       │                                                                   │
│       └─► Phase 6: factor_exposures table → stress test results         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Testing Plan

### Unit Tests

| Test | Description |
|------|-------------|
| `test_classify_all_known` | Portfolio with all known symbols |
| `test_classify_all_unknown` | Portfolio with all new symbols |
| `test_classify_mixed` | Portfolio with mixed symbols |
| `test_scoped_symbol_batch` | Phase 0/1/3 for specific symbols |
| `test_scoped_portfolio_refresh` | Phase 4/5/6 for single portfolio |
| `test_cache_utilization` | Verify caches are hit, not DB |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_v2_onboarding_known_symbols` | Full flow, all symbols known (<10s) |
| `test_v2_onboarding_unknown_symbols` | Full flow with new symbols (<60s) |
| `test_v2_onboarding_private_assets` | Handles HOME_EQUITY, FO_* correctly |
| `test_v1_fallback` | Falls back when BATCH_V2_ENABLED=false |

### Performance Tests

| Test | Target |
|------|--------|
| Known symbols (20 positions) | <10 seconds |
| 5 unknown symbols | <45 seconds |
| 10 unknown symbols | <75 seconds |
| Cache hit rate during Phase 4/5 | >95% |

---

## Files Reference

### New Files

| File | Purpose |
|------|---------|
| `app/services/v2_onboarding_service.py` | V2 onboarding orchestration |

### Modified Files

| File | Changes |
|------|---------|
| `app/batch/v2/symbol_batch_runner.py` | Add `run_symbol_batch_for_symbols()` |
| `app/batch/v2/portfolio_refresh_runner.py` | Add `run_portfolio_refresh_for_portfolio()` |
| `app/api/v1/portfolios.py` | Add V2 path in `/calculate` |
| `app/api/v1/onboarding_status.py` | Add V2 phase definitions |

### Existing V2 Files (Leveraged)

| File | How Used |
|------|----------|
| `app/cache/symbol_cache.py` | `symbol_cache._price_cache`, `_factor_cache` |
| `app/batch/pnl_calculator.py` | Phase 4 P&L calculations |
| `app/services/portfolio_factor_service.py` | Phase 5 factor aggregation |
| `app/calculations/stress_testing.py` | Phase 6 stress tests |

---

## Rollout Plan

### Stage 1: Development (Week 1)
- [ ] Implement scoped symbol batch functions
- [ ] Implement scoped portfolio refresh functions
- [ ] Create V2OnboardingService
- [ ] Update calculate endpoint
- [ ] Unit tests passing

### Stage 2: Testing (Week 2)
- [ ] Integration tests passing
- [ ] Performance benchmarks meeting targets
- [ ] Test with demo portfolios
- [ ] Test edge cases (private assets, options, etc.)

### Stage 3: Deployment (Week 3)
- [ ] Deploy behind `BATCH_V2_ENABLED=true`
- [ ] Monitor first 10 onboardings
- [ ] Verify cache hit rates
- [ ] Verify timing improvements

### Rollback Plan

If V2 onboarding causes issues:
1. Set `BATCH_V2_ENABLED=false` in Railway
2. Redeploy (automatic)
3. V1 batch resumes immediately

**Rollback time**: ~3 minutes

---

## Success Metrics

| Metric | V1 Baseline | V2 Target | Measurement |
|--------|-------------|-----------|-------------|
| Median onboarding time (known) | 18 min | <10 sec | Logs |
| Median onboarding time (unknown) | 18 min | <60 sec | Logs |
| Cache hit rate (Phase 4/5) | N/A | >95% | `symbol_cache.get_health_status()` |
| Onboarding failure rate | 2% | <1% | Error tracking |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-13 | Initial plan (aligned with 08-USER-ONBOARDING approach) |
| 2026-01-13 | Revised: Real work in /calculate, not no-op |
| 2026-01-13 | Revised: Blocking wait for unknown symbols |
| 2026-01-13 | Revised: Reuse V2 batch phases with scoping parameters |
