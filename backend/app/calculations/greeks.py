"""
Options Greeks Calculation Functions - Section 1.4.2
Implements V1.4 hybrid real/mock Greeks calculations with database integration
"""
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.models.positions import Position, PositionType
from app.models.market_data import PositionGreeks
from app.core.logging import get_logger

logger = get_logger(__name__)

# Import calculation libraries
try:
    import mibian
    MIBIAN_AVAILABLE = True
except ImportError:
    logger.warning("mibian not available, falling back to mock calculations")
    MIBIAN_AVAILABLE = False





def is_options_position(position: Position) -> bool:
    """
    Determine if a position is an options position
    
    Args:
        position: Position object
        
    Returns:
        True if position is options (LC, LP, SC, SP), False if stock (LONG, SHORT)
    """
    return position.position_type in [
        PositionType.LC,  # Long Call
        PositionType.LP,  # Long Put
        PositionType.SC,  # Short Call
        PositionType.SP   # Short Put
    ]


def is_expired_option(position: Position) -> bool:
    """
    Check if an options position has expired
    
    Args:
        position: Position object
        
    Returns:
        True if option is expired, False otherwise
    """
    if not is_options_position(position) or not position.expiration_date:
        return False
    
    return position.expiration_date < date.today()


def calculate_time_to_expiry(expiry_date: date) -> float:
    """
    Calculate time to expiry in years using calendar days / 365 convention
    
    Args:
        expiry_date: Option expiration date
        
    Returns:
        Time to expiry in years (float)
    """
    today = date.today()
    if expiry_date <= today:
        return 0.0
    
    days_to_expiry = (expiry_date - today).days
    return days_to_expiry / 365.0


def extract_option_parameters(position: Position) -> Dict[str, Any]:
    """
    Extract option parameters from position for Greeks calculation
    
    Args:
        position: Position object
        
    Returns:
        Dictionary with option parameters or None if invalid
    """
    if not is_options_position(position):
        return None
    
    if not all([position.strike_price, position.expiration_date, position.underlying_symbol]):
        logger.warning(f"Missing option parameters for position {position.id}")
        return None
    
    return {
        "strike": float(position.strike_price),
        "expiry_date": position.expiration_date,
        "time_to_expiry": calculate_time_to_expiry(position.expiration_date),
        "option_type": "c" if position.position_type in [PositionType.LC, PositionType.SC] else "p",
        "underlying_symbol": position.underlying_symbol
    }


def get_implied_volatility(symbol: str, market_data: Dict[str, Any]) -> float:
    """
    Retrieve or estimate implied volatility for option pricing
    
    Args:
        symbol: Underlying symbol
        market_data: Market data dictionary
        
    Returns:
        Implied volatility (default: 0.25 or 25%)
    """
    if market_data and symbol in market_data:
        symbol_data = market_data[symbol]
        if isinstance(symbol_data, dict) and "implied_volatility" in symbol_data:
            return float(symbol_data["implied_volatility"])
    
    # Default fallback volatility
    return 0.25


def get_risk_free_rate(market_data: Dict[str, Any]) -> float:
    """
    Get risk-free rate for Greeks calculation
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Risk-free rate (default: 0.05 or 5%)
    """
    if market_data and "risk_free_rate" in market_data:
        return float(market_data["risk_free_rate"])
    
    # Default risk-free rate
    return 0.05


def calculate_real_greeks(
    underlying_price: float,
    strike: float,
    time_to_expiry: float,
    volatility: float,
    risk_free_rate: float,
    option_type: str
) -> Dict[str, float]:
    """
    Calculate real Greeks using mibian Black-Scholes model
    
    Args:
        underlying_price: Current underlying price
        strike: Strike price
        time_to_expiry: Time to expiry in years
        volatility: Implied volatility
        risk_free_rate: Risk-free rate
        option_type: "c" for call, "p" for put
        
    Returns:
        Dictionary with all 5 Greeks
    """
    if not MIBIAN_AVAILABLE:
        raise ImportError("mibian not available")
    
    try:
        # Convert time to expiry to days for mibian
        days_to_expiry = time_to_expiry * 365
        
        # Calculate Greeks using mibian
        if option_type.lower() == 'c':
            # Call option
            bs_model = mibian.BS([underlying_price, strike, risk_free_rate, days_to_expiry], volatility=volatility * 100)
        else:
            # Put option
            bs_model = mibian.BS([underlying_price, strike, risk_free_rate, days_to_expiry], volatility=volatility * 100)
        
        # Get Greeks - mibian returns them in different units
        delta_val = bs_model.callDelta if option_type.lower() == 'c' else bs_model.putDelta
        gamma_val = bs_model.gamma
        theta_val = bs_model.callTheta if option_type.lower() == 'c' else bs_model.putTheta
        vega_val = bs_model.vega
        rho_val = bs_model.callRho if option_type.lower() == 'c' else bs_model.putRho
        
        # Convert to appropriate units
        # mibian returns theta as daily, vega as per 1%, rho as per 1%
        return {
            "delta": float(delta_val),
            "gamma": float(gamma_val),
            "theta": float(theta_val),        # Already daily
            "vega": float(vega_val / 100.0),  # Convert to per 1% volatility
            "rho": float(rho_val / 100.0)     # Convert to per 1% interest rate
        }
        
    except Exception as e:
        logger.error(f"Real Greeks calculation failed: {str(e)}")
        raise




