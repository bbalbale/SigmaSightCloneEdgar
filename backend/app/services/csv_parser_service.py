"""
CSV Parser Service

Handles CSV file validation and parsing for portfolio imports.

Supports 12-column CSV template with comprehensive validation:
- File-level validation (size, type, format)
- Row-level validation (35+ error codes)
- Investment class auto-detection
- Options symbol parsing (OCC format)
- Duplicate detection

CSV Columns (12):
1. Symbol (required)
2. Quantity (required, can be negative for shorts)
3. Entry Price Per Share (required)
4. Entry Date (required, YYYY-MM-DD)
5. Investment Class (optional: PUBLIC, OPTIONS, PRIVATE)
6. Investment Subtype (optional)
7. Underlying Symbol (options only)
8. Strike Price (options only)
9. Expiration Date (options only, YYYY-MM-DD)
10. Option Type (options only: CALL or PUT)
11. Exit Date (optional, YYYY-MM-DD)
12. Exit Price Per Share (optional)
"""
import csv
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, date as date_type
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, InvalidOperation
from fastapi import UploadFile

from app.core.logging import get_logger
from app.core.onboarding_errors import (
    create_csv_error,
    ERR_CSV_001, ERR_CSV_002, ERR_CSV_003, ERR_CSV_004, ERR_CSV_005, ERR_CSV_006,
    ERR_POS_001, ERR_POS_002, ERR_POS_003, ERR_POS_004, ERR_POS_005, ERR_POS_006,
    ERR_POS_007, ERR_POS_008, ERR_POS_009, ERR_POS_010, ERR_POS_011, ERR_POS_012,
    ERR_POS_013, ERR_POS_014, ERR_POS_015, ERR_POS_016, ERR_POS_017, ERR_POS_018,
    ERR_POS_019, ERR_POS_020, ERR_POS_021, ERR_POS_022, ERR_POS_023,
    get_error_message
)

logger = get_logger(__name__)

# Constants
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_SYMBOL_LENGTH = 100
MAX_QUANTITY_DECIMALS = 6
MAX_PRICE_DECIMALS = 2
MIN_DATE = datetime.now() - timedelta(days=365 * 100)  # 100 years ago
MAX_DATE = datetime.now()

# Required columns
REQUIRED_COLUMNS = [
    "Symbol",
    "Quantity",
    "Entry Price Per Share",
    "Entry Date"
]

# All expected columns
ALL_COLUMNS = [
    "Symbol",
    "Quantity",
    "Entry Price Per Share",
    "Entry Date",
    "Investment Class",
    "Investment Subtype",
    "Underlying Symbol",
    "Strike Price",
    "Expiration Date",
    "Option Type",
    "Exit Date",
    "Exit Price Per Share"
]

# Valid investment classes
VALID_INVESTMENT_CLASSES = ["PUBLIC", "OPTIONS", "PRIVATE"]

# Valid investment subtypes by class
VALID_SUBTYPES = {
    "PUBLIC": ["STOCK", "ETF", "MUTUAL_FUND", "BOND", "CASH"],
    "OPTIONS": ["CALL", "PUT"],
    "PRIVATE": [
        "PRIVATE_EQUITY",
        "VENTURE_CAPITAL",
        "HEDGE_FUND",
        "PRIVATE_REIT",
        "REAL_ESTATE",
        "CRYPTOCURRENCY",  # Also accept CRYPTO for backward compatibility
        "CRYPTO",  # Alias
        "ART",
        "MONEY_MARKET",
        "TREASURY_BILLS",
        "CASH",
        "COMMODITY",
        "OTHER"
    ]
}


@dataclass
class PositionData:
    """
    Parsed position data from CSV row.

    All 12 columns are represented, with optional fields as Optional types.
    """
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    entry_date: str  # YYYY-MM-DD format

    # Optional fields
    investment_class: Optional[str] = None
    investment_subtype: Optional[str] = None
    underlying_symbol: Optional[str] = None
    strike_price: Optional[Decimal] = None
    expiration_date: Optional[str] = None  # YYYY-MM-DD format
    option_type: Optional[str] = None  # CALL or PUT
    exit_date: Optional[str] = None  # YYYY-MM-DD format
    exit_price: Optional[Decimal] = None

    # Row number for error reporting
    row_number: int = 0


@dataclass
class CSVValidationResult:
    """Result of CSV validation"""
    is_valid: bool
    errors: List[Dict[str, Any]]
    positions: List[PositionData]
    total_rows: int
    valid_rows: int


