"""
Interest Rate Beta Integration for Stress Testing
Fetches IR betas and calculates IR shock impacts

Created: 2025-10-18
Integrates with: stress_testing.py for comprehensive stress testing
"""
from datetime import date
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.positions import Position
from app.models.market_data import PositionInterestRateBeta
from app.calculations.market_data import get_position_value
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_portfolio_ir_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    max_staleness_days: int = 7
) -> Dict[str, Any]:
    """
    Get portfolio-level IR beta from stored position IR betas.

    Calculates equity-weighted average IR beta for stress testing.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Date for stress test
        max_staleness_days: Maximum days IR beta can be old (default 7)

    Returns:
        {
            'portfolio_ir_beta': float,
            'ir_beta_date': date,
            'positions_with_beta': int,
            'total_positions': int,
            'portfolio_equity': float,
            'success': bool,
            'error': str (if failed)
        }
    """
    from datetime import timedelta
    from app.models.users import Portfolio

    try:
        # Get portfolio equity
        portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio or not portfolio.equity_balance or portfolio.equity_balance <= 0:
            return {
                'success': False,
                'error': 'Invalid portfolio or equity balance'
            }

        portfolio_equity = float(portfolio.equity_balance)

        # Get active positions
        positions_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None),
                Position.deleted_at.is_(None)
            )
        )
        positions_result = await db.execute(positions_stmt)
        positions = positions_result.scalars().all()

        if not positions:
            return {
                'success': False,
                'error': 'No active positions found'
            }

        # Fetch most recent IR betas for these positions
        # Allow some staleness (default 7 days)
        min_date = calculation_date - timedelta(days=max_staleness_days)

        position_ids = [p.id for p in positions]

        # Get latest IR beta for each position
        ir_beta_stmt = select(PositionInterestRateBeta).where(
            and_(
                PositionInterestRateBeta.position_id.in_(position_ids),
                PositionInterestRateBeta.calculation_date >= min_date,
                PositionInterestRateBeta.calculation_date <= calculation_date
            )
        ).order_by(PositionInterestRateBeta.calculation_date.desc())

        ir_beta_result = await db.execute(ir_beta_stmt)
        all_ir_betas = ir_beta_result.scalars().all()

        # Build map of position_id -> latest IR beta
        position_ir_betas = {}
        position_ir_dates = {}

        for ir_beta_record in all_ir_betas:
            if ir_beta_record.position_id not in position_ir_betas:
                position_ir_betas[ir_beta_record.position_id] = float(ir_beta_record.ir_beta)
                position_ir_dates[ir_beta_record.position_id] = ir_beta_record.calculation_date

        if not position_ir_betas:
            return {
                'success': False,
                'error': f'No IR betas found for any positions (checked {max_staleness_days} days back)'
            }

        # Calculate equity-weighted portfolio IR beta
        total_weighted_ir_beta = 0.0
        total_weight = 0.0
        positions_with_beta = 0

        for position in positions:
            if position.id in position_ir_betas:
                market_value = float(get_position_value(position, signed=False, recalculate=True))
                weight = market_value / portfolio_equity

                ir_beta = position_ir_betas[position.id]
                total_weighted_ir_beta += ir_beta * weight
                total_weight += weight
                positions_with_beta += 1

        # Get most recent IR beta calculation date
        latest_ir_date = max(position_ir_dates.values()) if position_ir_dates else calculation_date

        result = {
            'portfolio_ir_beta': total_weighted_ir_beta,
            'ir_beta_date': latest_ir_date,
            'positions_with_beta': positions_with_beta,
            'total_positions': len(positions),
            'portfolio_equity': portfolio_equity,
            'total_weight': total_weight,
            'success': True
        }

        logger.info(
            f"Portfolio IR beta: {total_weighted_ir_beta:.4f} "
            f"({positions_with_beta}/{len(positions)} positions, beta date: {latest_ir_date})"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting portfolio IR beta: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def calculate_ir_shock_impact(
    db: AsyncSession,
    portfolio_id: UUID,
    ir_shock_bps: float,
    calculation_date: date,
    max_staleness_days: int = 7
) -> Dict[str, Any]:
    """
    Calculate portfolio P&L impact from interest rate shock.

    Uses stored IR betas from position_interest_rate_betas table.

    Formula:
        IR P&L = Portfolio Value × IR Beta × Shock (in decimal)

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        ir_shock_bps: Interest rate shock in basis points (e.g., 100 for +100bp)
        calculation_date: Date for calculation
        max_staleness_days: Maximum days IR beta can be old

    Returns:
        {
            'ir_shock_bps': float,
            'ir_shock_pct': float (decimal, e.g., 0.01 for 100bp),
            'portfolio_ir_beta': float,
            'portfolio_value': float,
            'predicted_pnl': float,
            'positions_with_beta': int,
            'total_positions': int,
            'ir_beta_date': date,
            'success': bool,
            'error': str (if failed)
        }
    """
    try:
        # Get portfolio IR beta
        ir_beta_data = await get_portfolio_ir_beta(
            db, portfolio_id, calculation_date, max_staleness_days
        )

        if not ir_beta_data['success']:
            return {
                'success': False,
                'error': ir_beta_data.get('error', 'Failed to get IR beta')
            }

        portfolio_ir_beta = ir_beta_data['portfolio_ir_beta']
        portfolio_equity = ir_beta_data['portfolio_equity']

        # Convert basis points to decimal (100bp = 0.01)
        ir_shock_pct = ir_shock_bps / 10000.0

        # Calculate predicted P&L
        # Note: IR beta is typically negative (rates up → stocks down)
        predicted_pnl = portfolio_equity * portfolio_ir_beta * ir_shock_pct

        result = {
            'ir_shock_bps': ir_shock_bps,
            'ir_shock_pct': ir_shock_pct,
            'portfolio_ir_beta': portfolio_ir_beta,
            'portfolio_value': portfolio_equity,
            'predicted_pnl': predicted_pnl,
            'positions_with_beta': ir_beta_data['positions_with_beta'],
            'total_positions': ir_beta_data['total_positions'],
            'ir_beta_date': ir_beta_data['ir_beta_date'],
            'success': True
        }

        logger.info(
            f"IR shock impact: {ir_shock_bps:+.0f}bp shock → ${predicted_pnl:,.0f} P&L "
            f"(β_IR={portfolio_ir_beta:.4f}, portfolio=${portfolio_equity:,.0f})"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating IR shock impact: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Integration function to be called from stress_testing.py
async def add_ir_shocks_to_stress_results(
    db: AsyncSession,
    portfolio_id: UUID,
    shocked_factors: Dict[str, float],
    calculation_date: date
) -> Dict[str, Any]:
    """
    Add Interest_Rate shock impacts to stress test results.

    This function is called by stress_testing.py when IR shocks are in the scenario.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        shocked_factors: Dict of factor shocks (may include "Interest_Rate")
        calculation_date: Date for calculation

    Returns:
        {
            'has_ir_shock': bool,
            'ir_impact': Dict (if IR shock exists),
            'ir_exposure_dollar': float (for consistency with factor exposures)
        }
    """
    if 'Interest_Rate' not in shocked_factors:
        return {
            'has_ir_shock': False,
            'ir_impact': None,
            'ir_exposure_dollar': None
        }

    # Get IR shock amount (stored as decimal, e.g., 0.01 for 100bp)
    ir_shock_decimal = shocked_factors['Interest_Rate']
    ir_shock_bps = ir_shock_decimal * 10000  # Convert to basis points

    # Calculate IR impact
    ir_impact = await calculate_ir_shock_impact(
        db, portfolio_id, ir_shock_bps, calculation_date
    )

    if not ir_impact['success']:
        logger.warning(
            f"Could not calculate IR impact: {ir_impact.get('error')}. "
            "IR shock will be skipped in stress test."
        )
        return {
            'has_ir_shock': True,
            'ir_impact': None,
            'ir_exposure_dollar': None
        }

    # Calculate exposure_dollar for consistency with factor exposures
    # exposure_dollar = portfolio_value × beta
    ir_exposure_dollar = ir_impact['portfolio_value'] * ir_impact['portfolio_ir_beta']

    return {
        'has_ir_shock': True,
        'ir_impact': ir_impact,
        'ir_exposure_dollar': ir_exposure_dollar
    }
