"""
Equity Search API endpoints.

Provides search, filtering, and sorting for equities across the symbol universe.
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.users import User
from app.schemas.equity_search import (
    PeriodType,
    SortOrder,
    EquitySearchResponse,
    EquitySearchFiltersResponse,
    VALID_SORT_COLUMNS,
)
from app.services.equity_search_service import equity_search_service

router = APIRouter(prefix="/equity-search", tags=["equity-search"])


@router.get("", response_model=EquitySearchResponse)
async def search_equities(
    query: Optional[str] = Query(
        None,
        description="Text search on symbol or company name",
        min_length=1,
        max_length=100,
    ),
    sectors: Optional[str] = Query(
        None,
        description="Comma-separated list of sectors to filter by",
    ),
    industries: Optional[str] = Query(
        None,
        description="Comma-separated list of industries to filter by",
    ),
    min_market_cap: Optional[float] = Query(
        None,
        description="Minimum market cap filter",
        ge=0,
    ),
    max_market_cap: Optional[float] = Query(
        None,
        description="Maximum market cap filter",
        ge=0,
    ),
    min_pe_ratio: Optional[float] = Query(
        None,
        description="Minimum P/E ratio filter",
    ),
    max_pe_ratio: Optional[float] = Query(
        None,
        description="Maximum P/E ratio filter",
    ),
    period: PeriodType = Query(
        PeriodType.TTM,
        description="Period for fundamental data (ttm, last_year, forward, last_quarter)",
    ),
    sort_by: str = Query(
        "market_cap",
        description=f"Column to sort by. Valid values: {', '.join(sorted(VALID_SORT_COLUMNS))}",
    ),
    sort_order: SortOrder = Query(
        SortOrder.DESC,
        description="Sort order (asc or desc)",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of results to return",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip for pagination",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EquitySearchResponse:
    """
    Search and filter equities across the symbol universe.

    Features:
    - Full-text search on symbol and company name
    - Filter by sector, industry, market cap range, P/E range
    - Sort by any metric column (market cap, P/E, factors, etc.)
    - Period selector for fundamental data (TTM, last year, forward, last quarter)

    Returns paginated results with fundamental data and factor exposures.
    """
    # Parse comma-separated lists
    sectors_list = [s.strip() for s in sectors.split(",")] if sectors else None
    industries_list = [i.strip() for i in industries.split(",")] if industries else None

    # Validate sort column
    if sort_by not in VALID_SORT_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by value '{sort_by}'. Valid values: {', '.join(sorted(VALID_SORT_COLUMNS))}",
        )

    try:
        result = await equity_search_service.search(
            db=db,
            query=query,
            sectors=sectors_list,
            industries=industries_list,
            min_market_cap=min_market_cap,
            max_market_cap=max_market_cap,
            min_pe_ratio=min_pe_ratio,
            max_pe_ratio=max_pe_ratio,
            period=period,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching equities: {str(e)}",
        )


@router.get("/filters", response_model=EquitySearchFiltersResponse)
async def get_filter_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EquitySearchFiltersResponse:
    """
    Get available filter options for the equity search UI.

    Returns:
    - List of available sectors
    - List of available industries
    - Predefined market cap ranges
    """
    try:
        result = await equity_search_service.get_filter_options(db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting filter options: {str(e)}",
        )
