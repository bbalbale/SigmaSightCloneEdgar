"""
Portfolio snapshot generation for daily portfolio state tracking
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.positions import Position, PositionType
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionGreeks
from app.calculations.portfolio import (
    calculate_portfolio_exposures,
    aggregate_portfolio_greeks
)
from app.calculations.market_data import calculate_position_market_value
from app.utils.trading_calendar import trading_calendar

logger = logging.getLogger(__name__)


async def create_portfolio_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Generate a complete daily snapshot of portfolio state
    
    Args:
        db: Database session
        portfolio_id: UUID of the portfolio
        calculation_date: Date for the snapshot (typically today)
        
    Returns:
        Dictionary with snapshot creation results
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
        
        # Step 4: Aggregate Greeks
        greeks = aggregate_portfolio_greeks(positions_list)
        
        # Step 5: Calculate P&L
        pnl_data = await _calculate_pnl(db, portfolio_id, calculation_date, aggregations['gross_exposure'])
        
        # Step 6: Count position types
        position_counts = _count_positions(active_positions)
        
        # Step 7: Create or update snapshot
        snapshot = await _create_or_update_snapshot(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            aggregations=aggregations,
            greeks=greeks,
            pnl_data=pnl_data,
            position_counts=position_counts
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Snapshot created successfully",
            "snapshot": snapshot,
            "statistics": {
                "positions_processed": len(active_positions),
                "total_value": float(aggregations['gross_exposure']),
                "daily_pnl": float(pnl_data['daily_pnl']),
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
    """Prepare position data with market values and Greeks"""
    position_data = []
    warnings = []
    
    # Import needed for price lookup
    from app.models.market_data import MarketDataCache
    from sqlalchemy import select, and_
    
    for position in positions:
        try:
            # First, get the price for this position as of calculation_date
            price_query = select(MarketDataCache.close).where(
                and_(
                    MarketDataCache.symbol == position.symbol,
                    MarketDataCache.date <= calculation_date
                )
            ).order_by(MarketDataCache.date.desc()).limit(1)
            
            price_result = await db.execute(price_query)
            current_price = price_result.scalar_one_or_none()
            
            if current_price is None:
                warnings.append(f"No price data available for {position.symbol} as of {calculation_date}")
                continue
            
            # Calculate market value with correct function signature
            market_value_result = await calculate_position_market_value(
                position=position,
                current_price=Decimal(str(current_price))
            )
            
            # Fetch Greeks if available
            greeks_query = select(PositionGreeks).where(
                and_(
                    PositionGreeks.position_id == position.id,
                    PositionGreeks.calculation_date == calculation_date
                )
            )
            greeks_result = await db.execute(greeks_query)
            greeks_record = greeks_result.scalar_one_or_none()
            
            greeks = None
            if greeks_record:
                greeks = {
                    "delta": greeks_record.delta,
                    "gamma": greeks_record.gamma,
                    "theta": greeks_record.theta,
                    "vega": greeks_record.vega,
                    "rho": greeks_record.rho
                }
            elif _is_options_position(position):
                warnings.append(f"Missing Greeks for options position {position.symbol}")
            
            position_data.append({
                "id": position.id,
                "symbol": position.symbol,
                "quantity": position.quantity,
                "market_value": market_value_result["market_value"],  # Always positive
                "exposure": market_value_result["exposure"],          # Signed value (negative for shorts)
                "position_type": position.position_type,
                "greeks": greeks
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
    daily_pnl = current_value - previous_snapshot.total_value
    daily_return = (daily_pnl / previous_snapshot.total_value) if previous_snapshot.total_value != 0 else Decimal('0')
    
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
    greeks: Dict[str, Decimal],
    pnl_data: Dict[str, Decimal],
    position_counts: Dict[str, int]
) -> PortfolioSnapshot:
    """Create or update portfolio snapshot AND update portfolio equity_balance"""

    # Import Portfolio model for equity_balance lookup
    from app.models.users import Portfolio
    from app.models.market_data import PositionMarketBeta

    # Get portfolio to access equity_balance
    portfolio_query = select(Portfolio).where(Portfolio.id == portfolio_id)
    portfolio_result = await db.execute(portfolio_query)
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # Phase 1 Implementation: Calculate today's equity from yesterday's equity + today's P&L
    # Get previous snapshot to find yesterday's equity_balance
    previous_snapshot_query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date < calculation_date
        )
    ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

    previous_result = await db.execute(previous_snapshot_query)
    previous_snapshot = previous_result.scalar_one_or_none()

    if previous_snapshot and previous_snapshot.equity_balance:
        # Use yesterday's equity + today's P&L
        previous_equity = previous_snapshot.equity_balance
        today_equity = previous_equity + pnl_data['daily_pnl']
        logger.info(
            f"Calculating equity for {portfolio_id}: "
            f"${float(previous_equity):,.2f} + ${float(pnl_data['daily_pnl']):,.2f} = ${float(today_equity):,.2f}"
        )
    else:
        # First snapshot - use seed value from portfolio table
        today_equity = portfolio.equity_balance or Decimal('0')
        logger.info(
            f"First snapshot for {portfolio_id}, using seed equity: ${float(today_equity):,.2f}"
        )

    # Update portfolio table with current equity
    portfolio.equity_balance = today_equity
    await db.flush()

    # Fetch market beta data (Phase 0: Single-factor model)
    market_beta_query = select(PositionMarketBeta).where(
        and_(
            PositionMarketBeta.portfolio_id == portfolio_id,
            PositionMarketBeta.calc_date == calculation_date
        )
    )
    market_beta_result = await db.execute(market_beta_query)
    market_beta_records = market_beta_result.scalars().all()

    # Calculate portfolio-level market beta (equity-weighted average)
    market_beta_weighted = None
    market_beta_r_squared = None
    market_beta_observations = None

    if market_beta_records and today_equity > 0:
        total_weighted_beta = Decimal('0')
        total_weighted_r_squared = Decimal('0')
        min_observations = None

        for beta_record in market_beta_records:
            # Get position to find market value
            position_query = select(Position).where(Position.id == beta_record.position_id)
            position_result = await db.execute(position_query)
            position = position_result.scalar_one_or_none()

            if position and position.market_value:
                weight = position.market_value / today_equity
                total_weighted_beta += beta_record.beta * weight
                total_weighted_r_squared += (beta_record.r_squared or Decimal('0')) * weight

                # Track minimum observations
                if min_observations is None or beta_record.observations < min_observations:
                    min_observations = beta_record.observations

        market_beta_weighted = total_weighted_beta
        market_beta_r_squared = total_weighted_r_squared
        market_beta_observations = min_observations

        logger.info(
            f"Market beta for snapshot: {float(market_beta_weighted):.3f} "
            f"(R²={float(market_beta_r_squared):.3f}, obs={market_beta_observations})"
        )
    else:
        logger.info("No market beta data available for snapshot")

    # Phase 1: Sector exposure and concentration metrics
    sector_exposure_json = None
    hhi = None
    effective_num_positions = None
    top_3_concentration = None
    top_10_concentration = None

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

    # Phase 2: Volatility analytics
    realized_volatility_21d = None
    realized_volatility_63d = None
    expected_volatility_21d = None
    volatility_trend = None
    volatility_percentile = None

    try:
        from app.calculations.volatility_analytics import calculate_portfolio_volatility_batch

        volatility_result = await calculate_portfolio_volatility_batch(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date
        )

        if volatility_result.get('success'):
            # Extract portfolio-level volatility data
            if volatility_result.get('portfolio_volatility'):
                pv = volatility_result['portfolio_volatility']
                realized_volatility_21d = Decimal(str(pv.get('realized_volatility_21d', 0))) if pv.get('realized_volatility_21d') else None
                realized_volatility_63d = Decimal(str(pv.get('realized_volatility_63d', 0))) if pv.get('realized_volatility_63d') else None
                expected_volatility_21d = Decimal(str(pv.get('expected_volatility_21d', 0))) if pv.get('expected_volatility_21d') else None
                volatility_trend = pv.get('volatility_trend')
                volatility_percentile = Decimal(str(pv.get('volatility_percentile', 0))) if pv.get('volatility_percentile') else None
                logger.info(
                    f"Volatility metrics: 21d={float(realized_volatility_21d) if realized_volatility_21d else 0:.2%}, "
                    f"expected={float(expected_volatility_21d) if expected_volatility_21d else 0:.2%}, "
                    f"trend={volatility_trend}"
                )
        else:
            logger.warning(f"Volatility analytics failed for snapshot: {volatility_result.get('error')}")
    except Exception as e:
        logger.warning(f"Could not calculate volatility metrics for snapshot: {e}")

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
        "total_value": aggregations['gross_exposure'],
        "cash_value": Decimal('0'),  # Fully invested assumption
        "long_value": aggregations['long_exposure'],
        "short_value": aggregations['short_exposure'],
        "gross_exposure": aggregations['gross_exposure'],
        "net_exposure": aggregations['net_exposure'],
        "daily_pnl": pnl_data['daily_pnl'],
        "daily_return": pnl_data['daily_return'],
        "cumulative_pnl": pnl_data['cumulative_pnl'],
        "portfolio_delta": greeks['delta'],
        "portfolio_gamma": greeks['gamma'],
        "portfolio_theta": greeks['theta'],
        "portfolio_vega": greeks['vega'],
        "num_positions": position_counts['total'],
        "num_long_positions": position_counts['long'],
        "num_short_positions": position_counts['short'],
        "equity_balance": today_equity,  # Use calculated equity
        # Phase 0: Market beta (single-factor model)
        "market_beta_weighted": market_beta_weighted,
        "market_beta_r_squared": market_beta_r_squared,
        "market_beta_observations": market_beta_observations,
        "market_beta_direct": None,  # Reserved for Phase 3 (portfolio-level regression)
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
        total_value=zero_decimal,
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


def _is_options_position(position: Position) -> bool:
    """Check if position is an options position"""
    return position.position_type in [
        PositionType.LC, PositionType.LP, 
        PositionType.SC, PositionType.SP
    ]