"""
Batch Orchestrator V2 - Redesigned for SQLAlchemy Async Compatibility
Addresses greenlet errors through sequential processing and proper connection management
"""
import asyncio
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.users import Portfolio
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


def ensure_uuid(value: str | UUID) -> UUID:
    """Ensure value is a UUID object, converting from string if needed."""
    if isinstance(value, str):
        return UUID(value)
    elif isinstance(value, UUID):
        return value
    else:
        raise ValueError(f"Expected string or UUID, got {type(value)}")


@dataclass
class PortfolioData:
    """Simple data structure for portfolio information after database fetch."""
    id: str
    name: str
    user_id: Optional[str]
    positions_count: int


# Configuration constants
DEFAULT_MAX_RETRIES = 2
DEFAULT_SESSION_TIMEOUT = 300  # 5 minutes per session
DEFAULT_PORTFOLIO_DELAY = 1.0  # seconds between portfolios
DEFAULT_JOB_RETRY_DELAY = 2.0  # base delay for exponential backoff


class BatchOrchestratorV2:
    """
    Redesigned batch orchestrator that avoids SQLAlchemy greenlet errors through:
    1. Sequential portfolio processing (no concurrency)
    2. Proper session lifecycle management
    3. Connection pool isolation
    4. Graceful degradation for failed jobs
    """
    
    def __init__(self, max_retries: int = DEFAULT_MAX_RETRIES, session_timeout: int = DEFAULT_SESSION_TIMEOUT):
        self.max_retries = max_retries
        self.session_timeout = session_timeout
    
    async def run_daily_batch_sequence(
        self, 
        portfolio_id: Optional[str] = None,
        run_correlations: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point - processes portfolios sequentially to avoid concurrency issues.
        """
        start_time = utc_now()
        logger.info(f"Starting sequential batch processing at {start_time}")
        
        try:
            # Get portfolios to process
            portfolios = await self._get_portfolios_safely(portfolio_id)
            
            if not portfolios:
                logger.warning("No portfolios found to process")
                return []
            
            logger.info(f"Processing {len(portfolios)} portfolios sequentially")
            
            # Process each portfolio independently to avoid connection pool conflicts
            all_results = []
            for i, portfolio in enumerate(portfolios, 1):
                # Validate portfolio data before processing
                if not self._validate_portfolio_data(portfolio):
                    logger.error(f"Skipping invalid portfolio {i}/{len(portfolios)}")
                    continue
                
                logger.info(f"Processing portfolio {i}/{len(portfolios)}: {portfolio.name}")
                
                portfolio_results = await self._process_single_portfolio_safely(
                    portfolio, run_correlations
                )
                all_results.extend(portfolio_results)
                
                # Add small delay between portfolios to allow connection cleanup
                if i < len(portfolios):
                    await asyncio.sleep(DEFAULT_PORTFOLIO_DELAY)
            
            duration = utc_now() - start_time
            logger.info(f"Sequential batch processing completed in {duration.total_seconds():.2f}s")
            
            return all_results
            
        except Exception as e:
            logger.error(f"Batch sequence failed: {str(e)}")
            raise
    
    async def _get_portfolios_safely(self, portfolio_id: Optional[str] = None) -> List[Portfolio]:
        """
        Get portfolios with proper session management and eager loading.
        """
        async with self._get_isolated_session() as db:
            if portfolio_id:
                stmt = select(Portfolio).options(
                    selectinload(Portfolio.positions)  # Eager load to prevent lazy loading
                ).where(
                    Portfolio.id == portfolio_id,
                    Portfolio.deleted_at.is_(None)
                )
            else:
                stmt = select(Portfolio).options(
                    selectinload(Portfolio.positions)
                ).where(Portfolio.deleted_at.is_(None))
            
            result = await db.execute(stmt)
            portfolios = result.scalars().all()
            
            # Convert to simple data structures to avoid lazy loading later
            return [
                PortfolioData(
                    id=str(p.id),
                    name=str(p.name) if p.name else "Unknown",
                    user_id=str(p.user_id) if p.user_id else None,
                    positions_count=len(p.positions) if p.positions else 0
                ) for p in portfolios
            ]
    
    @asynccontextmanager
    async def _get_isolated_session(self):
        """
        Create an isolated session with proper cleanup to prevent connection pool issues.
        """
        session = None
        try:
            session = AsyncSessionLocal()
            # Ensure session doesn't expire objects
            yield session
            await session.commit()
        except Exception as e:
            if session:
                await session.rollback()
            raise
        finally:
            if session:
                await session.close()
    
    async def _process_single_portfolio_safely(
        self, 
        portfolio_data,
        run_correlations: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Process a single portfolio with isolated session and error handling.
        """
        results = []
        portfolio_id = portfolio_data.id
        portfolio_name = portfolio_data.name
        
        # Define job sequence with dependencies
        job_sequence = [
            ("market_data_update", self._update_market_data, []),
            ("position_values_update", self._update_position_values, [portfolio_id]),
            ("portfolio_aggregation", self._calculate_portfolio_aggregation, [portfolio_id]),
            # ("greeks_calculation", self._calculate_greeks, [portfolio_id]),  # DISABLED: No options feed
            ("factor_analysis", self._calculate_factors, [portfolio_id]),
            ("market_risk_scenarios", self._calculate_market_risk, [portfolio_id]),
            ("stress_testing", self._run_stress_tests, [portfolio_id]),
            ("portfolio_snapshot", self._create_snapshot, [portfolio_id]),
        ]
        
        # Always run correlations (important for risk metrics)
        job_sequence.append(("position_correlations", self._calculate_correlations, [portfolio_id]))

        # Execute jobs sequentially with isolated sessions
        for job_name, job_func, args in job_sequence:
            job_result = await self._execute_job_safely(
                f"{job_name}_{portfolio_id}", 
                job_func, 
                args,
                portfolio_name
            )
            results.append(job_result)
            
            # Stop processing this portfolio if critical jobs fail
            if job_result['status'] == 'failed' and job_name in ['market_data_update', 'portfolio_aggregation']:
                logger.warning(f"Critical job {job_name} failed for {portfolio_name}, skipping remaining jobs")
                break
        
        return results
    
    async def _execute_job_safely(
        self, 
        job_name: str, 
        job_func, 
        args: List, 
        portfolio_name: str = None
    ) -> Dict[str, Any]:
        """
        Execute a single job with proper error handling and session isolation.
        """
        start_time = utc_now()
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Starting job: {job_name} (attempt {attempt + 1})")
                
                # Execute job with isolated session
                async with self._get_isolated_session() as db:
                    if args:
                        result = await job_func(db, *args)
                    else:
                        result = await job_func(db)
                
                duration = (utc_now() - start_time).total_seconds()
                logger.info(f"Job {job_name} completed in {duration:.2f}s")
                
                return {
                    'job_name': job_name,
                    'status': 'completed',
                    'duration_seconds': duration,
                    'result': result,
                    'timestamp': utc_now(),
                    'portfolio_name': portfolio_name,
                    'attempt': attempt + 1
                }
                
            except Exception as e:
                duration = (utc_now() - start_time).total_seconds()
                error_msg = str(e)
                
                # Categorize error types for better handling  
                is_transient = self._is_transient_error(e)
                is_greenlet = 'greenlet_spawn' in error_msg
                
                # Enhanced logging with context
                if is_greenlet:
                    logger.error(f"Greenlet error in job {job_name} (attempt {attempt + 1}): {error_msg}")
                elif is_transient:
                    logger.warning(f"Transient error in job {job_name} (attempt {attempt + 1}): {error_msg}")
                else:
                    logger.error(f"Job {job_name} failed (attempt {attempt + 1}): {error_msg}")
                    # Add stack trace for permanent errors on final attempt
                    if attempt == self.max_retries:
                        import traceback
                        logger.error(f"Stack trace for {job_name}: {traceback.format_exc()}")
                
                # Skip retries for permanent errors unless it's the first attempt
                if not is_transient and not is_greenlet and attempt > 0:
                    logger.info(f"Permanent error detected for {job_name}, skipping remaining retries")
                    return {
                        'job_name': job_name,
                        'status': 'failed',
                        'duration_seconds': duration,
                        'error': error_msg,
                        'timestamp': utc_now(),
                        'portfolio_name': portfolio_name,
                        'attempts': attempt + 1,
                        'error_type': 'permanent'
                    }
                
                if attempt < self.max_retries:
                    # Exponential backoff with configurable base delay
                    delay = DEFAULT_JOB_RETRY_DELAY ** attempt
                    await asyncio.sleep(delay)
                    continue
                else:
                    return {
                        'job_name': job_name,
                        'status': 'failed',
                        'duration_seconds': duration,
                        'error': error_msg,
                        'timestamp': utc_now(),
                        'portfolio_name': portfolio_name,
                        'attempts': attempt + 1,
                        'error_type': 'greenlet' if is_greenlet else 'transient' if is_transient else 'permanent'
                    }
    
    def _is_transient_error(self, error: Exception) -> bool:
        """Categorize if error is likely transient and worth retrying."""
        error_str = str(error).lower()
        transient_indicators = [
            'timeout', 'connection', 'network', 'temporary', 
            'unavailable', 'busy', 'locked', 'deadlock',
            '429', '503', '502', '504', 'http error 5'
        ]
        return any(indicator in error_str for indicator in transient_indicators)
    
    def _validate_portfolio_data(self, portfolio_data: PortfolioData) -> bool:
        """Validate portfolio data has required fields."""
        if not portfolio_data.id:
            logger.error(f"Portfolio missing ID: {portfolio_data}")
            return False
        if not portfolio_data.name:
            logger.warning(f"Portfolio {portfolio_data.id} has no name, using 'Unknown'")
        if portfolio_data.positions_count == 0:
            logger.warning(f"Portfolio {portfolio_data.id} has no positions")
        return True
    
    # Job implementation methods (these would be imported from the original orchestrator)
    async def _update_market_data(self, db: AsyncSession):
        """Market data sync job with 252-day factor analysis validation"""
        from app.batch.market_data_sync import sync_market_data, validate_and_ensure_factor_analysis_data
        
        # Step 1: Standard daily market data sync (5 days)
        sync_results = await sync_market_data()
        
        # Step 2: Validate and ensure 252-day historical data for factor analysis
        validation_results = await validate_and_ensure_factor_analysis_data(db)
        
        # Combine results for batch execution summary
        combined_results = {
            'daily_sync': sync_results,
            'factor_data_validation': validation_results,
            'overall_status': 'completed' if validation_results.get('status') in ['passed', 'backfill_completed'] else 'failed'
        }
        
        return combined_results
    
    async def _update_position_values(self, db: AsyncSession, portfolio_id: str):
        """Update market values for all positions in portfolio"""
        from app.calculations.market_data import update_position_market_values
        from app.models.positions import Position
        from app.services.market_data_service import market_data_service
        from sqlalchemy import select
        from decimal import Decimal
        
        # Get portfolio positions
        stmt = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.deleted_at.is_(None),
            Position.exit_date.is_(None)
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        if not positions:
            return {'message': 'No active positions', 'updated': 0}
        
        updated_count = 0
        errors = []
        
        for position in positions:
            try:
                # Get cached price from market data cache
                prices = await market_data_service.get_cached_prices(
                    db, 
                    [position.symbol]
                )
                
                current_price = prices.get(position.symbol) if prices else None
                
                if current_price:
                    # Update position market value
                    await update_position_market_values(
                        db, 
                        position, 
                        Decimal(str(current_price))
                    )
                    updated_count += 1
                else:
                    logger.warning(f"No price available for {position.symbol}")
                    
            except Exception as e:
                error_msg = f"Failed to update {position.symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Commit the updates
        await db.commit()
        
        return {
            'portfolio_id': portfolio_id,
            'positions_updated': updated_count,
            'positions_total': len(positions),
            'errors': errors
        }
    
    async def _calculate_portfolio_aggregation(self, db: AsyncSession, portfolio_id: str):
        """Portfolio aggregation job"""
        from app.calculations.portfolio import calculate_portfolio_exposures
        from app.models.positions import Position
        from sqlalchemy import select
        
        # Get portfolio positions
        stmt = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.deleted_at.is_(None),
            Position.exit_date.is_(None)
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        if not positions:
            return {'message': 'No active positions', 'metrics': {}}
        
        # Convert positions to format expected by calculate_portfolio_exposures
        position_dicts = []
        for pos in positions:
            # Calculate exposure as market_value with correct sign
            market_value = float(pos.market_value) if pos.market_value else 0
            quantity = float(pos.quantity)
            
            # Market value is already signed (negative for shorts, positive for longs)
            # So exposure equals market value
            exposure = market_value
            
            position_dict = {
                'symbol': pos.symbol,
                'quantity': quantity,
                'market_value': market_value,
                'exposure': exposure,  # Add the missing exposure field
                'last_price': float(pos.last_price) if pos.last_price else 0,
                'position_type': pos.position_type.value if pos.position_type else 'LONG',
                'strike_price': float(pos.strike_price) if pos.strike_price else None,
                'expiration_date': pos.expiration_date
            }
            position_dicts.append(position_dict)
        
        exposures = calculate_portfolio_exposures(position_dicts)

        # For options portfolios, also calculate delta-adjusted exposure
        has_options = any(p.strike_price is not None for p in positions)

        # Update portfolio equity_balance = starting equity balance (from DB) + total realized P&L
        from decimal import Decimal

        # Get portfolio to access starting equity_balance from database
        portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if portfolio:
            # Use the equity_balance from database as starting balance
            # This should be set to the initial capital when portfolio is created
            starting_equity_balance = portfolio.equity_balance or Decimal("0")

            total_realized_pnl = sum(
                p.realized_pnl for p in positions
                if p.realized_pnl
            ) or Decimal("0")

            # equity_balance = starting equity balance (from DB) + realized P&L
            new_equity_balance = starting_equity_balance + total_realized_pnl

            # Only update if it changed
            if new_equity_balance != starting_equity_balance:
                portfolio.equity_balance = new_equity_balance
                await db.flush()

                logger.info(
                    f"Updated portfolio {portfolio_id} equity_balance: "
                    f"${float(starting_equity_balance):,.2f} -> ${float(new_equity_balance):,.2f} "
                    f"(realized P&L: ${float(total_realized_pnl):,.2f})"
                )

        return {
            'portfolio_id': portfolio_id,
            'metrics_calculated': len(exposures),
            'has_options': has_options,
            'exposures': exposures,
            'equity_balance_updated': float(new_equity_balance) if new_equity_balance else None
        }
    
    async def _calculate_greeks(self, db: AsyncSession, portfolio_id: str):
        """Greeks calculation job"""
        from app.calculations.greeks import bulk_update_portfolio_greeks
        from app.services.market_data_service import market_data_service
        from app.models.positions import Position
        
        # Get portfolio positions to extract symbols
        stmt = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.deleted_at.is_(None),
            Position.exit_date.is_(None)
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        if not positions:
            logger.warning(f"No positions found for portfolio {portfolio_id} in Greeks calculation")
            return {"updated": 0, "failed": 0, "errors": ["No positions found"]}
        
        # Extract underlying symbols for market data
        symbols = list(set([
            pos.underlying_symbol if pos.underlying_symbol else pos.symbol 
            for pos in positions
        ]))
        
        try:
            # Get current market prices using hybrid approach
            current_prices = await market_data_service.fetch_stock_prices_hybrid(symbols)
            
            # Convert to format expected by Greeks calculation
            market_data = {}
            for symbol, price_data in current_prices.items():
                if price_data and price_data.get('price'):
                    market_data[symbol] = {
                        'current_price': float(price_data['price']),
                        'implied_volatility': 0.25  # Default 25% IV
                    }
            
            logger.info(f"Fetched market data for {len(market_data)} symbols for Greeks calculation")
            return await bulk_update_portfolio_greeks(db, portfolio_id, market_data)
            
        except Exception as e:
            logger.error(f"Failed to fetch market data for Greeks calculation: {str(e)}")
            # Fallback with empty market data (will result in calculation failures)
            return await bulk_update_portfolio_greeks(db, portfolio_id, {})
    
    async def _calculate_factors(self, db: AsyncSession, portfolio_id: str):
        """Factor analysis job"""
        from app.calculations.factors import calculate_factor_betas_hybrid
        portfolio_uuid = ensure_uuid(portfolio_id)
        return await calculate_factor_betas_hybrid(db, portfolio_uuid, date.today())
    
    async def _calculate_market_risk(self, db: AsyncSession, portfolio_id: str):
        """Market risk scenarios job"""
        from app.calculations.market_risk import calculate_portfolio_market_beta
        portfolio_uuid = ensure_uuid(portfolio_id)
        return await calculate_portfolio_market_beta(db, portfolio_uuid, date.today())
    
    async def _run_stress_tests(self, db: AsyncSession, portfolio_id: str):
        """Stress testing job"""
        from app.calculations.stress_testing import run_comprehensive_stress_test, save_stress_test_results
        portfolio_uuid = ensure_uuid(portfolio_id)
        
        # Run stress tests
        results = await run_comprehensive_stress_test(db, portfolio_uuid, date.today())
        
        # Save results to database
        if results and 'stress_test_results' in results:
            saved_count = await save_stress_test_results(db, portfolio_uuid, results)
            results['saved_to_database'] = saved_count
            
        return results
    
    async def _create_snapshot(self, db: AsyncSession, portfolio_id: str):
        """Portfolio snapshot job"""
        from app.calculations.snapshots import create_portfolio_snapshot
        return await create_portfolio_snapshot(db, portfolio_id, date.today())
    
    async def _calculate_correlations(self, db: AsyncSession, portfolio_id: str):
        """Position correlations job"""
        from app.services.correlation_service import CorrelationService
        from datetime import datetime
        correlation_service = CorrelationService(db)
        portfolio_uuid = ensure_uuid(portfolio_id)
        return await correlation_service.calculate_portfolio_correlations(
            portfolio_uuid,
            calculation_date=utc_now()
        )


# Create singleton instance
batch_orchestrator_v2 = BatchOrchestratorV2()