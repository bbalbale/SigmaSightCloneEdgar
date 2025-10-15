"""
Market Risk Scenarios Calculation Functions - Section 1.4.5
Implements market risk scenarios using factor-based approach and interest rate scenarios
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import statsmodels.api as sm
from fredapi import Fred

from app.models.positions import Position
from app.models.market_data import MarketRiskScenario, PositionInterestRateBeta, FactorDefinition
from app.models.users import Portfolio
from app.calculations.factors import fetch_factor_returns, _aggregate_portfolio_betas
from app.calculations.factor_utils import get_position_market_value
from app.constants.factors import (
    FACTOR_ETFS, REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS,
    BETA_CAP_LIMIT, OPTIONS_MULTIPLIER
)
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)

# Market risk scenario constants
MARKET_SCENARIOS = {
    'market_up_5': 0.05,      # +5% market movement
    'market_down_5': -0.05,   # -5% market movement
    'market_up_10': 0.10,     # +10% market movement
    'market_down_10': -0.10,  # -10% market movement
    'market_up_20': 0.20,     # +20% market movement
    'market_down_20': -0.20,  # -20% market movement
}

INTEREST_RATE_SCENARIOS = {
    'ir_up_100bp': 0.01,      # +100 basis points
    'ir_down_100bp': -0.01,   # -100 basis points
    'ir_up_200bp': 0.02,      # +200 basis points
    'ir_down_200bp': -0.02,   # -200 basis points
}

# FRED series IDs for Treasury yields
TREASURY_SERIES = {
    '3M': 'DGS3MO',    # 3-Month Treasury
    '2Y': 'DGS2',      # 2-Year Treasury  
    '10Y': 'DGS10',    # 10-Year Treasury
    '30Y': 'DGS30',    # 30-Year Treasury
}


async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate portfolio market beta using existing factor betas
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID to analyze
        calculation_date: Date for the calculation
        
    Returns:
        Dictionary containing market beta and factor breakdown
    """
    logger.info(f"Calculating portfolio market beta for portfolio {portfolio_id}")
    
    try:
        # Get active positions for the portfolio
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        if not positions:
            raise ValueError(f"No active positions found for portfolio {portfolio_id}")
        
        # Get existing factor betas (reuse from Section 1.4.4)
        from app.calculations.factors import calculate_factor_betas_hybrid
        
        factor_analysis = await calculate_factor_betas_hybrid(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            use_delta_adjusted=False
        )
        
        portfolio_betas = factor_analysis['factor_betas']
        
        # Calculate market beta (SPY factor represents broad market exposure)
        market_beta = portfolio_betas.get('Market', 0.0)  # 'Market' from SPY factor
        
        # Calculate portfolio value for exposure calculations using centralized utility
        portfolio_value = Decimal('0')
        for position in positions:
            value = get_position_market_value(position, recalculate=True)
            portfolio_value += value
        
        results = {
            'portfolio_id': str(portfolio_id),
            'calculation_date': calculation_date,
            'market_beta': market_beta,
            'portfolio_value': float(portfolio_value),
            'factor_breakdown': portfolio_betas,
            'data_quality': factor_analysis['data_quality'],
            'positions_count': len(positions)
        }
        
        logger.info(f"Portfolio market beta calculated: {market_beta:.4f}")
        return results
        
    except Exception as e:
        logger.error(f"Error calculating portfolio market beta: {str(e)}")
        raise


