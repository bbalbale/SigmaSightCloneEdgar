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

        # Create new target price
        target_price = TargetPrice(
            portfolio_id=portfolio_id,
            position_id=target_price_data.position_id,
            symbol=target_price_data.symbol,
            position_type=target_price_data.position_type or 'LONG',
            target_price_eoy=target_price_data.target_price_eoy,
            target_price_next_year=target_price_data.target_price_next_year,
            downside_target_price=target_price_data.downside_target_price,
            current_price=target_price_data.current_price,
            current_implied_vol=target_price_data.current_implied_vol,
            analyst_notes=target_price_data.analyst_notes,
            data_source=target_price_data.data_source or 'USER_INPUT',
            created_by=user_id,
            price_updated_at=datetime.utcnow()
        )

        # Calculate expected returns
        target_price.calculate_expected_returns()

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

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(target_price, field, value)

        # Update timestamp
        target_price.price_updated_at = datetime.utcnow()

        # Recalculate expected returns
        target_price.calculate_expected_returns()

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

        # Get portfolio value
        portfolio_value = await self._get_portfolio_value(db, target_price.portfolio_id)

        if portfolio_value and portfolio_value > 0:
            # Calculate position weight
            target_price.position_weight = (
                abs(position.market_value) / portfolio_value * 100
            )

            # Calculate contribution to portfolio return
            if target_price.expected_return_eoy:
                target_price.contribution_to_portfolio_return = (
                    target_price.position_weight * target_price.expected_return_eoy / 100
                )

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