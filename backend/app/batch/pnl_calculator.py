"""
Phase 2: P&L Calculation & Snapshot Creation
Calculates simple mark-to-market P&L and equity rollforward

Simplified approach (V1):
- Mark-to-market P&L only (unrealized gains/losses)
- Equity rollforward: new_equity = previous_equity + daily_pnl
- No realized gains, dividends, fees, or corporate actions (future enhancement)
"""
import asyncio
from datetime import date
from decimal import Decimal
from typing import Dict, List, Any, Optional
from uuid import UUID

from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position, PositionType
from app.models.position_realized_events import PositionRealizedEvent
from app.models.equity_changes import EquityChange, EquityChangeType
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import MarketDataCache
from app.calculations.market_data import get_previous_trading_day_price
from app.calculations.snapshots import (
    create_portfolio_snapshot,  # Keep for backward compatibility
    lock_snapshot_slot,  # Phase 2.10: Insert-first pattern
    populate_snapshot_data  # Phase 2.10: Two-phase snapshot creation
)
from app.utils.trading_calendar import trading_calendar
from app.cache.price_cache import PriceCache
from sqlalchemy.exc import IntegrityError  # Phase 2.10: Duplicate detection

logger = get_logger(__name__)


class PnLCalculator:
    """
    Phase 2 of batch processing - calculate P&L and create snapshots with equity rollforward

    Key Features:
    - Simple mark-to-market P&L
    - Equity rollforward from previous day
    - Uses cached market data (no API calls)
    - Creates snapshot for the day
    """

    async def calculate_all_portfolios_pnl(
        self,
        calculation_date: date,
        db: Optional[AsyncSession] = None,
        portfolio_ids: Optional[List[UUID]] = None,
        price_cache: Optional[PriceCache] = None
    ) -> Dict[str, Any]:
        """
        Calculate P&L for all active portfolios

        Args:
            calculation_date: Date to calculate P&L for
            db: Optional database session
            portfolio_ids: Optional list of specific portfolios to process
            price_cache: Optional pre-loaded price cache for optimization

        Returns:
            Summary of portfolios processed
        """
        logger.info(f"Phase 2: P&L Calculation for {calculation_date}")

        start_time = asyncio.get_event_loop().time()

        if db is None:
            async with AsyncSessionLocal() as session:
                result = await self._process_all_with_session(session, calculation_date, portfolio_ids, price_cache)
        else:
            result = await self._process_all_with_session(db, calculation_date, portfolio_ids, price_cache)

        duration = int(asyncio.get_event_loop().time() - start_time)
        result['duration_seconds'] = duration

        logger.info(f"Phase 2 complete in {duration}s")
        logger.info(f"  Portfolios processed: {result['portfolios_processed']}")
        logger.info(f"  Snapshots created: {result['snapshots_created']}")

        if price_cache:
            cache_stats = price_cache.get_stats()
            logger.info(f"  Price cache stats: {cache_stats['cache_hits']} hits, {cache_stats['cache_misses']} misses ({cache_stats['hit_rate_pct']}% hit rate)")

        return result

    async def _process_all_with_session(
        self,
        db: AsyncSession,
        calculation_date: date,
        portfolio_ids: Optional[List[UUID]] = None,
        price_cache: Optional[PriceCache] = None
    ) -> Dict[str, Any]:
        """Process all portfolios with provided session and optional price cache"""

        # Get all active portfolios
        query = select(Portfolio).where(Portfolio.deleted_at.is_(None))
        if portfolio_ids is not None:
            query = query.where(Portfolio.id.in_(portfolio_ids))
        result = await db.execute(query)
        portfolios = result.scalars().all()

        logger.debug(f"Found {len(portfolios)} active portfolios")

        portfolios_processed = 0
        snapshots_created = 0
        errors = []

        for portfolio in portfolios:
            try:
                result = await self.calculate_portfolio_pnl(
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date,
                    db=db,
                    price_cache=price_cache  # Pass cache to portfolio processing
                )

                # Handle dict return (new) or bool return (backward compatibility)
                if isinstance(result, dict):
                    if result.get("status") == "skipped":
                        # Idempotency working as designed - not an error
                        logger.debug(f"{portfolio.name}: Skipped (duplicate run)")
                        continue
                    # Other dict responses treated as errors
                    errors.append(f"{portfolio.name}: {result.get('message', 'Unknown error')}")
                elif result is True:
                    # Success
                    portfolios_processed += 1
                    snapshots_created += 1
                elif result is False:
                    # Legacy False return (should not happen with new code)
                    errors.append(f"{portfolio.name}: Failed to create snapshot")

            except Exception as e:
                logger.error(f"Error processing portfolio {portfolio.name}: {e}")
                errors.append(f"{portfolio.name}: {str(e)}")

        return {
            'success': len(errors) == 0,
            'portfolios_processed': portfolios_processed,
            'snapshots_created': snapshots_created,
            'errors': errors
        }

    async def calculate_portfolio_pnl(
        self,
        portfolio_id: UUID,
        calculation_date: date,
        db: AsyncSession,
        price_cache: Optional[PriceCache] = None
    ) -> bool:
        """
        Calculate P&L for a single portfolio and create snapshot

        Phase 2.10 INSERT-FIRST PATTERN:
        1. Check if trading day (skip if not)
        2. **LOCK SNAPSHOT SLOT FIRST** (atomic, prevents duplicate runs)
        3. Get previous snapshot (for previous equity)
        4. Calculate position-level P&L (using price cache if available)
        5. Aggregate to portfolio-level P&L
        6. Calculate new equity = previous_equity + daily_pnl
        7. Update portfolio.equity_balance (safe - we own the slot)
        8. **POPULATE PLACEHOLDER** with real snapshot data
        9. Commit (releases lock)

        Args:
            portfolio_id: Portfolio to process
            calculation_date: Date to calculate for
            db: Database session
            price_cache: Optional pre-loaded price cache

        Returns:
            True if snapshot created successfully, False if skipped or failed
        """
        # Check if trading day
        if not trading_calendar.is_trading_day(calculation_date):
            logger.debug(f"  {portfolio_id}: {calculation_date} is not a trading day, skipping")
            return False

        logger.info(f"  Processing portfolio {portfolio_id}")

        # PHASE 2.10 FIX: Lock snapshot slot FIRST (before ANY calculations)
        # This prevents duplicate runs from processing the same (portfolio, date)
        try:
            placeholder = await lock_snapshot_slot(
                db=db,
                portfolio_id=portfolio_id,
                snapshot_date=calculation_date
            )
            logger.debug(f"    [IDEMPOTENCY] Locked snapshot slot {placeholder.id}")
        except IntegrityError as e:
            # Another process already owns this (portfolio, date) slot
            # Check for EITHER constraint name (old: uq_portfolio_snapshots_portfolio_date,
            # new: uq_portfolio_snapshot_date) or use SQLSTATE 23505 (unique violation)
            error_str = str(e).lower()
            if "uq_portfolio_snapshot" in error_str or "unique constraint" in error_str:
                logger.info(
                    f"    [IDEMPOTENCY] Snapshot already exists for {calculation_date}, "
                    f"skipping duplicate run (constraint: {e.orig.diag.constraint_name if hasattr(e.orig, 'diag') else 'unknown'})"
                )
                await db.rollback()
                return {"status": "skipped", "reason": "duplicate_run"}
            # Some other integrity error - re-raise
            raise

        # Get portfolio
        portfolio_query = select(Portfolio).where(Portfolio.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_query)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            logger.error(f"  Portfolio {portfolio_id} not found")
            return False

        # Get most recent snapshot for equity rollforward
        # CRITICAL FIX: Instead of looking for exact previous trading day,
        # find the MOST RECENT snapshot before calculation_date.
        # This prevents equity reset when snapshots are missing.
        previous_snapshot = None
        previous_equity = portfolio.equity_balance or Decimal('0')  # Default to initial equity or 0

        # Look for most recent snapshot before calculation_date
        prev_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.snapshot_date < calculation_date
            )
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

        prev_result = await db.execute(prev_query)
        previous_snapshot = prev_result.scalar_one_or_none()

        if previous_snapshot:
            previous_equity = previous_snapshot.equity_balance or previous_equity
            logger.debug(f"    Previous equity ({previous_snapshot.snapshot_date}): ${previous_equity:,.2f}")
        else:
            logger.debug(f"    No previous snapshot found, using initial equity: ${previous_equity:,.2f}")

        # Calculate unrealized and realized P&L components
        daily_unrealized_pnl = await self._calculate_daily_pnl(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            previous_snapshot=previous_snapshot,
            price_cache=price_cache  # Pass cache for fast price lookups
        )

        daily_realized_pnl = await self._calculate_daily_realized_pnl(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
        )

        daily_capital_flow = await self._calculate_daily_capital_flow(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
        )

        total_daily_pnl = daily_unrealized_pnl + daily_realized_pnl

        # Calculate new equity (incremental)
        new_equity = previous_equity + total_daily_pnl + daily_capital_flow

        # Equity calculation confirmation (single line)
        logger.info(f"[EQUITY] {calculation_date}: ${previous_equity:,.0f} + PnL ${total_daily_pnl:,.0f} = ${new_equity:,.0f}")

        # Persist rolled equity so Portfolio.equity_balance remains the source of truth
        try:
            portfolio.equity_balance = new_equity
            await db.flush()
        except Exception as e:
            logger.error(f"[EQUITY] Update failed: {e}")
            raise

        # PHASE 2.10 FIX: Populate placeholder instead of creating new snapshot
        # We already own the (portfolio, date) slot from lock_snapshot_slot()
        # OPTIMIZATION: Skip expensive analytics for historical dates (only needed for current date)
        is_historical = calculation_date < date.today()

        try:
            snapshot = await populate_snapshot_data(
                snapshot=placeholder,  # Pass the placeholder we locked earlier
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                skip_pnl_calculation=True,  # V3: We handle P&L calculation here
                skip_provider_beta=is_historical,  # Only calculate on current/final date
                skip_sector_analysis=is_historical  # Only calculate on current/final date
            )

            # Update the snapshot's P&L fields with our calculated equity values
            # (populate_snapshot_data sets is_complete=True, but we need to set P&L fields)
            snapshot.equity_balance = new_equity
            snapshot.daily_pnl = total_daily_pnl
            snapshot.daily_realized_pnl = daily_realized_pnl
            snapshot.daily_capital_flow = daily_capital_flow
            snapshot.daily_return = (total_daily_pnl / previous_equity) if previous_equity > 0 else Decimal('0')

            if previous_snapshot:
                snapshot.cumulative_pnl = (previous_snapshot.cumulative_pnl or Decimal('0')) + total_daily_pnl
                snapshot.cumulative_realized_pnl = (
                    (previous_snapshot.cumulative_realized_pnl or Decimal('0')) + daily_realized_pnl
                )
                snapshot.cumulative_capital_flow = (
                    (previous_snapshot.cumulative_capital_flow or Decimal('0')) + daily_capital_flow
                )
            else:
                snapshot.cumulative_pnl = total_daily_pnl
                snapshot.cumulative_realized_pnl = daily_realized_pnl
                snapshot.cumulative_capital_flow = daily_capital_flow

            await db.commit()
            return True

        except Exception as e:
            logger.error(f"    ✗ Snapshot population failed: {e}", exc_info=True)
            await db.rollback()
            return False

    async def _calculate_daily_pnl(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date,
        previous_snapshot: Optional[PortfolioSnapshot],
        price_cache: Optional[PriceCache] = None
    ) -> Decimal:
        """
        Calculate simple mark-to-market P&L

        P&L = Sum of (current_price - previous_price) × quantity for all positions

        Args:
            db: Database session
            portfolio_id: Portfolio to calculate for
            calculation_date: Current date
            previous_snapshot: Previous day's snapshot (for previous prices)
            price_cache: Optional pre-loaded price cache

        Returns:
            Daily P&L as Decimal
        """
        # Get active positions
        positions_query = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.entry_date <= calculation_date,
                Position.deleted_at.is_(None)
            )
        )
        positions_result = await db.execute(positions_query)
        positions = positions_result.scalars().all()

        if not positions:
            logger.debug("    No active positions, P&L = $0")
            return Decimal('0')

        total_pnl = Decimal('0')

        for position in positions:
            position_pnl = await self._calculate_position_pnl(
                db=db,
                position=position,
                calculation_date=calculation_date,
                previous_snapshot=previous_snapshot,
                price_cache=price_cache  # Pass cache through
            )

            total_pnl += position_pnl
            logger.debug(f"      {position.symbol}: ${position_pnl:,.2f}")

        return total_pnl

    async def _calculate_daily_realized_pnl(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date,
    ) -> Decimal:
        """Aggregate realized P&L from trades recorded on the calculation date."""
        query = select(func.sum(PositionRealizedEvent.realized_pnl)).where(
            and_(
                PositionRealizedEvent.portfolio_id == portfolio_id,
                PositionRealizedEvent.trade_date == calculation_date,
            )
        )

        result = await db.execute(query)
        realized_total = result.scalar() or Decimal("0")

        if realized_total != Decimal("0"):
            logger.debug(f"    Realized P&L from events: ${realized_total:,.2f}")

        return realized_total

    async def _calculate_daily_capital_flow(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date,
    ) -> Decimal:
        """Aggregate net capital contributions/withdrawals for the calculation date."""
        contributions_case = case(
            (EquityChange.change_type == EquityChangeType.CONTRIBUTION, EquityChange.amount),
            else_=Decimal("0"),
        )
        withdrawals_case = case(
            (EquityChange.change_type == EquityChangeType.WITHDRAWAL, EquityChange.amount),
            else_=Decimal("0"),
        )

        query = select(
            func.coalesce(func.sum(contributions_case), Decimal("0")),
            func.coalesce(func.sum(withdrawals_case), Decimal("0")),
        ).where(
            EquityChange.portfolio_id == portfolio_id,
            EquityChange.change_date == calculation_date,
            EquityChange.deleted_at.is_(None),
        )

        result = await db.execute(query)
        contributions_raw, withdrawals_raw = result.first() or (Decimal("0"), Decimal("0"))

        contributions_value = Decimal(contributions_raw or 0)
        withdrawals_value = Decimal(withdrawals_raw or 0)
        net_flow = contributions_value - withdrawals_value

        if net_flow != Decimal("0"):
            logger.debug(
                "    Capital flow: contributions=$%s withdrawals=$%s net=$%s",
                f"{contributions_value:,.2f}",
                f"{withdrawals_value:,.2f}",
                f"{net_flow:,.2f}",
            )

        return net_flow

    async def _calculate_position_pnl(
        self,
        db: AsyncSession,
        position: Position,
        calculation_date: date,
        previous_snapshot: Optional[PortfolioSnapshot],
        price_cache: Optional[PriceCache] = None
    ) -> Decimal:
        """
        Calculate P&L for a single position

        P&L = (current_price - previous_price) × quantity

        Args:
            db: Database session
            position: Position to calculate for
            calculation_date: Current date
            previous_snapshot: Previous snapshot
            price_cache: Optional pre-loaded price cache

        Returns:
            Position P&L as Decimal
        """
        # PRIVATE positions don't have daily market prices, so P&L is always $0
        # Their value is captured in equity via entry_price (or manually updated last_price)
        if position.investment_class and str(position.investment_class).upper() == 'PRIVATE':
            logger.debug(f"      {position.symbol}: PRIVATE position, P&L = $0 (no daily price changes)")
            return Decimal('0')

        # Get current price from cache (in-memory or database)
        current_price = await self._get_cached_price(db, position.symbol, calculation_date, price_cache)

        if not current_price:
            logger.warning(f"      {position.symbol}: No current price, skipping P&L")
            return Decimal('0')

        # Get previous price with configurable lookback
        previous_price: Optional[Decimal] = None
        price_date_used: Optional[date] = None

        # SPECIAL CASE: First calculation day (no previous snapshot)
        # FIX (2025-12-17): Use current_price as baseline so daily P&L = $0 for day 1.
        # Previously used entry_price which incorrectly added TOTAL unrealized gain to equity.
        # The equity_balance represents starting capital, not mark-to-market value.
        # Unrealized gains are reflected in position market_value, NOT in equity_balance.
        if previous_snapshot is None:
            # First calculation day - no prior day to compare, so daily P&L should be $0
            previous_price = current_price
            logger.debug(
                f"      {position.symbol}: First calculation day, P&L = $0 (no prior day to compare)"
            )
        else:
            # Normal day-over-day P&L calculation
            price_lookup = await get_previous_trading_day_price(
                db=db,
                symbol=position.symbol,
                current_date=calculation_date,
                max_lookback_days=10,
            )

            if price_lookup:
                previous_price, price_date_used = price_lookup

            if previous_price is None:
                previous_price = current_price
                logger.debug(
                    f"      {position.symbol}: No prior close within lookback, using current price (P&L=0)"
                )
            else:
                expected_previous = trading_calendar.get_previous_trading_day(calculation_date)
                if price_date_used and expected_previous and price_date_used != expected_previous:
                    logger.debug(
                        f"      {position.symbol}: Using fallback prior close from {price_date_used}"
                    )

        # Calculate P&L (apply option contract multiplier when applicable)
        price_change = current_price - previous_price
        if position.position_type in (PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP):
            multiplier = Decimal('100')
        else:
            multiplier = Decimal('1')

        position_pnl = price_change * position.quantity * multiplier

        return position_pnl

    async def _get_cached_price(
        self,
        db: AsyncSession,
        symbol: str,
        price_date: date,
        price_cache: Optional[PriceCache] = None
    ) -> Optional[Decimal]:
        """
        Get price from in-memory cache (if available) or database.

        OPTIMIZATION: If price_cache is provided, use it first (300x faster).
        Falls back to database query if cache misses or not provided.
        """
        # OPTIMIZATION: Try in-memory cache first (instant lookup)
        if price_cache:
            price = price_cache.get_price(symbol, price_date)
            if price is not None:
                return price
            # Cache miss - fall through to database query

        # Fallback: Database query (slower but always available)
        query = select(MarketDataCache).where(
            and_(
                MarketDataCache.symbol == symbol,
                MarketDataCache.date == price_date,
                MarketDataCache.close > 0
            )
        )
        result = await db.execute(query)
        cache_record = result.scalar_one_or_none()

        if cache_record:
            return cache_record.close

        return None


# Global instance
pnl_calculator = PnLCalculator()
