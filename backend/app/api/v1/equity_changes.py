"""
Equity Changes API

Endpoints for managing portfolio capital contributions and withdrawals.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.database import get_async_session
from app.models.equity_changes import EquityChangeType
from app.models.users import User
from app.schemas.equity_change_schemas import (
    EquityChangeCreateRequest,
    EquityChangeExportRequest,
    EquityChangeListResponse,
    EquityChangeResponse,
    EquityChangeSummaryPeriod,
    EquityChangeSummaryResponse,
    EquityChangeUpdateRequest,
)
from app.services.equity_change_service import EquityChangeService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/equity-changes",
    tags=["equity-changes"],
)

CurrentUser = User


def get_service(db: AsyncSession) -> EquityChangeService:
    return EquityChangeService(db)


@router.get("", response_model=EquityChangeListResponse)
async def list_equity_changes(
    portfolio_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_deleted: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List equity changes for a portfolio with pagination."""
    service = get_service(db)
    try:
        items, total_items = await service.list_equity_changes(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
            include_deleted=include_deleted,
        )

        total_pages = max((total_items + page_size - 1) // page_size, 1) if total_items else 0
        response_items = [EquityChangeResponse.model_validate(item) for item in items]

        return EquityChangeListResponse(
            items=response_items,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
    except ValueError as error:
        code, message = str(error).split(": ", 1) if ": " in str(error) else ("EQUITY_001", str(error))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": message}) from error


@router.post("", response_model=EquityChangeResponse, status_code=status.HTTP_201_CREATED)
async def create_equity_change(
    portfolio_id: UUID,
    payload: EquityChangeCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a contribution or withdrawal for the portfolio."""
    service = get_service(db)
    try:
        equity_change = await service.create_equity_change(
            portfolio_id=portfolio_id,
            user=current_user,
            change_type=payload.change_type,
            amount=payload.amount,
            change_date=payload.change_date,
            notes=payload.notes,
        )
        return EquityChangeResponse.model_validate(equity_change)
    except ValueError as error:
        code, message = str(error).split(": ", 1) if ": " in str(error) else ("EQUITY_001", str(error))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": message}) from error


@router.get("/{equity_change_id}", response_model=EquityChangeResponse)
async def get_equity_change(
    portfolio_id: UUID,
    equity_change_id: UUID,
    include_deleted: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve a single equity change."""
    service = get_service(db)
    try:
        equity_change = await service.get_equity_change(
            portfolio_id=portfolio_id,
            equity_change_id=equity_change_id,
            user_id=current_user.id,
            include_deleted=include_deleted,
        )
        return EquityChangeResponse.model_validate(equity_change)
    except ValueError as error:
        code, message = str(error).split(": ", 1) if ": " in str(error) else ("EQUITY_008", str(error))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": message}) from error


@router.put("/{equity_change_id}", response_model=EquityChangeResponse)
async def update_equity_change(
    portfolio_id: UUID,
    equity_change_id: UUID,
    payload: EquityChangeUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update an equity change within the edit window."""
    service = get_service(db)
    try:
        equity_change = await service.update_equity_change(
            portfolio_id=portfolio_id,
            equity_change_id=equity_change_id,
            user_id=current_user.id,
            amount=payload.amount,
            change_date=payload.change_date,
            notes=payload.notes,
        )
        return EquityChangeResponse.model_validate(equity_change)
    except ValueError as error:
        code, message = str(error).split(": ", 1) if ": " in str(error) else ("EQUITY_006", str(error))
        status_code = status.HTTP_400_BAD_REQUEST if code in {"EQUITY_001", "EQUITY_002", "EQUITY_003", "EQUITY_006"} else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail={"code": code, "message": message}) from error


@router.delete("/{equity_change_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equity_change(
    portfolio_id: UUID,
    equity_change_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Soft delete an equity change within the 30-day window."""
    service = get_service(db)
    try:
        await service.delete_equity_change(
            portfolio_id=portfolio_id,
            equity_change_id=equity_change_id,
            user_id=current_user.id,
        )
    except ValueError as error:
        code, message = str(error).split(": ", 1) if ": " in str(error) else ("EQUITY_009", str(error))
        status_code = status.HTTP_400_BAD_REQUEST if code in {"EQUITY_007", "EQUITY_009"} else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail={"code": code, "message": message}) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=EquityChangeSummaryResponse)
async def get_equity_change_summary(
    portfolio_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return aggregated equity change metrics for hero cards."""
    service = get_service(db)
    try:
        base_summary = await service.get_summary(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )
        last_change = await service.get_last_change(portfolio_id=portfolio_id, user_id=current_user.id)
        periods = {
            "30d": await service.get_period_summary(portfolio_id, current_user.id, 30),
            "90d": await service.get_period_summary(portfolio_id, current_user.id, 90),
        }

        summary_periods = {
            key: EquityChangeSummaryPeriod(
                contributions=value["total_contributions"],
                withdrawals=value["total_withdrawals"],
                net_flow=value["total_contributions"] - value["total_withdrawals"],
            )
            for key, value in periods.items()
        }

        return EquityChangeSummaryResponse(
            portfolio_id=portfolio_id,
            total_contributions=base_summary["total_contributions"],
            total_withdrawals=base_summary["total_withdrawals"],
            net_flow=base_summary["total_contributions"] - base_summary["total_withdrawals"],
            last_change=EquityChangeResponse.model_validate(last_change) if last_change else None,
            periods=summary_periods,
        )
    except ValueError as error:
        code, message = str(error).split(": ", 1) if ": " in str(error) else ("EQUITY_004", str(error))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": message}) from error


@router.get("/export")
async def export_equity_changes(
    portfolio_id: UUID,
    format: str = Query("csv"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Export equity changes (CSV)."""
    service = get_service(db)
    request = EquityChangeExportRequest(format=format, start_date=start_date, end_date=end_date)

    try:
        records = await service.export_equity_changes(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            start_date=request.start_date,
            end_date=request.end_date,
            include_deleted=False,
        )
    except ValueError as error:
        code, message = str(error).split(": ", 1) if ": " in str(error) else ("EQUITY_004", str(error))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": message}) from error

    if request.format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "portfolio_id",
                "change_type",
                "amount",
                "change_date",
                "notes",
                "created_at",
                "updated_at",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    record.id,
                    record.portfolio_id,
                    record.change_type.value,
                    f"{record.amount:.2f}",
                    record.change_date.isoformat(),
                    record.notes or "",
                    record.created_at.isoformat(),
                    record.updated_at.isoformat() if record.updated_at else "",
                ]
            )

        buffer.seek(0)
        filename = f"equity_changes_{portfolio_id}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "EQUITY_010", "message": "Unsupported export format"})