async def calculate_position_greeks(
    position: Position,
    market_data: Dict[str, Any]
) -> Optional[Dict[str, float]]:
    """
    Calculate Greeks using mibian Black-Scholes model
    
    Args:
        position: Position object (SQLAlchemy model or dict)
        market_data: Market data dictionary keyed by symbol
        
    Returns:
        Dictionary with all 5 Greeks as floats (scaled by quantity), or None if calculation fails
    """
    logger.debug(f"Calculating Greeks for position {position.id} ({position.symbol})")
    
    # Handle expired options
    if is_expired_option(position):
        logger.info(f"Position {position.symbol} is expired, returning zero Greeks")
        return {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0
        }
    
    # Handle stock positions - Greeks calculation not applicable
    if not is_options_position(position):
        logger.debug(f"Stock position {position.symbol}, Greeks calculation not applicable")
        return None
    
    # Calculate Greeks for options positions only
    try:
        option_params = extract_option_parameters(position)
        if not option_params:
            logger.error(f"Invalid option parameters for {position.symbol}, cannot calculate Greeks")
            return None
        
        # Get market data for underlying
        underlying_symbol = option_params["underlying_symbol"]
        if not market_data or underlying_symbol not in market_data:
            logger.error(f"No market data for {underlying_symbol}, cannot calculate Greeks")
            return None
        
        underlying_data = market_data[underlying_symbol]
        if not isinstance(underlying_data, dict) or "current_price" not in underlying_data:
            logger.error(f"Invalid market data for {underlying_symbol}, cannot calculate Greeks")
            return None
        
        underlying_price = float(underlying_data["current_price"])
        volatility = get_implied_volatility(underlying_symbol, market_data)
        risk_free_rate = get_risk_free_rate(market_data)
        
        # Calculate real Greeks using mibian
        real_greeks = calculate_real_greeks(
            underlying_price=underlying_price,
            strike=option_params["strike"],
            time_to_expiry=option_params["time_to_expiry"],
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            option_type=option_params["option_type"]
        )
        
        # Scale by quantity and handle short positions
        quantity_float = float(position.quantity)
        scaled_greeks = {
            "delta": real_greeks["delta"] * quantity_float,
            "gamma": real_greeks["gamma"] * quantity_float,
            "theta": real_greeks["theta"] * quantity_float,
            "vega": real_greeks["vega"] * quantity_float,
            "rho": real_greeks["rho"] * quantity_float
        }
        
        logger.debug(f"Greeks calculated for {position.symbol}: {scaled_greeks}")
        return scaled_greeks
        
    except Exception as e:
        logger.error(f"Greeks calculation failed for {position.symbol}: {str(e)}")
        return None


