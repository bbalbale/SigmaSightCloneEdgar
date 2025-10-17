# Risk Metrics Testing & Batch Processing Guide

**Companion to:** `RiskMetricsExecution.md`
**Purpose:** Detailed batch processing integration and comprehensive testing procedures
**Created:** 2025-10-16
**Status:** Ready for Implementation

---

## Table of Contents

1. [Batch Processing Integration](#batch-processing-integration)
2. [Testing & Validation](#testing--validation)
3. [Diagnostic Scripts](#diagnostic-scripts)
4. [Expected Results](#expected-results)

---

# Batch Processing Integration

## Critical Context

**The user is right** - the execution document didn't clearly explain how to integrate the new risk metrics into the existing batch processing system. This section provides comprehensive, step-by-step instructions.

## Current Batch Processing System

**File:** `backend/app/batch/batch_orchestrator_v2.py`

**Current Flow** (8 engines):
```
1. Portfolio Aggregation (delta-adjusted exposure)
2. Position Greeks
3. Factor Analysis ← BROKEN (VIF > 299, multicollinearity)
4. Market Risk Scenarios
5. Stress Testing ← Uses broken factor betas
6. Portfolio Snapshots ← Stores broken data
7. Position Correlations
8. Factor Correlations
```

**Problems:**
- Factor Analysis produces garbage betas (NVDA = -3 instead of +2.12)
- Stress Testing uses broken betas
- Portfolio Snapshots store broken data
- No sector exposure
- No concentration metrics
- No volatility analytics

## New Batch Processing System

**After Changes** (10 engines):
```
1. Portfolio Aggregation (unchanged)
2. Position Greeks (unchanged)
3. Market Beta Calculation ← NEW (Phase 0)
4. Sector & Concentration ← NEW (Phase 1)
5. Volatility Analytics ← NEW (Phase 2)
6. Market Risk Scenarios (updated to use new beta)
7. Stress Testing (updated to use new beta)
8. Portfolio Snapshots (updated to store new metrics)
9. Position Correlations (unchanged)
10. [DEPRECATED] Factor Correlations (can remove)
```

---

## Step-by-Step Batch Integration

### Integration Step 1: Add Market Beta (Phase 0)

**File:** `backend/app/batch/batch_orchestrator_v2.py`

**Location:** Find the section after portfolio aggregation (around line 140-160)

**Look for this pattern:**
```python
# Step 2: Portfolio aggregation complete
logger.info("Portfolio aggregation completed")

# Step 3: Greeks calculations
logger.info("Calculating position Greeks...")
```

**INSERT THIS CODE** between Steps 2 and 3:

```python
# ============================================================================
# STEP 2.5: MARKET BETA CALCULATION (Phase 0 - Single-Factor Model)
# ============================================================================
logger.info("=" * 80)
logger.info("STEP 2.5: Calculating Market Beta (Single-Factor Model)")
logger.info("=" * 80)

from app.calculations.market_beta import calculate_portfolio_market_beta

try:
    market_beta_start = datetime.now()

    market_beta_result = await calculate_portfolio_market_beta(
        db=db,
        portfolio_id=portfolio_id,
        calculation_date=calculation_date
    )

    market_beta_duration = (datetime.now() - market_beta_start).total_seconds()

    if market_beta_result['success']:
        results['market_beta'] = market_beta_result
        logger.info(
            f"✓ Market beta calculated in {market_beta_duration:.2f}s: "
            f"Beta={market_beta_result['market_beta']:.3f}, "
            f"R²={market_beta_result['r_squared']:.3f}, "
            f"Positions={market_beta_result['positions_count']}, "
            f"Observations={market_beta_result['observations']}"
        )

        # Store in batch results for snapshot creation
        results['batch_metrics']['market_beta_success'] = True
        results['batch_metrics']['market_beta_value'] = market_beta_result['market_beta']

    else:
        error_msg = market_beta_result.get('error', 'Unknown error')
        logger.warning(f"✗ Market beta calculation failed: {error_msg}")
        results['market_beta'] = {
            'success': False,
            'error': error_msg
        }
        results['batch_metrics']['market_beta_success'] = False

except Exception as e:
    logger.error(f"✗ Critical error in market beta calculation: {e}", exc_info=True)
    results['market_beta'] = {
        'success': False,
        'error': f"Exception: {str(e)}"
    }
    results['batch_metrics']['market_beta_success'] = False
```

**Why this location?**
- After portfolio aggregation (we need position market values)
- Before stress testing (stress tests need the correct beta)
- Independent of other calculations (can run separately)

---

### Integration Step 2: Add Sector & Concentration (Phase 1)

**File:** `backend/app/batch/batch_orchestrator_v2.py`

**Location:** Immediately after the market beta code block you just added

**INSERT THIS CODE:**

```python
# ============================================================================
# STEP 3: SECTOR ANALYSIS & CONCENTRATION METRICS (Phase 1)
# ============================================================================
logger.info("=" * 80)
logger.info("STEP 3: Calculating Sector Exposure & Concentration")
logger.info("=" * 80)

from app.calculations.sector_analysis import calculate_sector_and_concentration

try:
    sector_start = datetime.now()

    sector_conc_result = await calculate_sector_and_concentration(
        db=db,
        portfolio_id=portfolio_id
    )

    sector_duration = (datetime.now() - sector_start).total_seconds()

    results['sector_and_concentration'] = sector_conc_result

    # Log sector exposure results
    if sector_conc_result.get('sector_exposure', {}).get('success'):
        sector_data = sector_conc_result['sector_exposure']
        logger.info(f"✓ Sector exposure calculated in {sector_duration:.2f}s:")

        # Show top 3 sectors
        sorted_sectors = sorted(
            sector_data['portfolio_weights'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        for sector, weight in sorted_sectors:
            benchmark_weight = sector_data['benchmark_weights'].get(sector, 0)
            diff = sector_data['over_underweight'].get(sector, 0)
            print_weight = weight * 100
            print_benchmark = benchmark_weight * 100
            print_diff = diff * 100
            logger.info(
                f"  {sector}: {print_weight:.1f}% "
                f"(S&P 500: {print_benchmark:.1f}%, "
                f"{'Over' if diff > 0 else 'Under'}weight: {abs(print_diff):.1f}%)"
            )

        # Warn about unclassified positions
        if sector_data.get('unclassified_positions'):
            logger.warning(
                f"⚠ Unclassified positions: {', '.join(sector_data['unclassified_positions'])}"
            )

        results['batch_metrics']['sector_success'] = True

    else:
        error_msg = sector_conc_result.get('sector_exposure', {}).get('error', 'Unknown error')
        logger.warning(f"✗ Sector exposure failed: {error_msg}")
        results['batch_metrics']['sector_success'] = False

    # Log concentration results
    if sector_conc_result.get('concentration', {}).get('success'):
        conc_data = sector_conc_result['concentration']
        logger.info(
            f"✓ Concentration calculated: "
            f"HHI={conc_data['hhi']:.1f}, "
            f"Effective positions={conc_data['effective_num_positions']:.1f}, "
            f"Top 3={conc_data['top_3_concentration']*100:.1f}%, "
            f"Top 10={conc_data['top_10_concentration']*100:.1f}%"
        )

        # Concentration interpretation
        hhi = conc_data['hhi']
        if hhi > 2500:
            logger.info("  Concentration level: HIGHLY CONCENTRATED")
        elif hhi > 1500:
            logger.info("  Concentration level: CONCENTRATED")
        elif hhi > 1000:
            logger.info("  Concentration level: MODERATELY CONCENTRATED")
        else:
            logger.info("  Concentration level: WELL DIVERSIFIED")

        results['batch_metrics']['concentration_success'] = True

    else:
        error_msg = sector_conc_result.get('concentration', {}).get('error', 'Unknown error')
        logger.warning(f"✗ Concentration calculation failed: {error_msg}")
        results['batch_metrics']['concentration_success'] = False

except Exception as e:
    logger.error(f"✗ Critical error in sector/concentration: {e}", exc_info=True)
    results['sector_and_concentration'] = {
        'sector_exposure': {'success': False, 'error': str(e)},
        'concentration': {'success': False, 'error': str(e)}
    }
    results['batch_metrics']['sector_success'] = False
    results['batch_metrics']['concentration_success'] = False
```

---

### Integration Step 3: Add Volatility Analytics (Phase 2)

**File:** `backend/app/batch/batch_orchestrator_v2.py`

**Location:** Immediately after the sector/concentration code block

**INSERT THIS CODE:**

```python
# ============================================================================
# STEP 4: VOLATILITY ANALYTICS (Phase 2 - HAR Model)
# ============================================================================
logger.info("=" * 80)
logger.info("STEP 4: Calculating Volatility Analytics (HAR Model)")
logger.info("=" * 80)

from app.calculations.volatility_analytics import calculate_portfolio_volatility

try:
    vol_start = datetime.now()

    volatility_result = await calculate_portfolio_volatility(
        db=db,
        portfolio_id=portfolio_id,
        calculation_date=calculation_date
    )

    vol_duration = (datetime.now() - vol_start).total_seconds()

    results['volatility'] = volatility_result

    if volatility_result['success']:
        logger.info(f"✓ Volatility calculated in {vol_duration:.2f}s:")
        logger.info(
            f"  30-day realized: {volatility_result['realized_vol_30d']:.2%}, "
            f"60-day: {volatility_result['realized_vol_60d']:.2%}, "
            f"90-day: {volatility_result['realized_vol_90d']:.2%}"
        )
        logger.info(
            f"  Expected (30-day forecast): {volatility_result['expected_vol_30d']:.2%}"
        )
        logger.info(
            f"  Trend: {volatility_result['vol_trend'].upper()}, "
            f"Percentile: {volatility_result['vol_percentile']*100:.0f}th"
        )

        # Volatility interpretation
        vol_30d = volatility_result['realized_vol_30d']
        if vol_30d < 0.15:
            logger.info("  Volatility level: VERY LOW")
        elif vol_30d < 0.25:
            logger.info("  Volatility level: LOW")
        elif vol_30d < 0.35:
            logger.info("  Volatility level: MODERATE")
        elif vol_30d < 0.50:
            logger.info("  Volatility level: HIGH")
        else:
            logger.info("  Volatility level: VERY HIGH")

        results['batch_metrics']['volatility_success'] = True

    else:
        error_msg = volatility_result.get('error', 'Unknown error')
        logger.warning(f"✗ Volatility calculation failed: {error_msg}")
        results['batch_metrics']['volatility_success'] = False

except Exception as e:
    logger.error(f"✗ Critical error in volatility calculation: {e}", exc_info=True)
    results['volatility'] = {
        'success': False,
        'error': f"Exception: {str(e)}"
    }
    results['batch_metrics']['volatility_success'] = False
```

---

### Integration Step 4: Update Market Risk (Use New Beta)

**File:** `backend/app/calculations/market_risk.py`

**Find the function** `calculate_portfolio_market_beta()` (around line 50-90)

**REPLACE THE ENTIRE FUNCTION** with this:

```python
async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate portfolio market beta.

    NOTE: This now calls the new single-factor implementation from market_beta.py
    instead of the old broken 7-factor multivariate regression.

    The old implementation had severe multicollinearity (VIF > 299) which caused
    invalid betas (e.g., NVDA showing -3 instead of +2.12).

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation

    Returns:
        Portfolio beta calculation result
    """
    from app.calculations.market_beta import calculate_portfolio_market_beta as calc_new_beta

    logger.info(f"Using NEW single-factor market beta (not broken 7-factor model)")

    return await calc_new_beta(db, portfolio_id, calculation_date)
```

**Why this change?**
- The stress testing system calls `market_risk.calculate_portfolio_market_beta()`
- By updating this function, we ensure stress tests use the NEW correct beta
- Old code stays in place but is never called
- Clean migration path

---

### Integration Step 5: Update Snapshot Creation

**File:** `backend/app/calculations/snapshots.py`

**Find the function:** `create_portfolio_snapshot()`

**Find the snapshot creation section** (look for `snapshot = PortfolioSnapshot(`)

**ADD these new fields to the snapshot creation:**

```python
# Extract new risk metrics from batch results
market_beta_data = batch_results.get('market_beta', {})
sector_conc_data = batch_results.get('sector_and_concentration', {})
sector_data = sector_conc_data.get('sector_exposure', {})
conc_data = sector_conc_data.get('concentration', {})
vol_data = batch_results.get('volatility', {})

# Prepare sector exposure JSON
sector_exposure_json = None
if sector_data.get('success'):
    sector_exposure_json = {}
    for sector in sector_data.get('portfolio_weights', {}).keys():
        sector_exposure_json[sector] = {
            'portfolio': sector_data['portfolio_weights'].get(sector, 0),
            'benchmark': sector_data['benchmark_weights'].get(sector, 0),
            'diff': sector_data['over_underweight'].get(sector, 0)
        }

# Create snapshot with ALL fields (existing + new)
snapshot = PortfolioSnapshot(
    # ... KEEP ALL EXISTING FIELDS ...

    # ADD THESE NEW FIELDS (Phase 0):
    market_beta=(
        Decimal(str(market_beta_data.get('market_beta', 0)))
        if market_beta_data.get('success')
        else None
    ),
    market_beta_r_squared=(
        Decimal(str(market_beta_data.get('r_squared', 0)))
        if market_beta_data.get('success')
        else None
    ),
    market_beta_observations=(
        market_beta_data.get('observations', 0)
        if market_beta_data.get('success')
        else None
    ),

    # ADD THESE NEW FIELDS (Phase 1):
    sector_exposure=sector_exposure_json,
    hhi=(
        Decimal(str(conc_data.get('hhi', 0)))
        if conc_data.get('success')
        else None
    ),
    effective_num_positions=(
        Decimal(str(conc_data.get('effective_num_positions', 0)))
        if conc_data.get('success')
        else None
    ),
    top_3_concentration=(
        Decimal(str(conc_data.get('top_3_concentration', 0)))
        if conc_data.get('success')
        else None
    ),
    top_10_concentration=(
        Decimal(str(conc_data.get('top_10_concentration', 0)))
        if conc_data.get('success')
        else None
    ),

    # ADD THESE NEW FIELDS (Phase 2):
    realized_volatility_30d=(
        Decimal(str(vol_data.get('realized_vol_30d', 0)))
        if vol_data.get('success')
        else None
    ),
    realized_volatility_60d=(
        Decimal(str(vol_data.get('realized_vol_60d', 0)))
        if vol_data.get('success')
        else None
    ),
    realized_volatility_90d=(
        Decimal(str(vol_data.get('realized_vol_90d', 0)))
        if vol_data.get('success')
        else None
    ),
    expected_volatility_30d=(
        Decimal(str(vol_data.get('expected_vol_30d', 0)))
        if vol_data.get('success')
        else None
    ),
    volatility_trend=(
        vol_data.get('vol_trend')
        if vol_data.get('success')
        else None
    ),
    volatility_percentile=(
        Decimal(str(vol_data.get('vol_percentile', 0)))
        if vol_data.get('success')
        else None
    )
)
```

---

# Testing & Validation

## Overview

We MUST be able to prove that:
1. **Old approach was broken** (show NVDA beta = -3)
2. **New approach works** (show NVDA beta = ~2.12)
3. **All new metrics are reasonable** (sector weights sum to 100%, etc.)
4. **System performs well** (batch completes in < 5 minutes)

## Diagnostic Script 1: Compare Old vs New Beta

**File:** `backend/scripts/testing/compare_old_new_beta.py`

**Purpose:** Show side-by-side comparison of broken 7-factor vs fixed single-factor betas

```python
"""
Compare Old (7-Factor) vs New (Single-Factor) Beta Calculations

This script demonstrates the dramatic improvement from fixing the multicollinearity issue.

Expected Results:
- Old: NVDA beta = -3 (WRONG SIGN due to multicollinearity)
- New: NVDA beta = ~2.12 (CORRECT - matches market sources)
"""
import asyncio
from datetime import date
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.users import Portfolio

# Import BOTH approaches
from app.calculations.factors import calculate_position_factor_exposures  # OLD (broken)
from app.calculations.market_beta import calculate_position_market_beta  # NEW (fixed)

async def compare_betas():
    print("\n" + "=" * 100)
    print("BETA COMPARISON: OLD (7-FACTOR) VS NEW (SINGLE-FACTOR)")
    print("=" * 100)
    print("\nPurpose: Demonstrate that the new single-factor approach fixes the")
    print("         multicollinearity problem that caused negative betas.\n")

    async with AsyncSessionLocal() as db:
        # Get all demo portfolios
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = portfolios_result.scalars().all()

        print(f"Testing positions from {len(portfolios)} portfolios:\n")

        all_results = []

        for portfolio in portfolios:
            print(f"\n{'─' * 100}")
            print(f"Portfolio: {portfolio.name}")
            print(f"{'─' * 100}")

            # Get positions
            positions_result = await db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.exit_date.is_(None)  # Active positions only
                )
            )
            positions = positions_result.scalars().all()

            # Test first 10 positions from each portfolio
            test_positions = positions[:10]

            for position in test_positions:
                print(f"\n{position.symbol:8} ", end='')

                # OLD APPROACH (7-factor with multicollinearity)
                try:
                    old_result = await calculate_position_factor_exposures(
                        db, position.id, date.today()
                    )

                    if old_result.get('success') and 'exposures' in old_result:
                        # Find Market beta in exposures
                        old_beta = None
                        for exp in old_result['exposures']:
                            if exp.get('factor_name') == 'Market':
                                old_beta = exp.get('beta')
                                break

                        if old_beta is not None:
                            print(f"Old: {old_beta:7.3f} ", end='')
                        else:
                            print(f"Old: {'N/A':>7} ", end='')
                            old_beta = None
                    else:
                        print(f"Old: {'ERROR':>7} ", end='')
                        old_beta = None

                except Exception as e:
                    print(f"Old: {'ERROR':>7} ", end='')
                    old_beta = None

                # NEW APPROACH (single-factor, no multicollinearity)
                try:
                    new_result = await calculate_position_market_beta(
                        db, position.id, date.today()
                    )

                    if new_result.get('success'):
                        new_beta = new_result.get('beta', None)
                        new_r2 = new_result.get('r_squared', None)

                        if new_beta is not None:
                            print(f"→ New: {new_beta:7.3f} (R²={new_r2:.3f}) ", end='')
                        else:
                            print(f"→ New: {'N/A':>7} ", end='')

                    else:
                        print(f"→ New: {'ERROR':>7} ", end='')
                        new_beta = None
                        new_r2 = None

                except Exception as e:
                    print(f"→ New: {'ERROR':>7} ", end='')
                    new_beta = None
                    new_r2 = None

                # Determine if this is a fix
                if (old_beta is not None and new_beta is not None):
                    # Check for sign flip (negative → positive)
                    if old_beta < 0 and new_beta > 0:
                        print("🎉 SIGN FIXED!", end='')
                    # Check for magnitude improvement
                    elif abs(new_beta) < abs(old_beta) * 0.7:
                        print("✓ Improved", end='')

                print()  # New line

                # Store for summary
                all_results.append({
                    'symbol': position.symbol,
                    'portfolio': portfolio.name,
                    'old_beta': old_beta,
                    'new_beta': new_beta,
                    'new_r2': new_r2
                })

        # SUMMARY
        print("\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)

        total_positions = len(all_results)
        sign_flips = sum(
            1 for r in all_results
            if r['old_beta'] is not None and r['new_beta'] is not None
            and (r['old_beta'] < 0) and (r['new_beta'] > 0)
        )
        magnitude_improvements = sum(
            1 for r in all_results
            if r['old_beta'] is not None and r['new_beta'] is not None
            and abs(r['new_beta']) < abs(r['old_beta'])
        )

        print(f"\nPositions tested: {total_positions}")
        print(f"Sign flips (negative → positive): {sign_flips}")
        print(f"Magnitude improvements: {magnitude_improvements}")

        # NVDA specific check
        nvda_results = [r for r in all_results if r['symbol'] == 'NVDA']
        if nvda_results:
            nvda = nvda_results[0]
            print(f"\n{'─' * 100}")
            print("NVDA VALIDATION (Key Test Case)")
            print(f"{'─' * 100}")
            print(f"Old Beta: {nvda['old_beta']:.3f if nvda['old_beta'] else 'N/A'} (Expected: ~-3)")
            print(f"New Beta: {nvda['new_beta']:.3f if nvda['new_beta'] else 'N/A'} (Expected: 1.7-2.2)")
            print(f"R²: {nvda['new_r2']:.3f if nvda['new_r2'] else 'N/A'}")

            if nvda['new_beta']:
                if 1.7 <= nvda['new_beta'] <= 2.5:
                    print("✓ NVDA beta is now in correct range!")
                else:
                    print("⚠ NVDA beta outside expected range")

        print("\n" + "=" * 100 + "\n")


if __name__ == "__main__":
    asyncio.run(compare_betas())
```

---

## Diagnostic Script 2: Validate All New Metrics

**File:** `backend/scripts/testing/validate_new_metrics.py`

**Purpose:** Run complete validation after all 3 phases implemented

```python
"""
Comprehensive Validation of All New Risk Metrics

Tests all three phases:
- Phase 0: Market Beta
- Phase 1: Sector Exposure & Concentration
- Phase 2: Volatility Analytics

Expected Results:
- Market beta: reasonable values (0.5-2.5 for most stocks)
- Sector weights: sum to ~100%
- HHI: in valid range (0-10,000)
- Volatility: positive, < 300%
"""
import asyncio
from datetime import date
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.calculations.market_beta import calculate_portfolio_market_beta
from app.calculations.sector_analysis import calculate_sector_and_concentration
from app.calculations.volatility_analytics import calculate_portfolio_volatility

async def validate_all_metrics():
    print("\n" + "=" * 100)
    print("COMPREHENSIVE RISK METRICS VALIDATION")
    print("=" * 100)

    async with AsyncSessionLocal() as db:
        # Get demo portfolios
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = portfolios_result.scalars().all()

        print(f"\nTesting {len(portfolios)} portfolios\n")

        for portfolio in portfolios:
            print("=" * 100)
            print(f"Portfolio: {portfolio.name}")
            print("=" * 100)

            # PHASE 0: Market Beta
            print("\n[Phase 0] Market Beta")
            print("-" * 60)

            beta_result = await calculate_portfolio_market_beta(
                db, portfolio.id, date.today()
            )

            if beta_result['success']:
                beta = beta_result['market_beta']
                r2 = beta_result['r_squared']
                print(f"✓ Beta: {beta:.3f}")
                print(f"  R²: {r2:.3f}")
                print(f"  Positions: {beta_result['positions_count']}")
                print(f"  Observations: {beta_result['observations']}")

                # Validation
                if 0 < beta < 3:
                    print("  ✓ Beta in reasonable range")
                else:
                    print("  ⚠ Beta outside typical range [0, 3]")

                if r2 > 0.3:
                    print("  ✓ R² > 0.3 (good fit)")
                elif r2 > 0.15:
                    print("  ⚠ R² moderate (0.15-0.3)")
                else:
                    print("  ✗ R² < 0.15 (poor fit)")
            else:
                print(f"✗ Failed: {beta_result.get('error')}")

            # PHASE 1: Sector & Concentration
            print("\n[Phase 1] Sector Exposure & Concentration")
            print("-" * 60)

            sector_result = await calculate_sector_and_concentration(
                db, portfolio.id
            )

            # Sector Exposure
            if sector_result['sector_exposure']['success']:
                sector_data = sector_result['sector_exposure']
                weights = sector_data['portfolio_weights']
                total_weight = sum(weights.values())

                print(f"✓ Sector Exposure:")
                print(f"  Total weight: {total_weight*100:.1f}%")

                if 0.95 <= total_weight <= 1.05:
                    print("  ✓ Weights sum to ~100%")
                else:
                    print(f"  ✗ Weights sum to {total_weight*100:.1f}% (should be ~100%)")

                # Show top 3 sectors
                print(f"\n  Top 3 sectors:")
                sorted_sectors = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
                for sector, weight in sorted_sectors:
                    print(f"    {sector}: {weight*100:.1f}%")

                # Unclassified check
                if sector_data.get('unclassified_positions'):
                    print(f"  ⚠ Unclassified: {', '.join(sector_data['unclassified_positions'])}")
                else:
                    print("  ✓ All positions classified")

            else:
                print(f"✗ Sector exposure failed: {sector_result['sector_exposure'].get('error')}")

            # Concentration
            if sector_result['concentration']['success']:
                conc_data = sector_result['concentration']
                hhi = conc_data['hhi']
                effective_positions = conc_data['effective_num_positions']
                top_3 = conc_data['top_3_concentration']
                top_10 = conc_data['top_10_concentration']

                print(f"\n✓ Concentration Metrics:")
                print(f"  HHI: {hhi:.1f}")
                print(f"  Effective positions: {effective_positions:.1f}")
                print(f"  Top 3: {top_3*100:.1f}%")
                print(f"  Top 10: {top_10*100:.1f}%")

                # Validation
                if 0 < hhi <= 10000:
                    print("  ✓ HHI in valid range")
                else:
                    print(f"  ✗ HHI out of range: {hhi}")

                if effective_positions <= conc_data['total_positions']:
                    print("  ✓ Effective positions ≤ total positions")
                else:
                    print("  ✗ Effective positions > total (error in calculation)")

                # Interpretation
                if hhi > 2500:
                    print("  Level: HIGHLY CONCENTRATED")
                elif hhi > 1500:
                    print("  Level: CONCENTRATED")
                elif hhi > 1000:
                    print("  Level: MODERATELY CONCENTRATED")
                else:
                    print("  Level: WELL DIVERSIFIED")

            else:
                print(f"✗ Concentration failed: {sector_result['concentration'].get('error')}")

            # PHASE 2: Volatility
            print("\n[Phase 2] Volatility Analytics")
            print("-" * 60)

            vol_result = await calculate_portfolio_volatility(
                db, portfolio.id, date.today()
            )

            if vol_result['success']:
                vol_30d = vol_result['realized_vol_30d']
                vol_60d = vol_result['realized_vol_60d']
                vol_90d = vol_result['realized_vol_90d']
                expected = vol_result['expected_vol_30d']
                trend = vol_result['vol_trend']
                percentile = vol_result['vol_percentile']

                print(f"✓ Volatility Metrics:")
                print(f"  30-day realized: {vol_30d:.2%}")
                print(f"  60-day realized: {vol_60d:.2%}")
                print(f"  90-day realized: {vol_90d:.2%}")
                print(f"  Expected (30-day forecast): {expected:.2%}")
                print(f"  Trend: {trend.upper()}")
                print(f"  Percentile: {percentile*100:.0f}th")

                # Validation
                if 0 < vol_30d < 3:
                    print("  ✓ Volatility in valid range (0-300%)")
                else:
                    print(f"  ✗ Volatility out of range: {vol_30d:.2%}")

                if expected > 0:
                    print("  ✓ HAR forecast is positive")
                else:
                    print("  ✗ HAR forecast is not positive")

                if trend in ['increasing', 'decreasing', 'stable']:
                    print("  ✓ Trend classification valid")
                else:
                    print(f"  ✗ Invalid trend: {trend}")

                if 0 <= percentile <= 1:
                    print("  ✓ Percentile in valid range [0, 1]")
                else:
                    print(f"  ✗ Percentile out of range: {percentile}")

                # Interpretation
                if vol_30d < 0.15:
                    print("  Level: VERY LOW volatility")
                elif vol_30d < 0.25:
                    print("  Level: LOW volatility")
                elif vol_30d < 0.35:
                    print("  Level: MODERATE volatility")
                elif vol_30d < 0.50:
                    print("  Level: HIGH volatility")
                else:
                    print("  Level: VERY HIGH volatility")

            else:
                print(f"✗ Volatility failed: {vol_result.get('error')}")

            print("\n")

    print("=" * 100)
    print("VALIDATION COMPLETE")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    asyncio.run(validate_all_metrics())
```

---

## Diagnostic Script 3: Test Batch Processing End-to-End

**File:** `backend/scripts/testing/test_batch_integration.py`

**Purpose:** Run full batch process and verify all new metrics are stored

```python
"""
Test Complete Batch Processing Integration

Runs the full batch orchestrator and checks that:
1. All new calculations execute
2. Results are stored in portfolio_snapshots
3. No errors occur
4. Performance is acceptable
"""
import asyncio
from datetime import date, datetime
from sqlalchemy import select, text
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

async def test_batch_integration():
    print("\n" + "=" * 100)
    print("BATCH PROCESSING INTEGRATION TEST")
    print("=" * 100)

    async with AsyncSessionLocal() as db:
        # Get first demo portfolio
        portfolio_result = await db.execute(select(Portfolio).limit(1))
        portfolio = portfolio_result.scalar_one()

        print(f"\nTesting portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}\n")

        # Run batch processing
        print("Running batch orchestrator...")
        print("-" * 100)

        start_time = datetime.now()

        try:
            batch_result = await batch_orchestrator_v2.run_daily_batch_sequence(
                portfolio_id=str(portfolio.id)
            )
            duration = (datetime.now() - start_time).total_seconds()

            print(f"\n✓ Batch completed in {duration:.2f} seconds")

            # Check if new metrics were calculated
            print("\nBatch Results:")
            print("-" * 100)

            # Market Beta
            if 'market_beta' in batch_result and batch_result['market_beta'].get('success'):
                mb = batch_result['market_beta']
                print(f"✓ Market Beta: {mb['market_beta']:.3f} (R²={mb['r_squared']:.3f})")
            else:
                print("✗ Market Beta: Failed or not found")

            # Sector & Concentration
            if 'sector_and_concentration' in batch_result:
                sector_success = batch_result['sector_and_concentration'].get('sector_exposure', {}).get('success', False)
                conc_success = batch_result['sector_and_concentration'].get('concentration', {}).get('success', False)

                if sector_success:
                    print("✓ Sector Exposure: Success")
                else:
                    print("✗ Sector Exposure: Failed")

                if conc_success:
                    conc = batch_result['sector_and_concentration']['concentration']
                    print(f"✓ Concentration: HHI={conc['hhi']:.1f}")
                else:
                    print("✗ Concentration: Failed")

            # Volatility
            if 'volatility' in batch_result and batch_result['volatility'].get('success'):
                vol = batch_result['volatility']
                print(f"✓ Volatility: {vol['realized_vol_30d']:.2%} (30-day)")
            else:
                print("✗ Volatility: Failed or not found")

            # Check database snapshot
            print("\nChecking Database Storage:")
            print("-" * 100)

            snapshot_result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.calculation_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            if snapshot:
                print(f"✓ Latest snapshot found: {snapshot.calculation_date}")

                # Check each new metric
                checks = [
                    (snapshot.market_beta is not None, "Market Beta"),
                    (snapshot.market_beta_r_squared is not None, "Market Beta R²"),
                    (snapshot.sector_exposure is not None, "Sector Exposure"),
                    (snapshot.hhi is not None, "HHI"),
                    (snapshot.effective_num_positions is not None, "Effective Positions"),
                    (snapshot.realized_volatility_30d is not None, "Realized Volatility"),
                    (snapshot.expected_volatility_30d is not None, "Expected Volatility"),
                    (snapshot.volatility_trend is not None, "Volatility Trend"),
                ]

                print("\nMetrics Stored in Snapshot:")
                for has_value, metric_name in checks:
                    status = "✓" if has_value else "✗"
                    print(f"  {status} {metric_name}")

                # Show actual values
                if snapshot.market_beta:
                    print(f"\n  Market Beta: {float(snapshot.market_beta):.3f}")
                if snapshot.hhi:
                    print(f"  HHI: {float(snapshot.hhi):.1f}")
                if snapshot.realized_volatility_30d:
                    print(f"  30-day Volatility: {float(snapshot.realized_volatility_30d):.2%}")

            else:
                print("✗ No snapshot found in database")

            # Performance check
            print("\nPerformance:")
            print("-" * 100)
            if duration < 300:  # 5 minutes
                print(f"✓ Batch completed in {duration:.2f}s (under 5 minutes)")
            else:
                print(f"⚠ Batch took {duration:.2f}s (over 5 minutes)")

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n✗ Batch failed after {duration:.2f} seconds")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 100)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    asyncio.run(test_batch_integration())
```

---

# Expected Results

## Phase 0: Market Beta

### NVDA Specific
```
Old Beta: -3.127 (WRONG - multicollinearity caused sign flip)
New Beta: 1.879 (CORRECT - in range [1.7, 2.2])
R²: 0.573 (GOOD - explains 57% of variance)
```

### Typical High-Beta Stocks
```
NVDA: 1.7-2.2
TSLA: 1.8-2.5
META: 1.2-1.5
```

### Typical Low-Beta Stocks
```
JNJ: 0.6-0.9
KO: 0.5-0.8
PG: 0.4-0.7
```

## Phase 1: Sector & Concentration

### Sector Weights (Tech-Heavy Portfolio)
```
Technology: 45%
Healthcare: 15%
Financials: 12%
Consumer Discretionary: 10%
Communication Services: 8%
Other: 10%
Total: 100%
```

### Concentration Metrics (Balanced Portfolio)
```
HHI: 850
Effective Positions: 11.8
Top 3: 28%
Top 10: 72%
Level: WELL DIVERSIFIED
```

### Concentration Metrics (Concentrated Portfolio)
```
HHI: 2,800
Effective Positions: 3.6
Top 3: 65%
Top 10: 95%
Level: HIGHLY CONCENTRATED
```

## Phase 2: Volatility

### Normal Volatility (Large Cap Stock)
```
30-day: 22%
60-day: 24%
90-day: 26%
Expected: 23%
Trend: DECREASING
Percentile: 55th
Level: LOW
```

### High Volatility (Growth Stock)
```
30-day: 48%
60-day: 52%
90-day: 45%
Expected: 50%
Trend: INCREASING
Percentile: 85th
Level: VERY HIGH
```

---

# Running the Tests

## Complete Test Sequence

```bash
cd backend

# 1. Run migrations (must be done first)
uv run alembic upgrade head

# 2. Compare old vs new betas
uv run python scripts/testing/compare_old_new_beta.py

# 3. Validate all metrics
uv run python scripts/testing/validate_new_metrics.py

# 4. Test batch integration
uv run python scripts/testing/test_batch_integration.py
```

## What to Look For

### Success Indicators
- ✓ NVDA beta changes from negative to positive
- ✓ All sector weights sum to ~100%
- ✓ HHI in valid range (0-10,000)
- ✓ All volatility values positive and < 300%
- ✓ Batch completes in < 5 minutes
- ✓ All metrics stored in database

### Failure Indicators
- ✗ Betas still have wrong signs
- ✗ Sector weights sum to < 90% or > 110%
- ✗ HHI > 10,000 or < 0
- ✗ Volatility > 300% or negative
- ✗ Batch takes > 10 minutes
- ✗ Database has NULL values for new metrics

---

**Last Updated:** 2025-10-16
**Status:** Ready for Testing
**Next Steps:** Run migration, execute tests, validate results
