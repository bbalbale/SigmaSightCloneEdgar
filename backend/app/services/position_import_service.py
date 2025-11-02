"""
Position Import Service

Handles importing positions from parsed CSV data into the database.

Key responsibilities:
- Convert PositionData to Position database records
- Determine position_type from quantity and options fields
- Generate UUIDs using configured strategy
- Handle options-specific fields
- Handle closed positions (exit_date/exit_price)
- Auto-classify investment_class if not provided

Position Type Determination:
- Negative quantity → SHORT
- Options with quantity > 0 → LC (long call) or LP (long put)
- Options with quantity < 0 → SC (short call) or SP (short put)
- Positive quantity (stocks) → LONG
"""
from uuid import UUID
from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.positions import Position, PositionType
from app.services.csv_parser_service import PositionData
from app.core.uuid_strategy import generate_position_uuid
from app.core.logging import get_logger

logger = get_logger(__name__)


class ImportResult:
    """Result of position import operation"""

    def __init__(self):
        self.success_count: int = 0
        self.failure_count: int = 0
        self.positions: List[Position] = []
        self.errors: List[Dict[str, Any]] = []

    def add_success(self, position: Position):
        """Add successful import"""
        self.success_count += 1
        self.positions.append(position)

    def add_failure(self, error: Dict[str, Any]):
        """Add failed import"""
        self.failure_count += 1
        self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total": self.success_count + self.failure_count,
            "positions": [str(p.id) for p in self.positions],
            "errors": self.errors
        }


class PositionImportService:
    """Service for importing positions from CSV data"""

    @staticmethod
    def determine_position_type(
        quantity: Decimal,
        investment_class: str,
        option_type: str = None
    ) -> PositionType:
        """
        Determine position_type enum value.

        Logic:
        1. Negative quantity → SHORT (for stocks) or SHORT options
        2. OPTIONS class:
           - CALL + positive quantity → LC (long call)
           - CALL + negative quantity → SC (short call)
           - PUT + positive quantity → LP (long put)
           - PUT + negative quantity → SP (short put)
        3. Positive quantity → LONG (for stocks)

        Args:
            quantity: Position quantity (can be negative)
            investment_class: Investment class (PUBLIC, OPTIONS, PRIVATE)
            option_type: Option type (CALL or PUT) if OPTIONS class

        Returns:
            PositionType enum value

        Examples:
            >>> determine_position_type(Decimal("100"), "PUBLIC", None)
            PositionType.LONG
            >>> determine_position_type(Decimal("-100"), "PUBLIC", None)
            PositionType.SHORT
            >>> determine_position_type(Decimal("10"), "OPTIONS", "CALL")
            PositionType.LC
            >>> determine_position_type(Decimal("-10"), "OPTIONS", "PUT")
            PositionType.SP
        """
        # OPTIONS positions
        if investment_class == "OPTIONS" and option_type:
            if quantity > 0:
                return PositionType.LC if option_type == "CALL" else PositionType.LP
            else:
                return PositionType.SC if option_type == "CALL" else PositionType.SP

        # Stock positions
        if quantity < 0:
            return PositionType.SHORT
        else:
            return PositionType.LONG

    @staticmethod
    def auto_classify_investment_class(
        symbol: str,
        underlying_symbol: str = None,
        strike_price: Decimal = None,
        expiration_date: str = None
    ) -> str:
        """
        Auto-classify investment class if not provided.

        Logic:
        1. Has underlying/strike/expiration → OPTIONS
        2. Tickered money market (e.g., SPAXX) → PUBLIC
        3. Non-tickered cash (CASH_USD) → PRIVATE
        4. Default → PUBLIC

        Args:
            symbol: Position symbol
            underlying_symbol: Optional underlying symbol
            strike_price: Optional strike price
            expiration_date: Optional expiration date

        Returns:
            Investment class: PUBLIC, OPTIONS, or PRIVATE
        """
        # Check for options fields
        if underlying_symbol or strike_price or expiration_date:
            return "OPTIONS"

        # Non-tickered cash positions
        if symbol.upper().startswith("CASH_"):
            return "PRIVATE"

        # Default to PUBLIC (includes SPAXX, VMFXX, etc.)
        return "PUBLIC"

    @staticmethod
    async def import_positions(
        db: AsyncSession,
        portfolio_id: UUID,
        user_id: UUID,
        positions_data: List[PositionData]
    ) -> ImportResult:
        """
        Import positions from parsed CSV data.

        Creates Position records in the database with:
        - Deterministic UUIDs (based on config)
        - Auto-classified investment_class
        - Correct position_type enum
        - Options-specific fields
        - Closed position fields

        Args:
            db: Database session
            portfolio_id: Portfolio UUID
            user_id: User UUID (for logging/audit)
            positions_data: List of parsed PositionData

        Returns:
            ImportResult with success/failure counts and details

        Note:
            This method does NOT commit the transaction.
            Caller is responsible for transaction management.
        """
        result = ImportResult()

        for position_data in positions_data:
            try:
                # Auto-classify investment class if not provided
                investment_class = position_data.investment_class
                if not investment_class:
                    investment_class = PositionImportService.auto_classify_investment_class(
                        symbol=position_data.symbol,
                        underlying_symbol=position_data.underlying_symbol,
                        strike_price=position_data.strike_price,
                        expiration_date=position_data.expiration_date
                    )
                    logger.debug(f"Auto-classified {position_data.symbol} as {investment_class}")

                # Determine position_type
                position_type = PositionImportService.determine_position_type(
                    quantity=position_data.quantity,
                    investment_class=investment_class,
                    option_type=position_data.option_type
                )

                # Generate UUID (deterministic based on config)
                position_uuid = generate_position_uuid(
                    portfolio_id=portfolio_id,
                    symbol=position_data.symbol,
                    entry_date=position_data.entry_date
                )

                # Parse dates from strings to date objects
                entry_date = datetime.strptime(position_data.entry_date, "%Y-%m-%d").date()
                expiration_date = None
                if position_data.expiration_date:
                    expiration_date = datetime.strptime(position_data.expiration_date, "%Y-%m-%d").date()

                exit_date = None
                if position_data.exit_date:
                    exit_date = datetime.strptime(position_data.exit_date, "%Y-%m-%d").date()

                # Create Position record
                position = Position(
                    id=position_uuid,
                    portfolio_id=portfolio_id,
                    symbol=position_data.symbol.upper(),
                    position_type=position_type,
                    quantity=position_data.quantity,  # Keep signed quantity for long/short logic
                    entry_price=position_data.entry_price,
                    entry_date=entry_date,
                    exit_price=position_data.exit_price,
                    exit_date=exit_date,
                    # Options fields
                    underlying_symbol=position_data.underlying_symbol.upper() if position_data.underlying_symbol else None,
                    strike_price=position_data.strike_price,
                    expiration_date=expiration_date,
                    # Investment classification
                    investment_class=investment_class,
                    investment_subtype=position_data.investment_subtype,
                    # Market data (will be populated by batch processing)
                    last_price=None,
                    market_value=None,
                    unrealized_pnl=None,
                    realized_pnl=None
                )

                db.add(position)
                result.add_success(position)

                logger.info(
                    f"Imported position: {position_data.symbol} "
                    f"({position_type.value}, {investment_class})"
                )

            except Exception as e:
                logger.error(
                    f"Failed to import position {position_data.symbol}: {str(e)}",
                    exc_info=True
                )
                result.add_failure({
                    "symbol": position_data.symbol,
                    "row": position_data.row_number,
                    "error": str(e)
                })

        return result


# Convenience instance
position_import_service = PositionImportService()
