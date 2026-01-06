"""
Position Management API Endpoints - Full CRUD Operations

This module handles position lifecycle operations: creating, updating,
deleting positions with smart features (validation, duplicate detection, etc.).

**Architecture Context** (Position Management Phase 1 - Nov 3, 2025):
- Service Layer: app/services/position_service.py (PositionService)
- THIS FILE (API Layer): FastAPI REST endpoints
- Data Layer: app/models/positions.py (Position model)

**Endpoints - Core CRUD**:
- POST   /positions/                    -> Create single position
- POST   /positions/bulk                -> Bulk create positions
- GET    /positions/{id}                -> Get single position
- PUT    /positions/{id}                -> Update position
- DELETE /positions/{id}                -> Delete position (soft/hard)
- DELETE /positions/bulk                -> Bulk delete positions

**Endpoints - Smart Features**:
- POST   /positions/validate-symbol     -> Validate symbol via market data
- GET    /positions/check-duplicate     -> Check for duplicate symbols
- GET    /positions/tags-for-symbol     -> Get tags to inherit

**Related Files**:
- Service: app/services/position_service.py (PositionService)
- Schemas: app/schemas/position_schemas.py (Request/Response models)
- Models: app/models/positions.py (Position, PositionType)
- Frontend: src/services/positionApiService.ts
- Documentation: frontend/_docs/ClaudeUISuggestions/13-POSITION-MANAGEMENT-PLAN.md

**Router Registration**:
Registered in app/api/v1/router.py as:
  `api_router.include_router(positions_router)`
Router has prefix="/positions" defined internally, creating routes like: /api/v1/positions/
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_validated_user
from app.models import User
from app.services.position_service import PositionService
from app.schemas.position_schemas import (
    CreatePositionRequest,
    BulkCreatePositionsRequest,
    UpdatePositionRequest,
    BulkDeletePositionsRequest,
    PositionResponse,
    BulkPositionsResponse,
    DeletePositionResponse,
    BulkDeleteResponse,
    DuplicateCheckResponse,
    SymbolValidationResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/positions", tags=["positions"])


# ============================================================================
# CORE CRUD ENDPOINTS
# ============================================================================

@router.post("/", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(
    request: CreatePositionRequest,
    portfolio_id: UUID = Query(..., description="Portfolio to add position to"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Create a new position in the specified portfolio.

    **Validation:**
    - User must own the portfolio
    - Symbol format (1-20 uppercase chars)
    - Quantity > 0 for LONG, < 0 for SHORT
    - Avg cost > 0
    - Investment class (PUBLIC, OPTIONS, PRIVATE)

    **Smart Features:**
    - Use POST /positions/validate-symbol first to validate symbol
    - Use GET /positions/check-duplicate to check for duplicates
    - Use GET /positions/tags-for-symbol to get tags to inherit

    **Returns:** Created position with all fields
    """
    service = PositionService(db)

    try:
        position = await service.create_position(
            portfolio_id=portfolio_id,
            symbol=request.symbol,
            quantity=request.quantity,
            avg_cost=request.avg_cost,
            position_type=request.position_type,
            investment_class=request.investment_class,
            user_id=current_user.id,
            notes=request.notes,
            entry_date=request.entry_date,
            investment_subtype=request.investment_subtype,
            underlying_symbol=request.underlying_symbol,
            strike_price=request.strike_price,
            expiration_date=request.expiration_date,
        )

        return PositionResponse.model_validate(position)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create position: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create position")


