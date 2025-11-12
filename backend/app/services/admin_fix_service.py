"""
Shared helpers for Railway admin fix workflows.

Provides centralized clearing logic so HTTP endpoints and Railway scripts
stay in sync when wiping calculated analytics tables before reseeding.
"""
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple, Type

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import (
    FactorCorrelation,
    FactorExposure,
    MarketRiskScenario,
    PositionFactorExposure,
    PositionGreeks,
    PositionInterestRateBeta,
    PositionMarketBeta,
    PositionVolatility,
    StressTestResult,
)
from app.models.correlations import (
    CorrelationCalculation,
    CorrelationCluster,
    CorrelationClusterPosition,
    PairwiseCorrelation,
)
from app.models.positions import Position
from app.models.users import Portfolio, User
from app.core.logging import get_logger

logger = get_logger(__name__)

# (model, date_attr, label) for tables that can be cleared independently
TABLES_TO_CLEAR: Tuple[Tuple[Type[DeclarativeMeta], str, str], ...] = (
    (PortfolioSnapshot, "snapshot_date", "portfolio_snapshots"),
    (PositionGreeks, "calculation_date", "position_greeks"),
    (FactorExposure, "calculation_date", "portfolio_factor_exposures"),
    (PositionFactorExposure, "calculation_date", "position_factor_exposures"),
    (PositionInterestRateBeta, "calculation_date", "position_interest_rate_betas"),
    (PositionMarketBeta, "calc_date", "position_market_betas"),
    (PositionVolatility, "calculation_date", "position_volatility"),
    (MarketRiskScenario, "calculation_date", "market_risk_scenarios"),
    (StressTestResult, "calculation_date", "stress_test_results"),
)

# Correlation tables require ordered deletes due to FK relationships
CORRELATION_TABLES: Tuple[Tuple[Type[DeclarativeMeta], str], ...] = (
    (PairwiseCorrelation, "pairwise_correlations"),
    (CorrelationClusterPosition, "correlation_cluster_positions"),
    (CorrelationCluster, "correlation_clusters"),
    (FactorCorrelation, "factor_correlations"),
    (CorrelationCalculation, "correlation_calculations"),
)

SEED_DATE = date(2025, 6, 30)
DUPLICATE_CREATED_AT_CUTOFF = datetime(2025, 11, 1, 0, 0, 0)

DEMO_EQUITY_SEED_VALUES = {
    "demo_individual@sigmasight.com": Decimal("485000.00"),
    "demo_hnw@sigmasight.com": Decimal("2850000.00"),
    "demo_hedgefundstyle@sigmasight.com": Decimal("3200000.00"),
    "demo_familyoffice@sigmasight.com": {
        "Demo Family Office Public Growth": Decimal("1250000.00"),
        "Demo Family Office Private Opportunities": Decimal("950000.00"),
    },
}


async def _clear_table(
    db: AsyncSession,
    model: Type[DeclarativeMeta],
    date_attr: str,
    label: str,
    summary: Dict[str, int],
    start_date: Optional[date],
) -> int:
    """Clear rows from a table filtered by the provided date column."""
    column = getattr(model, date_attr, None)
    if column is None:
        raise AttributeError(f"{model.__name__} has no attribute '{date_attr}'")

    stmt = select(func.count()).select_from(model)
    delete_stmt = delete(model)

    if start_date:
        stmt = stmt.where(column >= start_date)
        delete_stmt = delete_stmt.where(column >= start_date)

    count = (await db.execute(stmt)).scalar() or 0

    if count:
        await db.execute(delete_stmt)

    summary[label] = count
    return count


async def _clear_correlation_tables(
    db: AsyncSession,
    summary: Dict[str, int],
    start_date: Optional[date],
) -> int:
    """Handle correlation calculations and their dependents."""
    calc_stmt = select(CorrelationCalculation.id)
    if start_date:
        calc_stmt = calc_stmt.where(CorrelationCalculation.calculation_date >= start_date)

    calculation_ids = (await db.execute(calc_stmt)).scalars().all()
    if not calculation_ids:
        for _, label in CORRELATION_TABLES:
            summary[label] = 0
        return 0

    total_deleted = 0

    # Pairwise correlations
    pairwise_count = (
        await db.execute(
            select(func.count()).where(PairwiseCorrelation.correlation_calculation_id.in_(calculation_ids))
        )
    ).scalar_one()
    await db.execute(
        delete(PairwiseCorrelation).where(PairwiseCorrelation.correlation_calculation_id.in_(calculation_ids))
    )
    summary["pairwise_correlations"] = pairwise_count
    total_deleted += pairwise_count

    # Cluster positions
    cluster_ids = (
        await db.execute(
            select(CorrelationCluster.id).where(CorrelationCluster.correlation_calculation_id.in_(calculation_ids))
        )
    ).scalars().all()

    if cluster_ids:
        cluster_position_count = (
            await db.execute(
                select(func.count()).where(CorrelationClusterPosition.cluster_id.in_(cluster_ids))
            )
        ).scalar_one()
        await db.execute(
            delete(CorrelationClusterPosition).where(CorrelationClusterPosition.cluster_id.in_(cluster_ids))
        )
    else:
        cluster_position_count = 0

    summary["correlation_cluster_positions"] = cluster_position_count
    total_deleted += cluster_position_count

    # Clusters
    if cluster_ids:
        await db.execute(delete(CorrelationCluster).where(CorrelationCluster.id.in_(cluster_ids)))
    summary["correlation_clusters"] = len(cluster_ids)
    total_deleted += len(cluster_ids)

    # Factor correlations
    factor_corr_count = (
        await db.execute(
            select(func.count()).where(FactorCorrelation.correlation_calculation_id.in_(calculation_ids))
        )
    ).scalar_one()
    await db.execute(
        delete(FactorCorrelation).where(FactorCorrelation.correlation_calculation_id.in_(calculation_ids))
    )
    summary["factor_correlations"] = factor_corr_count
    total_deleted += factor_corr_count

    # Calculations last
    await db.execute(delete(CorrelationCalculation).where(CorrelationCalculation.id.in_(calculation_ids)))
    summary["correlation_calculations"] = len(calculation_ids)
    total_deleted += len(calculation_ids)

    return total_deleted


