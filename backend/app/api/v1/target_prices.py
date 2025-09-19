"""
API endpoints for Target Price management
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.v1.auth import get_current_user
from app.models.users import User, Portfolio
from app.schemas.target_prices import (
    TargetPriceCreate,
    TargetPriceUpdate,
    TargetPriceResponse,
    TargetPriceBulkCreate,
    TargetPriceBulkUpdate,
    PortfolioTargetPriceSummary,
    TargetPriceImportCSV,
    TargetPriceExportRequest,
    TargetPriceDeleteResponse
)
from app.services.target_price_service import TargetPriceService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/target-prices", tags=["Target Prices"])
target_price_service = TargetPriceService()


@router.post(
    "/{portfolio_id}", 
    response_model=TargetPriceResponse,
    summary="Create a new target price for a portfolio position",
    description="""Creates a portfolio-specific target price with smart price resolution, automatic position linking, and investment class detection. 
    
    Features:
    - Smart price resolution (market data → live API → user provided)
    - Automatic position linking if position_id not provided
    - Investment class detection (PUBLIC/OPTIONS/PRIVATE)
    - Options underlying symbol resolution for accurate pricing
    - Equity-based position weight calculation and risk contributions
    
    Phase 2 changes: Removed deprecated fields (analyst_notes, data_source, current_implied_vol)""",
    responses={
        200: {"description": "Target price created successfully with calculated metrics"},
        400: {"description": "Invalid input data or target price already exists"},
        403: {"description": "Not authorized to access this portfolio"},
        404: {"description": "Portfolio not found"},
        500: {"description": "Internal server error during creation"}
    }
)
async def create_target_price(
    portfolio_id: UUID,
    target_price_data: TargetPriceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    try:
        target_price = await target_price_service.create_target_price(
            db,
            portfolio_id,
            target_price_data,
            current_user.id
        )
        return TargetPriceResponse.from_orm(target_price)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating target price: {e}")
        raise HTTPException(status_code=500, detail="Failed to create target price")


@router.get(
    "/{portfolio_id}", 
    response_model=List[TargetPriceResponse],
    summary="Get all target prices for a portfolio with optional filtering",
    description="""Returns all target prices for a portfolio with optional server-side filtering by symbol or position type. 
    
    Performance optimizations:
    - SQL-level filtering applied at database query level
    - Indexed lookups for optimal performance
    - Automatic portfolio ownership verification
    
    Filters are case-insensitive and applied efficiently in the database.""",
    responses={
        200: {"description": "List of target prices (may be empty)"},
        403: {"description": "Not authorized to access this portfolio"},
        404: {"description": "Portfolio not found"}
    }
)
async def get_portfolio_target_prices(
    portfolio_id: UUID,
    symbol: Optional[str] = Query(None, description="Filter by specific symbol (case-insensitive)"),
    position_type: Optional[str] = Query(None, description="Filter by position type (LONG, SHORT, LC, LP, SC, SP)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    # Apply filters at SQL level for better performance
    target_prices = await target_price_service.get_portfolio_target_prices(
        db, portfolio_id, symbol=symbol, position_type=position_type
    )

    return [TargetPriceResponse.from_orm(tp) for tp in target_prices]


@router.get(
    "/{portfolio_id}/summary", 
    response_model=PortfolioTargetPriceSummary,
    summary="Get portfolio target price summary with aggregated metrics",
    description="""Returns comprehensive portfolio-level target price analytics including coverage statistics, equity-weighted returns, and risk-adjusted metrics.
    
    Key features:
    - Equity-based weighting using portfolio.equity_balance for accurate calculations
    - Coverage analysis (percentage of positions with target prices)
    - Risk-adjusted metrics (Sharpe and Sortino ratios)
    - Graceful degradation when equity_balance unavailable
    
    Weighting methodology uses equity_balance instead of simple market value summation for more accurate portfolio analysis.""",
    responses={
        200: {"description": "Portfolio target price summary with all calculated metrics"},
        403: {"description": "Not authorized to access this portfolio"},
        404: {"description": "Portfolio not found"},
        500: {"description": "Error calculating portfolio metrics"}
    }
)
async def get_portfolio_target_summary(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    try:
        summary = await target_price_service.get_portfolio_summary(db, portfolio_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get portfolio summary")


@router.get("/target/{target_price_id}", response_model=TargetPriceResponse)
async def get_target_price(
    target_price_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific target price by ID.
    """
    target_price = await target_price_service.get_target_price(db, target_price_id)

    if not target_price:
        raise HTTPException(status_code=404, detail="Target price not found")

    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, target_price.portfolio_id, current_user.id)

    return TargetPriceResponse.from_orm(target_price)