class CSVParserService:
    """Service for parsing and validating CSV position imports"""

    @staticmethod
    async def validate_csv(csv_file: UploadFile) -> CSVValidationResult:
        """
        Validate CSV file and return validation result.

        Performs:
        1. File-level validation (size, type, format)
        2. Row-level validation (all position fields)
        3. Duplicate detection

        Args:
            csv_file: Uploaded CSV file

        Returns:
            CSVValidationResult with errors and parsed positions

        Raises:
            Does not raise exceptions - returns all errors in result
        """
        errors: List[Dict[str, Any]] = []
        positions: List[PositionData] = []

        # 1. File size check
        contents = await csv_file.read()
        await csv_file.seek(0)  # Reset for later reading

        if len(contents) > MAX_FILE_SIZE_BYTES:
            error = create_csv_error(
                ERR_CSV_001,
                get_error_message(ERR_CSV_001)
            )
            return CSVValidationResult(
                is_valid=False,
                errors=[{
                    "code": error.code,
                    "message": error.message,
                    "details": error.details
                }],
                positions=[],
                total_rows=0,
                valid_rows=0
            )

        # 2. File type check
        if not csv_file.filename or not csv_file.filename.lower().endswith('.csv'):
            error = create_csv_error(
                ERR_CSV_002,
                get_error_message(ERR_CSV_002)
            )
            return CSVValidationResult(
                is_valid=False,
                errors=[{
                    "code": error.code,
                    "message": error.message,
                    "details": error.details
                }],
                positions=[],
                total_rows=0,
                valid_rows=0
            )

        # 3. Parse CSV
        try:
            content_str = contents.decode('utf-8')
            lines = content_str.strip().split('\n')

            # Filter out comment lines (starting with #)
            lines = [line for line in lines if not line.strip().startswith('#')]

            if len(lines) == 0:
                error = create_csv_error(
                    ERR_CSV_003,
                    get_error_message(ERR_CSV_003)
                )
                return CSVValidationResult(
                    is_valid=False,
                    errors=[{
                        "row": error.details.get("row") if error.details else None,
                        "symbol": None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    }],
                    positions=[],
                    total_rows=0,
                    valid_rows=0
                )

            reader = csv.DictReader(lines)

            # 4. Validate headers
            if not reader.fieldnames:
                error = create_csv_error(
                    ERR_CSV_005,
                    get_error_message(ERR_CSV_005)
                )
                return CSVValidationResult(
                    is_valid=False,
                    errors=[{
                        "row": error.details.get("row") if error.details else None,
                        "symbol": None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    }],
                    positions=[],
                    total_rows=0,
                    valid_rows=0
                )

            # Check required columns
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
            if missing_columns:
                for col in missing_columns:
                    error = create_csv_error(
                        ERR_CSV_004,
                        get_error_message(ERR_CSV_004).format(column=col),
                        field=col
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })

                return CSVValidationResult(
                    is_valid=False,
                    errors=errors,
                    positions=[],
                    total_rows=0,
                    valid_rows=0
                )

            # 5. Validate rows
            row_number = 1  # Start at 1 (header is row 0)
            seen_positions = set()  # For duplicate detection

            for row in reader:
                row_number += 1

                # Skip empty rows
                if not any(row.values()):
                    continue

                # Validate and parse row
                position_result = CSVParserService._validate_row(row, row_number)

                if position_result["errors"]:
                    errors.extend(position_result["errors"])

                if position_result["position"]:
                    position = position_result["position"]

                    # Duplicate detection
                    position_key = (position.symbol.upper(), position.entry_date)
                    if position_key in seen_positions:
                        error = create_csv_error(
                            ERR_POS_023,
                            get_error_message(ERR_POS_023),
                            row_number=row_number,
                            field="Symbol + Entry Date",
                            value=f"{position.symbol} on {position.entry_date}"
                        )
                        errors.append({
                            "row": error.details.get("row") if error.details else None,
                            "symbol": symbol if symbol else None,
                            "code": error.code,
                            "message": error.message,
                            "field": error.details.get("field") if error.details else None
                        })
                    else:
                        seen_positions.add(position_key)
                        positions.append(position)

        except UnicodeDecodeError:
            error = create_csv_error(
                ERR_CSV_006,
                "File encoding error. Please ensure file is UTF-8 encoded."
            )
            return CSVValidationResult(
                is_valid=False,
                errors=[{
                    "code": error.code,
                    "message": error.message,
                    "details": error.details
                }],
                positions=[],
                total_rows=0,
                valid_rows=0
            )
        except Exception as e:
            logger.error(f"CSV parsing error: {str(e)}")
            error = create_csv_error(
                ERR_CSV_006,
                get_error_message(ERR_CSV_006)
            )
            return CSVValidationResult(
                is_valid=False,
                errors=[{
                    "code": error.code,
                    "message": error.message,
                    "details": {"exception": str(e)}
                }],
                positions=[],
                total_rows=0,
                valid_rows=0
            )

        # Return result
        is_valid = len(errors) == 0
        return CSVValidationResult(
            is_valid=is_valid,
            errors=errors,
            positions=positions,
            total_rows=row_number - 1,  # Exclude header
            valid_rows=len(positions)
        )

    @staticmethod
    def _validate_row(row: Dict[str, str], row_number: int) -> Dict[str, Any]:
        """
        Validate a single CSV row.

        Returns:
            Dictionary with 'errors' list and 'position' (PositionData or None)
        """
        errors = []

        # Trim all values
        row = {k: v.strip() if v else "" for k, v in row.items()}

        # 1. Symbol validation (allow empty for OPTIONS with separate fields)
        symbol = row.get("Symbol", "").strip()
        investment_class = row.get("Investment Class", "").strip().upper()
        underlying_symbol = row.get("Underlying Symbol", "").strip()

        # For OPTIONS positions, symbol can be empty if underlying is provided
        if not symbol:
            if investment_class == "OPTIONS" and underlying_symbol:
                # Use underlying symbol as placeholder for OPTIONS
                symbol = underlying_symbol
            else:
                error = create_csv_error(
                    ERR_POS_001,
                    get_error_message(ERR_POS_001),
                    row_number=row_number,
                    field="Symbol"
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })
                return {"errors": errors, "position": None}

        if len(symbol) > MAX_SYMBOL_LENGTH:
            error = create_csv_error(
                ERR_POS_002,
                get_error_message(ERR_POS_002),
                row_number=row_number,
                field="Symbol",
                value=symbol
            )
            errors.append({
                "row": error.details.get("row") if error.details else None,
                "symbol": symbol if symbol else None,
                "code": error.code,
                "message": error.message,
                "field": error.details.get("field") if error.details else None
            })

        # Symbol character validation (alphanumeric, dash, dot, underscore)
        if not re.match(r'^[A-Za-z0-9._-]+$', symbol):
            error = create_csv_error(
                ERR_POS_003,
                get_error_message(ERR_POS_003),
                row_number=row_number,
                field="Symbol",
                value=symbol
            )
            errors.append({
                "row": error.details.get("row") if error.details else None,
                "symbol": symbol if symbol else None,
                "code": error.code,
                "message": error.message,
                "field": error.details.get("field") if error.details else None
            })

        # 2. Quantity validation
        quantity_str = row.get("Quantity", "").strip()
        quantity = None

        if not quantity_str:
            error = create_csv_error(
                ERR_POS_004,
                get_error_message(ERR_POS_004),
                row_number=row_number,
                field="Quantity"
            )
            errors.append({
                "row": error.details.get("row") if error.details else None,
                "symbol": symbol if symbol else None,
                "code": error.code,
                "message": error.message,
                "field": error.details.get("field") if error.details else None
            })
        else:
            try:
                quantity = Decimal(quantity_str)
                if quantity == 0:
                    error = create_csv_error(
                        ERR_POS_006,
                        get_error_message(ERR_POS_006),
                        row_number=row_number,
                        field="Quantity",
                        value=quantity_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })

                # Check decimal places
                if abs(quantity.as_tuple().exponent) > MAX_QUANTITY_DECIMALS:
                    error = create_csv_error(
                        ERR_POS_007,
                        get_error_message(ERR_POS_007),
                        row_number=row_number,
                        field="Quantity",
                        value=quantity_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })
            except (InvalidOperation, ValueError):
                error = create_csv_error(
                    ERR_POS_005,
                    get_error_message(ERR_POS_005),
                    row_number=row_number,
                    field="Quantity",
                    value=quantity_str
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })

        # 3. Entry price validation
        entry_price_str = row.get("Entry Price Per Share", "").strip()
        entry_price = None

        if not entry_price_str:
            error = create_csv_error(
                ERR_POS_008,
                get_error_message(ERR_POS_008),
                row_number=row_number,
                field="Entry Price Per Share"
            )
            errors.append({
                "row": error.details.get("row") if error.details else None,
                "symbol": symbol if symbol else None,
                "code": error.code,
                "message": error.message,
                "field": error.details.get("field") if error.details else None
            })
        else:
            try:
                entry_price = Decimal(entry_price_str)
                if entry_price <= 0:
                    error = create_csv_error(
                        ERR_POS_010,
                        get_error_message(ERR_POS_010),
                        row_number=row_number,
                        field="Entry Price Per Share",
                        value=entry_price_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })

                # Check decimal places
                if abs(entry_price.as_tuple().exponent) > MAX_PRICE_DECIMALS:
                    error = create_csv_error(
                        ERR_POS_011,
                        get_error_message(ERR_POS_011),
                        row_number=row_number,
                        field="Entry Price Per Share",
                        value=entry_price_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })
            except (InvalidOperation, ValueError):
                error = create_csv_error(
                    ERR_POS_009,
                    get_error_message(ERR_POS_009),
                    row_number=row_number,
                    field="Entry Price Per Share",
                    value=entry_price_str
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })

        # 4. Entry date validation
        entry_date_str = row.get("Entry Date", "").strip()
        entry_date = None

        if not entry_date_str:
            error = create_csv_error(
                ERR_POS_012,
                get_error_message(ERR_POS_012),
                row_number=row_number,
                field="Entry Date"
            )
            errors.append({
                "row": error.details.get("row") if error.details else None,
                "symbol": symbol if symbol else None,
                "code": error.code,
                "message": error.message,
                "field": error.details.get("field") if error.details else None
            })
        else:
            try:
                entry_date_obj = datetime.strptime(entry_date_str, "%Y-%m-%d")
                entry_date = entry_date_str

                if entry_date_obj > MAX_DATE:
                    error = create_csv_error(
                        ERR_POS_014,
                        get_error_message(ERR_POS_014),
                        row_number=row_number,
                        field="Entry Date",
                        value=entry_date_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })

                if entry_date_obj < MIN_DATE:
                    error = create_csv_error(
                        ERR_POS_015,
                        get_error_message(ERR_POS_015),
                        row_number=row_number,
                        field="Entry Date",
                        value=entry_date_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })
            except ValueError:
                error = create_csv_error(
                    ERR_POS_013,
                    get_error_message(ERR_POS_013),
                    row_number=row_number,
                    field="Entry Date",
                    value=entry_date_str
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })

        # 5. Investment class validation
        investment_class = row.get("Investment Class", "").strip().upper()
        if investment_class and investment_class not in VALID_INVESTMENT_CLASSES:
            error = create_csv_error(
                ERR_POS_016,
                get_error_message(ERR_POS_016),
                row_number=row_number,
                field="Investment Class",
                value=investment_class
            )
            errors.append({
                "row": error.details.get("row") if error.details else None,
                "symbol": symbol if symbol else None,
                "code": error.code,
                "message": error.message,
                "field": error.details.get("field") if error.details else None
            })

        # 6. Investment subtype validation
        investment_subtype = row.get("Investment Subtype", "").strip().upper()
        if investment_subtype and investment_class:
            valid_subtypes = VALID_SUBTYPES.get(investment_class, [])
            if investment_subtype not in valid_subtypes:
                error = create_csv_error(
                    ERR_POS_017,
                    get_error_message(ERR_POS_017),
                    row_number=row_number,
                    field="Investment Subtype",
                    value=investment_subtype
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })

        # 7. Exit date validation (if provided)
        exit_date_str = row.get("Exit Date", "").strip()
        exit_date = None
        if exit_date_str:
            try:
                exit_date_obj = datetime.strptime(exit_date_str, "%Y-%m-%d")
                exit_date = exit_date_str

                # Exit date must be after entry date
                if entry_date:
                    entry_date_obj = datetime.strptime(entry_date, "%Y-%m-%d")
                    if exit_date_obj < entry_date_obj:
                        error = create_csv_error(
                            ERR_POS_018,
                            get_error_message(ERR_POS_018),
                            row_number=row_number,
                            field="Exit Date",
                            value=exit_date_str
                        )
                        errors.append({
                            "row": error.details.get("row") if error.details else None,
                            "symbol": symbol if symbol else None,
                            "code": error.code,
                            "message": error.message,
                            "field": error.details.get("field") if error.details else None
                        })
            except ValueError:
                error = create_csv_error(
                    ERR_POS_013,
                    f"Exit date must be in YYYY-MM-DD format",
                    row_number=row_number,
                    field="Exit Date",
                    value=exit_date_str
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })

        # 8. Exit price validation (if provided)
        exit_price_str = row.get("Exit Price Per Share", "").strip()
        exit_price = None
        if exit_price_str:
            try:
                exit_price = Decimal(exit_price_str)
            except (InvalidOperation, ValueError):
                pass  # Optional field, ignore parse errors

        # 9. Options-specific validation
        underlying_symbol = row.get("Underlying Symbol", "").strip()
        strike_price_str = row.get("Strike Price", "").strip()
        expiration_date_str = row.get("Expiration Date", "").strip()
        option_type = row.get("Option Type", "").strip().upper()

        strike_price = None
        expiration_date = None

        # If investment class is OPTIONS, validate options fields
        if investment_class == "OPTIONS":
            if not underlying_symbol:
                error = create_csv_error(
                    ERR_POS_019,
                    get_error_message(ERR_POS_019),
                    row_number=row_number,
                    field="Underlying Symbol"
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })

            if not strike_price_str:
                error = create_csv_error(
                    ERR_POS_020,
                    get_error_message(ERR_POS_020),
                    row_number=row_number,
                    field="Strike Price"
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })
            else:
                try:
                    strike_price = Decimal(strike_price_str)
                except (InvalidOperation, ValueError):
                    error = create_csv_error(
                        ERR_POS_020,
                        get_error_message(ERR_POS_020),
                        row_number=row_number,
                        field="Strike Price",
                        value=strike_price_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })

            if not expiration_date_str:
                error = create_csv_error(
                    ERR_POS_021,
                    get_error_message(ERR_POS_021),
                    row_number=row_number,
                    field="Expiration Date"
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })
            else:
                try:
                    datetime.strptime(expiration_date_str, "%Y-%m-%d")
                    expiration_date = expiration_date_str
                except ValueError:
                    error = create_csv_error(
                        ERR_POS_021,
                        get_error_message(ERR_POS_021),
                        row_number=row_number,
                        field="Expiration Date",
                        value=expiration_date_str
                    )
                    errors.append({
                        "row": error.details.get("row") if error.details else None,
                        "symbol": symbol if symbol else None,
                        "code": error.code,
                        "message": error.message,
                        "field": error.details.get("field") if error.details else None
                    })

            if not option_type or option_type not in ["CALL", "PUT"]:
                error = create_csv_error(
                    ERR_POS_022,
                    get_error_message(ERR_POS_022),
                    row_number=row_number,
                    field="Option Type"
                )
                errors.append({
                    "row": error.details.get("row") if error.details else None,
                    "symbol": symbol if symbol else None,
                    "code": error.code,
                    "message": error.message,
                    "field": error.details.get("field") if error.details else None
                })

        # If no critical errors, create PositionData
        if errors:
            return {"errors": errors, "position": None}

        position = PositionData(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            entry_date=entry_date,
            investment_class=investment_class if investment_class else None,
            investment_subtype=investment_subtype if investment_subtype else None,
            underlying_symbol=underlying_symbol if underlying_symbol else None,
            strike_price=strike_price,
            expiration_date=expiration_date,
            option_type=option_type if option_type else None,
            exit_date=exit_date,
            exit_price=exit_price,
            row_number=row_number
        )

        return {"errors": [], "position": position}

    @staticmethod
    def determine_investment_class(
        symbol: str,
        underlying_symbol: Optional[str] = None,
        strike_price: Optional[str] = None,
        expiration_date: Optional[str] = None
    ) -> str:
        """
        Auto-detect investment class if not provided.

        Detection logic:
        1. OCC options format (e.g., AAPL250117C00150000) → OPTIONS
        2. Has underlying/strike/expiration fields → OPTIONS
        3. Default → PUBLIC

        Args:
            symbol: Position symbol
            underlying_symbol: Optional underlying symbol
            strike_price: Optional strike price
            expiration_date: Optional expiration date

        Returns:
            Investment class: PUBLIC, OPTIONS, or PRIVATE
        """
        # OCC format: SYMBOL + YYMMDD + C/P + STRIKE (8 digits)
        occ_pattern = r'^[A-Z]{1,6}\d{6}[CP]\d{8}$'
        if re.match(occ_pattern, symbol.upper()):
            return "OPTIONS"

        # Check for options fields
        if underlying_symbol or strike_price or expiration_date:
            return "OPTIONS"

        # Default to PUBLIC
        return "PUBLIC"


# Convenience instance
csv_parser_service = CSVParserService()