async def clear_all_calculation_tables(
    db: AsyncSession,
    start_date: Optional[date] = None,
) -> Dict[str, Dict[str, int]]:
    """
    Clear every derived analytics table needed for a clean reseed.

    Returns:
        {
            "tables": {"portfolio_snapshots": 10, ...},
            "total_cleared": 1234
        }
    """
    summary: Dict[str, int] = OrderedDict()
    total_cleared = 0

    for model, column_name, label in TABLES_TO_CLEAR:
        total_cleared += await _clear_table(db, model, column_name, label, summary, start_date)

    total_cleared += await _clear_correlation_tables(db, summary, start_date)

    return {
        "tables": summary,
        "total_cleared": total_cleared,
    }


async def _reset_equity_balances(db: AsyncSession) -> int:
    """Reset portfolio equity balances to their seed values."""
    reset_count = 0

    for user_email, equity_value in DEMO_EQUITY_SEED_VALUES.items():
        user = (await db.execute(select(User).where(User.email == user_email))).scalar_one_or_none()
        if not user:
            logger.warning("Demo user not found while resetting equity: %s", user_email)
            continue

        if isinstance(equity_value, Decimal):
            portfolios = (
                await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))
            ).scalars().all()
            for portfolio in portfolios:
                portfolio.equity_balance = equity_value
                db.add(portfolio)
                reset_count += 1
        else:
            for portfolio_name, portfolio_equity in equity_value.items():
                portfolio = (
                    await db.execute(
                        select(Portfolio).where(
                            Portfolio.user_id == user.id,
                            Portfolio.name == portfolio_name,
                        )
                    )
                ).scalar_one_or_none()
                if not portfolio:
                    logger.warning(
                        "Portfolio %s not found for demo user %s while resetting equity",
                        portfolio_name,
                        user_email,
                    )
                    continue
                portfolio.equity_balance = portfolio_equity
                db.add(portfolio)
                reset_count += 1

    return reset_count


async def _remove_soft_deleted_positions(db: AsyncSession) -> int:
    """Permanently delete positions that were soft deleted."""
    soft_deleted_positions = (
        await db.execute(select(Position).where(Position.deleted_at.is_not(None)))
    ).scalars().all()

    if not soft_deleted_positions:
        return 0

    for position in soft_deleted_positions:
        await db.delete(position)

    return len(soft_deleted_positions)


async def _remove_duplicate_positions(db: AsyncSession) -> int:
    """
    Remove duplicate positions created after the canonical seed.
    Keeps positions created before Nov 1, 2025.
    """
    duplicate_positions = (
        await db.execute(
            select(Position).where(
                Position.entry_date == SEED_DATE,
                Position.created_at >= DUPLICATE_CREATED_AT_CUTOFF,
                Position.deleted_at.is_(None),
            )
        )
    ).scalars().all()

    if not duplicate_positions:
        return 0

    for pos in duplicate_positions:
        await db.delete(pos)

    return len(duplicate_positions)


async def clear_calculations_comprehensive(
    db: AsyncSession,
    start_date: Optional[date] = None,
) -> Dict[str, int]:
    """
    Perform the full cleanup sequence used by the CLI script:
    - Clear analytics tables
    - Remove soft-deleted positions
    - Remove duplicate positions created after the seed
    - Reset demo portfolio equity balances
    """
    start = start_date or date(2000, 1, 1)
    analytics_results = await clear_all_calculation_tables(db, start)

    soft_deleted_count = await _remove_soft_deleted_positions(db)
    duplicate_count = await _remove_duplicate_positions(db)
    equity_resets = await _reset_equity_balances(db)

    total_deleted = analytics_results["total_cleared"] + soft_deleted_count + duplicate_count

    return {
        "tables": analytics_results["tables"],
        "total_cleared": analytics_results["total_cleared"],
        "soft_deleted_positions": soft_deleted_count,
        "duplicate_positions": duplicate_count,
        "equity_resets": equity_resets,
        "grand_total_deleted": total_deleted,
    }
