"""
Portfolio Analytics Service

Service layer for portfolio analytics calculations including exposures, P&L metrics,
and aggregated portfolio data for dashboard consumption.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_
from uuid import UUID
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from app.models.users import Portfolio
from app.models.positions import Position, PositionType
from app.models.market_data import MarketDataCache, PositionGreeks, PositionFactorExposure
from app.core.datetime_utils import utc_now, to_utc_iso8601
from app.core.logging import get_logger

logger = get_logger(__name__)


class PortfolioAnalyticsService:
    """Service for portfolio analytics calculations"""
    
    async def get_portfolio_overview(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> Dict[str, Any]:
        """
        Get comprehensive portfolio overview with exposures, P&L, and position metrics.
        
        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            
        Returns:
            Dict with portfolio overview data matching API_SPECIFICATIONS_V1.4.5.md format
        """
        try:
            # Verify portfolio exists
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            # Get all positions with current market data
            positions_query = select(
                Position.id,
                Position.symbol,
                Position.position_type,
                Position.quantity,
                Position.entry_price,
                Position.last_price,
                Position.market_value,
                Position.unrealized_pnl,
                Position.realized_pnl,
                MarketDataCache.close.label('current_price'),
                MarketDataCache.updated_at.label('price_updated_at')
            ).outerjoin(
                MarketDataCache, MarketDataCache.symbol == Position.symbol
            ).where(
                Position.portfolio_id == portfolio_id
            )
            
            positions_result = await db.execute(positions_query)
            positions = positions_result.all()
            
            # Calculate portfolio metrics
            overview_data = await self._calculate_portfolio_metrics(db, portfolio_id, positions)
            
            # Add metadata
            overview_data.update({
                "portfolio_id": str(portfolio_id),
                "last_updated": to_utc_iso8601(utc_now())
            })
            
            return overview_data
            
        except Exception as e:
            logger.error(f"Error calculating portfolio overview for {portfolio_id}: {e}")
            raise
    
    async def _calculate_portfolio_metrics(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        positions: list
    ) -> Dict[str, Any]:
        """Calculate all portfolio metrics from positions data"""
        
        # Initialize metrics
        total_value = 0.0
        cash_balance = 0.0  # TODO: Get from portfolio.cash_balance when available
        long_exposure = 0.0
        short_exposure = 0.0
        total_pnl = 0.0
        unrealized_pnl = 0.0
        
        # Position counters
        total_positions = len(positions)
        long_count = 0
        short_count = 0
        option_count = 0
        
        # Calculate metrics from positions
        for pos in positions:
            quantity = float(pos.quantity) if pos.quantity else 0.0
            entry_price = float(pos.entry_price) if pos.entry_price else 0.0
            current_price = float(pos.current_price or pos.last_price or 0.0)
            
            # Calculate position market value
            position_value = quantity * current_price
            total_value += position_value
            
            # Calculate P&L for this position
            if cost_basis > 0 and current_price > 0:
                position_cost = quantity * cost_basis
                position_pnl = position_value - position_cost
                unrealized_pnl += position_pnl
            
            # Categorize position type
            if pos.position_type in [PositionType.LONG, PositionType.STOCK]:
                long_count += 1
                if quantity > 0:
                    long_exposure += position_value
                else:
                    short_exposure += abs(position_value)
                    short_count += 1
                    long_count -= 1
            elif pos.position_type == PositionType.SHORT:
                short_count += 1
                short_exposure += abs(position_value)
            elif pos.position_type in [PositionType.CALL, PositionType.PUT]:
                option_count += 1
                # Options contribute to exposure based on quantity sign
                if quantity > 0:
                    long_exposure += position_value
                else:
                    short_exposure += abs(position_value)
        
        # Calculate exposure percentages
        gross_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        
        # Calculate percentages (avoid division by zero)
        portfolio_total = total_value + cash_balance
        long_percentage = (long_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
        short_percentage = (short_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
        gross_percentage = (gross_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
        net_percentage = (net_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
        
        # Total P&L includes both realized and unrealized (for now, only unrealized)
        total_pnl = unrealized_pnl  # TODO: Add realized P&L from database
        realized_pnl = 0.0  # TODO: Calculate from historical data
        
        return {
            "total_value": round(portfolio_total, 2),
            "cash_balance": round(cash_balance, 2),
            "exposures": {
                "long_exposure": round(long_exposure, 2),
                "short_exposure": round(short_exposure, 2),
                "gross_exposure": round(gross_exposure, 2),
                "net_exposure": round(net_exposure, 2),
                "long_percentage": round(long_percentage, 1),
                "short_percentage": round(short_percentage, 1),
                "gross_percentage": round(gross_percentage, 1),
                "net_percentage": round(net_percentage, 1)
            },
            "pnl": {
                "total_pnl": round(total_pnl, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "realized_pnl": round(realized_pnl, 2)
            },
            "position_count": {
                "total_positions": total_positions,
                "long_count": long_count,
                "short_count": short_count,
                "option_count": option_count
            }
        }