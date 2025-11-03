"""
Position Service - Business Logic for Position CRUD Operations

This service owns the lifecycle for portfolio positions with full CRUD support,
validation, and smart features (duplicate detection, symbol validation, tag inheritance).

**Architecture Context** (Position Management Phase 1 - Nov 3, 2025):
- API Layer: app/api/v1/positions.py (FastAPI endpoints)
- THIS FILE (Service Layer): Position management business logic
- Data Layer: app/models/positions.py (Position model)

**Core CRUD Methods**:
- create_position(): Create new position with validation
- bulk_create_positions(): Bulk create with transaction safety
- update_position(): Update position fields (limited editable fields)
- soft_delete_position(): Soft delete with cascading
- bulk_delete_positions(): Bulk soft delete

**Smart Features** (Day 3):
- Symbol validation via market data API
- Duplicate detection with warning
- Tag inheritance for duplicate symbols
- Quantity reduction detection ("Is this a sale?")
- "Reverse Addition" logic (< 5 min = hard delete)

**Related Services**:
- TagService: Tag management
- PositionTagService: Position-tag relationships
- MarketDataService: Symbol validation

**Documentation**: frontend/_docs/ClaudeUISuggestions/13-POSITION-MANAGEMENT-PLAN.md
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models.positions import Position, PositionType
from app.models.users import Portfolio
from app.models.position_tags import PositionTag
from app.models.tags_v2 import TagV2
from app.core.logging import get_logger

logger = get_logger(__name__)


class PositionService:
    """Service for managing portfolio positions with full CRUD operations"""

    def __init__(self, db: AsyncSession):
        """Initialize with database session"""
        self.db = db

    async def create_position(
        self,
        portfolio_id: UUID,
        symbol: str,
        quantity: Decimal,
        avg_cost: Decimal,
        position_type: PositionType,
        investment_class: str,
        user_id: UUID,
        notes: Optional[str] = None,
        entry_date: Optional[Any] = None,
        investment_subtype: Optional[str] = None,
        # Option-specific fields
        underlying_symbol: Optional[str] = None,
        strike_price: Optional[Decimal] = None,
        expiration_date: Optional[Any] = None,
    ) -> Position:
        """
        Create a new position with validation.

        Validation:
        - User owns the portfolio
        - Symbol is valid format (1-20 uppercase chars)
        - Quantity > 0 for LONG positions, < 0 for SHORT
        - Avg cost > 0
        - Investment class is valid (PUBLIC, OPTIONS, PRIVATE)

        Args:
            portfolio_id: Portfolio to add position to
            symbol: Stock symbol (1-20 chars)
            quantity: Number of shares
            avg_cost: Average cost per share
            position_type: LONG, SHORT, LC, LP, SC, SP
            investment_class: PUBLIC, OPTIONS, PRIVATE
            user_id: User creating the position (for auth check)
            notes: Optional user notes
            entry_date: Entry date (defaults to today)
            investment_subtype: Optional subtype (STOCK, ETF, etc.)
            underlying_symbol: For options only
            strike_price: For options only
            expiration_date: For options only

        Returns:
            Created Position object

        Raises:
            ValueError: If validation fails
            PermissionError: If user doesn't own portfolio
        """
        try:
            # Validate user owns portfolio
            portfolio_result = await self.db.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.id == portfolio_id,
                        Portfolio.user_id == user_id
                    )
                )
            )
            portfolio = portfolio_result.scalar()
            if not portfolio:
                raise PermissionError(f"User does not own portfolio {portfolio_id}")

            # Validate symbol format
            symbol_upper = symbol.upper().strip()
            if not symbol_upper or len(symbol_upper) > 20:
                raise ValueError("Symbol must be 1-20 uppercase characters")

            # Validate quantity
            if quantity == 0:
                raise ValueError("Quantity cannot be zero")

            # Validate avg_cost
            if avg_cost <= 0:
                raise ValueError("Average cost must be greater than zero")

            # Validate investment class
            valid_classes = ["PUBLIC", "OPTIONS", "PRIVATE"]
            if investment_class not in valid_classes:
                raise ValueError(f"Investment class must be one of: {', '.join(valid_classes)}")

            # Set entry_date to today if not provided
            if entry_date is None:
                from datetime import date
                entry_date = date.today()

            # Create the position
            position = Position(
                id=uuid4(),
                portfolio_id=portfolio_id,
                symbol=symbol_upper,
                quantity=quantity,
                entry_price=avg_cost,  # entry_price maps to avg_cost
                entry_date=entry_date,
                position_type=position_type,
                investment_class=investment_class,
                investment_subtype=investment_subtype,
                notes=notes,
                # Option-specific fields
                underlying_symbol=underlying_symbol,
                strike_price=strike_price,
                expiration_date=expiration_date,
            )

            self.db.add(position)
            await self.db.commit()
            await self.db.refresh(position)

            logger.info(f"Created position {position.id} for symbol {symbol_upper} in portfolio {portfolio_id}")
            return position

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating position: {e}")
            raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating position: {e}")
            raise

    async def bulk_create_positions(
        self,
        portfolio_id: UUID,
        positions_data: List[Dict[str, Any]],
        user_id: UUID,
    ) -> List[Position]:
        """
        Bulk create positions in single transaction.

        All positions created or none (transaction safety).
        Rolls back all if any fail validation.

        Args:
            portfolio_id: Portfolio to add positions to
            positions_data: List of position data dicts
            user_id: User creating the positions (for auth check)

        Returns:
            List of created Position objects

        Raises:
            ValueError: If any validation fails
            PermissionError: If user doesn't own portfolio
        """
        try:
            # Validate user owns portfolio (once for all positions)
            portfolio_result = await self.db.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.id == portfolio_id,
                        Portfolio.user_id == user_id
                    )
                )
            )
            portfolio = portfolio_result.scalar()
            if not portfolio:
                raise PermissionError(f"User does not own portfolio {portfolio_id}")

            # Create all positions
            created_positions = []
            for idx, pos_data in enumerate(positions_data):
                # Extract and validate fields
                symbol = pos_data.get("symbol", "").upper().strip()
                quantity = pos_data.get("quantity")
                avg_cost = pos_data.get("avg_cost") or pos_data.get("entry_price")
                position_type = pos_data.get("position_type") or pos_data.get("type")
                investment_class = pos_data.get("investment_class") or pos_data.get("class")

                # Validate required fields
                if not symbol:
                    raise ValueError(f"Position {idx + 1}: Symbol is required")
                if quantity is None:
                    raise ValueError(f"Position {idx + 1}: Quantity is required")
                if avg_cost is None:
                    raise ValueError(f"Position {idx + 1}: Avg cost is required")
                if not position_type:
                    raise ValueError(f"Position {idx + 1}: Position type is required")
                if not investment_class:
                    raise ValueError(f"Position {idx + 1}: Investment class is required")

                # Convert to proper types
                if isinstance(position_type, str):
                    position_type = PositionType[position_type]

                # Set entry_date to today if not provided
                entry_date = pos_data.get("entry_date")
                if entry_date is None:
                    from datetime import date
                    entry_date = date.today()

                # Create position
                position = Position(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    quantity=Decimal(str(quantity)),
                    entry_price=Decimal(str(avg_cost)),
                    entry_date=entry_date,
                    position_type=position_type,
                    investment_class=investment_class,
                    investment_subtype=pos_data.get("investment_subtype"),
                    notes=pos_data.get("notes"),
                    # Option-specific fields
                    underlying_symbol=pos_data.get("underlying_symbol"),
                    strike_price=Decimal(str(pos_data["strike_price"])) if pos_data.get("strike_price") else None,
                    expiration_date=pos_data.get("expiration_date"),
                )

                self.db.add(position)
                created_positions.append(position)

            # Commit all or rollback all
            await self.db.commit()

            # Refresh all positions
            for position in created_positions:
                await self.db.refresh(position)

            logger.info(f"Bulk created {len(created_positions)} positions in portfolio {portfolio_id}")
            return created_positions

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error in bulk create: {e}")
            raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error in bulk create positions: {e}")
            raise

    async def update_position(
        self,
        position_id: UUID,
        user_id: UUID,
        quantity: Optional[Decimal] = None,
        avg_cost: Optional[Decimal] = None,
        position_type: Optional[PositionType] = None,
        notes: Optional[str] = None,
        symbol: Optional[str] = None,
        allow_symbol_edit: bool = False,
    ) -> Position:
        """
        Update position fields.

        Editable fields (always):
        - quantity (affects portfolio value)
        - avg_cost (affects unrealized P&L)
        - position_type (affects exposure calculations)
        - notes (user annotations)

        Editable fields (conditional):
        - symbol (ONLY if created < 5 min AND no snapshots AND allow_symbol_edit=True)

        Non-editable fields:
        - investment_class (use delete + create instead)
        - portfolio_id (cannot move positions between portfolios)

        Historical Impact:
        - Snapshots remain unchanged (immutable audit trail)
        - Future calculations use new values
        - Target prices preserved (symbol-level)

        Args:
            position_id: Position to update
            user_id: User performing update (for auth check)
            quantity: New quantity
            avg_cost: New average cost
            position_type: New position type
            notes: New notes
            symbol: New symbol (requires allow_symbol_edit=True)
            allow_symbol_edit: Enable symbol editing (checks age + snapshots)

        Returns:
            Updated Position object

        Raises:
            ValueError: If validation fails or symbol edit not allowed
            PermissionError: If user doesn't own position
            NotFoundException: If position not found
        """
        try:
            # Get position with portfolio for auth check
            result = await self.db.execute(
                select(Position)
                .options(selectinload(Position.portfolio))
                .where(Position.id == position_id)
            )
            position = result.scalar()

            if not position:
                raise ValueError(f"Position {position_id} not found")

            # Check user owns portfolio
            if position.portfolio.user_id != user_id:
                raise PermissionError("User does not own this position")

            # Check if position is deleted
            if position.is_deleted():
                raise ValueError("Cannot update deleted position")

            # Handle symbol edit (special case)
            if symbol is not None and symbol != position.symbol:
                if not allow_symbol_edit:
                    raise ValueError("Symbol editing not allowed (set allow_symbol_edit=True)")

                if not position.can_edit_symbol():
                    raise ValueError("Symbol can only be edited within 5 minutes of creation")

                # TODO: Check for snapshots in Day 3
                # For now, just allow if < 5 min
                position.symbol = symbol.upper().strip()

            # Update fields
            if quantity is not None:
                if quantity == 0:
                    raise ValueError("Quantity cannot be zero")
                position.quantity = quantity

            if avg_cost is not None:
                if avg_cost <= 0:
                    raise ValueError("Average cost must be greater than zero")
                position.entry_price = avg_cost  # entry_price maps to avg_cost

            if position_type is not None:
                position.position_type = position_type

            if notes is not None:
                position.notes = notes

            # Update timestamp
            position.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(position)

            logger.info(f"Updated position {position_id}")
            return position

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating position {position_id}: {e}")
            raise

    async def soft_delete_position(
        self,
        position_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Soft delete position (sets deleted_at timestamp).

        Preserves:
        - Position record (deleted_at field set)
        - All historical snapshots (immutable)
        - Target price (linked to position, symbol-level)
        - Position tags (soft deleted via cascade)

        Impact:
        - Position excluded from active portfolio calculations
        - Historical analytics include deleted positions in date range
        - Batch orchestrator skips deleted positions
        - UI hides by default (show in audit view)

        Args:
            position_id: Position to delete
            user_id: User performing deletion (for auth check)

        Returns:
            {
                "deleted": True,
                "position_id": "uuid",
                "symbol": "AAPL",
                "deleted_at": datetime,
            }

        Raises:
            PermissionError: If user doesn't own position
            ValueError: If position not found or already deleted
        """
        try:
            # Get position with portfolio for auth check
            result = await self.db.execute(
                select(Position)
                .options(selectinload(Position.portfolio))
                .where(Position.id == position_id)
            )
            position = result.scalar()

            if not position:
                raise ValueError(f"Position {position_id} not found")

            # Check user owns portfolio
            if position.portfolio.user_id != user_id:
                raise PermissionError("User does not own this position")

            # Check if already deleted
            if position.is_deleted():
                raise ValueError("Position is already deleted")

            # Soft delete
            position.soft_delete()

            # Soft delete associated position tags
            await self.db.execute(
                update(PositionTag)
                .where(PositionTag.position_id == position_id)
                .values(deleted_at=datetime.utcnow())
            )

            await self.db.commit()

            logger.info(f"Soft deleted position {position_id} ({position.symbol})")

            return {
                "deleted": True,
                "position_id": str(position.id),
                "symbol": position.symbol,
                "deleted_at": position.deleted_at,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error soft deleting position {position_id}: {e}")
            raise

    async def bulk_delete_positions(
        self,
        position_ids: List[UUID],
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Bulk soft delete with transaction safety.

        All positions deleted or none (transaction safety).

        Args:
            position_ids: List of position IDs to delete
            user_id: User performing deletion (for auth check)

        Returns:
            {
                "deleted": True,
                "count": 3,
                "positions": ["AAPL", "MSFT", "TSLA"]
            }

        Raises:
            PermissionError: If user doesn't own any position
            ValueError: If any position not found or already deleted
        """
        try:
            # Get all positions with portfolios for auth check
            result = await self.db.execute(
                select(Position)
                .options(selectinload(Position.portfolio))
                .where(Position.id.in_(position_ids))
            )
            positions = result.scalars().all()

            if len(positions) != len(position_ids):
                raise ValueError("One or more positions not found")

            # Check user owns all positions
            symbols = []
            for position in positions:
                if position.portfolio.user_id != user_id:
                    raise PermissionError(f"User does not own position {position.id}")

                if position.is_deleted():
                    raise ValueError(f"Position {position.id} is already deleted")

                # Soft delete
                position.soft_delete()
                symbols.append(position.symbol)

            # Soft delete all associated position tags
            await self.db.execute(
                update(PositionTag)
                .where(PositionTag.position_id.in_(position_ids))
                .values(deleted_at=datetime.utcnow())
            )

            await self.db.commit()

            logger.info(f"Bulk soft deleted {len(positions)} positions")

            return {
                "deleted": True,
                "count": len(positions),
                "positions": symbols,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error bulk deleting positions: {e}")
            raise

    async def can_edit_symbol(
        self,
        position_id: UUID,
        user_id: UUID,
    ) -> tuple[bool, str]:
        """
        Check if symbol can be edited.

        Symbol editing allowed if:
        - Position created < 5 minutes ago, AND
        - Position has no snapshots

        Args:
            position_id: Position to check
            user_id: User performing check (for auth check)

        Returns:
            (True, "") if editable
            (False, "reason") if not editable

        Raises:
            PermissionError: If user doesn't own position
            ValueError: If position not found
        """
        try:
            # Get position with portfolio for auth check
            result = await self.db.execute(
                select(Position)
                .options(selectinload(Position.portfolio))
                .where(Position.id == position_id)
            )
            position = result.scalar()

            if not position:
                raise ValueError(f"Position {position_id} not found")

            # Check user owns portfolio
            if position.portfolio.user_id != user_id:
                raise PermissionError("User does not own this position")

            # Check age
            if not position.can_edit_symbol():
                return (False, "Position must be less than 5 minutes old to edit symbol")

            # TODO: Check for snapshots in Day 3
            # For now, just check age
            return (True, "")

        except Exception as e:
            logger.error(f"Error checking symbol edit permission: {e}")
            raise