@router.post("/bulk", response_model=BulkPositionsResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_positions(
    request: BulkCreatePositionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Bulk create multiple positions in a single transaction.

    **Transaction Safety:**
    - All positions created or none (rollback on any failure)
    - Validates each position individually
    - User must own the portfolio

    **Request Body:**
    ```json
    {
        "portfolio_id": "uuid",
        "positions": [
            {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_cost": 150.00,
                "position_type": "LONG",
                "investment_class": "PUBLIC",
                "notes": "Optional notes"
            },
            ...
        ]
    }
    ```

    **Returns:** List of created positions
    """
    service = PositionService(db)

    try:
        # Convert Pydantic models to dicts for service layer
        positions_data = [pos.model_dump() for pos in request.positions]

        positions = await service.bulk_create_positions(
            portfolio_id=request.portfolio_id,
            positions_data=positions_data,
            user_id=current_user.id,
        )

        return BulkPositionsResponse(
            success=True,
            count=len(positions),
            positions=[PositionResponse.model_validate(p) for p in positions]
        )

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to bulk create positions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to bulk create positions")


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Get a single position by ID.

    **Permission Check:**
    - User must own the portfolio containing this position

    **Returns:** Position with all fields
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.positions import Position

    try:
        # Get position with portfolio for auth check
        result = await db.execute(
            select(Position)
            .options(selectinload(Position.portfolio))
            .where(Position.id == position_id)
        )
        position = result.scalar()

        if not position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

        # Check user owns portfolio
        if position.portfolio.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not own this position")

        return PositionResponse.model_validate(position)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get position {position_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get position")


@router.put("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: UUID,
    request: UpdatePositionRequest,
    allow_symbol_edit: bool = Query(False, description="Allow symbol editing (< 5 min only)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Update position fields.

    **Editable Fields (always):**
    - quantity (affects portfolio value)
    - avg_cost (affects unrealized P&L)
    - position_type (affects exposure calculations)
    - notes (user annotations)
    - exit_price / exit_date / close_quantity (calculate realized P&L)
    - entry_price (corrections)

    **Editable Fields (conditional):**
    - symbol (ONLY if allow_symbol_edit=true AND created < 5 min AND no snapshots)

    **Non-editable Fields:**
    - investment_class (use delete + create instead)
    - portfolio_id (cannot move positions between portfolios)

    **Permission Check:**
    - User must own the portfolio
    - Position must not be deleted

    **Returns:** Updated position
    """
    service = PositionService(db)

    try:
        position = await service.update_position(
            position_id=position_id,
            user_id=current_user.id,
            quantity=request.quantity,
            avg_cost=request.avg_cost,
            position_type=request.position_type,
            notes=request.notes,
            symbol=request.symbol,
            allow_symbol_edit=allow_symbol_edit,
            exit_price=request.exit_price,
            exit_date=request.exit_date,
            entry_price=request.entry_price,
            close_quantity=request.close_quantity,
        )

        return PositionResponse.model_validate(position)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update position {position_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update position")


@router.delete("/{position_id}", response_model=DeletePositionResponse)
async def delete_position(
    position_id: UUID,
    force_hard_delete: bool = Query(False, description="Force hard delete (Reverse Addition)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Delete a position (soft or hard delete).

    **Soft Delete (default):**
    - Sets deleted_at timestamp
    - Preserves historical snapshots
    - Preserves target prices
    - Cascades to position_tags
    - Position excluded from active calculations

    **Hard Delete (Reverse Addition):**
    - Only if force_hard_delete=true AND created < 5 min AND no snapshots
    - Permanently removes from database
    - No audit trail (use with caution)
    - Cascades to position_tags

    **Permission Check:**
    - User must own the portfolio

    **Returns:** Delete confirmation with type (soft/hard)
    """
    service = PositionService(db)

    try:
        if force_hard_delete:
            # Check if should hard delete
            should_hard, reason = await service.should_hard_delete(position_id)

            if should_hard:
                result = await service.hard_delete_position(position_id, current_user.id)
                return DeletePositionResponse(**result)
            else:
                # Fall back to soft delete
                logger.info(f"Hard delete not allowed for {position_id}: {reason}, using soft delete")
                result = await service.soft_delete_position(position_id, current_user.id)
                result["type"] = "soft_delete"
                return DeletePositionResponse(**result)
        else:
            # Soft delete
            result = await service.soft_delete_position(position_id, current_user.id)
            result["type"] = "soft_delete"
            return DeletePositionResponse(**result)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete position {position_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete position")


@router.delete("/bulk", response_model=BulkDeleteResponse)
async def bulk_delete_positions(
    request: BulkDeletePositionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Bulk delete multiple positions.

    **Transaction Safety:**
    - All positions deleted or none (rollback on any failure)
    - User must own all positions

    **Delete Type:**
    - Always soft delete for bulk operations (safety)
    - Use force_hard_delete=false (override not allowed for bulk)

    **Request Body:**
    ```json
    {
        "position_ids": ["uuid1", "uuid2", "uuid3"]
    }
    ```

    **Returns:** Delete confirmation with list of symbols
    """
    service = PositionService(db)

    try:
        result = await service.bulk_delete_positions(
            position_ids=request.position_ids,
            user_id=current_user.id,
        )

        return BulkDeleteResponse(**result)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to bulk delete positions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to bulk delete positions")


# ============================================================================
# SMART FEATURES ENDPOINTS
# ============================================================================

@router.post("/validate-symbol", response_model=SymbolValidationResponse)
async def validate_symbol(
    symbol: str = Query(..., description="Symbol to validate"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Validate symbol exists via market data API.

    **Validation:**
    - Uses YFinance primary provider
    - Skips synthetic symbols (private investments)
    - Graceful fallback (non-blocking)

    **Use Case:**
    - Call before creating position
    - Show warning if invalid: "Symbol 'XYZ' not found"

    **Returns:** Validation result with message
    """
    service = PositionService(db)

    try:
        is_valid, message = await service.validate_symbol(symbol)

        return SymbolValidationResponse(
            valid=is_valid,
            symbol=symbol.upper(),
            message=message if message else None
        )

    except Exception as e:
        logger.error(f"Failed to validate symbol {symbol}: {e}")
        # Non-blocking: return valid=True on errors
        return SymbolValidationResponse(
            valid=True,
            symbol=symbol.upper(),
            message=f"Validation error: {str(e)}"
        )


@router.get("/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate(
    portfolio_id: UUID = Query(..., description="Portfolio to check"),
    symbol: str = Query(..., description="Symbol to check for duplicates"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Check if symbol already exists in portfolio.

    **Duplicate Detection:**
    - Finds all active positions with this symbol
    - Returns existing positions
    - Returns tags to inherit (from existing positions)

    **Use Case:**
    - Call before creating position
    - Show warning: "AAPL already exists. Add as new lot?"
    - Auto-apply inherited tags to new lot

    **Returns:** Duplicate status with existing positions and tags
    """
    service = PositionService(db)

    try:
        has_duplicates, existing_positions = await service.check_duplicate_positions(
            portfolio_id=portfolio_id,
            symbol=symbol
        )

        tags_to_inherit = []
        if has_duplicates:
            tags = await service.get_tags_for_symbol(portfolio_id, symbol)
            tags_to_inherit = [tag.id for tag in tags]

        return DuplicateCheckResponse(
            has_duplicates=has_duplicates,
            existing_positions=[PositionResponse.model_validate(p) for p in existing_positions],
            tags_to_inherit=tags_to_inherit
        )

    except Exception as e:
        logger.error(f"Failed to check duplicates for {symbol}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check duplicates")


@router.get("/tags-for-symbol", response_model=List[UUID])
async def get_tags_for_symbol(
    portfolio_id: UUID = Query(..., description="Portfolio to check"),
    symbol: str = Query(..., description="Symbol to get tags for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_validated_user)
):
    """
    Get tags from existing positions of same symbol.

    **Tag Inheritance:**
    - Collects unique tags from all existing positions
    - New lot inherits these tags automatically
    - Ensures consistent tagging across lots

    **Use Case:**
    - Call when adding duplicate symbol
    - Auto-apply tags to new lot
    - User can modify before saving

    **Returns:** List of tag IDs to inherit
    """
    service = PositionService(db)

    try:
        tags = await service.get_tags_for_symbol(portfolio_id, symbol)
        return [tag.id for tag in tags]

    except Exception as e:
        logger.error(f"Failed to get tags for symbol {symbol}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get tags for symbol")