async def update_position_greeks(
    db: AsyncSession,
    position_id: str,
    greeks: Dict[str, float]
) -> None:
    """
    Insert or update position Greeks in the database
    
    Args:
        db: Database session
        position_id: Position ID
        greeks: Dictionary with Greeks values (must not be None)
    """
    if greeks is None:
        logger.warning(f"Cannot update Greeks for position {position_id}: Greeks is None")
        return
        
    try:
        # Calculate dollar Greeks (delta * 100 for options, gamma * 100 for options)
        multiplier = 100  # Options multiplier
        dollar_delta = greeks["delta"] * multiplier
        dollar_gamma = greeks["gamma"] * multiplier
        
        # Prepare upsert statement
        stmt = insert(PositionGreeks).values(
            position_id=position_id,
            calculation_date=date.today(),
            delta=Decimal(str(greeks["delta"])),
            gamma=Decimal(str(greeks["gamma"])),
            theta=Decimal(str(greeks["theta"])),
            vega=Decimal(str(greeks["vega"])),
            rho=Decimal(str(greeks["rho"])),
            delta_dollars=Decimal(str(dollar_delta)),
            gamma_dollars=Decimal(str(dollar_gamma)),
            updated_at=datetime.utcnow()
        )
        
        # Handle conflict by updating existing record
        stmt = stmt.on_conflict_do_update(
            index_elements=["position_id"],
            set_=dict(
                calculation_date=stmt.excluded.calculation_date,
                delta=stmt.excluded.delta,
                gamma=stmt.excluded.gamma,
                theta=stmt.excluded.theta,
                vega=stmt.excluded.vega,
                rho=stmt.excluded.rho,
                delta_dollars=stmt.excluded.delta_dollars,
                gamma_dollars=stmt.excluded.gamma_dollars,
                updated_at=stmt.excluded.updated_at
            )
        )
        
        await db.execute(stmt)
        logger.debug(f"Updated Greeks for position {position_id}")
        
    except Exception as e:
        logger.error(f"Error updating Greeks for position {position_id}: {str(e)}")
        raise


async def bulk_update_portfolio_greeks(
    db: AsyncSession,
    portfolio_id: str,
    market_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate and update Greeks for all positions in a portfolio
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
        market_data: Market data dictionary
        
    Returns:
        Summary dictionary with update results
    """
    logger.info(f"Starting bulk Greeks update for portfolio {portfolio_id}")

    try:
        # Get all positions for the portfolio
        # TODO: Add UUID conversion if this function is re-enabled in batch orchestrator
        # FIXME: portfolio_id is str, Position.portfolio_id is UUID - needs ensure_uuid() conversion
        # See Phase 7.0 UUID fixes in batch_orchestrator_v2.py for pattern
        stmt = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        if not positions:
            logger.warning(f"No positions found for portfolio {portfolio_id}")
            return {"updated": 0, "failed": 0, "errors": []}
        
        updated_count = 0
        failed_count = 0
        errors = []
        
        # Process positions in chunks of 100
        chunk_size = 100
        for i in range(0, len(positions), chunk_size):
            chunk = positions[i:i + chunk_size]
            
            for position in chunk:
                try:
                    # Calculate Greeks
                    greeks = await calculate_position_greeks(position, market_data)
                    
                    # Update database only if Greeks were calculated
                    if greeks is not None:
                        await update_position_greeks(db, position.id, greeks)
                        updated_count += 1
                    else:
                        # Greeks not applicable (stock position) or calculation failed
                        logger.debug(f"Skipping Greeks update for {position.symbol} (no Greeks calculated)")
                    
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Position {position.id} ({position.symbol}): {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        # Commit all updates
        await db.commit()
        
        summary = {
            "updated": updated_count,
            "failed": failed_count,
            "errors": errors,
            "total_positions": len(positions)
        }
        
        logger.info(f"Bulk Greeks update complete for portfolio {portfolio_id}: {summary}")
        return summary
        
    except Exception as e:
        logger.error(f"Bulk Greeks update failed for portfolio {portfolio_id}: {str(e)}")
        await db.rollback()
        raise


# Convenience functions for portfolio-level aggregations
async def aggregate_portfolio_greeks(positions_greeks: List[Optional[Dict[str, float]]]) -> Dict[str, float]:
    """
    Aggregate position-level Greeks to portfolio level
    
    Args:
        positions_greeks: List of position Greeks dictionaries (may contain None for non-option positions)
        
    Returns:
        Portfolio-level Greeks summary
    """
    if not positions_greeks:
        return {
            "total_delta": 0.0,
            "total_gamma": 0.0,
            "total_theta": 0.0,
            "total_vega": 0.0,
            "total_rho": 0.0
        }
    
    # Filter out None values (stock positions and failed calculations)
    valid_greeks = [pos for pos in positions_greeks if pos is not None]
    
    portfolio_greeks = {
        "total_delta": sum(pos.get("delta", 0.0) for pos in valid_greeks),
        "total_gamma": sum(pos.get("gamma", 0.0) for pos in valid_greeks),
        "total_theta": sum(pos.get("theta", 0.0) for pos in valid_greeks),
        "total_vega": sum(pos.get("vega", 0.0) for pos in valid_greeks),
        "total_rho": sum(pos.get("rho", 0.0) for pos in valid_greeks)
    }
    
    logger.debug(f"Portfolio Greeks aggregation: {portfolio_greeks}")
    return portfolio_greeks