"""
Target Price Service for managing portfolio target prices
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
import csv
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from sqlalchemy.orm import selectinload

from app.models.target_prices import TargetPrice
from app.models.positions import Position
from app.models.users import Portfolio
from app.models.market_data import MarketDataCache, PositionFactorExposure, FactorDefinition
from app.services.market_data_service import MarketDataService
from app.schemas.target_prices import (
    TargetPriceCreate,
    TargetPriceUpdate,
    TargetPriceResponse,
    PortfolioTargetPriceSummary
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class TargetPriceService:
    """Service for managing portfolio target prices"""
    
    def __init__(self):
        self.market_data_service = MarketDataService()

    async def _resolve_position_and_class(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        symbol: str,
        position_id: Optional[UUID] = None,
        position_type: Optional[str] = None
    ) -> tuple[Optional[Position], str]:
        """
        Resolve position and investment class using smart resolution logic.
        
        Returns:
            tuple: (Position or None, investment_class)
        """
        if position_id:
            # Direct lookup by position_id
            result = await db.execute(
                select(Position).where(Position.id == position_id)
            )
            position = result.scalar_one_or_none()
            if position:
                return position, position.investment_class or "PUBLIC"
            else:
                logger.warning(f"Position {position_id} not found, defaulting to PUBLIC")
                return None, "PUBLIC"
        
        # Smart resolution by symbol + position_type
        query = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol,
                Position.exit_date.is_(None)  # Active positions only
            )
        )
        
        if position_type:
            # Honor exact position_type if provided
            query = query.where(Position.position_type == position_type)
            result = await db.execute(query)
            positions = result.scalars().all()
            if positions:
                return positions[0], positions[0].investment_class or "PUBLIC"
        else:
            # Apply deterministic fallback rules
            result = await db.execute(query)
            all_positions = result.scalars().all()
            
            if not all_positions:
                return None, "PUBLIC"  # Default assumption
            
            # Prefer equity over options
            equity_positions = [p for p in all_positions if p.position_type.value in ['LONG', 'SHORT']]
            if equity_positions:
                return equity_positions[0], equity_positions[0].investment_class or "PUBLIC"
            
            # Fallback to first option position
            return all_positions[0], all_positions[0].investment_class or "PUBLIC"
        
        return None, "PUBLIC"

    async def _resolve_current_price(
        self,
        db: AsyncSession,
        symbol: str,
        investment_class: str,
        user_provided_price: Optional[Decimal] = None,
        underlying_symbol: Optional[str] = None
    ) -> tuple[Decimal, str]:
        """
        Resolve current price based on investment class and price resolution contract.
        
        Returns:
            tuple: (resolved_price, price_source)
        """
        effective_symbol = underlying_symbol if underlying_symbol else symbol
        
        if investment_class == "PRIVATE":
            # Private investments require user-provided price
            if user_provided_price is None:
                raise ValueError(f"Current price required for private investment: {symbol}")
            return user_provided_price, "user_supplied"
        
        # PUBLIC/OPTIONS: Try market data first, fallback to user price
        try:
            # Get latest price from MarketDataCache
            latest_price_result = await db.execute(
                select(MarketDataCache.close, MarketDataCache.date)
                .where(MarketDataCache.symbol == effective_symbol)
                .order_by(MarketDataCache.date.desc())
                .limit(1)
            )
            latest_data = latest_price_result.first()
            
            if latest_data:
                latest_price, price_date = latest_data
                
                # Check if data is stale (>1 trading day)
                days_old = (datetime.utcnow().date() - price_date).days
                if days_old <= 1:  # Fresh data
                    return latest_price, "market_data"
                else:
                    logger.warning(f"Market data for {effective_symbol} is {days_old} days old")
            
            # Fallback to live market data service
            current_prices = await self.market_data_service.fetch_current_prices([effective_symbol])
            market_price = current_prices.get(effective_symbol)
            
            if market_price:
                return market_price, "market_data_live"
                
        except Exception as e:
            logger.warning(f"Failed to fetch market data for {effective_symbol}: {e}")
        
        # Final fallback to user-provided price
        if user_provided_price:
            logger.info(f"Using user-provided price for {symbol}: {user_provided_price}")
            return user_provided_price, "user_provided_fallback"
        
        raise ValueError(f"No current price available for {symbol}. Please provide current_price.")

    async def create_target_price(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        target_price_data: TargetPriceCreate,
        user_id: Optional[UUID] = None
    ) -> TargetPrice:
        """
        Create a new target price for a portfolio position.
        """
        # Check if target price already exists for this symbol/position_type
        existing = await self._get_existing_target_price(
            db,
            portfolio_id,
            target_price_data.symbol,
            target_price_data.position_type
        )

        if existing:
            raise ValueError(
                f"Target price already exists for {target_price_data.symbol} "
                f"({target_price_data.position_type or 'LONG'}) in this portfolio"
            )

        # Resolve position and investment class
        position, investment_class = await self._resolve_position_and_class(
            db,
            portfolio_id,
            target_price_data.symbol,
            target_price_data.position_id,
            target_price_data.position_type
        )

        # Handle options underlying symbol resolution
        underlying_symbol = None
        if position and position.position_type.value in ['LC', 'LP', 'SC', 'SP']:
            underlying_symbol = position.underlying_symbol
            if not underlying_symbol:
                logger.warning(f"Options position {position.id} missing underlying_symbol")

        # Resolve current price using price resolution contract
        resolved_price, price_source = await self._resolve_current_price(
            db,
            target_price_data.symbol,
            investment_class,
            target_price_data.current_price,
            underlying_symbol
        )

        logger.info(f"Creating target price for {target_price_data.symbol} "
                   f"(class: {investment_class}, price_source: {price_source})")

        # Create new target price
        target_price = TargetPrice(
            portfolio_id=portfolio_id,
            position_id=position.id if position else target_price_data.position_id,
            symbol=target_price_data.symbol,
            position_type=target_price_data.position_type or 'LONG',
            target_price_eoy=target_price_data.target_price_eoy,
            target_price_next_year=target_price_data.target_price_next_year,
            downside_target_price=target_price_data.downside_target_price,
            current_price=resolved_price,
            current_implied_vol=target_price_data.current_implied_vol,
            analyst_notes=target_price_data.analyst_notes,
            data_source=target_price_data.data_source or 'USER_INPUT',
            created_by=user_id,
            price_updated_at=datetime.utcnow()
        )

        # Calculate expected returns using resolved price
        target_price.calculate_expected_returns(resolved_price)

        # Calculate position weight if position exists
        if target_price_data.position_id:
            await self._calculate_position_metrics(db, target_price)

        db.add(target_price)
        await db.commit()
        await db.refresh(target_price)

        logger.info(f"Created target price for {target_price.symbol} in portfolio {portfolio_id}")
        return target_price

    async def update_target_price(
        self,
        db: AsyncSession,
        target_price_id: UUID,
        update_data: TargetPriceUpdate
    ) -> TargetPrice:
        """
        Update an existing target price.
        """
        # Get existing target price
        result = await db.execute(
            select(TargetPrice).where(TargetPrice.id == target_price_id)
        )
        target_price = result.scalar_one_or_none()

        if not target_price:
            raise ValueError(f"Target price {target_price_id} not found")

        # Check if current_price is being updated and resolve if needed
        resolved_price = None
        update_dict = update_data.dict(exclude_unset=True)
        
        if 'current_price' in update_dict and update_dict['current_price'] is not None:
            # If user is providing a new current_price, resolve it using price contract
            position, investment_class = await self._resolve_position_and_class(
                db,
                target_price.portfolio_id,
                target_price.symbol,
                target_price.position_id,
                target_price.position_type
            )
            
            # Handle options underlying symbol
            underlying_symbol = None
            if position and position.position_type.value in ['LC', 'LP', 'SC', 'SP']:
                underlying_symbol = position.underlying_symbol
            
            resolved_price, price_source = await self._resolve_current_price(
                db,
                target_price.symbol,
                investment_class,
                update_dict['current_price'],
                underlying_symbol
            )
            
            logger.info(f"Updated target price {target_price_id} price "
                       f"(class: {investment_class}, price_source: {price_source})")
            
            # Update with resolved price
            update_dict['current_price'] = resolved_price

        # Update fields
        for field, value in update_dict.items():
            setattr(target_price, field, value)

        # Update timestamp
        target_price.price_updated_at = datetime.utcnow()

        # Recalculate expected returns with resolved price if available
        target_price.calculate_expected_returns(resolved_price)

        # Recalculate position metrics if linked to position
        if target_price.position_id:
            await self._calculate_position_metrics(db, target_price)

        await db.commit()
        await db.refresh(target_price)

        logger.info(f"Updated target price {target_price_id}")
        return target_price

    async def delete_target_price(
        self,
        db: AsyncSession,
        target_price_id: UUID
    ) -> bool:
        """
        Delete a target price.
        """
        result = await db.execute(
            delete(TargetPrice).where(TargetPrice.id == target_price_id)
        )

        await db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Deleted target price {target_price_id}")

        return deleted

    async def get_target_price(
        self,
        db: AsyncSession,
        target_price_id: UUID
    ) -> Optional[TargetPrice]:
        """
        Get a single target price by ID.
        """
        result = await db.execute(
            select(TargetPrice)
            .options(selectinload(TargetPrice.portfolio))
            .where(TargetPrice.id == target_price_id)
        )
        return result.scalar_one_or_none()

    async def get_portfolio_target_prices(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> List[TargetPrice]:
        """
        Get all target prices for a portfolio.
        """
        result = await db.execute(
            select(TargetPrice)
            .where(TargetPrice.portfolio_id == portfolio_id)
            .order_by(TargetPrice.symbol)
        )
        return result.scalars().all()

    async def get_portfolio_summary(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> PortfolioTargetPriceSummary:
        """
        Get portfolio target price summary with aggregated metrics.
        """
        # Get portfolio
        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        # Get all positions for the portfolio
        positions_result = await db.execute(
            select(Position)
            .where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.exit_date.is_(None)
                )
            )
        )
        positions = positions_result.scalars().all()

        # Get all target prices
        target_prices = await self.get_portfolio_target_prices(db, portfolio_id)

        # Calculate coverage
        total_positions = len(positions)
        positions_with_targets = len(target_prices)
        coverage = (Decimal(positions_with_targets) / Decimal(total_positions) * 100) if total_positions > 0 else Decimal(0)

        # Calculate portfolio-level metrics
        portfolio_metrics = await self._calculate_portfolio_metrics(
            db,
            portfolio_id,
            target_prices,
            positions
        )

        # Create summary
        summary = PortfolioTargetPriceSummary(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            total_positions=total_positions,
            positions_with_targets=positions_with_targets,
            coverage_percentage=coverage,
            weighted_expected_return_eoy=portfolio_metrics.get('weighted_return_eoy'),
            weighted_expected_return_next_year=portfolio_metrics.get('weighted_return_next_year'),
            weighted_downside_return=portfolio_metrics.get('weighted_downside'),
            expected_sharpe_ratio=portfolio_metrics.get('sharpe_ratio'),
            expected_sortino_ratio=portfolio_metrics.get('sortino_ratio'),
            target_prices=[
                TargetPriceResponse.from_orm(tp) for tp in target_prices
            ],
            last_updated=datetime.utcnow()
        )

        return summary

    async def bulk_create_target_prices(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        target_prices: List[TargetPriceCreate],
        user_id: Optional[UUID] = None
    ) -> List[TargetPrice]:
        """
        Bulk create multiple target prices.
        """
        created_prices = []

        for tp_data in target_prices:
            try:
                tp = await self.create_target_price(
                    db,
                    portfolio_id,
                    tp_data,
                    user_id
                )
                created_prices.append(tp)
            except ValueError as e:
                logger.warning(f"Skipping {tp_data.symbol}: {e}")
                continue

        logger.info(f"Created {len(created_prices)} target prices for portfolio {portfolio_id}")
        return created_prices

    async def import_from_csv(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        csv_content: str,
        update_existing: bool = False,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Import target prices from CSV.

        Expected CSV format:
        symbol,position_type,target_eoy,target_next_year,downside,current_price
        """
        reader = csv.DictReader(io.StringIO(csv_content))

        created = 0
        updated = 0
        errors = []

        for row in reader:
            try:
                symbol = row.get('symbol', '').strip().upper()
                position_type = row.get('position_type', 'LONG').strip().upper()

                if not symbol:
                    errors.append("Missing symbol in row")
                    continue

                # Check if exists
                existing = await self._get_existing_target_price(
                    db,
                    portfolio_id,
                    symbol,
                    position_type
                )

                if existing and not update_existing:
                    errors.append(f"{symbol} already exists, skipping")
                    continue

                # Parse values
                target_data = TargetPriceCreate(
                    symbol=symbol,
                    position_type=position_type,
                    target_price_eoy=Decimal(row['target_eoy']) if row.get('target_eoy') else None,
                    target_price_next_year=Decimal(row['target_next_year']) if row.get('target_next_year') else None,
                    downside_target_price=Decimal(row['downside']) if row.get('downside') else None,
                    current_price=Decimal(row['current_price']) if row.get('current_price') else Decimal(100)
                )

                if existing and update_existing:
                    # Update existing
                    update_data = TargetPriceUpdate(
                        target_price_eoy=target_data.target_price_eoy,
                        target_price_next_year=target_data.target_price_next_year,
                        downside_target_price=target_data.downside_target_price,
                        current_price=target_data.current_price
                    )
                    await self.update_target_price(db, existing.id, update_data)
                    updated += 1
                else:
                    # Create new
                    await self.create_target_price(db, portfolio_id, target_data, user_id)
                    created += 1

            except Exception as e:
                errors.append(f"Error processing row {reader.line_num}: {e}")

        return {
            'created': created,
            'updated': updated,
            'errors': errors,
            'total': created + updated
        }

    async def _get_existing_target_price(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        symbol: str,
        position_type: Optional[str]
    ) -> Optional[TargetPrice]:
        """
        Check if target price exists for symbol/position_type combination.
        """
        result = await db.execute(
            select(TargetPrice).where(
                and_(
                    TargetPrice.portfolio_id == portfolio_id,
                    TargetPrice.symbol == symbol,
                    TargetPrice.position_type == (position_type or 'LONG')
                )
            )
        )
        return result.scalar_one_or_none()

    async def _calculate_position_metrics(
        self,
        db: AsyncSession,
        target_price: TargetPrice
    ) -> None:
        """
        Calculate position-level metrics for a target price.
        """
        if not target_price.position_id:
            return

        # Get position
        result = await db.execute(
            select(Position).where(Position.id == target_price.position_id)
        )
        position = result.scalar_one_or_none()

        if not position or not position.market_value:
            return

        # Get portfolio equity balance
        equity_balance = await self._get_portfolio_equity_balance(db, target_price.portfolio_id)

        if equity_balance and equity_balance > 0:
            # Calculate position weight as fraction (0-1), will convert to percentage for API
            position_weight_fraction = abs(position.market_value) / equity_balance
            
            # Store as percentage for API compatibility but note it's converted from fraction
            target_price.position_weight = position_weight_fraction * 100

            # Calculate contribution to portfolio return using fraction
            if target_price.expected_return_eoy:
                target_price.contribution_to_portfolio_return = (
                    position_weight_fraction * target_price.expected_return_eoy / 100
                )

            # Calculate contribution to portfolio risk
            target_price.contribution_to_portfolio_risk = await self._calculate_risk_contribution(
                db, target_price, position_weight_fraction
            )
        else:
            # Equity balance is null or zero - skip weight calculations
            logger.warning(f"Portfolio {target_price.portfolio_id} has no equity_balance, "
                          f"skipping weight calculations for position {position.id}")
            target_price.position_weight = None
            target_price.contribution_to_portfolio_return = None
            target_price.contribution_to_portfolio_risk = None

    async def _calculate_portfolio_metrics(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        target_prices: List[TargetPrice],
        positions: List[Position]
    ) -> Dict[str, Optional[Decimal]]:
        """
        Calculate portfolio-level metrics from target prices.
        """
        if not target_prices:
            return {}

        portfolio_value = await self._get_portfolio_value(db, portfolio_id)
        if not portfolio_value or portfolio_value <= 0:
            return {}

        # Calculate weighted returns
        weighted_eoy = Decimal(0)
        weighted_next_year = Decimal(0)
        weighted_downside = Decimal(0)
        total_weight = Decimal(0)

        for tp in target_prices:
            # Find matching position
            position = next(
                (p for p in positions if p.symbol == tp.symbol
                 and (p.position_type.value if hasattr(p.position_type, 'value') else p.position_type) == tp.position_type),
                None
            )

            if position and position.market_value:
                weight = abs(position.market_value) / portfolio_value

                if tp.expected_return_eoy:
                    weighted_eoy += weight * tp.expected_return_eoy

                if tp.expected_return_next_year:
                    weighted_next_year += weight * tp.expected_return_next_year

                if tp.downside_return:
                    weighted_downside += weight * tp.downside_return

                total_weight += weight

        # Normalize by actual weight (in case not all positions have targets)
        if total_weight > 0:
            weighted_eoy = weighted_eoy / total_weight * 100
            weighted_next_year = weighted_next_year / total_weight * 100
            weighted_downside = weighted_downside / total_weight * 100

        # Calculate risk-adjusted metrics
        # Simple approximations for now
        sharpe_ratio = None
        sortino_ratio = None

        if weighted_eoy and weighted_downside:
            # Approximate volatility from upside/downside spread
            volatility = abs(weighted_eoy - weighted_downside) / 2
            if volatility > 0:
                risk_free_rate = Decimal(0.04)  # 4% risk-free rate assumption
                sharpe_ratio = (weighted_eoy - risk_free_rate) / volatility

                # Sortino uses downside deviation
                downside_dev = abs(weighted_downside) if weighted_downside < 0 else volatility / 2
                if downside_dev > 0:
                    sortino_ratio = (weighted_eoy - risk_free_rate) / downside_dev

        return {
            'weighted_return_eoy': weighted_eoy if total_weight > 0 else None,
            'weighted_return_next_year': weighted_next_year if total_weight > 0 else None,
            'weighted_downside': weighted_downside if total_weight > 0 else None,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio
        }

    async def _get_portfolio_value(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> Optional[Decimal]:
        """
        Get total portfolio value from positions.
        """
        result = await db.execute(
            select(func.sum(Position.market_value))
            .where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.exit_date.is_(None)
                )
            )
        )
        return result.scalar()

    async def _get_portfolio_equity_balance(
        self,
        db: AsyncSession,
        portfolio_id: UUID
    ) -> Optional[Decimal]:
        """
        Get portfolio equity balance from Portfolio model.
        """
        result = await db.execute(
            select(Portfolio.equity_balance).where(Portfolio.id == portfolio_id)
        )
        return result.scalar()

    async def _get_position_beta(
        self,
        db: AsyncSession,
        position_id: UUID
    ) -> Decimal:
        """
        Get market beta for a position from PositionFactorExposure table.
        
        Returns:
            Decimal: Beta value, defaults to 1.0 if not found
        """
        try:
            result = await db.execute(
                select(PositionFactorExposure.exposure_value)
                .join(FactorDefinition)
                .where(
                    and_(
                        PositionFactorExposure.position_id == position_id,
                        FactorDefinition.name == "Market Beta"
                    )
                )
                .order_by(PositionFactorExposure.calculation_date.desc())
                .limit(1)
            )
            beta_value = result.scalar()
            
            if beta_value is not None:
                return beta_value
            else:
                logger.debug(f"No beta found for position {position_id}, using default 1.0")
                return Decimal('1.0')
                
        except Exception as e:
            logger.warning(f"Error retrieving beta for position {position_id}: {e}")
            return Decimal('1.0')

    async def _get_position_volatility(
        self,
        db: AsyncSession,
        symbol: str,
        window_days: int = 90
    ) -> Optional[Decimal]:
        """
        Calculate volatility from historical price data.
        
        Args:
            symbol: Security symbol
            window_days: Number of trading days to use (default 90)
            
        Returns:
            Decimal: Annualized volatility or None if insufficient data
        """
        try:
            # Get historical prices for volatility calculation
            result = await db.execute(
                select(MarketDataCache.close, MarketDataCache.date)
                .where(MarketDataCache.symbol == symbol)
                .order_by(MarketDataCache.date.desc())
                .limit(window_days + 1)  # Need n+1 prices for n returns
            )
            price_data = result.fetchall()
            
            if len(price_data) < 30:  # Minimum 30 days for reasonable volatility
                logger.debug(f"Insufficient price data for {symbol} volatility calculation")
                return None
            
            # Calculate daily returns
            returns = []
            for i in range(1, len(price_data)):
                prev_price = price_data[i][0]  # Close price
                curr_price = price_data[i-1][0]  # More recent price
                
                if prev_price and curr_price and prev_price > 0:
                    daily_return = (curr_price - prev_price) / prev_price
                    returns.append(float(daily_return))
            
            if len(returns) < 20:
                return None
            
            # Calculate standard deviation of returns
            import statistics
            volatility_daily = statistics.stdev(returns)
            
            # Annualize using square root of 252 trading days
            volatility_annual = volatility_daily * (252 ** 0.5)
            
            return Decimal(str(round(volatility_annual, 4)))
            
        except Exception as e:
            logger.warning(f"Error calculating volatility for {symbol}: {e}")
            return None

    async def _calculate_risk_contribution(
        self,
        db: AsyncSession,
        target_price: TargetPrice,
        position_weight_fraction: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate position's contribution to portfolio risk.
        
        Formula: risk_contribution = position_weight × volatility × beta
        
        Args:
            target_price: TargetPrice instance
            position_weight_fraction: Position weight as fraction (0-1)
            
        Returns:
            Decimal: Risk contribution or None if insufficient data
        """
        if not target_price.position_id:
            return None
            
        try:
            # Get beta from factor exposures
            beta = await self._get_position_beta(db, target_price.position_id)
            
            # Get volatility from historical data
            volatility = await self._get_position_volatility(db, target_price.symbol)
            
            if volatility is not None:
                # Calculate risk contribution using fractions
                risk_contribution = position_weight_fraction * volatility * beta
                return risk_contribution
            else:
                logger.debug(f"No volatility available for {target_price.symbol}, risk contribution = None")
                return None
                
        except Exception as e:
            logger.warning(f"Error calculating risk contribution for {target_price.symbol}: {e}")
            return None