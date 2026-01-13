#!/usr/bin/env python
"""
Capture Current Baseline for V2 Batch Validation

This script captures the current calculated values (from V1 or existing batch)
for the 3 demo portfolios for a date range. The baseline is saved to JSON
for later comparison after re-running V2 batch calculations.

Usage:
    python scripts/validation/capture_current_baseline.py

Output:
    PlanningDocs/baseline_validation_2026-01-01_to_2026-01-12.json
"""
import sys
import asyncio
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

# CRITICAL: Windows + asyncpg compatibility fix - MUST be before any async imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Railway DATABASE_URL (convert to asyncpg if needed)
DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

# Date range for validation
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 1, 12)

# Demo user emails
DEMO_EMAILS = [
    "demo_individual@sigmasight.com",
    "demo_hnw@sigmasight.com",
    "demo_hedgefundstyle@sigmasight.com",
]

# Output path
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "PlanningDocs"


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, UUID, date, and datetime types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


async def get_demo_portfolio_ids(session: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """Get portfolio IDs for the 3 demo users."""
    from app.models.users import User, Portfolio

    portfolios = {}

    for email in DEMO_EMAILS:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"  [WARN] User not found: {email}")
            continue

        # Get the user's portfolio(s)
        result = await session.execute(
            select(Portfolio).where(
                and_(
                    Portfolio.user_id == user.id,
                    Portfolio.deleted_at.is_(None)
                )
            )
        )
        user_portfolios = result.scalars().all()

        for portfolio in user_portfolios:
            portfolios[str(portfolio.id)] = {
                "id": str(portfolio.id),
                "name": portfolio.name,
                "user_email": email,
                "user_id": str(user.id),
            }
            print(f"  Found portfolio: {portfolio.name} ({portfolio.id})")

    return portfolios


async def capture_portfolio_snapshots(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    """Capture all portfolio_snapshots for the date range."""
    from app.models.snapshots import PortfolioSnapshot

    result = await session.execute(
        select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                PortfolioSnapshot.snapshot_date >= start_date,
                PortfolioSnapshot.snapshot_date <= end_date,
            )
        ).order_by(PortfolioSnapshot.portfolio_id, PortfolioSnapshot.snapshot_date)
    )
    snapshots = result.scalars().all()

    captured = []
    for s in snapshots:
        captured.append({
            "id": str(s.id),
            "portfolio_id": str(s.portfolio_id),
            "snapshot_date": s.snapshot_date.isoformat(),
            "net_asset_value": s.net_asset_value,
            "cash_value": s.cash_value,
            "long_value": s.long_value,
            "short_value": s.short_value,
            "gross_exposure": s.gross_exposure,
            "net_exposure": s.net_exposure,
            "daily_pnl": s.daily_pnl,
            "daily_return": s.daily_return,
            "cumulative_pnl": s.cumulative_pnl,
            "daily_realized_pnl": s.daily_realized_pnl,
            "cumulative_realized_pnl": s.cumulative_realized_pnl,
            "daily_capital_flow": s.daily_capital_flow,
            "cumulative_capital_flow": s.cumulative_capital_flow,
            "portfolio_delta": s.portfolio_delta,
            "portfolio_gamma": s.portfolio_gamma,
            "portfolio_theta": s.portfolio_theta,
            "portfolio_vega": s.portfolio_vega,
            "num_positions": s.num_positions,
            "num_long_positions": s.num_long_positions,
            "num_short_positions": s.num_short_positions,
            "equity_balance": s.equity_balance,
            "realized_volatility_21d": s.realized_volatility_21d,
            "realized_volatility_63d": s.realized_volatility_63d,
            "expected_volatility_21d": s.expected_volatility_21d,
            "volatility_trend": s.volatility_trend,
            "volatility_percentile": s.volatility_percentile,
            "beta_calculated_90d": s.beta_calculated_90d,
            "beta_calculated_90d_r_squared": s.beta_calculated_90d_r_squared,
            "beta_calculated_90d_observations": s.beta_calculated_90d_observations,
            "beta_provider_1y": s.beta_provider_1y,
            "beta_portfolio_regression": s.beta_portfolio_regression,
            "sector_exposure": s.sector_exposure,
            "hhi": s.hhi,
            "effective_num_positions": s.effective_num_positions,
            "top_3_concentration": s.top_3_concentration,
            "top_10_concentration": s.top_10_concentration,
            "target_price_return_eoy": s.target_price_return_eoy,
            "target_price_return_next_year": s.target_price_return_next_year,
            "target_price_downside_return": s.target_price_downside_return,
            "target_price_upside_eoy_dollars": s.target_price_upside_eoy_dollars,
            "target_price_upside_next_year_dollars": s.target_price_upside_next_year_dollars,
            "target_price_downside_dollars": s.target_price_downside_dollars,
            "target_price_coverage_pct": s.target_price_coverage_pct,
            "target_price_positions_count": s.target_price_positions_count,
            "target_price_total_positions": s.target_price_total_positions,
            "is_complete": s.is_complete,
        })

    return captured


