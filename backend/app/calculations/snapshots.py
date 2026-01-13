"""
Portfolio snapshot generation for daily portfolio state tracking
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio as PortfolioModel
from app.calculations.portfolio import (
    calculate_portfolio_exposures
)
from app.utils.trading_calendar import trading_calendar

logger = logging.getLogger(__name__)


async def lock_snapshot_slot(
    db: AsyncSession,
    portfolio_id: UUID,
    snapshot_date: date
) -> Optional[PortfolioSnapshot]:
    """
    Claim ownership of a (portfolio, date) combination by inserting a placeholder snapshot.

    This is the FIRST step in the insert-first idempotency pattern (Phase 2.10).
    The database unique constraint on (portfolio_id, snapshot_date) ensures that
    only ONE process can successfully insert a placeholder for a given (portfolio, date).

    If this function succeeds, the caller owns the slot and should proceed with
    calculations. If it raises IntegrityError, another process is already handling
    this portfolio+date combination.

    Args:
        db: Database session (must be same session as caller's transaction)
        portfolio_id: Portfolio to lock
        snapshot_date: Date to lock (typically today)

    Returns:
        PortfolioSnapshot placeholder if successful (is_complete=False)
        Returns the placeholder object that should be populated later

    Raises:
        IntegrityError: If another process already owns this (portfolio, date)
            Caller should catch this and skip processing gracefully

    Usage:
        try:
            placeholder = await lock_snapshot_slot(db, portfolio_id, today)
        except IntegrityError as e:
            if "uq_portfolio_snapshot_date" in str(e):
                logger.info(f"Portfolio {portfolio_id} already processing, skipping")
                await db.rollback()
                return {"status": "skipped", "reason": "duplicate_run"}
            raise

        # Now safe to calculate - we own this slot
        calculate_pnl()

        # Update placeholder with real values
        placeholder.net_asset_value = calculated_nav
        # ... set all other fields
        placeholder.is_complete = True
        await db.flush()
    """
    # Create minimal placeholder snapshot with all required fields
    # All numeric fields set to zero, is_complete=False to mark as incomplete
    placeholder = PortfolioSnapshot(
        id=uuid4(),
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,  # Note: snapshot_date, not calculation_date!

        # Portfolio values (all zeros as placeholders)
        net_asset_value=Decimal("0"),
        cash_value=Decimal("0"),
        long_value=Decimal("0"),
        short_value=Decimal("0"),

        # Exposures (all zeros)
        gross_exposure=Decimal("0"),
        net_exposure=Decimal("0"),

        # Position counts (zeros)
        num_positions=0,
        num_long_positions=0,
        num_short_positions=0,

        # Phase 2.10: Mark as incomplete (will be set to True after calculations)
        is_complete=False
    )

    # Add to session and flush NOW to claim the slot atomically
    # The unique constraint on (portfolio_id, snapshot_date) will raise
    # IntegrityError if another process already inserted for this combination
    db.add(placeholder)
    await db.flush()  # ← This is where uniqueness is enforced

    logger.info(
        f"Successfully locked snapshot slot for portfolio {portfolio_id} "
        f"on {snapshot_date} (placeholder ID: {placeholder.id})"
    )

    return placeholder


async def populate_snapshot_data(
    snapshot: PortfolioSnapshot,
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    skip_pnl_calculation: bool = False,
    skip_provider_beta: bool = False,
    skip_sector_analysis: bool = False,
    equity_override: Optional[Decimal] = None,
) -> PortfolioSnapshot:
    """
    Populate an existing placeholder snapshot with real calculation data.

    This is the SECOND step in the insert-first idempotency pattern (Phase 2.10).
    The placeholder snapshot should be created first using lock_snapshot_slot().

    This function contains ALL the calculation logic from the original
    create_portfolio_snapshot(), but instead of creating a new snapshot,
    it updates the passed placeholder with real values.

    Args:
        snapshot: Placeholder snapshot to populate (from lock_snapshot_slot)
        db: Database session
        portfolio_id: UUID of the portfolio
        calculation_date: Date for the snapshot (typically today)
        skip_pnl_calculation: If True, skip P&L calculation (for V3 batch processor)
        skip_provider_beta: If True, skip provider beta calculation (for historical backfills)
        skip_sector_analysis: If True, skip sector analysis (for historical backfills)
        equity_override: If provided, use this equity value instead of querying portfolio.
                         This ensures cash calculation uses the correct (updated) equity
                         when called from pnl_calculator after equity rollforward.

    Returns:
        The populated snapshot with is_complete=True

    Usage:
        # Step 1: Lock the slot (insert placeholder)
        try:
            placeholder = await lock_snapshot_slot(db, portfolio_id, today)
        except IntegrityError:
            return {"status": "skipped"}  # Already processing

        # Step 2: Populate with real data
        snapshot = await populate_snapshot_data(
            snapshot=placeholder,
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=today
        )

        # Step 3: Commit
        await db.commit()
    """
    logger.info(f"Populating snapshot data for {portfolio_id} on {calculation_date}")

    # Step 1: Fetch all active positions
    active_positions = await _fetch_active_positions(db, portfolio_id, calculation_date)
    logger.info(f"Found {len(active_positions)} active positions")

    if not active_positions:
        logger.warning(f"No active positions found for portfolio {portfolio_id}")
        # Populate with zeros
        snapshot.net_asset_value = Decimal('0')
        snapshot.cash_value = Decimal('0')
        snapshot.long_value = Decimal('0')
        snapshot.short_value = Decimal('0')
        snapshot.gross_exposure = Decimal('0')
        snapshot.net_exposure = Decimal('0')
        snapshot.daily_pnl = Decimal('0')
        snapshot.daily_return = Decimal('0')
        snapshot.cumulative_pnl = Decimal('0')
        snapshot.num_positions = 0
        snapshot.num_long_positions = 0
        snapshot.num_short_positions = 0
        snapshot.is_complete = True  # Mark as complete (zero snapshot)
        await db.flush()
        return snapshot

    # Step 2: Calculate market values for all positions
    position_data = await _prepare_position_data(db, active_positions, calculation_date)

    # Step 3: Calculate portfolio aggregations
    positions_list = position_data.get("positions", [])
    logger.info(
        f"Prepared {len(positions_list)} positions for aggregation; "
        f"warnings={len(position_data.get('warnings', []))}"
    )
    aggregations = calculate_portfolio_exposures(positions_list)

    # Get portfolio object for equity_balance
    # CRITICAL FIX (2026-01-13): Use equity_override if provided to ensure cash
    # calculation uses the correct (updated) equity after P&L rollforward.
    # Re-querying the portfolio can return stale data in some session scenarios.
    if equity_override is not None:
        today_equity = equity_override
        logger.debug(f"Using equity_override for cash calculation: ${float(today_equity):,.2f}")
        # Still need to verify portfolio exists
        portfolio_result = await db.execute(
            select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
    else:
        portfolio_result = await db.execute(
            select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        today_equity = portfolio.equity_balance or Decimal('0')
        logger.debug(f"Using portfolio equity_balance from session: ${float(today_equity):,.2f}")

    # Step 4: Calculate P&L (skip if requested by V3 batch processor)
    if skip_pnl_calculation:
        pnl_data = {
            'daily_pnl': Decimal('0'),
            'daily_return': Decimal('0'),
            'cumulative_pnl': Decimal('0')
        }
        logger.debug("Skipping P&L calculation (will be set by caller)")
    else:
        pnl_data = await _calculate_pnl(db, portfolio_id, calculation_date, today_equity)

    # Step 5: Count position types
    position_counts = _count_positions(active_positions)

    # Step 6: Calculate cash (equity minus deployed capital)
    long_exposure = aggregations.get('long_exposure', Decimal('0'))
    short_exposure = aggregations.get('short_exposure', Decimal('0'))
    short_proceeds = abs(short_exposure)
    calculated_cash = today_equity - long_exposure + short_proceeds
    cash_value = calculated_cash if calculated_cash > Decimal('0') else Decimal('0')
    logger.debug(
        "Derived cash for snapshot: equity=%s, long=%s, short_proceeds=%s, cash=%s",
        today_equity,
        long_exposure,
        short_proceeds,
        cash_value,
    )

    # Step 7: Calculate betas (deferred to Phase 6)
    beta_calculated_90d = None
    beta_calculated_90d_r_squared = None
    beta_calculated_90d_observations = None
    beta_provider_1y = None
    logger.debug("Beta calculation deferred to Phase 6 (requires position.market_value from Phase 4)")

    # Calculate provider beta if not skipped
    if not skip_provider_beta:
        try:
            from app.calculations.market_beta import calculate_portfolio_provider_beta

            provider_result = await calculate_portfolio_provider_beta(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            if provider_result.get('success'):
                beta_provider_1y = Decimal(str(provider_result['portfolio_beta']))
                logger.info(
                    f"Provider beta (1y) for snapshot: {float(beta_provider_1y):.3f} "
                    f"({provider_result['positions_with_beta']}/{provider_result['positions_count']} positions)"
                )
            else:
                logger.warning(f"Provider beta calculation failed: {provider_result.get('error')}")
        except Exception as e:
            logger.warning(f"Could not calculate provider beta for snapshot: {e}")
    else:
        logger.debug(f"Skipping provider beta calculation for historical snapshot ({calculation_date})")

    # Step 8: Calculate sector exposure and concentration
    sector_exposure_json = None
    hhi = None
    effective_num_positions = None
    top_3_concentration = None
    top_10_concentration = None

    if not skip_sector_analysis:
        try:
            from app.calculations.sector_analysis import calculate_portfolio_sector_concentration

            sector_result = await calculate_portfolio_sector_concentration(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            if sector_result.get('success'):
                if sector_result.get('sector_exposure'):
                    se = sector_result['sector_exposure']
                    sector_exposure_json = se.get('portfolio_weights', {})
                    logger.info(f"Sector exposure: {len(sector_exposure_json)} sectors captured")

                if sector_result.get('concentration'):
                    conc = sector_result['concentration']
                    hhi = Decimal(str(conc.get('hhi', 0)))
                    effective_num_positions = Decimal(str(conc.get('effective_num_positions', 0)))
                    top_3_concentration = Decimal(str(conc.get('top_3_concentration', 0)))
                    top_10_concentration = Decimal(str(conc.get('top_10_concentration', 0)))
                    logger.info(
                        f"Concentration metrics: HHI={float(hhi):.2f}, "
                        f"Effective positions={float(effective_num_positions):.2f}"
                    )
            else:
                logger.warning(f"Sector analysis failed for snapshot: {sector_result.get('error')}")
        except Exception as e:
            logger.warning(f"Could not calculate sector/concentration metrics for snapshot: {e}")
    else:
        logger.debug(f"Skipping sector analysis for historical snapshot ({calculation_date})")

    # Step 9: Volatility (deferred to Phase 6)
    realized_volatility_21d = None
    realized_volatility_63d = None
    expected_volatility_21d = None
    volatility_trend = None
    volatility_percentile = None
    logger.debug("Volatility calculation deferred to Phase 6 (requires position.market_value from Phase 4)")

    # Step 10: Update snapshot with all calculated values
    snapshot.net_asset_value = today_equity
    snapshot.cash_value = cash_value
    snapshot.long_value = aggregations['long_exposure']
    snapshot.short_value = aggregations['short_exposure']
    snapshot.gross_exposure = aggregations['gross_exposure']
    snapshot.net_exposure = aggregations['net_exposure']
    snapshot.daily_pnl = pnl_data['daily_pnl']
    snapshot.daily_return = pnl_data['daily_return']
    snapshot.cumulative_pnl = pnl_data['cumulative_pnl']
    snapshot.portfolio_delta = Decimal('0')
    snapshot.portfolio_gamma = Decimal('0')
    snapshot.portfolio_theta = Decimal('0')
    snapshot.portfolio_vega = Decimal('0')
    snapshot.num_positions = position_counts['total']
    snapshot.num_long_positions = position_counts['long']
    snapshot.num_short_positions = position_counts['short']
    snapshot.equity_balance = today_equity

    # Betas
    snapshot.beta_calculated_90d = beta_calculated_90d
    snapshot.beta_calculated_90d_r_squared = beta_calculated_90d_r_squared
    snapshot.beta_calculated_90d_observations = beta_calculated_90d_observations
    snapshot.beta_provider_1y = beta_provider_1y
    snapshot.beta_portfolio_regression = None

    # Sector and concentration
    snapshot.sector_exposure = sector_exposure_json
    snapshot.hhi = hhi
    snapshot.effective_num_positions = effective_num_positions
    snapshot.top_3_concentration = top_3_concentration
    snapshot.top_10_concentration = top_10_concentration

    # Volatility
    snapshot.realized_volatility_21d = realized_volatility_21d
    snapshot.realized_volatility_63d = realized_volatility_63d
    snapshot.expected_volatility_21d = expected_volatility_21d
    snapshot.volatility_trend = volatility_trend
    snapshot.volatility_percentile = volatility_percentile

    # Mark as complete (CRITICAL for Phase 2.10)
    snapshot.is_complete = True

    await db.flush()
    logger.info(f"Populated snapshot {snapshot.id} for {calculation_date} (is_complete=True)")

    return snapshot


async def create_portfolio_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    skip_pnl_calculation: bool = False,
    skip_provider_beta: bool = False,
    skip_sector_analysis: bool = False
) -> Dict[str, Any]:
    """
    Generate a complete daily snapshot of portfolio state

    Args:
        db: Database session
        portfolio_id: UUID of the portfolio
        calculation_date: Date for the snapshot (typically today)
        skip_pnl_calculation: If True, skip P&L calculation (for V3 batch processor)
        skip_provider_beta: If True, skip provider beta calculation (for historical backfills)
        skip_sector_analysis: If True, skip sector analysis (for historical backfills)

    Returns:
        Dictionary with snapshot creation results

    Note:
        When skip_pnl_calculation=True, the caller is responsible for setting
        equity_balance, daily_pnl, daily_return, and cumulative_pnl on the snapshot.
        This is used by the BatchOrchestrator Phase 2 (PnLCalculator).
    """
    logger.info(f"Creating portfolio snapshot for {portfolio_id} on {calculation_date}")
    
    try:
        # Check if it's a trading day
        if not trading_calendar.is_trading_day(calculation_date):
            logger.warning(f"{calculation_date} is not a trading day, skipping snapshot")
            return {
                "success": False,
                "message": f"{calculation_date} is not a trading day",
                "snapshot": None
            }
        
        # Step 1: Fetch all active positions
        active_positions = await _fetch_active_positions(db, portfolio_id, calculation_date)
        logger.info(f"Found {len(active_positions)} active positions")
        
        if not active_positions:
            logger.warning(f"No active positions found for portfolio {portfolio_id}")
            # Still create a zero snapshot
            snapshot = await _create_zero_snapshot(db, portfolio_id, calculation_date)
            return {
                "success": True,
                "message": "Created zero snapshot (no active positions)",
                "snapshot": snapshot
            }
        
        # Step 2: Calculate market values for all positions
        position_data = await _prepare_position_data(db, active_positions, calculation_date)
        
        # Step 3: Calculate portfolio aggregations
        positions_list = position_data.get("positions", [])
        logger.info(
            f"Prepared {len(positions_list)} positions for aggregation; "
            f"warnings={len(position_data.get('warnings', []))}"
        )
        aggregations = calculate_portfolio_exposures(positions_list)

        # CRITICAL FIX #4 (2025-11-15): DO NOT re-query equity_balance!
        # The pnl_calculator has already updated portfolio.equity_balance and flushed it.
        # Re-querying here causes a race condition where we might get stale data.
        # Instead, get the portfolio object from the session (which has the updated equity).
        portfolio_result = await db.execute(
            select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        today_equity = portfolio.equity_balance or Decimal('0')
        logger.debug(f"Using portfolio equity_balance from session: ${float(today_equity):,.2f}")


        # Step 4: Calculate P&L (skip if requested by V3 batch processor)
        if skip_pnl_calculation:
            # V3 batch processor calculates P&L separately with equity rollforward
            pnl_data = {
                'daily_pnl': Decimal('0'),
                'daily_return': Decimal('0'),
                'cumulative_pnl': Decimal('0')
            }
            logger.debug("Skipping P&L calculation (will be set by caller)")
        else:
            pnl_data = await _calculate_pnl(db, portfolio_id, calculation_date, today_equity)

        # Step 5: Count position types
        position_counts = _count_positions(active_positions)

        # Step 6: Create or update snapshot
        snapshot = await _create_or_update_snapshot(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            aggregations=aggregations,
            pnl_data=pnl_data,
            position_counts=position_counts,
            skip_provider_beta=skip_provider_beta,
            skip_sector_analysis=skip_sector_analysis
        )

        # CRITICAL FIX (2025-11-14): Do NOT commit here!
        # The caller (pnl_calculator) needs to commit BOTH the portfolio equity update
        # AND the snapshot in a SINGLE transaction. Committing here causes the portfolio
        # equity update to be lost when the snapshot re-queries the portfolio object.
        # await db.commit()  # REMOVED - caller handles commit

        return {
            "success": True,
            "message": "Snapshot created successfully",
            "snapshot": snapshot,
            "statistics": {
                "positions_processed": len(active_positions),
                "net_asset_value": float(today_equity),
                "daily_pnl": float(pnl_data['daily_pnl']),
                "cash_value": float(snapshot.cash_value or Decimal('0')),
                "warnings": position_data.get('warnings', [])
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating portfolio snapshot: {str(e)}")
        await db.rollback()
        return {
            "success": False,
            "message": f"Error creating snapshot: {str(e)}",
            "snapshot": None
        }


async def _fetch_active_positions(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> List[Position]:
    """Fetch all active positions for a portfolio on a given date"""
    query = select(Position).where(
        and_(
            Position.portfolio_id == portfolio_id,
            Position.entry_date <= calculation_date,
            or_(
                Position.exit_date.is_(None),
                Position.exit_date > calculation_date
            ),
            Position.deleted_at.is_(None)
        )
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def _prepare_position_data(
    db: AsyncSession,
    positions: List[Position],
    calculation_date: date
) -> Dict[str, Any]:
    """
    Prepare position data with market values and Greeks.

    CRITICAL: Uses HISTORICAL prices from market_data_cache for the calculation_date,
    NOT current Position.market_value. This ensures snapshots reflect values as of
    that specific date, enabling accurate historical P&L tracking.
    """
    from app.services.market_data_service import market_data_service

    warnings = []
    position_data = []

    # Get historical prices for all symbols as of calculation_date
    symbols = [pos.symbol for pos in positions]
    historical_prices = await market_data_service.get_cached_prices(
        db=db,
        symbols=symbols,
        target_date=calculation_date
    )

    logger.info(f"Fetched historical prices for {len(historical_prices)} symbols as of {calculation_date}")

    # Process each position using historical prices
    for position in positions:
        try:
            # Get historical price for this symbol
            historical_price = historical_prices.get(position.symbol)

            # For private positions (no market data), use entry_price or position.market_value
            if historical_price is None or historical_price == 0:
                if position.investment_class == "PRIVATE":
                    # Use position's market_value if available, otherwise use entry value
                    if position.market_value and position.market_value > 0:
                        price = float(position.market_value / position.quantity)
                    else:
                        price = float(position.entry_price)
                    logger.debug(f"Using valuation for PRIVATE position {position.symbol}: ${price:,.2f}")
                else:
                    # For PUBLIC positions, missing price data is an error
                    warnings.append(f"No historical price data for PUBLIC position {position.symbol} on {calculation_date}")
                    continue
            else:
                # Use historical market price
                price = float(historical_price)

            # Calculate market value using price
            quantity = float(position.quantity)

            # Apply options multiplier (100 for options, 1 for stocks)
            OPTIONS_MULTIPLIER = 100
            if position.position_type.name in ['LC', 'LP', 'SC', 'SP']:
                multiplier = OPTIONS_MULTIPLIER
            else:
                multiplier = 1

            # Calculate market value (signed by quantity)
            # For SHORT/SC/SP positions, quantity is negative
            market_value = quantity * price * multiplier
            exposure = market_value

            # Build position dict with historical prices
            position_data.append({
                "id": position.id,
                "symbol": position.symbol,
                "quantity": position.quantity,
                "market_value": abs(Decimal(str(market_value))),  # Absolute value
                "exposure": Decimal(str(exposure)),                # Signed exposure
                "position_type": position.position_type
            })

        except Exception as e:
            logger.error(f"Error processing position {position.id}: {str(e)}")
            warnings.append(f"Error processing position {position.symbol}: {str(e)}")

    return {
        "positions": position_data,
        "warnings": warnings
    }


async def _calculate_pnl(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    current_value: Decimal
) -> Dict[str, Decimal]:
    """Calculate daily and cumulative P&L"""
    # Get previous trading day
    previous_date = trading_calendar.get_previous_trading_day(calculation_date)
    
    if not previous_date:
        logger.warning("No previous trading day found, setting P&L to 0")
        return {
            "daily_pnl": Decimal('0'),
            "daily_return": Decimal('0'),
            "cumulative_pnl": Decimal('0')
        }
    
    # Fetch previous snapshot
    prev_query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == previous_date
        )
    )
    prev_result = await db.execute(prev_query)
    previous_snapshot = prev_result.scalar_one_or_none()
    
    if not previous_snapshot:
        logger.info("No previous snapshot found, this is the first snapshot")
        return {
            "daily_pnl": Decimal('0'),
            "daily_return": Decimal('0'),
            "cumulative_pnl": Decimal('0')
        }
    
    # Calculate daily P&L
    daily_pnl = current_value - previous_snapshot.net_asset_value
    daily_return = (daily_pnl / previous_snapshot.net_asset_value) if previous_snapshot.net_asset_value != 0 else Decimal('0')
    
    # Calculate cumulative P&L (add today's P&L to previous cumulative)
    cumulative_pnl = (previous_snapshot.cumulative_pnl or Decimal('0')) + daily_pnl
    
    return {
        "daily_pnl": daily_pnl,
        "daily_return": daily_return,
        "cumulative_pnl": cumulative_pnl
    }


def _count_positions(positions: List[Position]) -> Dict[str, int]:
    """Count positions by type"""
    counts = {
        "total": len(positions),
        "long": 0,
        "short": 0
    }
    
    for position in positions:
        if position.quantity > 0:
            counts["long"] += 1
        else:
            counts["short"] += 1
    
    return counts


async def _create_or_update_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    aggregations: Dict[str, Decimal],
    pnl_data: Dict[str, Decimal],
    position_counts: Dict[str, int],
    skip_provider_beta: bool = False,
    skip_sector_analysis: bool = False
) -> PortfolioSnapshot:
    """Create or update portfolio snapshot AND update portfolio equity_balance"""

    # Import Portfolio model for equity_balance lookup
    from app.models.users import Portfolio

    # Get portfolio to access equity_balance (already updated by equity_balance_update job)
    portfolio_query = select(Portfolio).where(Portfolio.id == portfolio_id)
    portfolio_result = await db.execute(portfolio_query)
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # Use the pre-calculated equity balance from the equity_balance_update job
    # This job runs BEFORE factor calculations, ensuring factor betas use the correct equity
    today_equity = portfolio.equity_balance or Decimal('0')
    logger.info(
        f"Using pre-calculated equity balance for {portfolio_id}: ${float(today_equity):,.2f}"
    )

    # Calculate cash from equity minus deployed capital (long usage minus short proceeds)
    long_exposure = aggregations.get('long_exposure', Decimal('0'))
    short_exposure = aggregations.get('short_exposure', Decimal('0'))
    short_proceeds = abs(short_exposure)
    calculated_cash = today_equity - long_exposure + short_proceeds
    cash_value = calculated_cash if calculated_cash > Decimal('0') else Decimal('0')
    logger.debug(
        "Derived cash for snapshot: equity=%s, long=%s, short_proceeds=%s, cash=%s",
        today_equity,
        long_exposure,
        short_proceeds,
        cash_value,
    )

    # PHASE 3 FIX (2025-11-17): Remove beta calculation from Phase 3
    # Beta calculation moved to Phase 6 where position.market_value is available
    # Phase 6 will update snapshots after calculation completes
    beta_calculated_90d = None
    beta_calculated_90d_r_squared = None
    beta_calculated_90d_observations = None
    logger.debug("Beta calculation deferred to Phase 6 (requires position.market_value from Phase 4)")

    # Calculate provider beta (1-year, from CompanyProfile)
    # OPTIMIZATION: Skip for historical dates (only needed for current/final date)
    beta_provider_1y = None

    if not skip_provider_beta:
        try:
            from app.calculations.market_beta import calculate_portfolio_provider_beta

            provider_result = await calculate_portfolio_provider_beta(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            if provider_result.get('success'):
                beta_provider_1y = Decimal(str(provider_result['portfolio_beta']))
                logger.info(
                    f"Provider beta (1y) for snapshot: {float(beta_provider_1y):.3f} "
                    f"({provider_result['positions_with_beta']}/{provider_result['positions_count']} positions)"
                )
            else:
                logger.warning(f"Provider beta calculation failed: {provider_result.get('error')}")
        except Exception as e:
            logger.warning(f"Could not calculate provider beta for snapshot: {e}")
    else:
        logger.debug(f"Skipping provider beta calculation for historical snapshot ({calculation_date})")

    # Phase 1: Sector exposure and concentration metrics
    # OPTIMIZATION: Skip for historical dates (only needed for current/final date)
    sector_exposure_json = None
    hhi = None
    effective_num_positions = None
    top_3_concentration = None
    top_10_concentration = None

    if not skip_sector_analysis:
        try:
            from app.calculations.sector_analysis import calculate_portfolio_sector_concentration

            sector_result = await calculate_portfolio_sector_concentration(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            if sector_result.get('success'):
                # Extract sector exposure data
                if sector_result.get('sector_exposure'):
                    se = sector_result['sector_exposure']
                    sector_exposure_json = se.get('portfolio_weights', {})
                    logger.info(f"Sector exposure: {len(sector_exposure_json)} sectors captured")

                # Extract concentration metrics
                if sector_result.get('concentration'):
                    conc = sector_result['concentration']
                    hhi = Decimal(str(conc.get('hhi', 0)))
                    effective_num_positions = Decimal(str(conc.get('effective_num_positions', 0)))
                    top_3_concentration = Decimal(str(conc.get('top_3_concentration', 0)))
                    top_10_concentration = Decimal(str(conc.get('top_10_concentration', 0)))
                    logger.info(
                        f"Concentration metrics: HHI={float(hhi):.2f}, "
                        f"Effective positions={float(effective_num_positions):.2f}"
                    )
            else:
                logger.warning(f"Sector analysis failed for snapshot: {sector_result.get('error')}")
        except Exception as e:
            logger.warning(f"Could not calculate sector/concentration metrics for snapshot: {e}")
    else:
        logger.debug(f"Skipping sector analysis for historical snapshot ({calculation_date})")

    # PHASE 3 FIX (2025-11-17): Remove volatility calculation from Phase 3
    # Volatility calculation moved to Phase 6 where position.market_value is available
    # Phase 6 will update snapshots after calculation completes
    realized_volatility_21d = None
    realized_volatility_63d = None
    expected_volatility_21d = None
    volatility_trend = None
    volatility_percentile = None
    logger.debug("Volatility calculation deferred to Phase 6 (requires position.market_value from Phase 4)")

    # Check if snapshot already exists
    existing_query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == calculation_date
        )
    )
    existing_result = await db.execute(existing_query)
    existing_snapshot = existing_result.scalar_one_or_none()

    snapshot_data = {
        "portfolio_id": portfolio_id,
        "snapshot_date": calculation_date,
        "net_asset_value": today_equity,
        "cash_value": cash_value,
        "long_value": aggregations['long_exposure'],
        "short_value": aggregations['short_exposure'],
        "gross_exposure": aggregations['gross_exposure'],
        "net_exposure": aggregations['net_exposure'],
        "daily_pnl": pnl_data['daily_pnl'],
        "daily_return": pnl_data['daily_return'],
        "cumulative_pnl": pnl_data['cumulative_pnl'],
        "portfolio_delta": Decimal('0'),
        "portfolio_gamma": Decimal('0'),
        "portfolio_theta": Decimal('0'),
        "portfolio_vega": Decimal('0'),
        "num_positions": position_counts['total'],
        "num_long_positions": position_counts['long'],
        "num_short_positions": position_counts['short'],
        "equity_balance": today_equity,  # Use calculated equity
        # Phase 0: Market beta (single-factor models)
        "beta_calculated_90d": beta_calculated_90d,
        "beta_calculated_90d_r_squared": beta_calculated_90d_r_squared,
        "beta_calculated_90d_observations": beta_calculated_90d_observations,
        "beta_provider_1y": beta_provider_1y,
        "beta_portfolio_regression": None,  # Reserved for future (portfolio-level direct regression)
        # Phase 1: Sector exposure and concentration
        "sector_exposure": sector_exposure_json,
        "hhi": hhi,
        "effective_num_positions": effective_num_positions,
        "top_3_concentration": top_3_concentration,
        "top_10_concentration": top_10_concentration,
        # Phase 2: Volatility analytics
        "realized_volatility_21d": realized_volatility_21d,
        "realized_volatility_63d": realized_volatility_63d,
        "expected_volatility_21d": expected_volatility_21d,
        "volatility_trend": volatility_trend,
        "volatility_percentile": volatility_percentile
    }

    if existing_snapshot:
        # Update existing snapshot
        for key, value in snapshot_data.items():
            setattr(existing_snapshot, key, value)
        snapshot = existing_snapshot
        logger.info(f"Updated existing snapshot for {calculation_date}")
    else:
        # Create new snapshot
        snapshot = PortfolioSnapshot(**snapshot_data)
        db.add(snapshot)
        logger.info(f"Created new snapshot for {calculation_date}")

    return snapshot


async def _create_zero_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> PortfolioSnapshot:
    """Create a snapshot with zero values when no positions exist"""
    zero_decimal = Decimal('0')

    snapshot = PortfolioSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=calculation_date,
        net_asset_value=zero_decimal,
        cash_value=zero_decimal,
        long_value=zero_decimal,
        short_value=zero_decimal,
        gross_exposure=zero_decimal,
        net_exposure=zero_decimal,
        daily_pnl=zero_decimal,
        daily_return=zero_decimal,
        cumulative_pnl=zero_decimal,
        portfolio_delta=zero_decimal,
        portfolio_gamma=zero_decimal,
        portfolio_theta=zero_decimal,
        portfolio_vega=zero_decimal,
        num_positions=0,
        num_long_positions=0,
        num_short_positions=0
    )

    db.add(snapshot)
    await db.commit()

    return snapshot


async def cleanup_incomplete_snapshots(
    db: AsyncSession,
    age_threshold_hours: int = 1,
    portfolio_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Clean up incomplete snapshots (is_complete=False) that are older than threshold.

    This handles cases where batch processing crashed mid-calculation, leaving
    placeholder snapshots that would block retries due to unique constraint.

    Phase 2.10: Automated cleanup for stale placeholders

    Args:
        db: Database session
        age_threshold_hours: Delete placeholders older than this (default: 1 hour)
        portfolio_id: Optional - only clean up specific portfolio

    Returns:
        Dictionary with cleanup results:
        {
            'success': bool,
            'incomplete_found': int,
            'incomplete_deleted': int,
            'deleted_ids': List[UUID]
        }
    """
    from datetime import timedelta
    from sqlalchemy import delete

    logger.info(f"Starting cleanup of incomplete snapshots (age > {age_threshold_hours}h)")

    # Calculate cutoff time (UTC)
    cutoff_time = datetime.utcnow() - timedelta(hours=age_threshold_hours)

    # Find incomplete snapshots older than threshold
    query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.is_complete == False,  # noqa: E712
            PortfolioSnapshot.created_at < cutoff_time
        )
    )

    if portfolio_id:
        query = query.where(PortfolioSnapshot.portfolio_id == portfolio_id)

    result = await db.execute(query)
    incomplete_snapshots = result.scalars().all()

    incomplete_found = len(incomplete_snapshots)
    deleted_ids = [snapshot.id for snapshot in incomplete_snapshots]

    logger.info(f"Found {incomplete_found} incomplete snapshots older than {cutoff_time}")

    if incomplete_found == 0:
        return {
            'success': True,
            'incomplete_found': 0,
            'incomplete_deleted': 0,
            'deleted_ids': []
        }

    # Log snapshots to be deleted (for audit trail)
    for snapshot in incomplete_snapshots:
        age_hours = (datetime.utcnow() - snapshot.created_at).total_seconds() / 3600
        logger.warning(
            f"Deleting incomplete snapshot: "
            f"portfolio={snapshot.portfolio_id}, "
            f"date={snapshot.snapshot_date}, "
            f"id={snapshot.id}, "
            f"age={age_hours:.1f}h"
        )

    # Delete incomplete snapshots
    delete_query = delete(PortfolioSnapshot).where(
        PortfolioSnapshot.id.in_(deleted_ids)
    )

    delete_result = await db.execute(delete_query)
    deleted_count = delete_result.rowcount

    await db.commit()

    logger.info(f"Cleanup complete: deleted {deleted_count} incomplete snapshots")

    return {
        'success': True,
        'incomplete_found': incomplete_found,
        'incomplete_deleted': deleted_count,
        'deleted_ids': deleted_ids
    }
