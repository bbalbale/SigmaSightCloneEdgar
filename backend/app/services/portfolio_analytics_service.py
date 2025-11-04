"""
Portfolio Analytics Service

Service layer for portfolio analytics calculations including exposures, P&L metrics,
and aggregated portfolio data for dashboard consumption.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_
from uuid import UUID
from typing import Dict, Any, Optional
from datetime import datetime, date
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

            # CRITICAL FIX (2025-11-03): Get equity balance from most recent snapshot
            # PortfolioSnapshot.equity_balance is the rolled-forward value (changes with P&L)
            # Portfolio.equity_balance is the static initial value (never changes)
            from app.models.snapshots import PortfolioSnapshot

            snapshot_query = select(PortfolioSnapshot).where(
                PortfolioSnapshot.portfolio_id == portfolio_id
            ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

            snapshot_result = await db.execute(snapshot_query)
            latest_snapshot = snapshot_result.scalar_one_or_none()

            if latest_snapshot and latest_snapshot.equity_balance is not None:
                # Use rolled-forward equity from snapshot (correct)
                equity_balance = float(latest_snapshot.equity_balance)
                logger.info(f"Using rolled-forward equity ${equity_balance:,.2f} from snapshot {latest_snapshot.snapshot_date} for portfolio {portfolio_id}")
            else:
                # Fall back to initial equity from portfolio table
                equity_balance = float(portfolio.equity_balance) if portfolio.equity_balance else None
                if equity_balance is not None:
                    logger.info(f"Using initial equity ${equity_balance:,.2f} from portfolio (no snapshot found) for portfolio {portfolio_id}")
                else:
                    logger.info(f"No equity balance available for portfolio {portfolio_id}")
            
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
            overview_data = await self._calculate_portfolio_metrics(db, portfolio_id, positions, equity_balance, latest_snapshot)
            
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
        equity_balance: Optional[float] = None,
        snapshot: Optional[Any] = None
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

        # Check if positions have price data
        has_price_data = any(pos.last_price is not None for pos in positions)

        if not has_price_data and total_positions > 0:
            # Graceful degradation: Fall back to latest snapshot
            logger.info(f"No position price data available for portfolio {portfolio_id}, using latest snapshot")
            return await self._get_metrics_from_snapshot(db, portfolio_id, total_positions, equity_balance)

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

        # Calculate YTD and MTD P&L from snapshots
        period_pnl = await self._calculate_period_pnl(db, portfolio_id)

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
                "realized_pnl": round(realized_pnl, 2),
                "ytd_pnl": round(period_pnl["ytd_pnl"], 2),
                "mtd_pnl": round(period_pnl["mtd_pnl"], 2)
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

    async def _calculate_period_pnl(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> Dict[str, float]:
        """
        Calculate YTD and MTD P&L from portfolio snapshots.

        Args:
            db: Database session
            portfolio_id: Portfolio UUID

        Returns:
            Dict with ytd_pnl and mtd_pnl values
        """
        try:
            from app.models.snapshots import PortfolioSnapshot

            today = date.today()
            year_start = date(today.year, 1, 1)
            month_start = date(today.year, today.month, 1)

            # Query YTD snapshots
            ytd_result = await db.execute(
                select(PortfolioSnapshot.daily_pnl)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .where(PortfolioSnapshot.snapshot_date >= year_start)
                .where(PortfolioSnapshot.daily_pnl.isnot(None))
            )
            ytd_pnl_values = ytd_result.scalars().all()
            ytd_pnl = sum(float(val) for val in ytd_pnl_values if val is not None)

            # Query MTD snapshots
            mtd_result = await db.execute(
                select(PortfolioSnapshot.daily_pnl)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .where(PortfolioSnapshot.snapshot_date >= month_start)
                .where(PortfolioSnapshot.daily_pnl.isnot(None))
            )
            mtd_pnl_values = mtd_result.scalars().all()
            mtd_pnl = sum(float(val) for val in mtd_pnl_values if val is not None)

            logger.info(f"Calculated period P&L for portfolio {portfolio_id}: YTD=${ytd_pnl:,.2f}, MTD=${mtd_pnl:,.2f}")

            return {
                "ytd_pnl": ytd_pnl,
                "mtd_pnl": mtd_pnl
            }

        except Exception as e:
            logger.warning(f"Error calculating period P&L for portfolio {portfolio_id}: {e}")
            return {
                "ytd_pnl": 0.0,
                "mtd_pnl": 0.0
            }

    async def _get_metrics_from_snapshot(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        total_positions: int,
        equity_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Graceful degradation: Pull exposure metrics from latest PortfolioSnapshot
        when position price data is not available.

        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            total_positions: Number of positions in portfolio
            equity_balance: Portfolio equity balance

        Returns:
            Dict with portfolio metrics from snapshot or zeros if no snapshot exists
        """
        try:
            from app.models.snapshots import PortfolioSnapshot

            # Get the latest snapshot
            result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                logger.warning(f"No snapshot data available for portfolio {portfolio_id}, returning zeros")
                # Return zero values if no snapshot exists
                return self._get_zero_metrics(total_positions, equity_balance)

            # Extract values from snapshot
            long_exposure = float(snapshot.long_value) if snapshot.long_value else 0.0
            short_exposure = float(snapshot.short_value) if snapshot.short_value else 0.0
            gross_exposure = float(snapshot.gross_exposure) if snapshot.gross_exposure else 0.0
            net_exposure = float(snapshot.net_exposure) if snapshot.net_exposure else 0.0
            cash_balance = float(snapshot.cash_value) if snapshot.cash_value else 0.0
            portfolio_total = float(snapshot.total_value) if snapshot.total_value else 0.0

            # Position counts from snapshot
            long_count = snapshot.num_long_positions
            short_count = snapshot.num_short_positions
            # Note: Snapshot doesn't have option_count, estimate from total
            option_count = max(0, total_positions - long_count - short_count)

            # P&L from snapshot
            daily_pnl = float(snapshot.daily_pnl) if snapshot.daily_pnl else 0.0
            cumulative_pnl = float(snapshot.cumulative_pnl) if snapshot.cumulative_pnl else 0.0

            # Calculate percentages
            long_percentage = (long_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
            short_percentage = (abs(short_exposure) / portfolio_total * 100) if portfolio_total > 0 else 0.0
            gross_percentage = (gross_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0
            net_percentage = (net_exposure / portfolio_total * 100) if portfolio_total > 0 else 0.0

            # Leverage calculation
            if equity_balance and equity_balance > 0:
                leverage = gross_exposure / equity_balance
            else:
                leverage = gross_exposure / portfolio_total if portfolio_total > 0 else 0.0

            # Fetch target returns
            target_returns = await self._get_target_returns(db, portfolio_id)

            # Calculate YTD and MTD P&L from snapshots
            period_pnl = await self._calculate_period_pnl(db, portfolio_id)

            logger.info(f"Using snapshot data from {snapshot.snapshot_date} for portfolio {portfolio_id}")

            return {
                "equity_balance": round(equity_balance, 2) if equity_balance is not None else round(portfolio_total, 2),
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
                    "total_pnl": round(cumulative_pnl, 2),
                    "unrealized_pnl": round(cumulative_pnl, 2),  # Approximation
                    "realized_pnl": 0.0,  # Not in snapshot
                    "ytd_pnl": round(period_pnl["ytd_pnl"], 2),
                    "mtd_pnl": round(period_pnl["mtd_pnl"], 2)
                },
                "position_count": {
                    "total_positions": total_positions,
                    "long_count": long_count,
                    "short_count": short_count,
                    "option_count": option_count
                },
                "target_returns": target_returns
            }

        except Exception as e:
            logger.error(f"Error fetching snapshot data for portfolio {portfolio_id}: {e}")
            return self._get_zero_metrics(total_positions, equity_balance)

    def _get_zero_metrics(
        self,
        total_positions: int,
        equity_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Return zero-initialized metrics when no data is available"""
        return {
            "equity_balance": round(equity_balance, 2) if equity_balance is not None else 0.0,
            "total_value": 0.0,
            "cash_balance": 0.0,
            "leverage": 0.0,
            "exposures": {
                "long_exposure": 0.0,
                "short_exposure": 0.0,
                "gross_exposure": 0.0,
                "net_exposure": 0.0,
                "long_percentage": 0.0,
                "short_percentage": 0.0,
                "gross_percentage": 0.0,
                "net_percentage": 0.0
            },
            "pnl": {
                "total_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "ytd_pnl": 0.0,
                "mtd_pnl": 0.0
            },
            "position_count": {
                "total_positions": total_positions,
                "long_count": 0,
                "short_count": 0,
                "option_count": 0
            },
            "target_returns": None
        }