async def capture_symbol_factor_exposures(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    """Capture symbol_factor_exposures for symbols in the demo portfolios."""
    from app.models.symbol_analytics import SymbolFactorExposure
    from app.models.positions import Position

    # First get all symbols in the demo portfolios
    result = await session.execute(
        select(Position.symbol).where(
            and_(
                Position.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                Position.exit_date.is_(None),
            )
        ).distinct()
    )
    symbols = [row[0].upper() for row in result.fetchall() if row[0]]
    print(f"  Found {len(symbols)} symbols in demo portfolios")

    if not symbols:
        return []

    # Get factor exposures for these symbols
    result = await session.execute(
        select(SymbolFactorExposure).where(
            and_(
                SymbolFactorExposure.symbol.in_(symbols),
                SymbolFactorExposure.calculation_date >= start_date,
                SymbolFactorExposure.calculation_date <= end_date,
            )
        ).order_by(SymbolFactorExposure.symbol, SymbolFactorExposure.calculation_date)
    )
    exposures = result.scalars().all()

    captured = []
    for e in exposures:
        captured.append({
            "id": str(e.id),
            "symbol": e.symbol,
            "factor_id": str(e.factor_id) if e.factor_id else None,
            "beta_value": e.beta_value,
            "r_squared": e.r_squared,
            "observations": e.observations,
            "quality_flag": e.quality_flag,
            "calculation_date": e.calculation_date.isoformat() if e.calculation_date else None,
        })

    return captured


async def capture_factor_exposures(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    """Capture portfolio-level factor_exposures."""
    from app.models.market_data import FactorExposure

    result = await session.execute(
        select(FactorExposure).where(
            and_(
                FactorExposure.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                FactorExposure.calculation_date >= start_date,
                FactorExposure.calculation_date <= end_date,
            )
        ).order_by(FactorExposure.portfolio_id, FactorExposure.calculation_date)
    )
    exposures = result.scalars().all()

    captured = []
    for e in exposures:
        captured.append({
            "id": str(e.id),
            "portfolio_id": str(e.portfolio_id),
            "factor_id": str(e.factor_id) if e.factor_id else None,
            "exposure_value": e.exposure_value,
            "exposure_dollar": e.exposure_dollar,
            "calculation_date": e.calculation_date.isoformat() if e.calculation_date else None,
        })

    return captured


async def capture_correlation_data(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> Dict[str, List[Dict[str, Any]]]:
    """Capture correlation_calculations and pairwise_correlations."""
    from app.models.correlations import CorrelationCalculation, PairwiseCorrelation

    # Get correlation calculations (calculation_date is DateTime, need to filter by date part)
    result = await session.execute(
        select(CorrelationCalculation).where(
            and_(
                CorrelationCalculation.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
            )
        ).order_by(CorrelationCalculation.portfolio_id, CorrelationCalculation.calculation_date)
    )
    calculations = result.scalars().all()

    # Filter by date range (since calculation_date is DateTime)
    calc_captured = []
    calc_ids = []
    for c in calculations:
        calc_date = c.calculation_date.date() if c.calculation_date else None
        if calc_date and start_date <= calc_date <= end_date:
            calc_ids.append(c.id)
            calc_captured.append({
                "id": str(c.id),
                "portfolio_id": str(c.portfolio_id),
                "calculation_date": c.calculation_date.isoformat() if c.calculation_date else None,
                "duration_days": c.duration_days,
                "overall_correlation": c.overall_correlation,
                "correlation_concentration_score": c.correlation_concentration_score,
                "effective_positions": c.effective_positions,
                "data_quality": c.data_quality,
                "positions_included": c.positions_included,
                "positions_excluded": c.positions_excluded,
            })

    # Get pairwise correlations
    pair_captured = []
    if calc_ids:
        result = await session.execute(
            select(PairwiseCorrelation).where(
                PairwiseCorrelation.correlation_calculation_id.in_(calc_ids)
            )
        )
        pairs = result.scalars().all()

        for p in pairs:
            pair_captured.append({
                "id": str(p.id),
                "correlation_calculation_id": str(p.correlation_calculation_id),
                "symbol_1": p.symbol_1,
                "symbol_2": p.symbol_2,
                "correlation_value": p.correlation_value,
                "data_points": p.data_points,
            })

    return {
        "correlation_calculations": calc_captured,
        "pairwise_correlations": pair_captured,
    }


async def capture_stress_test_results(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    """Capture stress_test_results for the demo portfolios."""
    from app.models.market_data import StressTestResult

    result = await session.execute(
        select(StressTestResult).where(
            and_(
                StressTestResult.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                StressTestResult.calculation_date >= start_date,
                StressTestResult.calculation_date <= end_date,
            )
        ).order_by(StressTestResult.portfolio_id, StressTestResult.calculation_date)
    )
    results = result.scalars().all()

    captured = []
    for r in results:
        captured.append({
            "id": str(r.id),
            "portfolio_id": str(r.portfolio_id),
            "scenario_id": str(r.scenario_id) if r.scenario_id else None,
            "calculation_date": r.calculation_date.isoformat() if r.calculation_date else None,
            "direct_pnl": r.direct_pnl,
            "correlated_pnl": r.correlated_pnl,
            "correlation_effect": r.correlation_effect,
            "factor_impacts": r.factor_impacts,
        })

    return captured


async def main():
    """Main entry point."""
    print("=" * 70)
    print("CAPTURE CURRENT BASELINE FOR V2 BATCH VALIDATION")
    print("=" * 70)
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    baseline = {
        "metadata": {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(),
            "description": "Baseline data captured before V2 batch recalculation",
        },
        "portfolios": {},
        "portfolio_snapshots": [],
        "symbol_factor_exposures": [],
        "factor_exposures": [],
        "correlation_calculations": [],
        "pairwise_correlations": [],
        "stress_test_results": [],
    }

    async with async_session() as session:
        # Step 1: Get demo portfolio IDs
        print("Step 1: Finding demo portfolios...")
        portfolios = await get_demo_portfolio_ids(session)
        baseline["portfolios"] = portfolios
        portfolio_ids = list(portfolios.keys())
        print(f"  Found {len(portfolio_ids)} portfolios")
        print()

        if not portfolio_ids:
            print("[ERROR] No demo portfolios found!")
            return

        # Step 2: Capture portfolio_snapshots
        print("Step 2: Capturing portfolio_snapshots...")
        snapshots = await capture_portfolio_snapshots(session, portfolio_ids, START_DATE, END_DATE)
        baseline["portfolio_snapshots"] = snapshots
        print(f"  Captured {len(snapshots)} snapshots")
        print()

        # Step 3: Capture symbol_factor_exposures
        print("Step 3: Capturing symbol_factor_exposures...")
        symbol_factors = await capture_symbol_factor_exposures(session, portfolio_ids, START_DATE, END_DATE)
        baseline["symbol_factor_exposures"] = symbol_factors
        print(f"  Captured {len(symbol_factors)} symbol factor exposures")
        print()

        # Step 4: Capture factor_exposures (portfolio-level)
        print("Step 4: Capturing factor_exposures (portfolio-level)...")
        factors = await capture_factor_exposures(session, portfolio_ids, START_DATE, END_DATE)
        baseline["factor_exposures"] = factors
        print(f"  Captured {len(factors)} portfolio factor exposures")
        print()

        # Step 5: Capture correlation data
        print("Step 5: Capturing correlation data...")
        corr_data = await capture_correlation_data(session, portfolio_ids, START_DATE, END_DATE)
        baseline["correlation_calculations"] = corr_data["correlation_calculations"]
        baseline["pairwise_correlations"] = corr_data["pairwise_correlations"]
        print(f"  Captured {len(corr_data['correlation_calculations'])} correlation calculations")
        print(f"  Captured {len(corr_data['pairwise_correlations'])} pairwise correlations")
        print()

        # Step 6: Capture stress test results
        print("Step 6: Capturing stress_test_results...")
        stress = await capture_stress_test_results(session, portfolio_ids, START_DATE, END_DATE)
        baseline["stress_test_results"] = stress
        print(f"  Captured {len(stress)} stress test results")
        print()

    # Save baseline to JSON
    output_file = OUTPUT_DIR / f"baseline_validation_{START_DATE}_to_{END_DATE}.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(baseline, f, cls=DecimalEncoder, indent=2)

    print("=" * 70)
    print("BASELINE CAPTURE COMPLETE")
    print("=" * 70)
    print(f"Output file: {output_file}")
    print()
    print("Summary:")
    print(f"  Portfolios: {len(portfolio_ids)}")
    print(f"  Snapshots: {len(baseline['portfolio_snapshots'])}")
    print(f"  Symbol Factor Exposures: {len(baseline['symbol_factor_exposures'])}")
    print(f"  Portfolio Factor Exposures: {len(baseline['factor_exposures'])}")
    print(f"  Correlation Calculations: {len(baseline['correlation_calculations'])}")
    print(f"  Pairwise Correlations: {len(baseline['pairwise_correlations'])}")
    print(f"  Stress Test Results: {len(baseline['stress_test_results'])}")
    print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
