"""
Portfolio Exposure Service - Cached Snapshot Retrieval
Eliminates duplicate exposure calculations by using PortfolioSnapshot cache

Created: 2025-10-20 (Calculation Consolidation Refactor - Phase 1.2)
Purpose: Single source of truth for portfolio exposure retrieval

This service provides a critical performance optimization:
- Tries cached PortfolioSnapshot first (fast)
- Falls back to real-time calculation only when necessary (slower)
- Ensures consistency across market_risk, stress_testing, and analytics

Performance Impact:
- Cache hit: 1 database query (snapshot lookup)
- Cache miss: ~5 database queries (position fetch + aggregation)
- Expected cache hit rate: >70% in production
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position, PositionType
from app.calculations.portfolio import calculate_portfolio_exposures
from app.core.logging import get_logger

logger = get_logger(__name__)

OPTIONS_MULTIPLIER = 100  # Standard options contract size


async def get_portfolio_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    max_staleness_days: int = 3
) -> Dict[str, Any]:
    """
    Get portfolio net and gross exposures from snapshot or calculate real-time.

    This is the CANONICAL exposure retrieval function. All other modules
    (market_risk, stress_testing, analytics) should call this function instead
    of implementing their own exposure logic.

    Priority:
    1. Use latest snapshot if recent (within max_staleness_days)
    2. Calculate real-time from positions using calculate_portfolio_exposures()

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for calculation
        max_staleness_days: Maximum days snapshot can be old (default 3)

    Returns:
        Dict with:
            - net_exposure: float (signed sum of positions)
            - gross_exposure: float (sum of absolute values)
            - long_exposure: float (sum of long positions)
            - short_exposure: float (sum of short positions)
            - position_count: int (number of active positions)
            - source: 'snapshot' or 'real_time'
            - snapshot_date: date (if from snapshot) or None

    Example:
        >>> exposures = await get_portfolio_exposures(db, portfolio_id, date.today())
        >>> net = exposures['net_exposure']  # e.g., $2.3M for hedged portfolio
        >>> gross = exposures['gross_exposure']  # e.g., $6.6M for hedged portfolio
        >>>
        >>> if exposures['source'] == 'snapshot':
        >>>     print(f"Cache hit! Saved ~4 DB queries")

    Performance Notes:
        - Snapshot hit: ~1 DB query (fast)
        - Real-time calc: ~5 DB queries (slower)
        - Cache hit rate expected >70% in production
    """
    # Try to get latest snapshot (within calculation_date)
    snapshot_stmt = (
        select(PortfolioSnapshot)
        .where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.snapshot_date <= calculation_date
            )
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )

    snapshot_result = await db.execute(snapshot_stmt)
    latest_snapshot = snapshot_result.scalar_one_or_none()

    # Check if snapshot is recent enough
    if latest_snapshot:
        staleness = (calculation_date - latest_snapshot.snapshot_date).days
        if staleness <= max_staleness_days:
            logger.info(
                f"[OK] Cache HIT: Using snapshot from {latest_snapshot.snapshot_date} "
                f"({staleness} days old) for portfolio {portfolio_id}"
            )
            logger.debug(
                f"Snapshot exposures: net=${float(latest_snapshot.net_exposure):,.0f}, "
                f"gross=${float(latest_snapshot.gross_exposure):,.0f}"
            )

            return {
                'net_exposure': float(latest_snapshot.net_exposure),
                'gross_exposure': float(latest_snapshot.gross_exposure),
                'long_exposure': float(latest_snapshot.long_value),
                'short_exposure': float(latest_snapshot.short_value),
                'position_count': latest_snapshot.num_positions,
                'source': 'snapshot',
                'snapshot_date': latest_snapshot.snapshot_date
            }
        else:
            logger.warning(
                f"[ERROR] Cache MISS (stale): Latest snapshot is {staleness} days old "
                f"(max: {max_staleness_days}), calculating real-time for portfolio {portfolio_id}"
            )
    else:
        logger.info(
            f"[ERROR] Cache MISS (none): No snapshot found for portfolio {portfolio_id}, "
            "calculating real-time"
        )

    # Fallback: Calculate real-time from positions
    return await _calculate_realtime_exposures(db, portfolio_id)


async def _calculate_realtime_exposures(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, Any]:
    """
    Calculate portfolio exposures in real-time from positions.

    This is the fallback when no recent snapshot is available.
    Uses the authoritative calculate_portfolio_exposures() from portfolio.py.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID

    Returns:
        Dict with exposure metrics (same format as get_portfolio_exposures)
    """
    logger.info(f"Calculating real-time exposures for portfolio {portfolio_id}")

    # Fetch active positions only (exclude exited)
    positions_stmt = select(Position).where(
        and_(
            Position.portfolio_id == portfolio_id,
            Position.exit_date.is_(None)  # Active only
        )
    )
    positions_result = await db.execute(positions_stmt)
    positions = list(positions_result.scalars().all())

    if not positions:
        logger.warning(f"No active positions found for portfolio {portfolio_id}")
        return {
            'net_exposure': 0.0,
            'gross_exposure': 0.0,
            'long_exposure': 0.0,
            'short_exposure': 0.0,
            'position_count': 0,
            'source': 'real_time',
            'snapshot_date': None
        }

    # Prepare position data for calculate_portfolio_exposures()
    position_data = await prepare_positions_for_aggregation(db, positions)

    # Call the authoritative calculation function from portfolio.py
    aggregations = calculate_portfolio_exposures(position_data)

    logger.info(
        f"Real-time exposures calculated: net=${float(aggregations['net_exposure']):,.0f}, "
        f"gross=${float(aggregations['gross_exposure']):,.0f}, "
        f"{len(positions)} positions"
    )

    return {
        'net_exposure': float(aggregations['net_exposure']),
        'gross_exposure': float(aggregations['gross_exposure']),
        'long_exposure': float(aggregations['long_exposure']),
        'short_exposure': float(aggregations['short_exposure']),
        'position_count': len(positions),
        'source': 'real_time',
        'snapshot_date': None
    }


async def prepare_positions_for_aggregation(
    db: AsyncSession,
    positions: List[Position]
) -> List[Dict[str, Any]]:
    """
    Prepare positions for exposure calculation.

    Converts Position objects to the dict format expected by
    calculate_portfolio_exposures() in portfolio.py.

    This function handles:
    - Signed market value (negative for shorts)
    - Options multiplier (100x for LC, LP, SC, SP)
    - Missing price data (skips position with warning)

    Args:
        db: Database session
        positions: List of Position objects

    Returns:
        List of dicts with exposure, market_value, position_type for each position

    Example:
        >>> position_data = await prepare_positions_for_aggregation(db, positions)
        >>> aggregations = calculate_portfolio_exposures(position_data)
    """
    position_data = []

    for pos in positions:
        try:
            # Use cached market_value if available
            if pos.market_value is not None:
                signed_value = float(pos.market_value)
                exposure = signed_value
            elif pos.last_price is not None:
                # Calculate from price
                quantity = float(pos.quantity)
                price = float(pos.last_price)

                # Apply options multiplier (100 for options, 1 for stocks)
                if pos.position_type.name in ['LC', 'LP', 'SC', 'SP']:
                    multiplier = OPTIONS_MULTIPLIER
                else:
                    multiplier = 1

                # Calculate market value (already signed by quantity)
                # For SHORT positions, quantity is negative
                # For SC/SP positions, quantity is negative
                market_value = quantity * price * multiplier
                exposure = market_value
            else:
                # No price data available
                logger.warning(
                    f"Position {pos.id} ({pos.symbol}) has no price data, skipping"
                )
                continue

            # Add to position data
            position_data.append({
                'exposure': Decimal(str(exposure)),
                'market_value': Decimal(str(abs(exposure))),  # Absolute for gross calc
                'position_type': pos.position_type.name
            })

        except Exception as e:
            logger.error(f"Error preparing position {pos.id}: {e}")
            continue

    return position_data