async def calculate_market_scenarios(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    scenarios: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Calculate portfolio P&L under various market scenarios using factor-based approach
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID to analyze
        calculation_date: Date for the calculation
        scenarios: Optional custom scenarios (defaults to MARKET_SCENARIOS)
        
    Returns:
        Dictionary containing scenario results and storage information
    """
    logger.info(f"Calculating market scenarios for portfolio {portfolio_id}")
    
    if scenarios is None:
        scenarios = MARKET_SCENARIOS
    
    try:
        # Get portfolio market beta
        market_data = await calculate_portfolio_market_beta(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date
        )
        
        market_beta = market_data['market_beta']
        portfolio_value = market_data['portfolio_value']
        
        # Calculate scenario P&L for each market scenario
        scenario_results = {}
        records_to_store = []
        
        for scenario_name, market_change in scenarios.items():
            # P&L = Portfolio Value × Market Beta × Market Change
            predicted_pnl = portfolio_value * market_beta * market_change
            
            scenario_results[scenario_name] = {
                'scenario_value': market_change,
                'predicted_pnl': predicted_pnl,
                'market_beta': market_beta
            }
            
            # Prepare record for database storage
            record = MarketRiskScenario(
                portfolio_id=portfolio_id,
                scenario_type=scenario_name,
                scenario_value=Decimal(str(market_change)),
                predicted_pnl=Decimal(str(predicted_pnl)),
                calculation_date=calculation_date
            )
            records_to_store.append(record)
        
        # Store scenario results in database
        for record in records_to_store:
            db.add(record)
        
        await db.commit()
        
        results = {
            'portfolio_id': str(portfolio_id),
            'calculation_date': calculation_date,
            'market_beta': market_beta,
            'portfolio_value': portfolio_value,
            'scenarios': scenario_results,
            'records_stored': len(records_to_store),
            'market_data_quality': market_data['data_quality']
        }
        
        logger.info(f"Market scenarios calculated and stored: {len(records_to_store)} scenarios")
        return results
        
    except Exception as e:
        logger.error(f"Error calculating market scenarios: {str(e)}")
        await db.rollback()
        raise


async def calculate_position_interest_rate_betas(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    treasury_series: str = '10Y'
) -> Dict[str, Any]:
    """
    Calculate position-level interest rate betas using Treasury yield data
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID to analyze
        calculation_date: Date for the calculation
        treasury_series: Treasury series to use (default: 10Y)
        
    Returns:
        Dictionary containing interest rate betas and storage information
    """
    logger.info(f"Calculating position interest rate betas for portfolio {portfolio_id}")
    
    try:
        # Initialize FRED API
        if not hasattr(settings, 'FRED_API_KEY') or not settings.FRED_API_KEY:
            logger.warning("FRED API key not configured, using mock data for interest rate betas")
            return await _calculate_mock_interest_rate_betas(db, portfolio_id, calculation_date)
        
        fred = Fred(api_key=settings.FRED_API_KEY)
        
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
            raise ValueError(f"No active positions found for portfolio {portfolio_id}")
        
        # Fetch Treasury yield data
        end_date = calculation_date
        start_date = end_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)
        
        fred_series = TREASURY_SERIES.get(treasury_series, 'DGS10')
        treasury_data = fred.get_series(
            fred_series, 
            observation_start=start_date, 
            observation_end=end_date
        )
        
        # Calculate Treasury yield changes (daily changes in basis points)
        # Using fill_method=None to avoid FutureWarning (Pandas 2.1+)
        treasury_changes = treasury_data.pct_change(fill_method=None).dropna() * 10000  # Convert to basis points
        
        if len(treasury_changes) < MIN_REGRESSION_DAYS:
            logger.warning(f"Insufficient Treasury data: {len(treasury_changes)} days")
        
        # Get position returns (reuse from factor calculations)
        from app.calculations.factors import calculate_position_returns
        
        position_returns = await calculate_position_returns(
            db=db,
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
            use_delta_adjusted=False
        )
        
        if position_returns.empty:
            raise ValueError("No position returns data available")
        
        # Align data on common dates
        common_dates = treasury_changes.index.intersection(position_returns.index)
        
        if len(common_dates) < MIN_REGRESSION_DAYS:
            logger.warning(f"Insufficient overlapping data: {len(common_dates)} days")
        
        treasury_aligned = treasury_changes.loc[common_dates]
        returns_aligned = position_returns.loc[common_dates]
        
        # Calculate interest rate beta for each position
        position_ir_betas = {}
        records_to_store = []
        
        for position_id in returns_aligned.columns:
            try:
                # Get position and treasury data
                y = returns_aligned[position_id].values  # Position returns
                x = treasury_aligned.values  # Treasury changes
                
                # Run OLS regression: Position Return = α + β × Treasury Change + ε
                x_with_const = sm.add_constant(x)
                model = sm.OLS(y, x_with_const).fit()
                
                # Extract interest rate beta (slope coefficient)
                ir_beta = model.params[1] if len(model.params) > 1 else 0.0
                r_squared = model.rsquared
                
                # Cap beta to prevent extreme outliers
                ir_beta = max(-BETA_CAP_LIMIT, min(BETA_CAP_LIMIT, ir_beta))
                
                position_ir_betas[position_id] = {
                    'ir_beta': float(ir_beta),
                    'r_squared': float(r_squared)
                }
                
                # Prepare record for database storage
                record = PositionInterestRateBeta(
                    position_id=UUID(position_id),
                    ir_beta=Decimal(str(ir_beta)),
                    r_squared=Decimal(str(r_squared)),
                    calculation_date=calculation_date
                )
                records_to_store.append(record)
                
            except Exception as e:
                logger.error(f"Error calculating IR beta for position {position_id}: {str(e)}")
                # Set default values on error
                position_ir_betas[position_id] = {'ir_beta': 0.0, 'r_squared': 0.0}
        
        # Store results in database
        for record in records_to_store:
            db.add(record)
        
        await db.commit()
        
        results = {
            'portfolio_id': str(portfolio_id),
            'calculation_date': calculation_date,
            'treasury_series': treasury_series,
            'position_ir_betas': position_ir_betas,
            'records_stored': len(records_to_store),
            'regression_days': len(common_dates),
            'treasury_data_points': len(treasury_changes)
        }
        
        logger.info(f"Interest rate betas calculated: {len(position_ir_betas)} positions")
        return results
        
    except Exception as e:
        logger.error(f"Error calculating interest rate betas: {str(e)}")
        await db.rollback()
        raise


async def calculate_interest_rate_scenarios(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    scenarios: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Calculate portfolio P&L under interest rate scenarios
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID to analyze
        calculation_date: Date for the calculation
        scenarios: Optional custom scenarios (defaults to INTEREST_RATE_SCENARIOS)
        
    Returns:
        Dictionary containing interest rate scenario results
    """
    logger.info(f"Calculating interest rate scenarios for portfolio {portfolio_id}")
    
    if scenarios is None:
        scenarios = INTEREST_RATE_SCENARIOS
    
    try:
        # Get position interest rate betas
        ir_data = await calculate_position_interest_rate_betas(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date
        )
        
        position_ir_betas = ir_data['position_ir_betas']
        
        # Get position values for weighting
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        # Calculate portfolio-weighted interest rate beta
        total_value = Decimal('0')
        weighted_ir_beta = 0.0
        
        for position in positions:
            position_id = str(position.id)
            if position_id in position_ir_betas:
                value = get_position_market_value(position, recalculate=True)
                total_value += value

                ir_beta = position_ir_betas[position_id]['ir_beta']
                weighted_ir_beta += ir_beta * float(value)
        
        if total_value > 0:
            weighted_ir_beta /= float(total_value)
        
        # Calculate scenario P&L for each interest rate scenario
        scenario_results = {}
        records_to_store = []
        
        for scenario_name, rate_change in scenarios.items():
            # P&L = Portfolio Value × Interest Rate Beta × Rate Change (in basis points)
            rate_change_bp = rate_change * 10000  # Convert to basis points
            predicted_pnl = float(total_value) * weighted_ir_beta * rate_change_bp
            
            scenario_results[scenario_name] = {
                'scenario_value': rate_change,
                'rate_change_bp': rate_change_bp,
                'predicted_pnl': predicted_pnl,
                'portfolio_ir_beta': weighted_ir_beta
            }
            
            # Store as market risk scenario with IR scenario type
            record = MarketRiskScenario(
                portfolio_id=portfolio_id,
                scenario_type=scenario_name,
                scenario_value=Decimal(str(rate_change)),
                predicted_pnl=Decimal(str(predicted_pnl)),
                calculation_date=calculation_date
            )
            records_to_store.append(record)
        
        # Store scenario results
        for record in records_to_store:
            db.add(record)
        
        await db.commit()
        
        results = {
            'portfolio_id': str(portfolio_id),
            'calculation_date': calculation_date,
            'portfolio_ir_beta': weighted_ir_beta,
            'portfolio_value': float(total_value),
            'scenarios': scenario_results,
            'records_stored': len(records_to_store),
            'position_count': len(positions)
        }
        
        logger.info(f"Interest rate scenarios calculated: {len(scenario_results)} scenarios")
        return results
        
    except Exception as e:
        logger.error(f"Error calculating interest rate scenarios: {str(e)}")
        await db.rollback()
        raise


# Helper functions

def _is_options_position(position: Position) -> bool:
    """Check if position is an options position"""
    from app.models.positions import PositionType
    return position.position_type in [
        PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP
    ]


async def _calculate_mock_interest_rate_betas(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate mock interest rate betas when FRED API is not available
    Uses simplified assumptions based on position types
    """
    logger.info("Using mock interest rate betas (FRED API not configured)")
    
    # Get active positions
    stmt = select(Position).where(
        and_(
            Position.portfolio_id == portfolio_id,
            Position.exit_date.is_(None)
        )
    )
    result = await db.execute(stmt)
    positions = result.scalars().all()
    
    position_ir_betas = {}
    records_to_store = []
    
    for position in positions:
        # Simple heuristic: bonds have higher IR sensitivity, stocks have lower
        # This is a simplified approach for when real Treasury data isn't available
        if 'TLT' in position.symbol.upper() or 'IEF' in position.symbol.upper():
            # Treasury ETFs: high interest rate sensitivity
            ir_beta = -0.05  # Negative: bond prices fall when rates rise
            r_squared = 0.8
        elif 'REIT' in position.symbol.upper() or 'REI' in position.symbol.upper():
            # REITs: moderate interest rate sensitivity
            ir_beta = -0.02
            r_squared = 0.4
        else:
            # Regular stocks: low interest rate sensitivity
            ir_beta = -0.01
            r_squared = 0.2
        
        position_ir_betas[str(position.id)] = {
            'ir_beta': ir_beta,
            'r_squared': r_squared
        }
        
        # Store in database
        record = PositionInterestRateBeta(
            position_id=position.id,
            ir_beta=Decimal(str(ir_beta)),
            r_squared=Decimal(str(r_squared)),
            calculation_date=calculation_date
        )
        records_to_store.append(record)
    
    # Store results
    for record in records_to_store:
        db.add(record)
    
    await db.commit()
    
    return {
        'portfolio_id': str(portfolio_id),
        'calculation_date': calculation_date,
        'treasury_series': 'MOCK',
        'position_ir_betas': position_ir_betas,
        'records_stored': len(records_to_store),
        'regression_days': 0,  # Mock data
        'treasury_data_points': 0  # Mock data
    }