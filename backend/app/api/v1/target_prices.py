"""
API endpoints for Target Price management
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
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


@router.post("/{portfolio_id}", response_model=TargetPriceResponse)
async def create_target_price(
    portfolio_id: UUID,
    target_price_data: TargetPriceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new target price for a portfolio position.

    - **portfolio_id**: The portfolio to add the target price to
    - **symbol**: The security symbol
    - **position_type**: LONG, SHORT, LC, LP, SC, SP (optional, defaults to LONG)
    - **target_price_eoy**: End-of-year target price
    - **target_price_next_year**: Next year target price
    - **downside_target_price**: Downside scenario target
    - **current_price**: Current market price (required for calculations)
    """
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


@router.get("/{portfolio_id}", response_model=List[TargetPriceResponse])
async def get_portfolio_target_prices(
    portfolio_id: UUID,
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    position_type: Optional[str] = Query(None, description="Filter by position type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get all target prices for a portfolio.

    Optionally filter by symbol or position type.
    """
    # Verify user owns the portfolio
    portfolio = await _verify_portfolio_ownership(db, portfolio_id, current_user.id)

    # Apply filters at SQL level for better performance
    target_prices = await target_price_service.get_portfolio_target_prices(
        db, portfolio_id, symbol=symbol, position_type=position_type
    )

    return [TargetPriceResponse.from_orm(tp) for tp in target_prices]


@router.get("/{portfolio_id}/summary", response_model=PortfolioTargetPriceSummary)
async def get_portfolio_target_summary(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get portfolio target price summary with aggregated metrics.

    Returns:
    - Coverage percentage
    - Weighted expected returns
    - Risk-adjusted metrics (Sharpe, Sortino)
    - Individual target prices with calculations
    """
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
    db: AsyncSession = Depends(get_async_session)
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
    db: AsyncSession = Depends(get_async_session)
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


@router.delete("/target/{target_price_id}", response_model=TargetPriceDeleteResponse)
async def delete_target_price(
    target_price_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete a target price.
    """
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
    db: AsyncSession = Depends(get_async_session)
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


@router.put("/{portfolio_id}/bulk-update")
async def bulk_update_target_prices(
    portfolio_id: UUID,
    bulk_update: TargetPriceBulkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Bulk update target prices by symbol.

    Expects a list of updates with symbol, position_type, and fields to update.
    """
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
    db: AsyncSession = Depends(get_async_session)
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


@router.post("/{portfolio_id}/export")
async def export_target_prices(
    portfolio_id: UUID,
    export_request: TargetPriceExportRequest = Body(default=TargetPriceExportRequest()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Export target prices to CSV or JSON format.
    """
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