@router.put("/target/{target_price_id}", response_model=TargetPriceResponse)
async def update_target_price(
    target_price_id: UUID,
    update_data: TargetPriceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing target price.

    All fields are optional - only provided fields will be updated.
    """
    # Get the target price first to verify ownership
    target_price = await target_price_service.get_target_price(db, target_price_id)

    if not target_price:
        raise HTTPException(status_code=404, detail="Target price not found")

    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, target_price.portfolio_id, current_user.id)

    try:
        updated_target = await target_price_service.update_target_price(
            db,
            target_price_id,
            update_data
        )
        return TargetPriceResponse.from_orm(updated_target)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating target price: {e}")
        raise HTTPException(status_code=500, detail="Failed to update target price")


@router.delete(
    "/target/{target_price_id}", 
    response_model=TargetPriceDeleteResponse,
    summary="Delete a target price",
    description="""Permanently removes a target price record with portfolio ownership verification. 
    
    Returns standardized deletion result with count and any error messages.
    
    Phase 2 changes: Updated response format from simple message to structured result with 'deleted' count and 'errors' array.""",
    responses={
        200: {"description": "Target price deleted successfully", "content": {"application/json": {"example": {"deleted": 1, "errors": []}}}},
        403: {"description": "Not authorized to access this portfolio"},
        404: {"description": "Target price not found"},
        500: {"description": "Error during deletion"}
    }
)
async def delete_target_price(
    target_price_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get the target price first to verify ownership
    target_price = await target_price_service.get_target_price(db, target_price_id)

    if not target_price:
        raise HTTPException(status_code=404, detail="Target price not found")

    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, target_price.portfolio_id, current_user.id)

    deleted = await target_price_service.delete_target_price(db, target_price_id)

    if deleted:
        return {
            "deleted": 1,
            "errors": []
        }
    else:
        return {
            "deleted": 0,
            "errors": ["Target price not found"]
        }


@router.post("/{portfolio_id}/bulk", response_model=List[TargetPriceResponse])
async def bulk_create_target_prices(
    portfolio_id: UUID,
    bulk_data: TargetPriceBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create multiple target prices at once.

    Useful for initial setup or bulk updates.
    Existing target prices for the same symbol/position_type will be skipped.
    """
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    created_targets = await target_price_service.bulk_create_target_prices(
        db,
        portfolio_id,
        bulk_data.target_prices,
        current_user.id
    )

    return [TargetPriceResponse.from_orm(tp) for tp in created_targets]


@router.put(
    "/{portfolio_id}/bulk-update",
    summary="Bulk update target prices by symbol", 
    description="""Updates multiple target prices by symbol and position type with optimized performance and comprehensive error tracking.

    Performance optimizations (Phase 1):
    - O(1) lookups using pre-indexed target prices by (symbol, position_type)
    - Single database query instead of per-update queries
    - Detailed error reporting for failed updates
    
    Supports partial updates - only provided fields are updated for each target price.""",
    responses={
        200: {"description": "Bulk update completed with success/error counts", "content": {"application/json": {"example": {"updated": 5, "errors": ["MSFT not found"]}}}},
        403: {"description": "Not authorized to access this portfolio"},
        404: {"description": "Portfolio not found"}
    }
)
async def bulk_update_target_prices(
    portfolio_id: UUID,
    bulk_update: TargetPriceBulkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    # Fetch all target prices once and index by (symbol, position_type) for O(1) lookup
    target_prices = await target_price_service.get_portfolio_target_prices(db, portfolio_id)
    target_price_index = {
        (tp.symbol, tp.position_type): tp for tp in target_prices
    }

    updated_count = 0
    errors = []

    for update_item in bulk_update.updates:
        try:
            symbol = update_item.get('symbol')
            position_type = update_item.get('position_type', 'LONG')

            # Fast lookup using index
            target_price = target_price_index.get((symbol, position_type))

            if target_price:
                # Create update data
                update_data = TargetPriceUpdate(**{
                    k: v for k, v in update_item.items()
                    if k not in ['symbol', 'position_type']
                })

                await target_price_service.update_target_price(
                    db,
                    target_price.id,
                    update_data
                )
                updated_count += 1
            else:
                errors.append(f"Target price not found for {symbol} ({position_type})")

        except Exception as e:
            errors.append(f"Error updating {symbol}: {str(e)}")

    return {
        "updated": updated_count,
        "errors": errors
    }


@router.post("/{portfolio_id}/import-csv")
async def import_target_prices_csv(
    portfolio_id: UUID,
    csv_import: TargetPriceImportCSV,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Import target prices from CSV format.

    Expected CSV headers:
    symbol,position_type,target_eoy,target_next_year,downside,current_price

    Example:
    ```
    symbol,position_type,target_eoy,target_next_year,downside,current_price
    AAPL,LONG,200,220,150,180
    MSFT,LONG,400,450,350,375
    ```
    """
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    result = await target_price_service.import_from_csv(
        db,
        portfolio_id,
        csv_import.csv_content,
        csv_import.update_existing,
        current_user.id
    )

    return result


@router.post(
    "/{portfolio_id}/export",
    summary="Export target prices to CSV or JSON format",
    description="""Exports portfolio target prices with configurable format options. Always includes calculated returns and metrics.
    
    Phase 2 changes:
    - Removed 'include_calculations' parameter (always included now)
    - Simplified export always includes expected returns and risk metrics
    - Optional metadata controls inclusion of created_at/updated_at fields only
    
    Export formats:
    - CSV: Returns structured CSV string with all metrics
    - JSON: Returns array of target price objects""",
    responses={
        200: {"description": "Target prices exported successfully"},
        403: {"description": "Not authorized to access this portfolio"},
        404: {"description": "Portfolio not found"}
    }
)
async def export_target_prices(
    portfolio_id: UUID,
    export_request: TargetPriceExportRequest = Body(default=TargetPriceExportRequest()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    target_prices = await target_price_service.get_portfolio_target_prices(db, portfolio_id)

    if export_request.format == "json":
        # Return as JSON
        return [
            {
                "symbol": tp.symbol,
                "position_type": tp.position_type,
                "target_price_eoy": float(tp.target_price_eoy) if tp.target_price_eoy else None,
                "target_price_next_year": float(tp.target_price_next_year) if tp.target_price_next_year else None,
                "downside_target_price": float(tp.downside_target_price) if tp.downside_target_price else None,
                "current_price": float(tp.current_price),
                "expected_return_eoy": float(tp.expected_return_eoy) if tp.expected_return_eoy else None,
                "expected_return_next_year": float(tp.expected_return_next_year) if tp.expected_return_next_year else None,
                "downside_return": float(tp.downside_return) if tp.downside_return else None,
            }
            for tp in target_prices
        ]
    else:
        # Return as CSV string
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers (always include calculations)
        headers = ["symbol", "position_type", "target_eoy", "target_next_year", "downside", "current_price", 
                  "expected_return_eoy", "expected_return_next_year", "downside_return"]
        if export_request.include_metadata:
            headers.extend(["created_at", "updated_at"])

        writer.writerow(headers)

        # Write data (always include calculations)
        for tp in target_prices:
            row = [
                tp.symbol,
                tp.position_type,
                float(tp.target_price_eoy) if tp.target_price_eoy else "",
                float(tp.target_price_next_year) if tp.target_price_next_year else "",
                float(tp.downside_target_price) if tp.downside_target_price else "",
                float(tp.current_price),
                float(tp.expected_return_eoy) if tp.expected_return_eoy else "",
                float(tp.expected_return_next_year) if tp.expected_return_next_year else "",
                float(tp.downside_return) if tp.downside_return else ""
            ]

            if export_request.include_metadata:
                row.extend([
                    tp.created_at.isoformat() if tp.created_at else "",
                    tp.updated_at.isoformat() if tp.updated_at else ""
                ])

            writer.writerow(row)

        return {"csv": output.getvalue()}


async def _verify_portfolio_ownership(
    db: AsyncSession,
    portfolio_id: UUID,
    user_id: UUID
) -> Portfolio:
    """
    Verify that the user owns the portfolio.
    Raises HTTPException if not found or not owned.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if portfolio.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this portfolio")

    return portfolio