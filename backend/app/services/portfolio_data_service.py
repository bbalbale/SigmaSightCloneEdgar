"""
Service layer for Agent-optimized portfolio data operations
"""
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.market_data import get_position_valuation
from app.core.datetime_utils import utc_now, to_utc_iso8601
from app.core.logging import get_logger
from app.models.market_data import MarketDataCache
from app.models.positions import Position, PositionType
from app.models.users import Portfolio
from app.schemas.data import (
    TopPositionsResponse,
    PortfolioSummaryResponse,
    PositionSummary,
    MetaInfo,
    HistoricalPricesResponse,
    PricePoint,
)

logger = get_logger(__name__)


class PortfolioDataService:
    """Service layer for Agent-optimized portfolio data operations"""
    
    async def get_top_positions(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        limit: int = 20,
        sort_by: str = "market_value", 
        as_of_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get top N positions sorted by market value or weight
        
        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            limit: Maximum positions to return (capped at 50)
            sort_by: Sorting method - "market_value" or "weight" 
            as_of_date: Optional date for historical data (max 180d lookback)
            
        Returns:
            Dict with positions array, coverage %, and meta object
        """
        try:
            # Validate and cap limit
            limit = min(limit, 50)
            
            # Validate as_of_date if provided (max 180 days lookback)
            cutoff_date = None
            if as_of_date:
                from datetime import datetime
                try:
                    as_of_dt = datetime.fromisoformat(as_of_date.replace('Z', '+00:00'))
                    cutoff_date = utc_now() - timedelta(days=180)
                    if as_of_dt < cutoff_date:
                        as_of_dt = cutoff_date
                except ValueError:
                    # Invalid date format, ignore and use current
                    as_of_dt = utc_now()
            else:
                as_of_dt = utc_now()
            
            # Get portfolio
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            # Get active positions (not soft-deleted)
            positions_result = await db.execute(
                select(Position)
                .where(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.deleted_at == None
                    )
                )
            )
            positions = positions_result.scalars().all()
            
            # Calculate market values for each position
            position_data = []
            total_portfolio_value = Decimal("0")
            
            for position in positions:
                # Get latest price from MarketDataCache
                price_result = await db.execute(
                    select(MarketDataCache.close)
                    .where(
                        and_(
                            MarketDataCache.symbol == position.symbol,
                            MarketDataCache.date <= as_of_dt
                        )
                    )
                    .order_by(desc(MarketDataCache.date))
                    .limit(1)
                )
                latest_price = price_result.scalar_one_or_none()
                
                price_override: Optional[Decimal] = None
                if latest_price is not None:
                    price_override = Decimal(str(latest_price))

                valuation = get_position_valuation(position, price=price_override)
                market_value_decimal = valuation.abs_market_value
                total_portfolio_value += market_value_decimal

                # Store position data for sorting
                position_data.append({
                    'symbol': position.symbol,
                    'name': position.symbol,  # Use symbol as name since Position doesn't have name field
                    'quantity': float(position.quantity),
                    'market_value': float(market_value_decimal),
                    'market_value_decimal': market_value_decimal,
                    'sector': None  # TODO: Add sector lookup when sector data available
                })
            
            # Calculate weights and sort
            total_value_positive = total_portfolio_value > 0
            for pos in position_data:
                if total_value_positive:
                    weight_decimal = (pos['market_value_decimal'] / total_portfolio_value) * Decimal("100")
                    pos['weight'] = round(float(weight_decimal), 4)
                else:
                    pos['weight'] = 0.0
            
            # Sort by requested field
            if sort_by == "weight":
                position_data.sort(key=lambda x: x['weight'], reverse=True)
            else:  # default to market_value
                position_data.sort(key=lambda x: x['market_value_decimal'], reverse=True)
            
            # Apply limit
            top_positions = position_data[:limit]
            
            # Calculate portfolio coverage
            covered_value = sum(pos['market_value_decimal'] for pos in top_positions)
            coverage_percent = round(
                float((covered_value / total_portfolio_value) * Decimal("100")) if total_value_positive else 0.0,
                2
            )
            
            # Create response with exact shape specified: {symbol, name, qty, value, weight, sector}
            positions_response = []
            for pos in top_positions:
                positions_response.append({
                    'symbol': pos['symbol'],
                    'name': pos['name'], 
                    'qty': pos['quantity'],
                    'value': round(pos['market_value'], 2),
                    'weight': pos['weight'],  # Already rounded to 4dp
                    'sector': pos['sector']   # TODO: Implement sector lookup
                })
            
            # Create meta object
            meta = {
                'as_of': to_utc_iso8601(as_of_dt),
                'requested': {
                    'portfolio_id': str(portfolio_id),
                    'limit': limit,
                    'sort_by': sort_by,
                    'as_of_date': as_of_date
                },
                'applied': {
                    'limit': len(positions_response),
                    'sort_by': sort_by,
                    'as_of_date': to_utc_iso8601(as_of_dt)
                },
                'limits': {
                    'max_limit': 50,
                    'max_lookback_days': 180
                },
                'rows_returned': len(positions_response),
                'truncated': len(position_data) > limit,
                'schema_version': '1.0'
            }
            
            return {
                'meta': meta,
                'data': positions_response,
                'coverage_percent': coverage_percent,
                'total_positions': len(position_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting top positions: {e}")
            raise
    
    async def get_portfolio_summary(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> PortfolioSummaryResponse:
        """
        Get condensed portfolio overview
        
        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            
        Returns:
            PortfolioSummaryResponse with summary metrics and top holdings
        """
        try:
            # Get portfolio
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            # Get top positions (reuse the other method)
            top_positions_response = await self.get_top_positions(
                db, portfolio_id, limit=5
            )
            
            # Extract total value from the response
            total_value = sum(pos['value'] for pos in top_positions_response['data'])
            
            # Get position count and asset allocation
            positions_result = await db.execute(
                select(
                    func.count(Position.id),
                    Position.position_type,
                    func.sum(Position.quantity * Position.cost_basis)
                )
                .where(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.deleted_at == None
                    )
                )
                .group_by(Position.position_type)
            )
            
            position_stats = positions_result.all()
            total_positions = top_positions_response['total_positions']
            
            # Calculate asset allocation
            asset_allocation = {}
            
            for count, position_type, type_value in position_stats:
                if position_type:
                    asset_type = position_type.value if hasattr(position_type, 'value') else str(position_type)
                    allocation_pct = (float(type_value or 0) / total_value * 100) if total_value else 0
                    asset_allocation[asset_type] = round(allocation_pct, 2)
            
            # Calculate cash balance (5% of portfolio as per backend convention)
            cash_balance = total_value * 0.05
            
            # Create meta object
            meta = {
                'as_of': utc_now().isoformat() + 'Z',
                'requested': {'portfolio_id': str(portfolio_id)},
                'applied': {'top_holdings_count': 5},
                'limits': {'max_top_holdings': 5},
                'rows_returned': len(top_positions_response['data']),
                'truncated': False,
                'schema_version': '1.0'
            }
            
            return {
                'meta': meta,
                'portfolio_id': str(portfolio.id),
                'portfolio_name': portfolio.name,
                'total_value': total_value,
                'cash_balance': cash_balance,
                'positions_count': total_positions,
                'top_holdings': top_positions_response['data'][:5],
                'asset_allocation': asset_allocation
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            raise
    
    async def get_historical_prices_with_selection(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        selection_method: str = "top_by_value",
        max_symbols: int = 5,
        lookback_days: int = 180
    ) -> Dict[str, Any]:
        """
        Get historical prices for selected symbols based on portfolio composition
        
        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            selection_method: Method for selecting symbols (top_by_value, top_by_weight, all)
            max_symbols: Maximum number of symbols to return
            lookback_days: Number of days of history
            
        Returns:
            Dictionary with historical price data and metadata
        """
        try:
            # Get top positions to determine which symbols to include
            if selection_method in ["top_by_value", "top_by_weight"]:
                sort_by = "market_value" if selection_method == "top_by_value" else "weight"
                top_positions = await self.get_top_positions(
                    db, portfolio_id, limit=max_symbols, sort_by=sort_by
                )
                selected_symbols = [pos['symbol'] for pos in top_positions['data']]
            else:  # all
                # Get all active position symbols
                result = await db.execute(
                    select(Position.symbol)
                    .where(
                        and_(
                            Position.portfolio_id == portfolio_id,
                            Position.is_active == True
                        )
                    )
                    .limit(max_symbols)
                )
                selected_symbols = [row[0] for row in result.all()]
            
            # Calculate date range
            end_date = utc_now()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get historical prices for selected symbols
            price_data = {}
            symbols_excluded = []
            
            for symbol in selected_symbols:
                prices_result = await db.execute(
                    select(MarketDataCache)
                    .where(
                        and_(
                            MarketDataCache.symbol == symbol,
                            MarketDataCache.date >= start_date,
                            MarketDataCache.date <= end_date
                        )
                    )
                    .order_by(MarketDataCache.date)
                )
                
                prices = prices_result.scalars().all()
                
                if prices:
                    price_data[symbol] = [
                        PricePoint(
                            date=to_utc_iso8601(price.date),
                            open=price.open,
                            high=price.high,
                            low=price.low,
                            close=price.close,
                            volume=price.volume
                        )
                        for price in prices
                    ]
                else:
                    symbols_excluded.append(symbol)
            
            # Get factor ETF prices if requested
            factor_etfs = {}
            factor_etf_symbols = ['SPY', 'IWM', 'QQQ', 'DIA', 'XLF', 'XLE', 'XLK']
            
            for etf in factor_etf_symbols:
                etf_result = await db.execute(
                    select(MarketDataCache)
                    .where(
                        and_(
                            MarketDataCache.symbol == etf,
                            MarketDataCache.date >= start_date,
                            MarketDataCache.date <= end_date
                        )
                    )
                    .order_by(MarketDataCache.date)
                    .limit(lookback_days)
                )
                
                etf_prices = etf_result.scalars().all()
                if etf_prices:
                    factor_etfs[etf] = [
                        PricePoint(
                            date=to_utc_iso8601(price.date),
                            open=price.open,
                            high=price.high,
                            low=price.low,
                            close=price.close,
                            volume=price.volume
                        )
                        for price in etf_prices
                    ]
            
            # Create meta object
            meta = MetaInfo(
                as_of=utc_now(),
                requested={
                    'portfolio_id': str(portfolio_id),
                    'selection_method': selection_method,
                    'max_symbols': max_symbols,
                    'lookback_days': lookback_days
                },
                applied={
                    'symbols_returned': len(price_data),
                    'days_returned': lookback_days,
                    'selection_method': selection_method
                },
                limits={
                    'max_symbols': max_symbols,
                    'max_days': 180
                },
                rows_returned=sum(len(prices) for prices in price_data.values()),
                truncated=len(selected_symbols) > max_symbols
            )
            
            return {
                'meta': meta.model_dump(),
                'symbols_included': list(price_data.keys()),
                'symbols_excluded': symbols_excluded,
                'price_data': {k: [p.model_dump() for p in v] for k, v in price_data.items()},
                'factor_etfs': {k: [p.model_dump() for p in v] for k, v in factor_etfs.items()} if factor_etfs else None
            }
            
        except Exception as e:
            logger.error(f"Error getting historical prices: {e}")
            raise
