# Risk Metrics System - Execution Plan

**Created:** 2025-10-15
**Status:** Ready for Execution
**Companion Document:** See `RiskMetricsPlanning.md` for context and decision rationale

---

## Document Purpose

This is a step-by-step execution guide for implementing the Risk Metrics System overhaul. Every task is specific, actionable, and includes validation steps.

**Target Audience:** AI coding agents, developers implementing the system
**Approach:** Can be executed mechanically - no decisions required

---

## Table of Contents

1. [Phase 0: Fix Market Beta](#phase-0-fix-market-beta)
2. [Phase 1: Sector Analysis & Concentration](#phase-1-sector-analysis--concentration)
3. [Phase 2: Volatility Analytics](#phase-2-volatility-analytics)
4. [Testing & Validation](#testing--validation)

---

# Phase 0: Fix Market Beta

**Duration:** Week 1 (5 days)
**Goal:** Replace broken 7-factor model with single-factor market beta calculation

## Objective

**Problem:** Current factor beta calculation has severe multicollinearity (VIF > 299), producing invalid betas (NVDA showing -3 instead of +2.12).

**Solution:** Implement single-factor market beta calculation (position returns vs SPY returns only).

**Success Criteria:**
- NVDA position beta = 1.7 to 2.2
- All positions have R² > 0.3 for high-beta stocks
- No VIF warnings (single factor = VIF of 1)
- Stress testing uses new market beta and produces reasonable results

---

## Section 1: Database Changes (Alembic)

### Migration 1: Add Market Beta Columns to portfolio_snapshots

**File:** `backend/alembic/versions/XXXX_add_market_beta_to_snapshots.py`

**Command to create:**
```bash
cd backend
uv run alembic revision -m "add_market_beta_to_snapshots"
```

**Migration content:**

```python
"""add_market_beta_to_snapshots

Revision ID: XXXX
Revises: [previous_revision]
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'XXXX'
down_revision = '[previous_revision]'  # Will be auto-filled
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to portfolio_snapshots table
    op.add_column('portfolio_snapshots',
        sa.Column('market_beta', sa.Numeric(10, 4), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('market_beta_r_squared', sa.Numeric(10, 4), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('market_beta_observations', sa.Integer, nullable=True)
    )


def downgrade():
    # Remove columns if rollback needed
    op.drop_column('portfolio_snapshots', 'market_beta_observations')
    op.drop_column('portfolio_snapshots', 'market_beta_r_squared')
    op.drop_column('portfolio_snapshots', 'market_beta')
```

**Validation:**
```bash
# Run migration
uv run alembic upgrade head

# Verify columns added
uv run python -c "
from app.database import AsyncSessionLocal
from sqlalchemy import text
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(\"\"\"
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='portfolio_snapshots'
            AND column_name LIKE '%market_beta%'
        \"\"\"))
        print(list(result))

asyncio.run(check())
"

# Expected output:
# [('market_beta', 'numeric'), ('market_beta_r_squared', 'numeric'), ('market_beta_observations', 'integer')]
```

---

## Section 2: Calculation Scripts

### Task 1: Create market_beta.py

**File:** `backend/app/calculations/market_beta.py`

**Full implementation:**

```python
"""
Market Beta Calculation - Single Factor Model
Calculates position and portfolio market beta using OLS regression against SPY.

Created: 2025-10-15
Replaces: Broken multi-factor model in factors.py
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

import pandas as pd
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import statsmodels.api as sm

from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.constants.factors import REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS, BETA_CAP_LIMIT
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_returns_for_beta(
    db: AsyncSession,
    symbol: str,
    start_date: date,
    end_date: date
) -> pd.Series:
    """
    Fetch historical prices and calculate returns for a symbol.

    Args:
        db: Database session
        symbol: Symbol to fetch (e.g., 'NVDA', 'SPY')
        start_date: Start date for data
        end_date: End date for data

    Returns:
        Pandas Series of daily returns with date index
    """
    stmt = select(
        MarketDataCache.date,
        MarketDataCache.close
    ).where(
        and_(
            MarketDataCache.symbol == symbol.upper(),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date)

    result = await db.execute(stmt)
    records = result.all()

    if not records:
        logger.warning(f"No price data found for {symbol}")
        return pd.Series(dtype=float)

    # Convert to DataFrame
    df = pd.DataFrame([
        {'date': r.date, 'close': float(r.close)}
        for r in records
    ])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Calculate returns
    returns = df['close'].pct_change(fill_method=None).dropna()

    return returns


async def calculate_position_market_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS
) -> Dict[str, Any]:
    """
    Calculate market beta for a single position using OLS regression.

    Beta = Cov(Position_Return, Market_Return) / Var(Market_Return)

    Args:
        db: Database session
        position_id: Position UUID
        calculation_date: Date for calculation (end of window)
        window_days: Lookback period in days (default 90)

    Returns:
        {
            'position_id': UUID,
            'beta': float,
            'r_squared': float,
            'std_error': float,
            'p_value': float,
            'observations': int,
            'calculation_date': date,
            'success': bool,
            'error': str (if failed)
        }
    """
    logger.info(f"Calculating market beta for position {position_id}")

    try:
        # Get position details
        position_stmt = select(Position).where(Position.id == position_id)
        position_result = await db.execute(position_stmt)
        position = position_result.scalar_one_or_none()

        if not position:
            return {
                'position_id': position_id,
                'success': False,
                'error': 'Position not found'
            }

        # Define date range (add buffer for trading days)
        end_date = calculation_date
        start_date = end_date - timedelta(days=window_days + 30)

        # Fetch position returns
        position_returns = await fetch_returns_for_beta(
            db, position.symbol, start_date, end_date
        )

        if position_returns.empty or len(position_returns) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient data: {len(position_returns)} days',
                'observations': len(position_returns)
            }

        # Fetch SPY returns (market)
        spy_returns = await fetch_returns_for_beta(
            db, 'SPY', start_date, end_date
        )

        if spy_returns.empty:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': 'No SPY data available'
            }

        # Align dates (only use common trading days)
        common_dates = position_returns.index.intersection(spy_returns.index)

        if len(common_dates) < MIN_REGRESSION_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient aligned data: {len(common_dates)} days',
                'observations': len(common_dates)
            }

        # Get aligned returns
        y = position_returns.loc[common_dates].values  # Position returns
        X = spy_returns.loc[common_dates].values        # Market returns

        # Run OLS regression: position_return = alpha + beta * market_return + error
        X_with_const = sm.add_constant(X)
        model = sm.OLS(y, X_with_const).fit()

        # Extract results
        beta = float(model.params[1])  # Slope coefficient
        alpha = float(model.params[0])  # Intercept
        r_squared = float(model.rsquared)
        std_error = float(model.bse[1])
        p_value = float(model.pvalues[1])

        # Cap beta to prevent extreme outliers
        original_beta = beta
        beta = max(-BETA_CAP_LIMIT, min(BETA_CAP_LIMIT, beta))

        if abs(original_beta) > BETA_CAP_LIMIT:
            logger.warning(
                f"Beta capped for {position.symbol}: {original_beta:.3f} -> {beta:.3f}"
            )

        # Determine significance
        is_significant = p_value < 0.10  # 90% confidence

        result = {
            'position_id': position_id,
            'symbol': position.symbol,
            'beta': beta,
            'alpha': alpha,
            'r_squared': r_squared,
            'std_error': std_error,
            'p_value': p_value,
            'observations': len(common_dates),
            'calculation_date': calculation_date,
            'is_significant': is_significant,
            'success': True
        }

        logger.info(
            f"Beta calculated for {position.symbol}: {beta:.3f} "
            f"(R²={r_squared:.3f}, p={p_value:.3f}, n={len(common_dates)})"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating beta for position {position_id}: {e}")
        return {
            'position_id': position_id,
            'success': False,
            'error': str(e)
        }


async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate portfolio-level market beta as equity-weighted average of position betas.

    Portfolio Beta = Σ(position_market_value_i × position_beta_i) / portfolio_equity

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation

    Returns:
        {
            'portfolio_id': UUID,
            'market_beta': float,
            'r_squared': float (weighted average),
            'observations': int (min across positions),
            'positions_count': int,
            'calculation_date': date,
            'position_betas': Dict[UUID, float],
            'success': bool
        }
    """
    logger.info(f"Calculating portfolio market beta for {portfolio_id}")

    try:
        # Get portfolio
        from app.models.users import Portfolio as PortfolioModel
        portfolio_stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'Portfolio not found'
            }

        # Validate equity balance
        if not portfolio.equity_balance or portfolio.equity_balance <= 0:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'Invalid portfolio equity balance'
            }

        portfolio_equity = float(portfolio.equity_balance)

        # Get active positions
        positions_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        positions_result = await db.execute(positions_stmt)
        positions = positions_result.scalars().all()

        if not positions:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No active positions found'
            }

        # Calculate beta for each position
        position_betas = {}
        position_market_values = {}
        position_r_squareds = {}
        min_observations = float('inf')

        for position in positions:
            beta_result = await calculate_position_market_beta(
                db, position.id, calculation_date
            )

            if not beta_result['success']:
                logger.warning(
                    f"Could not calculate beta for {position.symbol}: "
                    f"{beta_result.get('error', 'Unknown error')}"
                )
                continue

            # Get position market value
            from app.calculations.factor_utils import get_position_market_value
            market_value = float(get_position_market_value(position, recalculate=True))

            position_betas[position.id] = beta_result['beta']
            position_market_values[position.id] = market_value
            position_r_squareds[position.id] = beta_result['r_squared']
            min_observations = min(min_observations, beta_result['observations'])

        if not position_betas:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No position betas could be calculated'
            }

        # Calculate equity-weighted portfolio beta
        total_weighted_beta = 0.0
        total_weighted_r_squared = 0.0

        for pos_id, beta in position_betas.items():
            market_value = position_market_values[pos_id]
            weight = market_value / portfolio_equity

            total_weighted_beta += beta * weight
            total_weighted_r_squared += position_r_squareds[pos_id] * weight

        result = {
            'portfolio_id': portfolio_id,
            'market_beta': total_weighted_beta,
            'r_squared': total_weighted_r_squared,
            'observations': int(min_observations) if min_observations != float('inf') else 0,
            'positions_count': len(position_betas),
            'calculation_date': calculation_date,
            'position_betas': {str(k): v for k, v in position_betas.items()},
            'success': True
        }

        logger.info(
            f"Portfolio beta calculated: {total_weighted_beta:.3f} "
            f"({len(position_betas)} positions)"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating portfolio beta: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }
```

**Validation:**
```bash
# Test import
cd backend
uv run python -c "from app.calculations.market_beta import calculate_position_market_beta; print('✓ Import successful')"

# Test on NVDA position (should get beta ~1.7-2.2)
uv run python -c "
import asyncio
from datetime import date
from uuid import UUID
from app.database import AsyncSessionLocal
from app.calculations.market_beta import calculate_position_market_beta

async def test():
    # Replace with actual NVDA position ID from your database
    nvda_position_id = UUID('your-nvda-position-uuid-here')

    async with AsyncSessionLocal() as db:
        result = await calculate_position_market_beta(
            db, nvda_position_id, date.today()
        )
        print(f'Beta: {result.get(\"beta\")}')
        print(f'R²: {result.get(\"r_squared\")}')
        print(f'Observations: {result.get(\"observations\")}')

asyncio.run(test())
"
```

---

## Section 3: API Changes

### No New API Endpoints Required

**Rationale:** Market beta calculation is a backend batch process, not a real-time API call. Results are stored in `portfolio_snapshots` and accessed via existing `/api/v1/data/portfolio/{id}/complete` endpoint.

### Modified API Response

**Endpoint:** `GET /api/v1/data/portfolio/{id}/complete`
**Service:** `backend/app/api/v1/data.py`

**No code changes needed** - The endpoint already returns the complete `portfolio_snapshots` record. New columns will automatically appear in response once populated.

**Expected response changes:**
```json
{
  "snapshot": {
    ...existing fields...,
    "market_beta": 1.24,
    "market_beta_r_squared": 0.68,
    "market_beta_observations": 81
  }
}
```

---

## Section 4: Frontend Changes

### Task 1: Update Portfolio Metrics Display

**File:** `frontend/src/components/portfolio/PortfolioMetrics.tsx`

**Changes:**
1. Add market beta to metrics display
2. Add tooltip explaining market beta
3. Color-code based on risk level

**Implementation:**

```typescript
// Add to PortfolioMetrics.tsx

interface PortfolioMetricsProps {
  metrics: {
    ...existing...
    market_beta?: number;
    market_beta_r_squared?: number;
  };
}

// Add new metric card
<Card>
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
      Market Beta
      <Tooltip>
        <TooltipTrigger>
          <Info className="h-4 w-4 text-muted-foreground" />
        </TooltipTrigger>
        <TooltipContent>
          <p>Measures sensitivity to market movements.</p>
          <p className="text-xs">Beta of 1.0 = moves with market</p>
          <p className="text-xs">Beta &gt; 1.0 = more volatile than market</p>
        </TooltipContent>
      </Tooltip>
    </CardTitle>
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold">
      {metrics.market_beta?.toFixed(2) ?? 'N/A'}
    </div>
    <p className="text-xs text-muted-foreground mt-1">
      R² = {metrics.market_beta_r_squared?.toFixed(2) ?? 'N/A'}
    </p>
    <p className="text-xs mt-1">
      {getBetaInterpretation(metrics.market_beta)}
    </p>
  </CardContent>
</Card>

// Helper function
function getBetaInterpretation(beta?: number): string {
  if (!beta) return 'Not calculated';
  if (beta < 0.5) return 'Low volatility - defensive';
  if (beta < 0.8) return 'Below market volatility';
  if (beta < 1.2) return 'Market-like volatility';
  if (beta < 1.5) return 'Above market volatility';
  return 'High volatility - aggressive';
}
```

**Validation:**
- View portfolio page
- Verify market beta displays correctly
- Verify tooltip shows explanation
- Verify interpretation text makes sense

---

## Section 5: Integration & Testing

### Task 1: Update Batch Orchestrator

**File:** `backend/app/batch/batch_orchestrator_v2.py`

**Changes:**
Add market beta calculation to daily batch sequence.

**Find this section** (around line 100-150):
```python
async def run_daily_batch_sequence(
    portfolio_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """Run daily batch calculations"""
    ...
```

**Add after portfolio aggregation:**
```python
# After existing portfolio aggregation
logger.info("Step 2.5: Calculating market betas")
from app.calculations.market_beta import calculate_portfolio_market_beta

market_beta_result = await calculate_portfolio_market_beta(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calculation_date
)

if market_beta_result['success']:
    # Store in portfolio snapshot
    # (This will be done in snapshot creation step)
    results['market_beta'] = market_beta_result
    logger.info(f"Market beta: {market_beta_result['market_beta']:.3f}")
else:
    logger.warning(f"Market beta calculation failed: {market_beta_result.get('error')}")
    results['market_beta'] = {'success': False, 'error': market_beta_result.get('error')}
```

### Task 2: Update Snapshot Creation

**File:** `backend/app/calculations/snapshots.py`

**Find:** `create_portfolio_snapshot()` function

**Add** market beta fields to snapshot:
```python
# In create_portfolio_snapshot() function
# After calculating other metrics

# Get market beta (should be calculated earlier in batch)
market_beta_data = batch_results.get('market_beta', {})

snapshot = PortfolioSnapshot(
    ...existing fields...,
    market_beta=Decimal(str(market_beta_data.get('market_beta', 0))) if market_beta_data.get('success') else None,
    market_beta_r_squared=Decimal(str(market_beta_data.get('r_squared', 0))) if market_beta_data.get('success') else None,
    market_beta_observations=market_beta_data.get('observations', 0) if market_beta_data.get('success') else None
)
```

### Task 3: Update Stress Testing

**File:** `backend/app/calculations/market_risk.py`

**Find:** `calculate_portfolio_market_beta()` function (line ~56)

**Replace** with call to new market beta:
```python
async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate portfolio market beta (wrapper for new implementation)
    """
    from app.calculations.market_beta import calculate_portfolio_market_beta as calc_beta

    return await calc_beta(db, portfolio_id, calculation_date)
```

This ensures stress testing uses the new, correct market beta.

---

## Validation Checklist

### Unit Tests
```bash
cd backend

# Test market beta calculation
uv run python scripts/debug_multivariate_regression.py

# Should now show single-factor results (not 7 factors)

# Run on all demo portfolios
uv run python -c "
import asyncio
from datetime import date
from app.database import AsyncSessionLocal
from app.calculations.market_beta import calculate_portfolio_market_beta
from sqlalchemy import select
from app.models.users import Portfolio

async def test_all():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()

        for portfolio in portfolios:
            beta_result = await calculate_portfolio_market_beta(
                db, portfolio.id, date.today()
            )
            print(f'{portfolio.name}: Beta = {beta_result.get(\"market_beta\")}')

asyncio.run(test_all())
"
```

### Integration Tests
```bash
# Run full batch with new market beta
uv run python scripts/run_batch_calculations.py

# Check database for results
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select, text

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT
                calculation_date,
                market_beta,
                market_beta_r_squared,
                market_beta_observations
            FROM portfolio_snapshots
            WHERE market_beta IS NOT NULL
            ORDER BY calculation_date DESC
            LIMIT 5
        '''))

        for row in result:
            print(row)

asyncio.run(check())
"
```

### Acceptance Criteria
- [ ] NVDA position beta = 1.7 to 2.2 (not -3!)
- [ ] All high-beta stocks have R² > 0.3
- [ ] Portfolio betas are reasonable (0.8 to 1.5 for balanced portfolios)
- [ ] Stress testing produces reasonable P&L estimates
- [ ] No VIF warnings in logs (single factor = no multicollinearity)
- [ ] Frontend displays market beta correctly
- [ ] Tooltip explains beta clearly

---

# Phase 1: Sector Analysis & Concentration

**Duration:** Week 2 (5 days)
**Goal:** Add sector exposure vs S&P 500 benchmark and concentration metrics

## Objective

**What:** Show users their sector allocation compared to S&P 500, plus concentration risk.

**Why:** "I'm 45% in Tech" is more actionable than "Growth spread beta +0.85"

**Success Criteria:**
- Sector weights sum to 100%
- All positions have sector assigned
- Over/underweight calculations correct
- HHI matches manual calculation
- Top 10 concentration makes sense

---

## Section 1: Database Changes (Alembic)

### Migration 2: Add Sector & Concentration Columns

**File:** `backend/alembic/versions/XXXX_add_sector_concentration_to_snapshots.py`

**Command:**
```bash
cd backend
uv run alembic revision -m "add_sector_concentration_to_snapshots"
```

**Migration content:**

```python
"""add_sector_concentration_to_snapshots

Revision ID: XXXX
Revises: [previous - market beta migration]
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'XXXX'
down_revision = '[market_beta_migration_id]'
branch_labels = None
depends_on = None


def upgrade():
    # Add JSONB column for sector exposure
    op.add_column('portfolio_snapshots',
        sa.Column('sector_exposure', postgresql.JSONB, nullable=True)
    )

    # Add concentration metrics
    op.add_column('portfolio_snapshots',
        sa.Column('hhi', sa.Numeric(10, 2), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('effective_num_positions', sa.Numeric(10, 2), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('top_3_concentration', sa.Numeric(10, 4), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('top_10_concentration', sa.Numeric(10, 4), nullable=True)
    )


def downgrade():
    op.drop_column('portfolio_snapshots', 'top_10_concentration')
    op.drop_column('portfolio_snapshots', 'top_3_concentration')
    op.drop_column('portfolio_snapshots', 'effective_num_positions')
    op.drop_column('portfolio_snapshots', 'hhi')
    op.drop_column('portfolio_snapshots', 'sector_exposure')
```

**Validation:**
```bash
uv run alembic upgrade head

# Verify
uv run python -c "
from app.database import AsyncSessionLocal
from sqlalchemy import text
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(\"\"\"
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='portfolio_snapshots'
            AND (column_name LIKE '%sector%' OR column_name LIKE '%hhi%' OR column_name LIKE '%concentration%')
        \"\"\"))
        for row in result:
            print(row)

asyncio.run(check())
"
```

---

## Section 2: Calculation Scripts

### Task 1: Create sector_analysis.py

**File:** `backend/app/calculations/sector_analysis.py`

**Full implementation:**

```python
"""
Sector Analysis & Concentration Metrics
Calculates portfolio sector exposure vs S&P 500 benchmark and concentration metrics.

Created: 2025-10-15
"""
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.positions import Position
from app.models.users import Portfolio as PortfolioModel
from app.calculations.factor_utils import get_position_market_value
from app.core.logging import get_logger

logger = get_logger(__name__)

# S&P 500 sector weights (as of 2025)
# Source: SPDR Sector ETFs
SP500_SECTOR_WEIGHTS = {
    'Technology': 0.28,
    'Healthcare': 0.13,
    'Financials': 0.13,
    'Consumer Discretionary': 0.10,
    'Industrials': 0.08,
    'Communication Services': 0.08,
    'Consumer Staples': 0.06,
    'Energy': 0.04,
    'Utilities': 0.03,
    'Real Estate': 0.02,
    'Materials': 0.02,
    'Other': 0.03
}


def calculate_hhi(weights: Dict[str, float]) -> float:
    """
    Calculate Herfindahl-Hirschman Index.

    HHI = Σ(weight_i²) × 10,000

    Interpretation:
    - 10,000 = single position (max concentration)
    - 1,000 = 10 equal positions
    - 100 = 100 equal positions (highly diversified)

    Args:
        weights: Dictionary of {position_id: weight} (weights as decimals, sum to 1.0)

    Returns:
        HHI value (0 to 10,000)
    """
    return sum(w ** 2 for w in weights.values()) * 10000


def calculate_effective_positions(hhi: float) -> float:
    """
    Calculate effective number of positions from HHI.

    N_effective = 10,000 / HHI

    Args:
        hhi: Herfindahl-Hirschman Index

    Returns:
        Effective number of positions
    """
    if hhi == 0:
        return 0
    return 10000 / hhi


async def calculate_sector_exposure(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, Any]:
    """
    Calculate sector exposure for portfolio and compare to S&P 500.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID

    Returns:
        {
            'portfolio_weights': {'Technology': 0.45, ...},
            'benchmark_weights': {'Technology': 0.28, ...},
            'over_underweight': {'Technology': 0.17, ...},
            'largest_overweight': 'Technology',
            'largest_underweight': 'Energy',
            'total_portfolio_value': float,
            'positions_by_sector': {'Technology': 15, ...},
            'success': bool
        }
    """
    logger.info(f"Calculating sector exposure for portfolio {portfolio_id}")

    try:
        # Get active positions with sectors
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()

        if not positions:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No active positions'
            }

        # Aggregate by sector
        sector_values = {}
        total_value = Decimal('0')
        positions_by_sector = {}
        unclassified_positions = []

        for position in positions:
            market_value = get_position_market_value(position, recalculate=True)
            total_value += market_value

            # Get sector from market_data_cache
            # Note: Position model should have sector field or we fetch from market_data_cache
            sector = None

            # Try to get sector from position's linked market data
            # This is a simplified approach - you may need to join with market_data_cache
            if hasattr(position, 'sector') and position.sector:
                sector = position.sector
            else:
                # Fetch from market_data_cache
                from app.models.market_data import MarketDataCache
                market_data_stmt = select(MarketDataCache.sector).where(
                    MarketDataCache.symbol == position.symbol
                ).limit(1)
                sector_result = await db.execute(market_data_stmt)
                sector_row = sector_result.scalar_one_or_none()
                sector = sector_row if sector_row else None

            if not sector:
                sector = 'Unclassified'
                unclassified_positions.append(position.symbol)

            sector_values[sector] = sector_values.get(sector, Decimal('0')) + market_value
            positions_by_sector[sector] = positions_by_sector.get(sector, 0) + 1

        if unclassified_positions:
            logger.warning(
                f"Unclassified positions: {', '.join(unclassified_positions)}"
            )

        # Calculate portfolio weights
        portfolio_weights = {
            sector: float(value / total_value)
            for sector, value in sector_values.items()
        }

        # Calculate over/underweight vs S&P 500
        over_underweight = {}
        for sector in set(list(portfolio_weights.keys()) + list(SP500_SECTOR_WEIGHTS.keys())):
            portfolio_weight = portfolio_weights.get(sector, 0.0)
            benchmark_weight = SP500_SECTOR_WEIGHTS.get(sector, 0.0)
            over_underweight[sector] = portfolio_weight - benchmark_weight

        # Find largest over/underweights
        sorted_diff = sorted(over_underweight.items(), key=lambda x: x[1])
        largest_underweight = sorted_diff[0][0] if sorted_diff else None
        largest_overweight = sorted_diff[-1][0] if sorted_diff else None

        result = {
            'portfolio_id': portfolio_id,
            'portfolio_weights': portfolio_weights,
            'benchmark_weights': SP500_SECTOR_WEIGHTS,
            'over_underweight': over_underweight,
            'largest_overweight': largest_overweight,
            'largest_underweight': largest_underweight,
            'total_portfolio_value': float(total_value),
            'positions_by_sector': positions_by_sector,
            'unclassified_positions': unclassified_positions,
            'success': True
        }

        logger.info(
            f"Sector exposure calculated: "
            f"Largest overweight = {largest_overweight}, "
            f"Largest underweight = {largest_underweight}"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating sector exposure: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }


async def calculate_concentration_metrics(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, Any]:
    """
    Calculate portfolio concentration metrics.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID

    Returns:
        {
            'hhi': float,
            'effective_num_positions': float,
            'top_3_concentration': float,
            'top_10_concentration': float,
            'total_positions': int,
            'top_3_positions': List[str],
            'top_10_positions': List[str],
            'success': bool
        }
    """
    logger.info(f"Calculating concentration metrics for portfolio {portfolio_id}")

    try:
        # Get portfolio for equity balance
        portfolio_stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'Portfolio not found'
            }

        portfolio_equity = float(portfolio.equity_balance)

        # Get active positions
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()

        if not positions:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No active positions'
            }

        # Calculate weights and market values
        position_data = []
        for position in positions:
            market_value = float(get_position_market_value(position, recalculate=True))
            weight = market_value / portfolio_equity

            position_data.append({
                'symbol': position.symbol,
                'market_value': market_value,
                'weight': weight
            })

        # Sort by market value descending
        position_data.sort(key=lambda x: x['market_value'], reverse=True)

        # Calculate HHI
        weights = {p['symbol']: p['weight'] for p in position_data}
        hhi = calculate_hhi(weights)
        effective_positions = calculate_effective_positions(hhi)

        # Top 3 concentration
        top_3_weight = sum(p['weight'] for p in position_data[:3])
        top_3_symbols = [p['symbol'] for p in position_data[:3]]

        # Top 10 concentration
        top_10_weight = sum(p['weight'] for p in position_data[:10])
        top_10_symbols = [p['symbol'] for p in position_data[:10]]

        result = {
            'portfolio_id': portfolio_id,
            'hhi': hhi,
            'effective_num_positions': effective_positions,
            'top_3_concentration': top_3_weight,
            'top_10_concentration': top_10_weight,
            'total_positions': len(positions),
            'top_3_positions': top_3_symbols,
            'top_10_positions': top_10_symbols,
            'success': True
        }

        logger.info(
            f"Concentration metrics: HHI={hhi:.2f}, "
            f"Effective positions={effective_positions:.2f}, "
            f"Top 3={top_3_weight*100:.1f}%"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating concentration metrics: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }


async def calculate_sector_and_concentration(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, Any]:
    """
    Calculate both sector exposure and concentration metrics.

    Convenience function for batch processing.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID

    Returns:
        Combined results from both calculations
    """
    sector_result = await calculate_sector_exposure(db, portfolio_id)
    concentration_result = await calculate_concentration_metrics(db, portfolio_id)

    return {
        'sector_exposure': sector_result,
        'concentration': concentration_result
    }
```

**Validation:**
```bash
cd backend

# Test import
uv run python -c "from app.calculations.sector_analysis import calculate_sector_exposure; print('✓ Import successful')"

# Test on demo portfolio
uv run python -c "
import asyncio
from datetime import date
from app.database import AsyncSessionLocal
from app.calculations.sector_analysis import calculate_sector_and_concentration
from sqlalchemy import select
from app.models.users import Portfolio

async def test():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one()

        analysis = await calculate_sector_and_concentration(db, portfolio.id)

        print('Sector Exposure:')
        for sector, weight in analysis['sector_exposure']['portfolio_weights'].items():
            benchmark = analysis['sector_exposure']['benchmark_weights'].get(sector, 0)
            diff = analysis['sector_exposure']['over_underweight'][sector]
            print(f'  {sector}: {weight*100:.1f}% (S&P: {benchmark*100:.1f}%, diff: {diff*100:+.1f}%)')

        print('\nConcentration:')
        conc = analysis['concentration']
        print(f'  HHI: {conc[\"hhi\"]:.2f}')
        print(f'  Effective positions: {conc[\"effective_num_positions\"]:.2f}')
        print(f'  Top 3: {conc[\"top_3_concentration\"]*100:.1f}%')

asyncio.run(test())
"
```

---

## Section 3: API Changes

### No New API Endpoints Required

Results stored in `portfolio_snapshots` and accessed via existing endpoints.

**Modified response** for `GET /api/v1/data/portfolio/{id}/complete`:

```json
{
  "snapshot": {
    ...existing fields...,
    "sector_exposure": {
      "Technology": {
        "portfolio": 0.45,
        "benchmark": 0.28,
        "diff": 0.17
      },
      "Healthcare": {
        "portfolio": 0.15,
        "benchmark": 0.13,
        "diff": 0.02
      }
    },
    "hhi": 850.25,
    "effective_num_positions": 11.76,
    "top_3_concentration": 0.35,
    "top_10_concentration": 0.78
  }
}
```

---

## Section 4: Frontend Changes

### Task 1: Create Sector Exposure Component

**File:** `frontend/src/components/portfolio/SectorExposure.tsx`

**Create new file:**

```typescript
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

interface SectorData {
  portfolio: number;
  benchmark: number;
  diff: number;
}

interface SectorExposureProps {
  sectorExposure: Record<string, SectorData>;
}

export function SectorExposure({ sectorExposure }: SectorExposureProps) {
  // Sort by portfolio weight descending
  const sectors = Object.entries(sectorExposure).sort(
    ([, a], [, b]) => b.portfolio - a.portfolio
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sector Exposure vs S&P 500</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sectors.map(([sector, data]) => (
            <div key={sector}>
              <div className="flex justify-between text-sm mb-1">
                <span>{sector}</span>
                <span className="text-muted-foreground">
                  {(data.portfolio * 100).toFixed(1)}%
                  <span className={data.diff > 0 ? 'text-orange-600' : 'text-green-600'}>
                    {' '}({data.diff > 0 ? '+' : ''}{(data.diff * 100).toFixed(1)}%)
                  </span>
                </span>
              </div>
              <div className="space-y-1">
                <Progress value={data.portfolio * 100} className="h-2" />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>S&P 500: {(data.benchmark * 100).toFixed(1)}%</span>
                  <span>
                    {Math.abs(data.diff) > 0.05
                      ? data.diff > 0
                        ? 'Overweight'
                        : 'Underweight'
                      : 'Neutral'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Task 2: Create Concentration Metrics Component

**File:** `frontend/src/components/portfolio/ConcentrationMetrics.tsx`

**Create new file:**

```typescript
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Info } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface ConcentrationMetricsProps {
  hhi: number;
  effectiveNumPositions: number;
  top3Concentration: number;
  top10Concentration: number;
  top3Positions?: string[];
  top10Positions?: string[];
}

export function ConcentrationMetrics({
  hhi,
  effectiveNumPositions,
  top3Concentration,
  top10Concentration,
  top3Positions,
  top10Positions,
}: ConcentrationMetricsProps) {
  const getConcentrationLevel = (hhi: number): string => {
    if (hhi > 2500) return 'Highly Concentrated';
    if (hhi > 1500) return 'Concentrated';
    if (hhi > 1000) return 'Moderately Concentrated';
    return 'Well Diversified';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Concentration Risk
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p>Measures how concentrated your portfolio is.</p>
                <p className="text-xs">Lower = more diversified</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium">HHI Score</span>
              <span className="text-sm text-muted-foreground">
                {hhi.toFixed(0)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {getConcentrationLevel(hhi)}
            </p>
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium">Effective Positions</span>
              <span className="text-sm text-muted-foreground">
                {effectiveNumPositions.toFixed(1)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Portfolio acts like {effectiveNumPositions.toFixed(0)} equal-sized positions
            </p>
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium">Top 3 Holdings</span>
              <span className="text-sm text-muted-foreground">
                {(top3Concentration * 100).toFixed(1)}%
              </span>
            </div>
            {top3Positions && top3Positions.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {top3Positions.join(', ')}
              </p>
            )}
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium">Top 10 Holdings</span>
              <span className="text-sm text-muted-foreground">
                {(top10Concentration * 100).toFixed(1)}%
              </span>
            </div>
            {top10Positions && top10Positions.length > 0 && (
              <p className="text-xs text-muted-foreground truncate">
                {top10Positions.slice(0, 5).join(', ')}
                {top10Positions.length > 5 ? '...' : ''}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Task 3: Update Portfolio Page

**File:** `frontend/app/portfolio/page.tsx`

**Add** new components to the page:

```typescript
// Add imports
import { SectorExposure } from '@/components/portfolio/SectorExposure';
import { ConcentrationMetrics } from '@/components/portfolio/ConcentrationMetrics';

// In the page component, after existing components:
<div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
  {snapshot?.sector_exposure && (
    <SectorExposure sectorExposure={snapshot.sector_exposure} />
  )}

  {snapshot?.hhi && (
    <ConcentrationMetrics
      hhi={snapshot.hhi}
      effectiveNumPositions={snapshot.effective_num_positions}
      top3Concentration={snapshot.top_3_concentration}
      top10Concentration={snapshot.top_10_concentration}
      top3Positions={snapshot.top_3_positions}
      top10Positions={snapshot.top_10_positions}
    />
  )}
</div>
```

---

## Section 5: Integration & Testing

### Task 1: Update Batch Orchestrator

**File:** `backend/app/batch/batch_orchestrator_v2.py`

**Add** after market beta calculation:

```python
# Step 3: Calculate sector exposure and concentration
logger.info("Step 3: Calculating sector exposure and concentration")
from app.calculations.sector_analysis import calculate_sector_and_concentration

sector_conc_result = await calculate_sector_and_concentration(
    db=db,
    portfolio_id=portfolio_id
)

results['sector_and_concentration'] = sector_conc_result
```

### Task 2: Update Snapshot Creation

**File:** `backend/app/calculations/snapshots.py`

**Add** to `create_portfolio_snapshot()`:

```python
# Get sector and concentration data
sector_conc_data = batch_results.get('sector_and_concentration', {})
sector_data = sector_conc_data.get('sector_exposure', {})
conc_data = sector_conc_data.get('concentration', {})

# Prepare sector exposure JSON
sector_exposure_json = {}
if sector_data.get('success'):
    for sector in sector_data['portfolio_weights'].keys():
        sector_exposure_json[sector] = {
            'portfolio': sector_data['portfolio_weights'].get(sector, 0),
            'benchmark': sector_data['benchmark_weights'].get(sector, 0),
            'diff': sector_data['over_underweight'].get(sector, 0)
        }

snapshot = PortfolioSnapshot(
    ...existing fields...,
    sector_exposure=sector_exposure_json if sector_data.get('success') else None,
    hhi=Decimal(str(conc_data['hhi'])) if conc_data.get('success') else None,
    effective_num_positions=Decimal(str(conc_data['effective_num_positions'])) if conc_data.get('success') else None,
    top_3_concentration=Decimal(str(conc_data['top_3_concentration'])) if conc_data.get('success') else None,
    top_10_concentration=Decimal(str(conc_data['top_10_concentration'])) if conc_data.get('success') else None
)
```

---

## Validation Checklist

### Unit Tests
```bash
# Test sector analysis
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.calculations.sector_analysis import calculate_sector_and_concentration
from sqlalchemy import select
from app.models.users import Portfolio

async def test():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one()

        analysis = await calculate_sector_and_concentration(db, portfolio.id)

        # Validate sector weights sum to ~1.0
        total_weight = sum(analysis['sector_exposure']['portfolio_weights'].values())
        assert 0.95 <= total_weight <= 1.05, f'Weights sum to {total_weight}, should be ~1.0'

        # Validate HHI range
        hhi = analysis['concentration']['hhi']
        assert 0 < hhi <= 10000, f'HHI {hhi} out of valid range'

        # Validate effective positions
        eff_pos = analysis['concentration']['effective_num_positions']
        total_pos = analysis['concentration']['total_positions']
        assert eff_pos <= total_pos, f'Effective positions ({eff_pos}) > total ({total_pos})'

        print('✓ All validations passed')

asyncio.run(test())
"
```

### Integration Tests
```bash
# Run full batch
uv run python scripts/run_batch_calculations.py

# Check results
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select, text

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT
                calculation_date,
                sector_exposure,
                hhi,
                effective_num_positions,
                top_3_concentration
            FROM portfolio_snapshots
            WHERE sector_exposure IS NOT NULL
            ORDER BY calculation_date DESC
            LIMIT 1
        '''))

        row = result.first()
        if row:
            print('Latest snapshot:')
            print(f'  Date: {row[0]}')
            print(f'  Sectors: {len(row[1])} sectors')
            print(f'  HHI: {row[2]}')
            print(f'  Effective positions: {row[3]}')
            print(f'  Top 3: {float(row[4])*100:.1f}%')

asyncio.run(check())
"
```

### Acceptance Criteria
- [ ] Sector weights sum to 100% (±5% for rounding)
- [ ] All positions have sector assigned (or marked Unclassified)
- [ ] Over/underweight calculations correct
- [ ] HHI in valid range (0-10,000)
- [ ] Effective positions ≤ total positions
- [ ] Top 3 + Top 10 concentration make sense
- [ ] Frontend displays sector exposure chart
- [ ] Frontend displays concentration metrics

---

# Phase 2: Volatility Analytics

**Duration:** Weeks 3-4 (10 days)
**Goal:** Add realized + expected volatility with HAR forecasting

## Objective

**What:** Implement position and portfolio volatility analytics with forecasting.

**Why:** Investors want to know current volatility and whether it's increasing/decreasing.

**Metrics to Calculate:**
1. **Realized Volatility** - Historical volatility over multiple windows (30d, 60d, 90d)
2. **Expected Volatility** - HAR model forecast (next 30 days)
3. **Volatility Trend** - Is volatility increasing or decreasing?
4. **Volatility Percentile** - Current volatility vs 1-year historical distribution

**Success Criteria:**
- All positions have realized volatility calculated
- HAR model produces reasonable forecasts (not negative, not > 300%)
- Volatility trend correctly identifies direction
- Portfolio volatility aggregates position volatilities correctly
- Frontend displays volatility clearly with visual indicators

---

## Section 1: Database Changes (Alembic)

### Migration 3: Add Volatility Columns to portfolio_snapshots

**File:** `backend/alembic/versions/XXXX_add_volatility_to_snapshots.py`

**Command:**
```bash
cd backend
uv run alembic revision -m "add_volatility_to_snapshots"
```

**Migration content:**

```python
"""add_volatility_to_snapshots

Revision ID: XXXX
Revises: [previous - sector/concentration migration]
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'XXXX'
down_revision = '[sector_concentration_migration_id]'
branch_labels = None
depends_on = None


def upgrade():
    # Add portfolio-level volatility columns
    op.add_column('portfolio_snapshots',
        sa.Column('realized_volatility_30d', sa.Numeric(10, 4), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('realized_volatility_60d', sa.Numeric(10, 4), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('realized_volatility_90d', sa.Numeric(10, 4), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('expected_volatility_30d', sa.Numeric(10, 4), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('volatility_trend', sa.String(20), nullable=True)
    )
    op.add_column('portfolio_snapshots',
        sa.Column('volatility_percentile', sa.Numeric(10, 4), nullable=True)
    )


def downgrade():
    op.drop_column('portfolio_snapshots', 'volatility_percentile')
    op.drop_column('portfolio_snapshots', 'volatility_trend')
    op.drop_column('portfolio_snapshots', 'expected_volatility_30d')
    op.drop_column('portfolio_snapshots', 'realized_volatility_90d')
    op.drop_column('portfolio_snapshots', 'realized_volatility_60d')
    op.drop_column('portfolio_snapshots', 'realized_volatility_30d')
```

### Migration 4: Create position_volatility Table

**File:** `backend/alembic/versions/XXXX_create_position_volatility_table.py`

**Command:**
```bash
uv run alembic revision -m "create_position_volatility_table"
```

**Migration content:**

```python
"""create_position_volatility_table

Revision ID: XXXX
Revises: [previous - volatility columns]
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = 'XXXX'
down_revision = '[volatility_columns_migration_id]'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'position_volatility',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calculation_date', sa.Date, nullable=False),

        # Realized volatility (multiple windows)
        sa.Column('realized_vol_30d', sa.Numeric(10, 4), nullable=True),
        sa.Column('realized_vol_60d', sa.Numeric(10, 4), nullable=True),
        sa.Column('realized_vol_90d', sa.Numeric(10, 4), nullable=True),

        # HAR model components
        sa.Column('vol_daily', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol_weekly', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol_monthly', sa.Numeric(10, 4), nullable=True),

        # Forecast
        sa.Column('expected_vol_30d', sa.Numeric(10, 4), nullable=True),

        # Trend analysis
        sa.Column('vol_trend', sa.String(20), nullable=True),  # 'increasing', 'decreasing', 'stable'
        sa.Column('vol_trend_strength', sa.Numeric(10, 4), nullable=True),  # 0-1 scale

        # Percentile (vs 1-year history)
        sa.Column('vol_percentile', sa.Numeric(10, 4), nullable=True),  # 0-1 scale

        # Metadata
        sa.Column('observations', sa.Integer, nullable=True),
        sa.Column('model_r_squared', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        # Foreign key
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ondelete='CASCADE'),

        # Unique constraint
        sa.UniqueConstraint('position_id', 'calculation_date', name='uq_position_volatility_date')
    )

    # Indexes for query performance
    op.create_index('ix_position_volatility_position_id', 'position_volatility', ['position_id'])
    op.create_index('ix_position_volatility_calculation_date', 'position_volatility', ['calculation_date'])


def downgrade():
    op.drop_index('ix_position_volatility_calculation_date')
    op.drop_index('ix_position_volatility_position_id')
    op.drop_table('position_volatility')
```

**Validation:**
```bash
# Run migrations
uv run alembic upgrade head

# Verify columns added
uv run python -c "
from app.database import AsyncSessionLocal
from sqlalchemy import text
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        # Check portfolio_snapshots columns
        result = await db.execute(text('''
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='portfolio_snapshots'
            AND column_name LIKE '%volatility%'
        '''))
        print('Portfolio snapshot columns:')
        for row in result:
            print(f'  {row[0]}: {row[1]}')

        # Check position_volatility table exists
        result = await db.execute(text('''
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name='position_volatility'
        '''))
        print(f'\nposition_volatility table: {\"✓ exists\" if result.scalar() else \"✗ missing\"}')

asyncio.run(check())
"
```

---

## Section 2: Calculation Scripts

### Task 1: Create volatility_analytics.py

**File:** `backend/app/calculations/volatility_analytics.py`

**Full implementation:**

```python
"""
Volatility Analytics - HAR Model Implementation
Calculates realized volatility, forecasts future volatility using HAR model.

HAR Model: Heterogeneous Autoregressive model
Forecast = β₀ + β₁*RV_daily + β₂*RV_weekly + β₃*RV_monthly

Created: 2025-10-15
Reference: Corsi (2009) "A Simple Approximate Long-Memory Model of Realized Volatility"
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

import pandas as pd
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import statsmodels.api as sm

from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.constants.factors import MIN_REGRESSION_DAYS
from app.core.logging import get_logger

logger = get_logger(__name__)

# Volatility calculation constants
VOL_WINDOW_30D = 30
VOL_WINDOW_60D = 60
VOL_WINDOW_90D = 90
MIN_VOL_DAYS = 60
ANNUALIZATION_FACTOR = np.sqrt(252)  # Trading days per year
VOL_CAP = 3.0  # 300% annualized vol cap


async def fetch_returns_for_volatility(
    db: AsyncSession,
    symbol: str,
    start_date: date,
    end_date: date
) -> pd.Series:
    """
    Fetch historical prices and calculate returns for volatility analysis.

    Args:
        db: Database session
        symbol: Symbol to fetch
        start_date: Start date for data
        end_date: End date for data

    Returns:
        Pandas Series of daily returns with date index
    """
    stmt = select(
        MarketDataCache.date,
        MarketDataCache.close
    ).where(
        and_(
            MarketDataCache.symbol == symbol.upper(),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date)

    result = await db.execute(stmt)
    records = result.all()

    if not records:
        logger.warning(f"No price data found for {symbol}")
        return pd.Series(dtype=float)

    # Convert to DataFrame
    df = pd.DataFrame([
        {'date': r.date, 'close': float(r.close)}
        for r in records
    ])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Calculate returns
    returns = df['close'].pct_change(fill_method=None).dropna()

    return returns


def calculate_realized_volatility(returns: pd.Series, window_days: int) -> float:
    """
    Calculate realized volatility over a window.

    Realized Vol = sqrt(sum of squared returns) * sqrt(252)

    Args:
        returns: Daily returns series
        window_days: Number of days to use

    Returns:
        Annualized realized volatility (decimal, e.g., 0.35 = 35%)
    """
    if len(returns) < window_days:
        return None

    # Get last N days
    recent_returns = returns.tail(window_days)

    # Realized volatility = sqrt(sum of squared returns) * annualization factor
    realized_vol = np.sqrt(np.sum(recent_returns ** 2)) * ANNUALIZATION_FACTOR / np.sqrt(window_days)

    # Cap extreme values
    realized_vol = min(realized_vol, VOL_CAP)

    return float(realized_vol)


def calculate_har_components(returns: pd.Series) -> Tuple[float, float, float]:
    """
    Calculate HAR model components (daily, weekly, monthly realized volatility).

    Args:
        returns: Full returns series

    Returns:
        Tuple of (daily_vol, weekly_vol, monthly_vol)
    """
    # Daily component: last 1 day squared return
    daily_vol = abs(returns.iloc[-1]) * ANNUALIZATION_FACTOR if len(returns) > 0 else 0

    # Weekly component: sqrt(mean of last 5 days squared returns)
    if len(returns) >= 5:
        weekly_vol = np.sqrt(np.mean(returns.tail(5) ** 2)) * ANNUALIZATION_FACTOR
    else:
        weekly_vol = daily_vol

    # Monthly component: sqrt(mean of last 22 days squared returns)
    if len(returns) >= 22:
        monthly_vol = np.sqrt(np.mean(returns.tail(22) ** 2)) * ANNUALIZATION_FACTOR
    else:
        monthly_vol = weekly_vol

    return float(daily_vol), float(weekly_vol), float(monthly_vol)


def fit_har_model(returns: pd.Series) -> Dict[str, Any]:
    """
    Fit HAR (Heterogeneous Autoregressive) model to forecast volatility.

    HAR Model:
    RV_t = β₀ + β₁*RV_daily_(t-1) + β₂*RV_weekly_(t-1) + β₃*RV_monthly_(t-1) + ε_t

    Args:
        returns: Full returns series (needs at least 90 days)

    Returns:
        {
            'forecast_30d': float,
            'r_squared': float,
            'coefficients': Dict[str, float],
            'success': bool
        }
    """
    if len(returns) < 90:
        return {
            'success': False,
            'error': f'Insufficient data: {len(returns)} days'
        }

    try:
        # Calculate rolling realized volatility (target variable)
        # Use 22-day (monthly) rolling window
        rolling_rv = returns.rolling(window=22).apply(
            lambda x: np.sqrt(np.sum(x ** 2)) * ANNUALIZATION_FACTOR / np.sqrt(22),
            raw=True
        ).dropna()

        # Calculate HAR components for each day
        daily_components = []
        weekly_components = []
        monthly_components = []

        for i in range(len(rolling_rv)):
            # Get returns up to this point
            returns_slice = returns.iloc[:len(rolling_rv.index[i])]

            if len(returns_slice) >= 22:
                # Daily: last day
                daily = abs(returns_slice.iloc[-1]) * ANNUALIZATION_FACTOR

                # Weekly: last 5 days
                if len(returns_slice) >= 5:
                    weekly = np.sqrt(np.mean(returns_slice.tail(5) ** 2)) * ANNUALIZATION_FACTOR
                else:
                    weekly = daily

                # Monthly: last 22 days
                monthly = np.sqrt(np.mean(returns_slice.tail(22) ** 2)) * ANNUALIZATION_FACTOR

                daily_components.append(daily)
                weekly_components.append(weekly)
                monthly_components.append(monthly)
            else:
                # Not enough data for this observation
                break

        # Align arrays
        min_len = min(len(rolling_rv), len(daily_components))
        y = rolling_rv.values[:min_len]
        X = pd.DataFrame({
            'daily': daily_components[:min_len],
            'weekly': weekly_components[:min_len],
            'monthly': monthly_components[:min_len]
        })

        if len(y) < 30:
            return {
                'success': False,
                'error': 'Insufficient aligned data for HAR model'
            }

        # Fit OLS regression
        X_with_const = sm.add_constant(X)
        model = sm.OLS(y, X_with_const).fit()

        # Generate forecast using most recent components
        latest_daily, latest_weekly, latest_monthly = calculate_har_components(returns)

        forecast_input = pd.DataFrame({
            'const': [1.0],
            'daily': [latest_daily],
            'weekly': [latest_weekly],
            'monthly': [latest_monthly]
        })

        forecast_30d = float(model.predict(forecast_input)[0])

        # Cap forecast
        forecast_30d = max(0, min(forecast_30d, VOL_CAP))

        return {
            'forecast_30d': forecast_30d,
            'r_squared': float(model.rsquared),
            'coefficients': {
                'intercept': float(model.params[0]),
                'daily': float(model.params[1]),
                'weekly': float(model.params[2]),
                'monthly': float(model.params[3])
            },
            'success': True
        }

    except Exception as e:
        logger.error(f"HAR model fitting error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def calculate_volatility_trend(
    vol_30d: float,
    vol_60d: float,
    vol_90d: float
) -> Tuple[str, float]:
    """
    Determine volatility trend and strength.

    Args:
        vol_30d: 30-day realized volatility
        vol_60d: 60-day realized volatility
        vol_90d: 90-day realized volatility

    Returns:
        Tuple of (trend_direction, trend_strength)
        - trend_direction: 'increasing', 'decreasing', 'stable'
        - trend_strength: 0-1 scale (0 = weak, 1 = strong)
    """
    # Calculate trend slope (linear regression)
    windows = np.array([30, 60, 90])
    vols = np.array([vol_30d, vol_60d, vol_90d])

    # Simple linear fit
    slope, _ = np.polyfit(windows, vols, 1)

    # Determine direction
    if abs(slope) < 0.001:  # Less than 0.1% change per day
        direction = 'stable'
        strength = 0.0
    elif slope > 0:
        direction = 'increasing'
        strength = min(abs(slope) * 100, 1.0)  # Scale to 0-1
    else:
        direction = 'decreasing'
        strength = min(abs(slope) * 100, 1.0)

    return direction, float(strength)


def calculate_volatility_percentile(
    current_vol: float,
    returns: pd.Series,
    lookback_days: int = 252
) -> float:
    """
    Calculate percentile of current volatility vs historical distribution.

    Args:
        current_vol: Current realized volatility (30d)
        returns: Full returns series
        lookback_days: Days to look back (default 1 year = 252 trading days)

    Returns:
        Percentile (0-1), e.g., 0.75 = 75th percentile
    """
    if len(returns) < lookback_days:
        lookback_days = len(returns)

    # Calculate rolling 30-day volatility over lookback period
    rolling_vols = []
    for i in range(30, lookback_days):
        window_returns = returns.iloc[i-30:i]
        vol = np.sqrt(np.sum(window_returns ** 2)) * ANNUALIZATION_FACTOR / np.sqrt(30)
        rolling_vols.append(vol)

    if not rolling_vols:
        return 0.5  # Default to median if not enough data

    # Calculate percentile
    percentile = np.sum(np.array(rolling_vols) <= current_vol) / len(rolling_vols)

    return float(percentile)


async def calculate_position_volatility(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate all volatility metrics for a position.

    Args:
        db: Database session
        position_id: Position UUID
        calculation_date: Date for calculation

    Returns:
        {
            'position_id': UUID,
            'realized_vol_30d': float,
            'realized_vol_60d': float,
            'realized_vol_90d': float,
            'expected_vol_30d': float,
            'vol_daily': float,
            'vol_weekly': float,
            'vol_monthly': float,
            'vol_trend': str,
            'vol_trend_strength': float,
            'vol_percentile': float,
            'observations': int,
            'model_r_squared': float,
            'success': bool
        }
    """
    logger.info(f"Calculating volatility for position {position_id}")

    try:
        # Get position
        position_stmt = select(Position).where(Position.id == position_id)
        position_result = await db.execute(position_stmt)
        position = position_result.scalar_one_or_none()

        if not position:
            return {
                'position_id': position_id,
                'success': False,
                'error': 'Position not found'
            }

        # Fetch returns (need 1 year + buffer)
        end_date = calculation_date
        start_date = end_date - timedelta(days=365 + 30)

        returns = await fetch_returns_for_volatility(
            db, position.symbol, start_date, end_date
        )

        if returns.empty or len(returns) < MIN_VOL_DAYS:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': f'Insufficient data: {len(returns)} days',
                'observations': len(returns)
            }

        # Calculate realized volatility (multiple windows)
        vol_30d = calculate_realized_volatility(returns, VOL_WINDOW_30D)
        vol_60d = calculate_realized_volatility(returns, VOL_WINDOW_60D)
        vol_90d = calculate_realized_volatility(returns, VOL_WINDOW_90D)

        if vol_30d is None:
            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'success': False,
                'error': 'Could not calculate realized volatility'
            }

        # Calculate HAR components
        vol_daily, vol_weekly, vol_monthly = calculate_har_components(returns)

        # Fit HAR model and forecast
        har_result = fit_har_model(returns)

        if not har_result['success']:
            expected_vol = vol_30d  # Fallback to current realized vol
            model_r_squared = 0.0
        else:
            expected_vol = har_result['forecast_30d']
            model_r_squared = har_result['r_squared']

        # Calculate trend
        trend_direction, trend_strength = calculate_volatility_trend(
            vol_30d, vol_60d, vol_90d
        )

        # Calculate percentile
        percentile = calculate_volatility_percentile(vol_30d, returns)

        result = {
            'position_id': position_id,
            'symbol': position.symbol,
            'realized_vol_30d': vol_30d,
            'realized_vol_60d': vol_60d,
            'realized_vol_90d': vol_90d,
            'expected_vol_30d': expected_vol,
            'vol_daily': vol_daily,
            'vol_weekly': vol_weekly,
            'vol_monthly': vol_monthly,
            'vol_trend': trend_direction,
            'vol_trend_strength': trend_strength,
            'vol_percentile': percentile,
            'observations': len(returns),
            'model_r_squared': model_r_squared,
            'calculation_date': calculation_date,
            'success': True
        }

        logger.info(
            f"Volatility calculated for {position.symbol}: "
            f"30d={vol_30d:.2%}, expected={expected_vol:.2%}, trend={trend_direction}"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating volatility for position {position_id}: {e}")
        return {
            'position_id': position_id,
            'success': False,
            'error': str(e)
        }


async def calculate_portfolio_volatility(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate portfolio-level volatility as equity-weighted average.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation

    Returns:
        {
            'portfolio_id': UUID,
            'realized_vol_30d': float,
            'realized_vol_60d': float,
            'realized_vol_90d': float,
            'expected_vol_30d': float,
            'vol_trend': str,
            'vol_percentile': float,
            'positions_count': int,
            'success': bool
        }
    """
    logger.info(f"Calculating portfolio volatility for {portfolio_id}")

    try:
        # Get portfolio
        from app.models.users import Portfolio as PortfolioModel
        portfolio_stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'Portfolio not found'
            }

        portfolio_equity = float(portfolio.equity_balance)

        # Get active positions
        positions_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        positions_result = await db.execute(positions_stmt)
        positions = positions_result.scalars().all()

        if not positions:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No active positions'
            }

        # Calculate volatility for each position
        position_vols = {}
        position_market_values = {}

        for position in positions:
            vol_result = await calculate_position_volatility(
                db, position.id, calculation_date
            )

            if not vol_result['success']:
                logger.warning(
                    f"Could not calculate volatility for {position.symbol}: "
                    f"{vol_result.get('error', 'Unknown error')}"
                )
                continue

            # Get position market value
            from app.calculations.factor_utils import get_position_market_value
            market_value = float(get_position_market_value(position, recalculate=True))

            position_vols[position.id] = vol_result
            position_market_values[position.id] = market_value

        if not position_vols:
            return {
                'portfolio_id': portfolio_id,
                'success': False,
                'error': 'No position volatilities could be calculated'
            }

        # Calculate equity-weighted portfolio volatility
        total_weighted_vol_30d = 0.0
        total_weighted_vol_60d = 0.0
        total_weighted_vol_90d = 0.0
        total_weighted_expected = 0.0
        total_weighted_percentile = 0.0

        for pos_id, vol_data in position_vols.items():
            market_value = position_market_values[pos_id]
            weight = market_value / portfolio_equity

            total_weighted_vol_30d += vol_data['realized_vol_30d'] * weight
            total_weighted_vol_60d += vol_data['realized_vol_60d'] * weight
            total_weighted_vol_90d += vol_data['realized_vol_90d'] * weight
            total_weighted_expected += vol_data['expected_vol_30d'] * weight
            total_weighted_percentile += vol_data['vol_percentile'] * weight

        # Determine portfolio trend
        trend_direction, trend_strength = calculate_volatility_trend(
            total_weighted_vol_30d,
            total_weighted_vol_60d,
            total_weighted_vol_90d
        )

        result = {
            'portfolio_id': portfolio_id,
            'realized_vol_30d': total_weighted_vol_30d,
            'realized_vol_60d': total_weighted_vol_60d,
            'realized_vol_90d': total_weighted_vol_90d,
            'expected_vol_30d': total_weighted_expected,
            'vol_trend': trend_direction,
            'vol_percentile': total_weighted_percentile,
            'positions_count': len(position_vols),
            'calculation_date': calculation_date,
            'success': True
        }

        logger.info(
            f"Portfolio volatility: 30d={total_weighted_vol_30d:.2%}, "
            f"expected={total_weighted_expected:.2%}, trend={trend_direction}"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating portfolio volatility: {e}")
        return {
            'portfolio_id': portfolio_id,
            'success': False,
            'error': str(e)
        }
```

**Validation:**
```bash
cd backend

# Test import
uv run python -c "from app.calculations.volatility_analytics import calculate_position_volatility; print('✓ Import successful')"

# Test on NVDA position
uv run python -c "
import asyncio
from datetime import date
from uuid import UUID
from app.database import AsyncSessionLocal
from app.calculations.volatility_analytics import calculate_position_volatility

async def test():
    # Replace with actual NVDA position ID
    nvda_position_id = UUID('your-nvda-position-uuid-here')

    async with AsyncSessionLocal() as db:
        result = await calculate_position_volatility(
            db, nvda_position_id, date.today()
        )
        print(f'30d Vol: {result.get(\"realized_vol_30d\", 0):.2%}')
        print(f'Expected: {result.get(\"expected_vol_30d\", 0):.2%}')
        print(f'Trend: {result.get(\"vol_trend\")}')
        print(f'Percentile: {result.get(\"vol_percentile\", 0):.0%}')

asyncio.run(test())
"
```

---

## Section 3: API Changes

### No New API Endpoints Required

Volatility data is stored in `portfolio_snapshots` and accessed via existing `/api/v1/data/portfolio/{id}/complete` endpoint.

**Modified response:**
```json
{
  "snapshot": {
    ...existing fields...,
    "realized_volatility_30d": 0.28,
    "realized_volatility_60d": 0.32,
    "realized_volatility_90d": 0.35,
    "expected_volatility_30d": 0.30,
    "volatility_trend": "decreasing",
    "volatility_percentile": 0.65
  }
}
```

---

## Section 4: Frontend Changes

### Task 1: Create Volatility Display Component

**File:** `frontend/src/components/portfolio/VolatilityMetrics.tsx`

**Create new file:**

```typescript
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface VolatilityMetricsProps {
  realizedVol30d: number;
  realizedVol60d: number;
  realizedVol90d: number;
  expectedVol30d: number;
  volTrend: 'increasing' | 'decreasing' | 'stable';
  volPercentile: number;
}

export function VolatilityMetrics({
  realizedVol30d,
  realizedVol60d,
  realizedVol90d,
  expectedVol30d,
  volTrend,
  volPercentile,
}: VolatilityMetricsProps) {
  const getTrendIcon = () => {
    if (volTrend === 'increasing') return <TrendingUp className="h-5 w-5 text-red-600" />;
    if (volTrend === 'decreasing') return <TrendingDown className="h-5 w-5 text-green-600" />;
    return <Minus className="h-5 w-5 text-gray-600" />;
  };

  const getTrendColor = () => {
    if (volTrend === 'increasing') return 'text-red-600';
    if (volTrend === 'decreasing') return 'text-green-600';
    return 'text-gray-600';
  };

  const getVolatilityLevel = (vol: number): string => {
    if (vol < 0.15) return 'Very Low';
    if (vol < 0.25) return 'Low';
    if (vol < 0.35) return 'Moderate';
    if (vol < 0.50) return 'High';
    return 'Very High';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Volatility Analysis
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p>Historical and forecasted portfolio volatility.</p>
                <p className="text-xs">Lower = more stable returns</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Current Volatility */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium">Current (30-day)</span>
              <span className="text-2xl font-bold">
                {(realizedVol30d * 100).toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {getVolatilityLevel(realizedVol30d)} volatility
            </p>
          </div>

          {/* Historical Windows */}
          <div className="grid grid-cols-2 gap-4 py-2 border-t border-b">
            <div>
              <p className="text-xs text-muted-foreground">60-day</p>
              <p className="text-sm font-medium">
                {(realizedVol60d * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">90-day</p>
              <p className="text-sm font-medium">
                {(realizedVol90d * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Expected Volatility */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium">Expected (30-day forecast)</span>
              <span className="text-lg font-semibold">
                {(expectedVol30d * 100).toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              HAR model forecast
            </p>
          </div>

          {/* Trend */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              {getTrendIcon()}
              <span className={`text-sm font-medium ${getTrendColor()}`}>
                Volatility {volTrend}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
              {volPercentile >= 0.75 && 'Well above historical'}
              {volPercentile >= 0.5 && volPercentile < 0.75 && 'Above historical'}
              {volPercentile >= 0.25 && volPercentile < 0.5 && 'Near historical average'}
              {volPercentile < 0.25 && 'Below historical'}
            </span>
          </div>

          {/* Percentile Bar */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span>Volatility Percentile</span>
              <span className="font-medium">{(volPercentile * 100).toFixed(0)}th</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  volPercentile >= 0.75
                    ? 'bg-red-500'
                    : volPercentile >= 0.5
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${volPercentile * 100}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              vs. 1-year historical distribution
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Task 2: Update Portfolio Page

**File:** `frontend/app/portfolio/page.tsx`

**Add** volatility component:

```typescript
// Add import
import { VolatilityMetrics } from '@/components/portfolio/VolatilityMetrics';

// In the page component, after existing metrics:
<div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
  {snapshot?.realized_volatility_30d && (
    <VolatilityMetrics
      realizedVol30d={snapshot.realized_volatility_30d}
      realizedVol60d={snapshot.realized_volatility_60d}
      realizedVol90d={snapshot.realized_volatility_90d}
      expectedVol30d={snapshot.expected_volatility_30d}
      volTrend={snapshot.volatility_trend}
      volPercentile={snapshot.volatility_percentile}
    />
  )}
</div>
```

---

## Section 5: Integration & Testing

### Task 1: Update Batch Orchestrator

**File:** `backend/app/batch/batch_orchestrator_v2.py`

**Add** after sector/concentration calculation:

```python
# Step 4: Calculate volatility
logger.info("Step 4: Calculating volatility analytics")
from app.calculations.volatility_analytics import calculate_portfolio_volatility

volatility_result = await calculate_portfolio_volatility(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calculation_date
)

results['volatility'] = volatility_result

if volatility_result['success']:
    logger.info(
        f"Volatility: 30d={volatility_result['realized_vol_30d']:.2%}, "
        f"expected={volatility_result['expected_vol_30d']:.2%}"
    )
else:
    logger.warning(f"Volatility calculation failed: {volatility_result.get('error')}")
```

### Task 2: Update Snapshot Creation

**File:** `backend/app/calculations/snapshots.py`

**Add** volatility fields:

```python
# Get volatility data
vol_data = batch_results.get('volatility', {})

snapshot = PortfolioSnapshot(
    ...existing fields...,
    realized_volatility_30d=Decimal(str(vol_data.get('realized_vol_30d', 0))) if vol_data.get('success') else None,
    realized_volatility_60d=Decimal(str(vol_data.get('realized_vol_60d', 0))) if vol_data.get('success') else None,
    realized_volatility_90d=Decimal(str(vol_data.get('realized_vol_90d', 0))) if vol_data.get('success') else None,
    expected_volatility_30d=Decimal(str(vol_data.get('expected_vol_30d', 0))) if vol_data.get('success') else None,
    volatility_trend=vol_data.get('vol_trend') if vol_data.get('success') else None,
    volatility_percentile=Decimal(str(vol_data.get('vol_percentile', 0))) if vol_data.get('success') else None
)
```

### Task 3: Create Position Volatility Model

**File:** `backend/app/models/volatility.py`

**Create new file:**

```python
"""
Position Volatility Model
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class PositionVolatility(Base):
    """Position-level volatility analytics"""

    __tablename__ = "position_volatility"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id = Column(PG_UUID(as_uuid=True), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    calculation_date = Column(Date, nullable=False)

    # Realized volatility (multiple windows)
    realized_vol_30d = Column(Numeric(10, 4))
    realized_vol_60d = Column(Numeric(10, 4))
    realized_vol_90d = Column(Numeric(10, 4))

    # HAR model components
    vol_daily = Column(Numeric(10, 4))
    vol_weekly = Column(Numeric(10, 4))
    vol_monthly = Column(Numeric(10, 4))

    # Forecast
    expected_vol_30d = Column(Numeric(10, 4))

    # Trend analysis
    vol_trend = Column(String(20))  # 'increasing', 'decreasing', 'stable'
    vol_trend_strength = Column(Numeric(10, 4))  # 0-1 scale

    # Percentile (vs 1-year history)
    vol_percentile = Column(Numeric(10, 4))  # 0-1 scale

    # Metadata
    observations = Column(Integer)
    model_r_squared = Column(Numeric(10, 4))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    position = relationship("Position", back_populates="volatility_records")


# Add to Position model in app/models/positions.py:
# volatility_records = relationship("PositionVolatility", back_populates="position")
```

---

## Validation Checklist

### Unit Tests
```bash
# Test volatility calculation
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.calculations.volatility_analytics import calculate_portfolio_volatility
from sqlalchemy import select
from app.models.users import Portfolio
from datetime import date

async def test():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one()

        vol_result = await calculate_portfolio_volatility(
            db, portfolio.id, date.today()
        )

        print(f'30d Vol: {vol_result.get(\"realized_vol_30d\", 0):.2%}')
        print(f'Expected: {vol_result.get(\"expected_vol_30d\", 0):.2%}')
        print(f'Trend: {vol_result.get(\"vol_trend\")}')

        # Validate
        assert 0 < vol_result['realized_vol_30d'] < 3.0, 'Vol out of range'
        assert vol_result['vol_trend'] in ['increasing', 'decreasing', 'stable'], 'Invalid trend'
        print('✓ All validations passed')

asyncio.run(test())
"
```

### Integration Tests
```bash
# Run full batch with volatility
uv run python scripts/run_batch_calculations.py

# Check results
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT
                calculation_date,
                realized_volatility_30d,
                expected_volatility_30d,
                volatility_trend,
                volatility_percentile
            FROM portfolio_snapshots
            WHERE realized_volatility_30d IS NOT NULL
            ORDER BY calculation_date DESC
            LIMIT 1
        '''))

        row = result.first()
        if row:
            print('Latest volatility snapshot:')
            print(f'  Date: {row[0]}')
            print(f'  30d Vol: {float(row[1]):.2%}')
            print(f'  Expected: {float(row[2]):.2%}')
            print(f'  Trend: {row[3]}')
            print(f'  Percentile: {float(row[4]):.0%}')

asyncio.run(check())
"
```

### Acceptance Criteria
- [ ] All positions with sufficient data have volatility calculated
- [ ] HAR model produces reasonable forecasts (0% - 300%)
- [ ] Volatility trend correctly identifies direction
- [ ] Percentile calculation produces 0-100% values
- [ ] Portfolio volatility is equity-weighted correctly
- [ ] Frontend displays volatility with visual indicators
- [ ] Volatility component shows trend icon correctly

---

## Key Features of This Execution Plan

**1. Mechanical Steps**
- Every task has exact file paths
- Every function has full implementation
- Every validation has copy-paste commands
- Over 600 lines of complete Python code ready to copy

**2. No Decisions Required**
- All architecture decisions already made
- All approach questions answered
- Agent just follows steps
- HAR model implementation fully specified

**3. Testable at Every Stage**
- Unit tests after each script
- Integration tests after each phase
- Acceptance criteria clearly defined
- Validation commands for every migration

**4. Rollback Procedures**
- Alembic downgrade commands included
- Each migration is reversible
- Clear error handling in all calculation functions

**5. Complete Context**
- Links to planning doc (`RiskMetricsPlanning.md`) for "why"
- Execution doc is pure "how"
- Can be executed independently by any AI agent
- 4 sections per phase: Objective, Alembic, Scripts, Frontend

---

# Testing & Validation

## Phase 0 Testing Summary

After Phase 0 implementation, verify:
1. Market beta for NVDA = 1.7-2.2 (not -3!)
2. All high-beta stocks have R² > 0.3
3. No VIF warnings (single factor)
4. Stress testing uses new beta and works
5. Frontend displays beta with tooltip

## Phase 1 Testing Summary

After Phase 1 implementation, verify:
1. Sector weights sum to 100% (±5%)
2. All positions have sectors assigned
3. Over/underweight calculations correct
4. HHI in valid range (0-10,000)
5. Effective positions ≤ total positions
6. Frontend shows sector charts and concentration

## Phase 2 Testing Summary

After Phase 2 implementation, verify:
1. All positions have volatility calculated
2. HAR forecasts in range (0-300%)
3. Volatility trend identifies direction correctly
4. Percentile calculations produce 0-100%
5. Portfolio volatility is equity-weighted
6. Frontend shows volatility with trend indicators

---

# Implementation Roadmap

## Week 1: Phase 0 - Fix Market Beta (5 days)
**Days 1-2:** Database migrations + market_beta.py script
**Days 3-4:** Integration (batch orchestrator, snapshots, stress testing)
**Day 5:** Frontend display + full testing

## Week 2: Phase 1 - Sector & Concentration (5 days)
**Days 1-2:** Database migrations + sector_analysis.py script
**Days 3-4:** Frontend components (SectorExposure, ConcentrationMetrics)
**Day 5:** Integration + full testing

## Weeks 3-4: Phase 2 - Volatility Analytics (10 days)
**Days 1-3:** Database migrations + volatility_analytics.py (600 lines)
**Days 4-6:** HAR model testing and refinement
**Days 7-8:** Frontend VolatilityMetrics component
**Days 9-10:** Integration, testing, and performance optimization

---

# File Summary

This execution document includes complete implementations for:

**Alembic Migrations:** 4 migrations
- Phase 0: 1 migration (market beta columns)
- Phase 1: 1 migration (sector/concentration columns)
- Phase 2: 2 migrations (volatility columns + position_volatility table)

**Calculation Scripts:** 3 major scripts (~1,500 total lines)
- `backend/app/calculations/market_beta.py` (~500 lines)
- `backend/app/calculations/sector_analysis.py` (~400 lines)
- `backend/app/calculations/volatility_analytics.py` (~600 lines)

**Frontend Components:** 4 new components
- `PortfolioMetrics.tsx` (market beta display)
- `SectorExposure.tsx` (sector comparison chart)
- `ConcentrationMetrics.tsx` (HHI and concentration)
- `VolatilityMetrics.tsx` (volatility with HAR forecast)

**Integration Updates:** 3 files
- `batch_orchestrator_v2.py` (add new calculation steps)
- `snapshots.py` (store new metrics)
- `market_risk.py` (use new market beta)

---

# Success Criteria for Complete Implementation

## Phase 0: Market Beta ✅
- [ ] NVDA beta = 1.7-2.2 (validated against market sources)
- [ ] All positions have reasonable betas
- [ ] R² > 0.3 for high-beta stocks
- [ ] Stress testing produces sensible results
- [ ] Frontend displays beta with clear explanation

## Phase 1: Sector & Concentration ✅
- [ ] All positions assigned to sectors
- [ ] Sector weights sum to ~100%
- [ ] Over/underweight vs S&P 500 calculated correctly
- [ ] HHI matches manual calculation
- [ ] Frontend shows sector exposure chart
- [ ] Frontend displays concentration metrics

## Phase 2: Volatility Analytics ✅
- [ ] Realized volatility calculated for all positions
- [ ] HAR model produces forecasts (0-300% range)
- [ ] Volatility trend correctly identifies direction
- [ ] Percentile calculation validated
- [ ] Portfolio volatility aggregates correctly
- [ ] Frontend shows volatility with visual indicators
- [ ] Trend icons display correctly

## Overall System ✅
- [ ] All batch calculations complete without errors
- [ ] Database snapshots contain all new metrics
- [ ] Frontend renders all new components
- [ ] User can see: beta, sectors, concentration, volatility
- [ ] Documentation updated with new features
- [ ] Performance acceptable (batch < 5 minutes per portfolio)

---

# Deployment Checklist

## Before Deploying to Production

1. **Database Backups**
   - [ ] Backup production database
   - [ ] Test restore procedure

2. **Migrations**
   - [ ] Test all 4 migrations on staging
   - [ ] Verify rollback procedures work
   - [ ] Check migration performance (should be < 1 minute each)

3. **Data Validation**
   - [ ] Run batch calculations on staging
   - [ ] Validate all metrics against known values
   - [ ] Check for null values in snapshots

4. **Frontend Testing**
   - [ ] Test all components in staging
   - [ ] Verify responsive design
   - [ ] Check tooltips and interactions

5. **Performance**
   - [ ] Measure batch processing time
   - [ ] Check database query performance
   - [ ] Monitor memory usage

6. **Documentation**
   - [ ] Update API documentation
   - [ ] Update user-facing documentation
   - [ ] Document any known issues

---

# Troubleshooting Guide

## Issue: Market beta calculations failing

**Symptoms:** Beta = 0 or null for all positions

**Debugging:**
```bash
# Check if SPY data exists
uv run python -c "
from app.models.market_data import MarketDataCache
from app.database import AsyncSessionLocal
from sqlalchemy import select, func
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count(MarketDataCache.id))
            .where(MarketDataCache.symbol == 'SPY')
        )
        print(f'SPY records: {result.scalar()}')

asyncio.run(check())
"
```

**Solutions:**
1. Verify SPY market data exists in database
2. Check date range has sufficient overlap
3. Verify MIN_REGRESSION_DAYS is not too high

## Issue: Sector exposure not summing to 100%

**Symptoms:** Sector weights sum to < 95% or > 105%

**Debugging:**
```bash
# Check for unclassified positions
uv run python -c "
from app.calculations.sector_analysis import calculate_sector_exposure
from app.database import AsyncSessionLocal
from uuid import UUID
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        portfolio_id = UUID('your-portfolio-id')
        result = await calculate_sector_exposure(db, portfolio_id)

        if 'unclassified_positions' in result:
            print(f'Unclassified: {result[\"unclassified_positions\"]}')

asyncio.run(check())
"
```

**Solutions:**
1. Verify all positions have sector assigned in market_data_cache
2. Check for missing market value calculations
3. Verify position_market_value calculation is correct

## Issue: HAR model not converging

**Symptoms:** expected_volatility_30d = null or unreasonably high

**Debugging:**
```bash
# Check returns data quality
uv run python -c "
from app.calculations.volatility_analytics import fetch_returns_for_volatility
from app.database import AsyncSessionLocal
from datetime import date, timedelta
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        symbol = 'NVDA'
        end_date = date.today()
        start_date = end_date - timedelta(days=400)

        returns = await fetch_returns_for_volatility(db, symbol, start_date, end_date)
        print(f'Returns available: {len(returns)} days')
        print(f'Returns range: {returns.min():.4f} to {returns.max():.4f}')

asyncio.run(check())
"
```

**Solutions:**
1. Verify at least 90 days of returns data
2. Check for extreme outliers (> 50% daily return)
3. Ensure price data doesn't have gaps
4. Try fallback to realized volatility if HAR fails

---

**Document Version:** 1.0 (Complete)
**Last Updated:** 2025-10-15
**Status:** ✅ Ready for Execution (All 3 Phases Complete)
**Owner:** Development Team
**Companion Doc:** `RiskMetricsPlanning.md` for decision context

---

**Total Implementation Effort:**
- **Lines of Code:** ~1,500 (3 calculation scripts + 4 frontend components)
- **Database Changes:** 4 Alembic migrations
- **Timeline:** 4 weeks (20 working days)
- **Complexity:** Medium-High (HAR model, multicollinearity fix, sector mapping)

**Dependencies:**
- pandas, numpy, statsmodels (already in requirements)
- Market data (SPY prices, position prices, 1 year history)
- Existing batch orchestrator framework

**Risk Assessment:**
- **Low Risk:** Market beta fix (straightforward OLS regression)
- **Low Risk:** Sector analysis (simple aggregation)
- **Medium Risk:** HAR model (complex, needs careful validation)

**Rollback Plan:**
- Each migration has downgrade function
- All calculations gracefully degrade if data unavailable
- Frontend components hide if data missing
- Can roll back one phase at a time

---

# Next Steps

1. **Review with stakeholders** - Confirm approach and timeline
2. **Set up development environment** - Ensure all dependencies installed
3. **Begin Phase 0 implementation** - Start with market beta fix
4. **Progressive testing** - Validate each phase before moving to next
5. **Deploy incrementally** - Consider phased rollout (0 → 1 → 2)

**Ready to begin implementation!** 🚀
