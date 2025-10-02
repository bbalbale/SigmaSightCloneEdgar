"""
Strategy Service - Business logic for managing trading strategies
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models import (
    Strategy, StrategyType, StrategyLeg, StrategyMetrics,
    Position, Portfolio, User
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class StrategyService:
    """Service for managing trading strategies"""

    def __init__(self, db: AsyncSession):
        """Initialize with database session"""
        self.db = db

    def _calculate_strategy_categorization(
        self,
        strategy_type: str,
        positions: List[Position]
    ) -> Dict[str, Optional[str]]:
        """
        Calculate direction and primary_investment_class for a strategy.

        Args:
            strategy_type: The type of strategy
            positions: List of positions in the strategy

        Returns:
            Dict with 'direction' and 'primary_investment_class' keys
        """
        if not positions:
            return {'direction': None, 'primary_investment_class': None}

        # Standalone strategies: Inherit from single position
        if len(positions) == 1:
            pos = positions[0]
            return {
                'direction': pos.position_type.value if hasattr(pos.position_type, 'value') else str(pos.position_type),
                'primary_investment_class': pos.investment_class
            }

        # Multi-leg strategies: Use strategy type mapping
        strategy_type_mapping = {
            'covered_call': {'direction': 'LONG', 'class': 'PUBLIC'},
            'protective_put': {'direction': 'LONG', 'class': 'PUBLIC'},
            'iron_condor': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
            'straddle': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
            'strangle': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
            'butterfly': {'direction': 'NEUTRAL', 'class': 'OPTIONS'},
            'pairs_trade': {'direction': 'NEUTRAL', 'class': 'PUBLIC'},
        }

        if strategy_type in strategy_type_mapping:
            mapping = strategy_type_mapping[strategy_type]
            return {
                'direction': mapping['direction'],
                'primary_investment_class': mapping['class']
            }

        # Fallback: Use position with largest absolute market value
        primary_position = max(
            positions,
            key=lambda p: abs(float(p.market_value or 0))
        )

        return {
            'direction': primary_position.position_type.value if hasattr(primary_position.position_type, 'value') else str(primary_position.position_type),
            'primary_investment_class': primary_position.investment_class
        }

    async def create_strategy(
        self,
        portfolio_id: UUID,
        name: str,
        strategy_type: StrategyType = StrategyType.STANDALONE,
        description: Optional[str] = None,
        position_ids: Optional[List[UUID]] = None,
        created_by: Optional[UUID] = None
    ) -> Strategy:
        """
        Create a new strategy

        Args:
            portfolio_id: Portfolio this strategy belongs to
            name: Name of the strategy
            strategy_type: Type of strategy (default: STANDALONE)
            description: Optional description
            position_ids: Optional list of positions to include
            created_by: Optional user ID who created this

        Returns:
            Created Strategy object
        """
        try:
            # Fetch positions if provided to calculate categorization
            positions = []
            if position_ids:
                result = await self.db.execute(
                    select(Position).where(Position.id.in_(position_ids))
                )
                positions = list(result.scalars().all())

            # Calculate categorization
            categorization = self._calculate_strategy_categorization(
                strategy_type=strategy_type.value if isinstance(strategy_type, StrategyType) else strategy_type,
                positions=positions
            )

            # Create the strategy
            strategy = Strategy(
                id=uuid4(),
                portfolio_id=portfolio_id,
                name=name,
                strategy_type=strategy_type.value if isinstance(strategy_type, StrategyType) else strategy_type,
                description=description,
                is_synthetic=strategy_type != StrategyType.STANDALONE,
                direction=categorization['direction'],
                primary_investment_class=categorization['primary_investment_class'],
                created_by=created_by
            )

            self.db.add(strategy)

            # If positions provided, link them to the strategy
            if position_ids:
                await self._add_positions_to_strategy(strategy.id, position_ids)

            await self.db.commit()
            await self.db.refresh(strategy)

            logger.info(f"Created strategy {strategy.id} ({strategy.name}) for portfolio {portfolio_id}")
            return strategy

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create strategy: {e}")
            raise ValueError(f"Failed to create strategy: {e}")

    async def auto_create_standalone_strategy(
        self,
        position: Position,
        created_by: Optional[UUID] = None
    ) -> Strategy:
        """
        Automatically create a standalone strategy for a position

        Args:
            position: Position to create strategy for
            created_by: Optional user ID

        Returns:
            Created Strategy object
        """
        # Generate a descriptive name
        position_type_names = {
            'LONG': 'Long',
            'SHORT': 'Short',
            'LC': 'Long Call',
            'LP': 'Long Put',
            'SC': 'Short Call',
            'SP': 'Short Put'
        }

        type_name = position_type_names.get(
            position.position_type.value if hasattr(position.position_type, 'value') else str(position.position_type),
            position.position_type
        )
        strategy_name = f"{type_name} {position.symbol}"

        # Calculate cost basis
        cost_basis = None
        if position.entry_price and position.quantity:
            cost_basis = float(position.entry_price * position.quantity)

        # Calculate categorization (direction and investment class)
        categorization = self._calculate_strategy_categorization(
            strategy_type=StrategyType.STANDALONE.value,
            positions=[position]
        )

        # Create the standalone strategy
        strategy = Strategy(
            id=uuid4(),
            portfolio_id=position.portfolio_id,
            name=strategy_name,
            strategy_type=StrategyType.STANDALONE.value,
            description=f"Standalone strategy for {position.symbol}",
            is_synthetic=False,
            total_cost_basis=cost_basis,
            direction=categorization['direction'],
            primary_investment_class=categorization['primary_investment_class'],
            created_by=created_by
        )

        self.db.add(strategy)

        # Update the position with strategy_id
        position.strategy_id = strategy.id

        # Create strategy_leg entry
        strategy_leg = StrategyLeg(
            strategy_id=strategy.id,
            position_id=position.id,
            leg_type='single',
            leg_order=0
        )
        self.db.add(strategy_leg)

        await self.db.commit()
        await self.db.refresh(strategy)

        logger.info(f"Auto-created standalone strategy {strategy.id} for position {position.id}")
        return strategy

    async def get_strategy(
        self,
        strategy_id: UUID,
        include_positions: bool = True,
        include_metrics: bool = False
    ) -> Optional[Strategy]:
        """
        Get a strategy by ID with optional relationships

        Args:
            strategy_id: Strategy ID
            include_positions: Include positions in response
            include_metrics: Include metrics in response

        Returns:
            Strategy object or None
        """
        query = select(Strategy).where(Strategy.id == strategy_id)

        if include_positions:
            query = query.options(selectinload(Strategy.positions))

        if include_metrics:
            query = query.options(selectinload(Strategy.metrics))

        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_strategies(
        self,
        portfolio_id: Optional[UUID] = None,
        strategy_type: Optional[StrategyType] = None,
        is_synthetic: Optional[bool] = None,
        include_positions: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Strategy]:
        """
        List strategies with optional filters

        Args:
            portfolio_id: Filter by portfolio
            strategy_type: Filter by strategy type
            is_synthetic: Filter by synthetic status
            include_positions: Include positions in response
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Strategy objects
        """
        query = select(Strategy)

        # Apply filters
        filters = []
        if portfolio_id:
            filters.append(Strategy.portfolio_id == portfolio_id)
        if strategy_type:
            filters.append(Strategy.strategy_type == strategy_type.value)
        if is_synthetic is not None:
            filters.append(Strategy.is_synthetic == is_synthetic)

        # Always filter out closed (soft-deleted) strategies
        filters.append(Strategy.closed_at.is_(None))

        if filters:
            query = query.where(and_(*filters))

        # Include relationships
        if include_positions:
            query = query.options(selectinload(Strategy.positions))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_strategy(
        self,
        strategy_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        strategy_type: Optional[StrategyType] = None
    ) -> Optional[Strategy]:
        """
        Update a strategy

        Args:
            strategy_id: Strategy to update
            name: New name (optional)
            description: New description (optional)
            strategy_type: New type (optional)

        Returns:
            Updated Strategy or None if not found
        """
        strategy = await self.get_strategy(strategy_id, include_positions=False)
        if not strategy:
            return None

        if name is not None:
            strategy.name = name
        if description is not None:
            strategy.description = description
        if strategy_type is not None:
            strategy.strategy_type = strategy_type.value
            strategy.is_synthetic = strategy_type != StrategyType.STANDALONE

        strategy.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(strategy)

        logger.info(f"Updated strategy {strategy_id}")
        return strategy

    async def delete_strategy(
        self,
        strategy_id: UUID,
        reassign_positions: bool = True
    ) -> bool:
        """
        Delete a strategy (or close it)

        Args:
            strategy_id: Strategy to delete
            reassign_positions: If True, create standalone strategies for orphaned positions

        Returns:
            True if deleted, False if not found
        """
        strategy = await self.get_strategy(strategy_id, include_positions=True)
        if not strategy:
            return False

        # If there are positions and we need to reassign them
        if strategy.positions and reassign_positions:
            for position in strategy.positions:
                # Create a standalone strategy for each position
                await self.auto_create_standalone_strategy(position)

        # Mark strategy as closed instead of deleting (soft delete)
        strategy.closed_at = datetime.utcnow()

        await self.db.commit()
        logger.info(f"Closed strategy {strategy_id}")
        return True

    async def combine_into_strategy(
        self,
        position_ids: List[UUID],
        strategy_name: str,
        strategy_type: StrategyType,
        portfolio_id: UUID,
        description: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Strategy:
        """
        Combine multiple positions into a multi-leg strategy

        Args:
            position_ids: Positions to combine
            strategy_name: Name for the new strategy
            strategy_type: Type of multi-leg strategy
            portfolio_id: Portfolio ID
            description: Optional description
            created_by: Optional user ID

        Returns:
            Created Strategy object
        """
        # Verify all positions exist and belong to the same portfolio
        query = select(Position).where(
            and_(
                Position.id.in_(position_ids),
                Position.portfolio_id == portfolio_id
            )
        )
        result = await self.db.execute(query)
        positions = result.scalars().all()

        if len(positions) != len(position_ids):
            raise ValueError("Some positions not found or don't belong to the portfolio")

        # Create the multi-leg strategy
        strategy = await self.create_strategy(
            portfolio_id=portfolio_id,
            name=strategy_name,
            strategy_type=strategy_type,
            description=description,
            created_by=created_by
        )

        # Collect old standalone strategies to delete
        old_strategy_ids = set()
        for position in positions:
            if position.strategy_id:
                # Query to check if this is a standalone strategy
                old_strategy_result = await self.db.execute(
                    select(Strategy).where(Strategy.id == position.strategy_id)
                )
                old_strategy = old_strategy_result.scalar_one_or_none()
                if old_strategy and old_strategy.strategy_type == 'standalone':
                    old_strategy_ids.add(old_strategy.id)

        # Link positions to the new strategy
        for i, position in enumerate(positions):
            # Update position's strategy_id
            position.strategy_id = strategy.id

            # Create strategy_leg entry
            leg_type = self._determine_leg_type(position, strategy_type)
            strategy_leg = StrategyLeg(
                strategy_id=strategy.id,
                position_id=position.id,
                leg_type=leg_type,
                leg_order=i
            )
            self.db.add(strategy_leg)

        # Delete old standalone strategies (they now have no positions)
        if old_strategy_ids:
            await self.db.execute(
                delete(Strategy).where(Strategy.id.in_(old_strategy_ids))
            )
            logger.info(f"Deleted {len(old_strategy_ids)} orphaned standalone strategies")

        # Calculate aggregated metrics
        await self._calculate_strategy_metrics(strategy)

        await self.db.commit()
        await self.db.refresh(strategy)

        logger.info(f"Combined {len(positions)} positions into strategy {strategy.id}")
        return strategy

    async def detect_strategies(
        self,
        portfolio_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Detect potential multi-leg strategies in a portfolio

        Args:
            portfolio_id: Portfolio to analyze

        Returns:
            List of detected strategy patterns
        """
        # Get all positions in the portfolio that are in standalone strategies
        query = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.strategy_id.in_(
                    select(Strategy.id).where(
                        Strategy.strategy_type == StrategyType.STANDALONE.value
                    )
                )
            )
        ).options(selectinload(Position.strategy))

        result = await self.db.execute(query)
        positions = result.scalars().all()

        detected = []

        # Group positions by underlying symbol for options
        positions_by_underlying = {}
        for pos in positions:
            if pos.underlying_symbol:
                if pos.underlying_symbol not in positions_by_underlying:
                    positions_by_underlying[pos.underlying_symbol] = []
                positions_by_underlying[pos.underlying_symbol].append(pos)

        # Detect common patterns
        for underlying, related_positions in positions_by_underlying.items():
            # Check for covered call (long stock + short call)
            stocks = [p for p in related_positions if p.position_type.value in ['LONG', 'SHORT']]
            calls = [p for p in related_positions if p.position_type.value in ['SC', 'LC']]
            puts = [p for p in related_positions if p.position_type.value in ['SP', 'LP']]

            # Covered Call detection
            for stock in stocks:
                if stock.position_type.value == 'LONG':
                    for call in calls:
                        if call.position_type.value == 'SC':
                            detected.append({
                                'type': StrategyType.COVERED_CALL,
                                'positions': [stock.id, call.id],
                                'confidence': 0.9,
                                'description': f"Covered Call on {underlying}"
                            })

            # Protective Put detection
            for stock in stocks:
                if stock.position_type.value == 'LONG':
                    for put in puts:
                        if put.position_type.value == 'LP':
                            detected.append({
                                'type': StrategyType.PROTECTIVE_PUT,
                                'positions': [stock.id, put.id],
                                'confidence': 0.9,
                                'description': f"Protective Put on {underlying}"
                            })

        return detected

    async def _add_positions_to_strategy(
        self,
        strategy_id: UUID,
        position_ids: List[UUID]
    ):
        """Add positions to a strategy"""
        for i, position_id in enumerate(position_ids):
            # Update position's strategy_id
            stmt = update(Position).where(Position.id == position_id).values(strategy_id=strategy_id)
            await self.db.execute(stmt)

            # Create strategy_leg entry
            strategy_leg = StrategyLeg(
                strategy_id=strategy_id,
                position_id=position_id,
                leg_type='single' if len(position_ids) == 1 else 'multi',
                leg_order=i
            )
            self.db.add(strategy_leg)

    def _determine_leg_type(self, position: Position, strategy_type: StrategyType) -> str:
        """Determine the leg type based on position and strategy type"""
        if strategy_type == StrategyType.COVERED_CALL:
            if position.position_type.value in ['LONG', 'SHORT']:
                return 'underlying'
            elif position.position_type.value == 'SC':
                return 'short_call'
        elif strategy_type == StrategyType.PROTECTIVE_PUT:
            if position.position_type.value in ['LONG', 'SHORT']:
                return 'underlying'
            elif position.position_type.value == 'LP':
                return 'protective_put'

        return 'leg'

    async def _calculate_strategy_metrics(self, strategy: Strategy):
        """Calculate and store aggregated metrics for a strategy"""
        # This would aggregate Greeks, P&L, etc. across all positions
        # For now, just calculate total cost basis
        query = select(
            func.sum(Position.entry_price * Position.quantity)
        ).where(Position.strategy_id == strategy.id)

        result = await self.db.execute(query)
        total_cost = result.scalar()

        if total_cost:
            strategy.total_cost_basis = float(total_cost)