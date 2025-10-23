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
            # Verify portfolio exists and get equity_balance
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            # Get equity balance (use default if not set)
            equity_balance = float(portfolio.equity_balance) if portfolio.equity_balance else None
            
            # Get all positions (NO JOIN - use Position.last_price)
            positions_query = select(
                Position.id,
                Position.symbol,
                Position.position_type,
                Position.quantity,
                Position.entry_price,
                Position.last_price,
                Position.market_value,
                Position.unrealized_pnl,
                Position.realized_pnl
            ).where(
                Position.portfolio_id == portfolio_id
            )
            
            positions_result = await db.execute(positions_query)
            positions = positions_result.all()
            
            # Calculate portfolio metrics
            overview_data = await self._calculate_portfolio_metrics(db, portfolio_id, positions, equity_balance)
            
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
        positions: list,
        equity_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculate all portfolio metrics from positions data with equity-based calculations"""
        
        # Initialize metrics
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
            last_price = float(pos.last_price or 0.0)
            
            # Calculate position market value (keep sign)
            position_value = quantity * last_price
            
            # Calculate P&L for this position
            if entry_price > 0 and last_price > 0:
                position_cost = quantity * entry_price
                position_pnl = position_value - position_cost
                unrealized_pnl += position_pnl
            
            # Simple exposure calculation based on quantity sign
            if quantity > 0:
                long_exposure += position_value
                # Count based on position type
                if pos.position_type == PositionType.SHORT:
                    short_count += 1  # Covered short
                elif pos.position_type in [PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP]:
                    option_count += 1
                else:
                    long_count += 1
            else:  # quantity < 0 means short position
                short_exposure += position_value  # Keep negative!
                # Count based on position type
                if pos.position_type in [PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP]:
                    option_count += 1
                else:
                    short_count += 1
        
        # Calculate exposure aggregates (short_exposure is negative)
        gross_exposure = long_exposure + abs(short_exposure)
        net_exposure = long_exposure + short_exposure  # Add negative
        
        # Calculate cash balance from equity (if equity provided)
        if equity_balance is not None:
            # Cash = Equity - Long MV + |Short MV|
            cash_balance = equity_balance - long_exposure + abs(short_exposure)
            portfolio_total = equity_balance  # Portfolio total equals equity
            leverage = gross_exposure / equity_balance if equity_balance > 0 else 0.0
        else:
            # Fallback to old calculation if no equity set
            cash_balance = 0.0
            portfolio_total = net_exposure  # Just sum of positions
            leverage = 0.0
        
        # Calculate percentages (avoid division by zero)
        long_percentage = (long_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
        short_percentage = (abs(short_exposure) / portfolio_total * 100) if portfolio_total > 0 else 0.0
        gross_percentage = (gross_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
        net_percentage = (net_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
        
        # Total P&L includes both realized and unrealized (for now, only unrealized)
        total_pnl = unrealized_pnl  # TODO: Add realized P&L from database
        realized_pnl = 0.0  # TODO: Calculate from historical data

        # Fetch target return data from latest PortfolioSnapshot
        target_returns = await self._get_target_returns(db, portfolio_id)

        return {
            "equity_balance": round(equity_balance, 2) if equity_balance is not None else None,
            "total_value": round(portfolio_total, 2),
            "cash_balance": round(cash_balance, 2),
            "leverage": round(leverage, 2),
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
            },
            "target_returns": target_returns
        }

    async def _get_target_returns(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch target return data from the latest PortfolioSnapshot.

        Returns:
            Dict with target return metrics or None if no data available
        """
        try:
            from app.models.snapshots import PortfolioSnapshot

            # Get the latest snapshot with target price data
            result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .where(PortfolioSnapshot.target_price_return_eoy.isnot(None))
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                logger.debug(f"No target price data found in snapshots for portfolio {portfolio_id}")
                return None

            # Extract target return fields
            return {
                "expected_return_eoy": float(snapshot.target_price_return_eoy) if snapshot.target_price_return_eoy else None,
                "expected_return_next_year": float(snapshot.target_price_return_next_year) if snapshot.target_price_return_next_year else None,
                "downside_return": float(snapshot.target_price_downside_return) if snapshot.target_price_downside_return else None,
                "coverage_pct": float(snapshot.target_price_coverage_pct) if snapshot.target_price_coverage_pct else None,
                "positions_with_targets": snapshot.target_price_positions_count,
                "total_positions": snapshot.target_price_total_positions,
                "last_updated": to_utc_iso8601(snapshot.target_price_last_updated) if snapshot.target_price_last_updated else None
            }

        except Exception as e:
            logger.warning(f"Error fetching target returns for portfolio {portfolio_id}: {e}")
            return None