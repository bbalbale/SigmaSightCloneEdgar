"""
Database helpers for retrieving latest available portfolio snapshots and factor exposures.
Implements graceful fallback pattern for when current-day data is not available.
"""
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import FactorExposure
from app.core.logging import get_logger

logger = get_logger(__name__)

# Staleness threshold from config (72 hours = 3 days)
STALENESS_THRESHOLD_HOURS = 72


def is_weekend(check_date: date) -> bool:
    """Check if a date falls on a weekend."""
    return check_date.weekday() >= 5  # Saturday = 5, Sunday = 6


def is_trading_day(check_date: date) -> bool:
    """
    Determine if a date is a trading day.
    For now, just checks if it's not a weekend.
    Could be enhanced with holiday calendar.
    """
    return not is_weekend(check_date)


def calculate_data_age(snapshot_date: date, reference_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Calculate age metrics for a snapshot date relative to a reference date (default: today).

    Args:
        snapshot_date: The date of the snapshot
        reference_date: The date to compare against (default: today)

    Returns:
        Dictionary with age metrics:
        - age_days: Number of days old
        - age_hours: Number of hours old (approximate)
        - is_stale: Whether data exceeds staleness threshold
        - is_current: Whether data is from a current trading day
        - is_weekend: Whether missing data is due to weekend
    """
    if reference_date is None:
        reference_date = date.today()

    age_delta = reference_date - snapshot_date
    age_days = age_delta.days
    age_hours = age_days * 24

    # Check if data is stale (older than threshold)
    is_stale = age_hours > STALENESS_THRESHOLD_HOURS

    # Check if this is current trading day data
    is_current = (snapshot_date == reference_date) or (
        is_weekend(reference_date) and snapshot_date >= reference_date - timedelta(days=2)
    )

    # Check if missing data is expected due to weekend
    is_weekend_missing = is_weekend(reference_date) and age_days <= 2

    return {
        'age_days': age_days,
        'age_hours': age_hours,
        'is_stale': is_stale,
        'is_current': is_current,
        'is_weekend': is_weekend_missing,
        'should_recalculate': is_stale and is_trading_day(reference_date)
    }


async def get_latest_portfolio_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    max_age_days: int = 7
) -> Tuple[Optional[PortfolioSnapshot], Dict[str, Any]]:
    """
    Get the most recent portfolio snapshot with metadata about data age and staleness.

    This implements the "latest available data" pattern, ensuring the system
    always returns data even when current-day calculations haven't run yet.

    Args:
        db: Database session
        portfolio_id: Portfolio to query
        max_age_days: Maximum acceptable age (returns None if older)

    Returns:
        Tuple of (snapshot, metadata) where:
        - snapshot: Most recent PortfolioSnapshot or None if too old
        - metadata: Dict with age metrics and staleness indicators

    Example metadata:
        {
            'snapshot_date': date(2025, 10, 20),
            'age_days': 2,
            'age_hours': 48,
            'is_stale': False,
            'is_current': False,
            'is_weekend': True,
            'should_recalculate': False
        }
    """
    try:
        # Query for the most recent snapshot
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if snapshot is None:
            logger.warning(f"No snapshots found for portfolio {portfolio_id}")
            return None, {
                'snapshot_date': None,
                'age_days': None,
                'age_hours': None,
                'is_stale': True,
                'is_current': False,
                'is_weekend': False,
                'should_recalculate': True,
                'error': 'no_snapshots_found'
            }

        # Calculate age metrics
        age_metrics = calculate_data_age(snapshot.snapshot_date)

        # Check if snapshot is too old
        if age_metrics['age_days'] > max_age_days:
            logger.warning(
                f"Snapshot for portfolio {portfolio_id} is {age_metrics['age_days']} days old "
                f"(exceeds max of {max_age_days} days)"
            )
            return None, {
                **age_metrics,
                'snapshot_date': snapshot.snapshot_date,
                'error': 'snapshot_too_old'
            }

        # Log if data is stale
        if age_metrics['is_stale']:
            logger.info(
                f"Serving stale snapshot for portfolio {portfolio_id}: "
                f"{age_metrics['age_hours']} hours old (from {snapshot.snapshot_date})"
            )

        return snapshot, {
            **age_metrics,
            'snapshot_date': snapshot.snapshot_date,
            'error': None
        }

    except Exception as e:
        logger.error(f"Error retrieving latest snapshot for portfolio {portfolio_id}: {e}")
        return None, {
            'snapshot_date': None,
            'age_days': None,
            'age_hours': None,
            'is_stale': True,
            'is_current': False,
            'is_weekend': False,
            'should_recalculate': True,
            'error': str(e)
        }


async def get_latest_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    max_age_days: int = 7
) -> Tuple[Optional[date], Dict[str, Any]]:
    """
    Get the most recent calculation date for factor exposures with staleness metadata.

    Args:
        db: Database session
        portfolio_id: Portfolio to query
        max_age_days: Maximum acceptable age (returns None if older)

    Returns:
        Tuple of (calculation_date, metadata) where:
        - calculation_date: Most recent date with factor exposures or None
        - metadata: Dict with age metrics and staleness indicators
    """
    try:
        # Query for the most recent calculation date
        result = await db.execute(
            select(func.max(FactorExposure.calculation_date))
            .where(FactorExposure.portfolio_id == portfolio_id)
        )
        latest_date = result.scalar_one_or_none()

        if latest_date is None:
            logger.warning(f"No factor exposures found for portfolio {portfolio_id}")
            return None, {
                'calculation_date': None,
                'age_days': None,
                'age_hours': None,
                'is_stale': True,
                'is_current': False,
                'is_weekend': False,
                'should_recalculate': True,
                'error': 'no_factor_exposures_found'
            }

        # Calculate age metrics
        age_metrics = calculate_data_age(latest_date)

        # Check if too old
        if age_metrics['age_days'] > max_age_days:
            logger.warning(
                f"Factor exposures for portfolio {portfolio_id} are {age_metrics['age_days']} days old "
                f"(exceeds max of {max_age_days} days)"
            )
            return None, {
                **age_metrics,
                'calculation_date': latest_date,
                'error': 'factor_exposures_too_old'
            }

        # Log if data is stale
        if age_metrics['is_stale']:
            logger.info(
                f"Serving stale factor exposures for portfolio {portfolio_id}: "
                f"{age_metrics['age_hours']} hours old (from {latest_date})"
            )

        return latest_date, {
            **age_metrics,
            'calculation_date': latest_date,
            'error': None
        }

    except Exception as e:
        logger.error(f"Error retrieving latest factor exposures for portfolio {portfolio_id}: {e}")
        return None, {
            'calculation_date': None,
            'age_days': None,
            'age_hours': None,
            'is_stale': True,
            'is_current': False,
            'is_weekend': False,
            'should_recalculate': True,
            'error': str(e)
        }


async def get_snapshot_data_quality(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, Any]:
    """
    Get comprehensive data quality assessment for a portfolio's snapshot data.

    Combines snapshot and factor exposure staleness into a single quality metric.

    Args:
        db: Database session
        portfolio_id: Portfolio to assess

    Returns:
        Dictionary with combined quality metrics:
        - has_snapshot: Whether a snapshot exists
        - has_factors: Whether factor exposures exist
        - snapshot_date: Date of latest snapshot
        - factor_date: Date of latest factor exposures
        - overall_age_hours: Age of older of the two
        - is_stale: Whether any component is stale
        - should_recalculate: Whether recalculation should be triggered
    """
    # Get both snapshot and factor data
    snapshot, snapshot_meta = await get_latest_portfolio_snapshot(db, portfolio_id)
    factor_date, factor_meta = await get_latest_factor_exposures(db, portfolio_id)

    # Determine overall quality
    has_snapshot = snapshot is not None
    has_factors = factor_date is not None

    # Use the older of the two dates for overall staleness
    overall_age_hours = max(
        snapshot_meta.get('age_hours') or 0,
        factor_meta.get('age_hours') or 0
    )

    overall_is_stale = snapshot_meta.get('is_stale', True) or factor_meta.get('is_stale', True)
    should_recalculate = snapshot_meta.get('should_recalculate', True) or factor_meta.get('should_recalculate', True)

    return {
        'has_snapshot': has_snapshot,
        'has_factors': has_factors,
        'snapshot_date': snapshot_meta.get('snapshot_date'),
        'factor_date': factor_meta.get('calculation_date'),
        'overall_age_hours': overall_age_hours,
        'is_stale': overall_is_stale,
        'should_recalculate': should_recalculate,
        'snapshot_metadata': snapshot_meta,
        'factor_metadata': factor_meta
    }
