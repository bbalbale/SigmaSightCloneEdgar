"""
Batch Orchestrator V3 - Production-Ready 5-Phase Architecture with Automatic Backfill

Architecture:
- Phase 1: Market Data Collection (1-year lookback)
- Phase 1.5: Fundamental Data Collection (earnings-driven updates)
- Phase 2: P&L Calculation & Snapshots (equity rollforward)
- Phase 2.5: Position Market Value Updates (for analytics accuracy)
- Phase 2.75: Sector Tag Restoration (auto-tag from company profiles)
- Phase 3: Risk Analytics (betas, factors, volatility, correlations)

Features:
- Automatic backfill detection
- Phase isolation (failures don't cascade)
- Performance tracking
- Data coverage reporting
- Automatic sector tagging from company profiles
- Smart fundamentals fetching (3+ days after earnings)
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.batch_tracking import BatchRunTracking
from app.models.positions import Position
from app.models.users import Portfolio
from app.utils.trading_calendar import trading_calendar
from app.batch.market_data_collector import market_data_collector
from app.batch.fundamentals_collector import fundamentals_collector
from app.batch.pnl_calculator import pnl_calculator
from app.batch.analytics_runner import analytics_runner

logger = get_logger(__name__)


class BatchOrchestratorV3:
    """
    Main orchestrator for 3-phase batch processing with automatic backfill

    Usage:
        # Run with automatic backfill
        await batch_orchestrator_v3.run_daily_batch_with_backfill()

        # Run for specific date
        await batch_orchestrator_v3.run_daily_batch_sequence(date(2025, 7, 1))

        # Run for specific portfolios
        await batch_orchestrator_v3.run_daily_batch_sequence(
            calculation_date=date(2025, 7, 1),
            portfolio_ids=['uuid1', 'uuid2']
        )
    """

    async def run_daily_batch_with_backfill(
        self,
        target_date: Optional[date] = None,
        portfolio_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - automatically detects and fills missing dates

        Args:
            target_date: Date to process up to (defaults to today)
            portfolio_ids: Specific portfolios to process (defaults to all)

        Returns:
            Summary of backfill operation
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"=" * 80)
        logger.info(f"Batch Orchestrator V3 - Backfill to {target_date}")
        logger.info(f"=" * 80)

        start_time = asyncio.get_event_loop().time()

        # Step 1: Get last successful batch run (use temporary session)
        async with AsyncSessionLocal() as db:
            last_run_date = await self._get_last_batch_run_date(db)

            if last_run_date:
                logger.info(f"Last successful run: {last_run_date}")
            else:
                # First run ever - get earliest position date
                last_run_date = await self._get_earliest_position_date(db)
                if last_run_date:
                    # Start from day before earliest position
                    last_run_date = last_run_date - timedelta(days=1)
                    logger.info(f"First run - starting from {last_run_date}")
                else:
                    logger.warning("No positions found, nothing to process")
                    return {
                        'success': True,
                        'message': 'No positions to process',
                        'dates_processed': 0
                    }

        # Step 2: Calculate missing trading days
        missing_dates = trading_calendar.get_trading_days_between(
            start_date=last_run_date + timedelta(days=1),
            end_date=target_date
        )

        if not missing_dates:
            logger.info(f"Batch processing up to date as of {target_date}")
            return {
                'success': True,
                'message': f'Already up to date as of {target_date}',
                'dates_processed': 0
            }

        logger.info(f"Backfilling {len(missing_dates)} missing dates: {missing_dates[0]} to {missing_dates[-1]}")

        # Step 3: Process each missing date with its own fresh session
        # CRITICAL FIX: Each date gets a fresh session to avoid greenlet errors
        # caused by expired objects after commits in analytics calculations
        results = []
        for i, calc_date in enumerate(missing_dates, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Processing {calc_date} ({i}/{len(missing_dates)})")
            logger.info(f"{'=' * 80}")

            # Create fresh session for this date
            async with AsyncSessionLocal() as db:
                result = await self.run_daily_batch_sequence(
                    calculation_date=calc_date,
                    portfolio_ids=portfolio_ids,
                    db=db
                )

                results.append(result)

                # Mark as complete in tracking table
                if result['success']:
                    await self._mark_batch_run_complete(db, calc_date, result)

        duration = int(asyncio.get_event_loop().time() - start_time)

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Backfill Complete in {duration}s")
        logger.info(f"  Dates processed: {len(missing_dates)}")
        logger.info(f"  Success: {sum(1 for r in results if r['success'])}/{len(results)}")
        logger.info(f"={'=' * 80}\n")

        return {
            'success': all(r['success'] for r in results),
            'dates_processed': len(missing_dates),
            'duration_seconds': duration,
            'results': results
        }

    async def run_daily_batch_sequence(
        self,
        calculation_date: date,
        portfolio_ids: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Run 3-phase batch sequence for a single date

        Args:
            calculation_date: Date to process
            portfolio_ids: Specific portfolios (None = all)
            db: Optional database session

        Returns:
            Summary of batch run
        """
        try:
            if db is None:
                async with AsyncSessionLocal() as session:
                    return await self._run_sequence_with_session(
                        session, calculation_date, portfolio_ids
                    )
            else:
                return await self._run_sequence_with_session(
                    db, calculation_date, portfolio_ids
                )
        finally:
            # Clear batch run tracker when batch completes (success or failure)
            from app.batch.batch_run_tracker import batch_run_tracker
            batch_run_tracker.complete()

    async def _run_sequence_with_session(
        self,
        db: AsyncSession,
        calculation_date: date,
        portfolio_ids: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Run 5-phase sequence with provided session"""

        result = {
            'success': False,
            'calculation_date': calculation_date,
            'phase_1': {},
            'phase_1_5': {},
            'phase_2': {},
            'phase_3': {},
            'errors': []
        }

        # Phase 1: Market Data Collection
        try:
            logger.info("\n--- Phase 1: Market Data Collection ---")
            phase1_result = await market_data_collector.collect_daily_market_data(
                calculation_date=calculation_date,
                lookback_days=365,
                db=db
            )
            result['phase_1'] = phase1_result

            if not phase1_result.get('success'):
                result['errors'].append("Phase 1 failed")
                return result

        except Exception as e:
            logger.error(f"Phase 1 error: {e}")
            result['errors'].append(f"Phase 1 error: {str(e)}")
            return result

        # Phase 1.5: Fundamental Data Collection
        try:
            logger.info("\n--- Phase 1.5: Fundamental Data Collection ---")
            phase15_result = await fundamentals_collector.collect_fundamentals_data(
                db=db
            )
            result['phase_1_5'] = phase15_result

            if not phase15_result.get('success'):
                logger.warning("Phase 1.5 had errors, continuing to Phase 2")
                # Continue even if fundamentals fail - not critical for P&L

        except Exception as e:
            logger.error(f"Phase 1.5 error: {e}")
            result['errors'].append(f"Phase 1.5 error: {str(e)}")
            # Continue to Phase 2 even if fundamentals fail

        # Phase 2: P&L & Snapshots
        try:
            logger.info("\n--- Phase 2: P&L Calculation & Snapshots ---")
            phase2_result = await pnl_calculator.calculate_all_portfolios_pnl(
                calculation_date=calculation_date,
                db=db
            )
            result['phase_2'] = phase2_result

            if not phase2_result.get('success'):
                result['errors'].append("Phase 2 had errors")
                # Continue to Phase 2.5 even if Phase 2 has issues

        except Exception as e:
            logger.error(f"Phase 2 error: {e}")
            result['errors'].append(f"Phase 2 error: {str(e)}")
            # Continue to Phase 2.5

        # Phase 2.5: Update Position Market Values (CRITICAL for Phase 3 analytics)
        try:
            logger.info("\n--- Phase 2.5: Update Position Market Values ---")
            phase25_result = await self._update_all_position_market_values(
                calculation_date=calculation_date,
                db=db
            )
            result['phase_2_5'] = phase25_result

            if not phase25_result.get('success'):
                logger.warning("Phase 2.5 had errors, continuing to Phase 2.75")
                # Continue to Phase 2.75 even if position updates fail

        except Exception as e:
            logger.error(f"Phase 2.5 error: {e}")
            result['errors'].append(f"Phase 2.5 error: {str(e)}")
            # Continue to Phase 2.75

        # Phase 2.75: Restore Sector Tags from Company Profiles
        try:
            logger.info("\n--- Phase 2.75: Restore Sector Tags ---")
            phase275_result = await self._restore_all_sector_tags(
                db=db
            )
            result['phase_2_75'] = phase275_result

            if not phase275_result.get('success'):
                logger.warning("Phase 2.75 had errors, continuing to Phase 3")
                # Continue to Phase 3 even if sector tagging fails

        except Exception as e:
            logger.error(f"Phase 2.75 error: {e}")
            result['errors'].append(f"Phase 2.75 error: {str(e)}")
            # Continue to Phase 3

        # Phase 3: Risk Analytics
        try:
            logger.info("\n--- Phase 3: Risk Analytics ---")
            phase3_result = await analytics_runner.run_all_portfolios_analytics(
                calculation_date=calculation_date,
                db=db
            )
            result['phase_3'] = phase3_result

            if not phase3_result.get('success'):
                result['errors'].append("Phase 3 had errors")

        except Exception as e:
            logger.error(f"Phase 3 error: {e}")
            result['errors'].append(f"Phase 3 error: {str(e)}")

        # Determine overall success
        result['success'] = len(result['errors']) == 0

        return result

    async def _update_all_position_market_values(
        self,
        calculation_date: date,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Update last_price and market_value for all active positions

        This is CRITICAL for Phase 3 analytics that rely on position.market_value
        (e.g., provider beta calculation)

        Args:
            calculation_date: Date to get prices for
            db: Database session

        Returns:
            Summary of positions updated
        """
        from app.models.market_data import MarketDataCache
        from decimal import Decimal

        logger.info(f"Updating position market values for {calculation_date}")

        try:
            # Get all active positions
            positions_query = select(Position).where(
                and_(
                    Position.exit_date.is_(None),
                    Position.deleted_at.is_(None)
                )
            )
            positions_result = await db.execute(positions_query)
            positions = positions_result.scalars().all()

            logger.info(f"Found {len(positions)} active positions to update")

            positions_updated = 0
            positions_skipped = 0

            for position in positions:
                # Get current price from market_data_cache
                price_query = select(MarketDataCache).where(
                    and_(
                        MarketDataCache.symbol == position.symbol,
                        MarketDataCache.date == calculation_date
                    )
                )
                price_result = await db.execute(price_query)
                market_data = price_result.scalar_one_or_none()

                if market_data and market_data.close and market_data.close > 0:
                    current_price = market_data.close

                    # Calculate market value
                    # For stocks: quantity * price
                    # For options: quantity * price * 100 (contract multiplier)
                    multiplier = Decimal('100') if position.position_type.name in ['CALL', 'PUT', 'LC', 'LP', 'SC', 'SP'] else Decimal('1')
                    market_value = position.quantity * current_price * multiplier

                    # Update position
                    position.last_price = current_price
                    position.market_value = market_value

                    positions_updated += 1
                    logger.debug(f"  {position.symbol}: price=${float(current_price):.2f}, market_value=${float(market_value):,.2f}")
                else:
                    positions_skipped += 1
                    logger.debug(f"  {position.symbol}: No price data available")

            # Commit all position updates
            await db.commit()

            logger.info(f"Position market values updated: {positions_updated} updated, {positions_skipped} skipped")

            return {
                'success': True,
                'positions_updated': positions_updated,
                'positions_skipped': positions_skipped,
                'total_positions': len(positions)
            }

        except Exception as e:
            logger.error(f"Error updating position market values: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'positions_updated': 0
            }

    async def _restore_all_sector_tags(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Restore sector tags for all portfolios based on company profile data.

        This updates sector tags to match current company profile sectors,
        ensuring tags stay in sync with the latest sector classifications.

        Args:
            db: Database session

        Returns:
            Summary of sector tag restoration
        """
        from app.services.sector_tag_service import restore_sector_tags_for_portfolio

        logger.info("Restoring sector tags for all portfolios")

        try:
            # Get all active portfolios
            portfolios_query = select(Portfolio).where(
                Portfolio.deleted_at.is_(None)
            )
            portfolios_result = await db.execute(portfolios_query)
            portfolios = portfolios_result.scalars().all()

            logger.info(f"Found {len(portfolios)} active portfolios to update sector tags")

            total_positions_tagged = 0
            total_positions_skipped = 0
            total_tags_created = 0
            portfolios_processed = 0

            for portfolio in portfolios:
                try:
                    # Restore sector tags for this portfolio
                    result = await restore_sector_tags_for_portfolio(
                        db=db,
                        portfolio_id=portfolio.id,
                        user_id=portfolio.user_id
                    )

                    total_positions_tagged += result.get('positions_tagged', 0)
                    total_positions_skipped += result.get('positions_skipped', 0)
                    total_tags_created += result.get('tags_created', 0)
                    portfolios_processed += 1

                    logger.info(
                        f"  {portfolio.name}: {result.get('positions_tagged', 0)} positions tagged, "
                        f"{result.get('tags_created', 0)} tags created"
                    )

                except Exception as e:
                    logger.error(f"  Error restoring sector tags for portfolio {portfolio.name}: {e}")
                    # Continue to next portfolio

            logger.info(
                f"Sector tag restoration complete: "
                f"{portfolios_processed} portfolios, "
                f"{total_positions_tagged} positions tagged, "
                f"{total_tags_created} tags created"
            )

            return {
                'success': True,
                'portfolios_processed': portfolios_processed,
                'total_portfolios': len(portfolios),
                'positions_tagged': total_positions_tagged,
                'positions_skipped': total_positions_skipped,
                'tags_created': total_tags_created
            }

        except Exception as e:
            logger.error(f"Error restoring sector tags: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'portfolios_processed': 0
            }

    async def _get_last_batch_run_date(self, db: AsyncSession) -> Optional[date]:
        """Get the date of the last successful batch run"""
        query = select(BatchRunTracking).where(
            BatchRunTracking.phase_1_status == 'success'
        ).order_by(desc(BatchRunTracking.run_date)).limit(1)

        result = await db.execute(query)
        last_run = result.scalar_one_or_none()

        if last_run:
            return last_run.run_date

        return None

    async def _get_earliest_position_date(self, db: AsyncSession) -> Optional[date]:
        """Get the earliest position entry date across all portfolios"""
        query = select(Position.entry_date).order_by(Position.entry_date).limit(1)

        result = await db.execute(query)
        earliest_date = result.scalar_one_or_none()

        return earliest_date

    async def _mark_batch_run_complete(
        self,
        db: AsyncSession,
        run_date: date,
        batch_result: Dict[str, Any]
    ):
        """Mark a batch run as complete in tracking table"""
        from datetime import datetime, timezone

        # Extract metrics from results
        phase1 = batch_result.get('phase_1', {})
        phase2 = batch_result.get('phase_2', {})
        phase3 = batch_result.get('phase_3', {})

        tracking = BatchRunTracking(
            id=uuid4(),
            run_date=run_date,
            phase_1_status='success' if phase1.get('success') else 'failed',
            phase_2_status='success' if phase2.get('success') else 'failed',
            phase_3_status='success' if phase3.get('success') else 'failed',
            phase_1_duration_seconds=phase1.get('duration_seconds'),
            phase_2_duration_seconds=phase2.get('duration_seconds'),
            phase_3_duration_seconds=phase3.get('duration_seconds'),
            portfolios_processed=phase2.get('portfolios_processed'),
            symbols_fetched=phase1.get('symbols_fetched'),
            data_coverage_pct=phase1.get('data_coverage_pct'),
            error_message='; '.join(batch_result.get('errors', [])) if batch_result.get('errors') else None,
            completed_at=datetime.now(timezone.utc)
        )

        db.add(tracking)
        await db.commit()

        logger.debug(f"Batch run tracking record created for {run_date}")


# Global instance
batch_orchestrator_v3 = BatchOrchestratorV3()
