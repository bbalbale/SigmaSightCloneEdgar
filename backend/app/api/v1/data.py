"""
Raw Data API endpoints (/data/)
Provides unprocessed data for LLM consumption
"""
import uuid
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database import get_async_session, get_db
from app.core.dependencies import get_current_user
from app.core.datetime_utils import utc_now, to_utc_iso8601, to_iso_date
from app.models.users import Portfolio
from app.models.tags_v2 import TagV2
from app.models.positions import Position
from app.models.position_tags import PositionTag
from app.models.market_data import MarketDataCache, CompanyProfile
from app.models.snapshots import PortfolioSnapshot
from app.schemas.auth import CurrentUser
from app.core.logging import get_logger
from app.services.market_data_service import MarketDataService
from app.services.portfolio_data_service import PortfolioDataService

logger = get_logger(__name__)

router = APIRouter(prefix="/data", tags=["raw-data"])


# Portfolio Raw Data Endpoints

@router.get("/portfolios")
async def get_user_portfolios(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get list of portfolios for the authenticated user.
    
    Returns:
        List of portfolios with basic information (id, name, total_value, created_at)
        
    Note: Currently each user has exactly one portfolio, but this endpoint
    returns a list for future compatibility.
    """
    async with db as session:
        # Get all portfolios for the current user with positions loaded
        stmt = select(Portfolio).where(
            Portfolio.user_id == (UUID(str(current_user.id)) if not isinstance(current_user.id, UUID) else current_user.id)
        ).options(selectinload(Portfolio.positions))
        
        result = await session.execute(stmt)
        portfolios = result.scalars().all()
        
        # Format response
        portfolio_list = []
        for portfolio in portfolios:
            # Calculate total market value (sum of all positions)
            total_market_value = 0
            if portfolio.positions:
                for position in portfolio.positions:
                    if position.last_price and position.quantity:
                        total_market_value += float(position.last_price) * float(position.quantity)

            # Get equity balance (capital account)
            equity_balance = float(portfolio.equity_balance) if portfolio.equity_balance else 0.0

            portfolio_list.append({
                "id": str(portfolio.id),
                "name": portfolio.name,
                "total_value": total_market_value + equity_balance,
                "equity_balance": equity_balance,
                "total_market_value": total_market_value,
                "created_at": to_utc_iso8601(portfolio.created_at) if portfolio.created_at else None,
                "updated_at": to_utc_iso8601(portfolio.updated_at) if portfolio.updated_at else None,
                "position_count": len(portfolio.positions) if portfolio.positions else 0
            })
        
        return portfolio_list

@router.get("/portfolio/{portfolio_id}/complete")
async def get_portfolio_complete(
    portfolio_id: UUID,
    include_holdings: bool = Query(True, description="Include position details"),
    include_position_tags: bool = Query(True, description="Include position tags"),
    include_timeseries: bool = Query(False, description="Include historical data"),
    include_attrib: bool = Query(False, description="Include attribution data"),
    as_of_date: Optional[date] = Query(None, description="Historical snapshot date"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get complete portfolio data with optional sections.
    
    API layer owns:
    - Consistent as_of timestamps across all sections
    - Deterministic ordering of positions/data
    - Full meta object population
    
    Returns raw data with proper meta object.
    """
    async with db as session:
        # Verify portfolio ownership
        stmt = select(Portfolio).where(
            and_(
                Portfolio.id == (portfolio_id if isinstance(portfolio_id, UUID) else UUID(str(portfolio_id))),
                Portfolio.user_id == (UUID(str(current_user.id)) if not isinstance(current_user.id, UUID) else current_user.id)
            )
        ).options(selectinload(Portfolio.positions))
        
        result = await session.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        # Set consistent as_of timestamp
        as_of_timestamp = utc_now()
        
        # Get positions with current market values
        positions_data = []
        total_market_value = 0
        long_count = 0
        short_count = 0
        option_count = 0
        complete_data_count = 0
        partial_data_count = 0

        # Preload position tags if requested
        position_tags_map = {}
        if include_holdings and include_position_tags:
            position_ids = [p.id for p in portfolio.positions]
            if position_ids:
                tags_stmt = (
                    select(PositionTag, TagV2)
                    .join(TagV2, PositionTag.tag_id == TagV2.id)
                    .where(PositionTag.position_id.in_(position_ids))
                    .where(TagV2.is_archived == False)
                )
                tags_result = await session.execute(tags_stmt)

                for position_tag, tag in tags_result:
                    if position_tag.position_id not in position_tags_map:
                        position_tags_map[position_tag.position_id] = []
                    position_tags_map[position_tag.position_id].append({
                        "id": str(tag.id),
                        "name": tag.name,
                        "color": tag.color
                    })

        if include_holdings:
            for position in portfolio.positions:
                # Get current price from market data cache
                cache_stmt = select(MarketDataCache).where(
                    MarketDataCache.symbol == position.symbol
                ).order_by(MarketDataCache.updated_at.desc())
                cache_result = await session.execute(cache_stmt)
                market_data = cache_result.scalars().first()

                last_price = market_data.close if market_data else position.entry_price
                market_value = float(position.quantity) * float(last_price)

                # Count position types
                if position.position_type.value.startswith("L"):
                    if position.position_type.value in ["LC", "LP"]:
                        option_count += 1
                    else:
                        long_count += 1
                elif position.position_type.value.startswith("S"):
                    if position.position_type.value in ["SC", "SP"]:
                        option_count += 1
                    else:
                        short_count += 1
                        market_value = -market_value  # Negative for shorts

                total_market_value += market_value

                # Check data completeness (simplified for now - using market data cache)
                # In a full implementation, we'd have a separate historical prices table
                has_complete_history = market_data is not None  # Simplified check
                if has_complete_history:
                    complete_data_count += 1
                else:
                    partial_data_count += 1

                position_data = {
                    "id": str(position.id),
                    "symbol": position.symbol,
                    "quantity": float(position.quantity),
                    "position_type": position.position_type.value,
                    "investment_class": position.investment_class if position.investment_class else "PUBLIC",
                    "market_value": market_value,
                    "last_price": float(last_price),
                    "has_complete_history": has_complete_history
                }

                # Add tags if requested
                if include_position_tags:
                    position_data["tags"] = position_tags_map.get(position.id, [])

                positions_data.append(position_data)
        
        # Sort positions for deterministic ordering
        positions_data.sort(key=lambda x: (x['symbol'], x['id']))

        # Build response with proper meta object
        # Use the portfolio's equity_balance which tracks the capital account
        # (starting balance + realized P&L)
        equity_balance = float(portfolio.equity_balance) if portfolio.equity_balance else 0.0
        
        # Create meta object
        meta = {
            "as_of": to_utc_iso8601(as_of_timestamp),
            "requested": {
                "portfolio_id": str(portfolio_id),
                "include_holdings": include_holdings,
                "include_timeseries": include_timeseries,
                "include_attrib": include_attrib,
                "as_of_date": str(as_of_date) if as_of_date else None
            },
            "applied": {
                "include_holdings": include_holdings,
                "include_timeseries": include_timeseries,
                "include_attrib": include_attrib,
                "as_of_date": to_utc_iso8601(as_of_timestamp)
            },
            "limits": {
                "max_positions": 2000,
                "max_days": 180,
                "max_symbols": 5 if include_timeseries else None
            },
            "rows_returned": len(positions_data) if include_holdings else 0,
            "truncated": False,
            "schema_version": "1.0"
        }
        
        response = {
            "meta": meta,
            "portfolio": {
                "id": str(portfolio.id),
                "name": portfolio.name,
                "total_value": total_market_value + equity_balance,
                "equity_balance": equity_balance,
                "position_count": len(positions_data),
                "as_of": to_utc_iso8601(as_of_timestamp)
            },
            "positions_summary": {
                "long_count": long_count,
                "short_count": short_count,
                "option_count": option_count,
                "total_market_value": total_market_value
            }
        }

        # Add holdings section if requested
        if include_holdings:
            response["holdings"] = positions_data
            
        # Add timeseries section if requested (placeholder for now)
        if include_timeseries:
            # TODO: Implement actual timeseries data retrieval
            # For now, return empty structure
            response["timeseries"] = {
                "dates": [],
                "values": [],
                "note": "Timeseries data not yet implemented"
            }
            
        # Add attribution section if requested (placeholder for now)  
        if include_attrib:
            # TODO: Implement actual attribution data retrieval
            # For now, return empty structure
            response["attribution"] = {
                "contributors": [],
                "detractors": [],
                "note": "Attribution data not yet implemented"
            }
            
        response["data_quality"] = {
            "complete_data_positions": complete_data_count,
            "partial_data_positions": partial_data_count,
            "as_of": to_utc_iso8601(as_of_timestamp)
        }
        
        return response


@router.get("/portfolio/{portfolio_id}/snapshot")
async def get_portfolio_snapshot(
    portfolio_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get latest portfolio snapshot with target price metrics, betas, and daily P&L.

    Returns portfolio-level aggregate target returns calculated by backend.
    These values are automatically updated whenever target prices are modified.

    Returns:
        - target_price_return_eoy: Expected % return to EOY targets
        - target_price_return_next_year: Expected % return for next year
        - target_price_coverage_pct: % of positions with target prices
        - Position counts and last update timestamp
        - beta_calculated_90d: Portfolio beta (90-day calculation)
        - beta_provider_1y: Portfolio beta (1-year provider data)
        - daily_pnl: Daily profit/loss
        - daily_return: Daily return percentage
    """
    async with db as session:
        # Verify portfolio ownership
        portfolio_stmt = select(Portfolio).where(
            and_(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            )
        )
        portfolio_result = await session.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        # Get latest snapshot
        snapshot_stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snapshot_result = await session.execute(snapshot_stmt)
        snapshot = snapshot_result.scalar_one_or_none()

        if not snapshot:
            # No snapshot exists yet - return zeros
            return {
                "portfolio_id": str(portfolio_id),
                "snapshot_date": None,
                "target_price_return_eoy": 0.0,
                "target_price_return_next_year": 0.0,
                "target_price_coverage_pct": 0.0,
                "target_price_positions_count": 0,
                "target_price_total_positions": 0,
                "target_price_last_updated": None,
                "beta_calculated_90d": None,
                "beta_provider_1y": None,
                "daily_pnl": None,
                "daily_return": None
            }

        return {
            "portfolio_id": str(portfolio_id),
            "snapshot_date": snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else None,
            "target_price_return_eoy": float(snapshot.target_price_return_eoy) if snapshot.target_price_return_eoy else 0.0,
            "target_price_return_next_year": float(snapshot.target_price_return_next_year) if snapshot.target_price_return_next_year else 0.0,
            "target_price_coverage_pct": float(snapshot.target_price_coverage_pct) if snapshot.target_price_coverage_pct else 0.0,
            "target_price_positions_count": snapshot.target_price_positions_count or 0,
            "target_price_total_positions": snapshot.target_price_total_positions or 0,
            "target_price_last_updated": snapshot.target_price_last_updated.isoformat() if snapshot.target_price_last_updated else None,
            # Portfolio betas for risk metrics
            "beta_calculated_90d": float(snapshot.beta_calculated_90d) if snapshot.beta_calculated_90d is not None else None,
            "beta_provider_1y": float(snapshot.beta_provider_1y) if snapshot.beta_provider_1y is not None else None,
            # Daily P&L metrics
            "daily_pnl": float(snapshot.daily_pnl) if snapshot.daily_pnl is not None else None,
            "daily_return": float(snapshot.daily_return) if snapshot.daily_return is not None else None
        }


# Note: The /portfolios/{portfolio_id}/strategies endpoint has been removed
# Use position tagging directly instead - positions now have tags attached
# See /positions/details endpoint with position tags included


@router.get("/portfolio/{portfolio_id}/data-quality")
async def get_portfolio_data_quality(
    portfolio_id: UUID,
    check_factors: bool = Query(True, description="Check factor data completeness"),
    check_correlations: bool = Query(True, description="Check correlation feasibility"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Assess data availability for portfolio calculations.
    Indicates which calculations are feasible given available data.
    """
    async with db as session:
        # Verify portfolio ownership
        stmt = select(Portfolio).where(
            and_(
                Portfolio.id == (portfolio_id if isinstance(portfolio_id, UUID) else UUID(str(portfolio_id))),
                Portfolio.user_id == (UUID(str(current_user.id)) if not isinstance(current_user.id, UUID) else current_user.id)
            )
        ).options(selectinload(Portfolio.positions))
        
        result = await session.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        # Analyze data quality for each position
        complete_history = []
        partial_history = []
        insufficient_data = []
        
        for position in portfolio.positions:
            # Check if we have market data (simplified check)
            # In production, we'd check actual historical price records
            cache_stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == position.symbol
            )
            cache_result = await session.execute(cache_stmt)
            market_data = cache_result.scalars().first()
            
            # Simulate days available based on whether we have data
            days_available = 150 if market_data else 0
            
            if days_available >= 150:  # Full history for all calculations
                complete_history.append(position.symbol)
            elif days_available >= 30:  # Partial history
                partial_history.append({
                    "symbol": position.symbol,
                    "days_available": days_available,
                    "days_missing": 150 - days_available
                })
            else:  # Insufficient data
                reason = "recent_listing" if days_available < 20 else "incomplete_data"
                insufficient_data.append({
                    "symbol": position.symbol,
                    "days_available": days_available,
                    "reason": reason
                })
        
        # Calculate feasibility
        correlation_eligible = len(complete_history) + len([p for p in partial_history if p["days_available"] >= 30])
        factor_eligible = len(complete_history) + len([p for p in partial_history if p["days_available"] >= 60])
        volatility_eligible = len(complete_history) + len([p for p in partial_history if p["days_available"] >= 20])
        
        response = {
            "portfolio_id": str(portfolio_id),
            "assessment_date": to_iso_date(date.today()),
            "summary": {
                "total_positions": len(portfolio.positions),
                "complete_data": len(complete_history),
                "partial_data": len(partial_history),
                "insufficient_data": len(insufficient_data),
                "data_coverage_percent": (len(complete_history) / len(portfolio.positions) * 100) if portfolio.positions else 0
            },
            "position_data_quality": {
                "complete_history": complete_history,
                "partial_history": partial_history,
                "insufficient_data": insufficient_data
            },
            "calculation_feasibility": {
                "correlation_matrix": {
                    "feasible": correlation_eligible >= 2,
                    "positions_eligible": correlation_eligible,
                    "positions_excluded": len(portfolio.positions) - correlation_eligible,
                    "min_days_overlap": 30
                },
                "factor_regression": {
                    "feasible": factor_eligible >= 1,
                    "positions_eligible": factor_eligible,
                    "positions_excluded": len(portfolio.positions) - factor_eligible,
                    "min_days_required": 60
                },
                "volatility_analysis": {
                    "feasible": volatility_eligible >= 1,
                    "positions_eligible": volatility_eligible,
                    "positions_excluded": len(portfolio.positions) - volatility_eligible,
                    "min_days_required": 20
                }
            }
        }
        
        if check_factors:
            # Check factor ETF data availability
            factor_etfs = ["SPY", "VTV", "VUG", "MTUM", "QUAL", "SLY", "USMV"]
            complete_factors = []
            partial_factors = []
            missing_factors = []
            
            for etf in factor_etfs:
                # Check if we have market data for the ETF
                cache_stmt = select(MarketDataCache).where(
                    MarketDataCache.symbol == etf
                )
                cache_result = await session.execute(cache_stmt)
                market_data = cache_result.scalars().first()
                count = 150 if market_data else 0
                
                if count >= 150:
                    complete_factors.append(etf)
                elif count > 0:
                    partial_factors.append(etf)
                else:
                    missing_factors.append(etf)
            
            response["factor_etf_coverage"] = {
                "complete": complete_factors,
                "partial": partial_factors,
                "missing": missing_factors
            }
        
        response["last_update"] = to_utc_iso8601(utc_now())
        
        return response


# Position Raw Data Endpoints

@router.get("/positions/details")
async def get_positions_details(
    portfolio_id: Optional[UUID] = Query(None, description="Portfolio UUID"),
    position_ids: Optional[str] = Query(None, description="Comma-separated position IDs"),
    include_closed: bool = Query(False, description="Include closed positions"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed position information including entry prices and cost basis.
    Returns raw position data without calculations.
    """
    import time
    import logging
    logger = logging.getLogger(__name__)
    
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"[{request_id}] Starting positions request for portfolio {portfolio_id}")
    
    # db is already a session from get_db dependency
    # Build query based on parameters
    if portfolio_id:
        # Verify portfolio ownership
        logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Verifying portfolio ownership")
        port_stmt = select(Portfolio).where(
            and_(
                Portfolio.id == (portfolio_id if isinstance(portfolio_id, UUID) else UUID(str(portfolio_id))),
                Portfolio.user_id == (UUID(str(current_user.id)) if not isinstance(current_user.id, UUID) else current_user.id)
            )
        )
        port_result = await db.execute(port_stmt)
        portfolio = port_result.scalar_one_or_none()
            
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        stmt = select(Position).where(Position.portfolio_id == portfolio_id)
    elif position_ids:
        # Parse position IDs
        ids = [UUID(pid.strip()) for pid in position_ids.split(",")]
        stmt = select(Position).where(Position.id.in_(ids))
    else:
        raise HTTPException(status_code=400, detail="Either portfolio_id or position_ids required")
        
    # Execute query
    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Fetching positions")
    result = await db.execute(stmt)
    positions = result.scalars().all()
    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Found {len(positions)} positions")
    
    # Batch fetch all market data at once to avoid N+1 queries
    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Batch fetching market data")
    symbols = [position.symbol for position in positions]
    
    # Use a single query to get all market data
    if symbols:
        # Subquery to get the latest market data for each symbol
        from sqlalchemy import func
        subquery = (
            select(
                MarketDataCache.symbol,
                func.max(MarketDataCache.updated_at).label('max_updated')
            )
            .where(MarketDataCache.symbol.in_(symbols))
            .group_by(MarketDataCache.symbol)
            .subquery()
        )
        
        market_stmt = select(MarketDataCache).join(
            subquery,
            and_(
                MarketDataCache.symbol == subquery.c.symbol,
                MarketDataCache.updated_at == subquery.c.max_updated
            )
        )
        market_result = await db.execute(market_stmt)
        market_data_map = {m.symbol: m for m in market_result.scalars().all()}
    else:
        market_data_map = {}
    
    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Market data fetched for {len(market_data_map)} symbols")

    # Batch fetch company profiles (name, sector, industry)
    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Batch fetching company profiles")
    if symbols:
        profiles_stmt = select(
            CompanyProfile.symbol,
            CompanyProfile.company_name,
            CompanyProfile.sector,
            CompanyProfile.industry
        ).where(CompanyProfile.symbol.in_(symbols))
        profiles_result = await db.execute(profiles_stmt)
        company_profiles_map = {
            row[0]: {
                "company_name": row[1],
                "sector": row[2],
                "industry": row[3]
            }
            for row in profiles_result.all()
        }
    else:
        company_profiles_map = {}

    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Company profiles fetched for {len(company_profiles_map)} symbols")

    # Batch fetch all position tags to avoid N+1 queries
    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Batch fetching position tags")
    from app.models.position_tags import PositionTag
    from app.models.tags_v2 import TagV2

    position_ids = [p.id for p in positions]
    if position_ids:
        tags_stmt = (
            select(PositionTag, TagV2)
            .join(TagV2, PositionTag.tag_id == TagV2.id)
            .where(PositionTag.position_id.in_(position_ids))
            .where(TagV2.is_archived == False)
        )
        tags_result = await db.execute(tags_stmt)

        # Build a map of position_id -> list of tags
        position_tags_map = {}
        for position_tag, tag in tags_result:
            if position_tag.position_id not in position_tags_map:
                position_tags_map[position_tag.position_id] = []
            position_tags_map[position_tag.position_id].append({
                "id": str(tag.id),
                "name": tag.name,
                "color": tag.color,
                "description": tag.description
            })
    else:
        position_tags_map = {}

    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Tags fetched for {len(position_tags_map)} positions")

    # Build response
    positions_data = []
    total_cost_basis = 0
    total_market_value = 0
    total_unrealized_pnl = 0

    for position in positions:
        # Get current price from pre-fetched map
        market_data = market_data_map.get(position.symbol)
            
        current_price = market_data.close if market_data else position.entry_price
        cost_basis = float(position.quantity) * float(position.entry_price)
        market_value = float(position.quantity) * float(current_price)
            
        # Adjust for shorts
        if position.position_type.value == "SHORT":
            market_value = -market_value
            unrealized_pnl = cost_basis - abs(market_value)  # Profit when price goes down
        else:
            unrealized_pnl = market_value - cost_basis
            
        unrealized_pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0
        
        total_cost_basis += abs(cost_basis)
        total_market_value += market_value
        total_unrealized_pnl += unrealized_pnl

        # Get company profile data from pre-fetched map
        company_profile = company_profiles_map.get(position.symbol, {})
        company_name = company_profile.get("company_name")
        sector = company_profile.get("sector")
        industry = company_profile.get("industry")

        positions_data.append({
            "id": str(position.id),
            "portfolio_id": str(position.portfolio_id),
            "symbol": position.symbol,
            "company_name": company_name,
            "sector": sector,  # NEW: Sector classification
            "industry": industry,  # NEW: Industry classification
            "position_type": position.position_type.value,
            "investment_class": position.investment_class if position.investment_class else "PUBLIC",  # Default to PUBLIC if not set
            "investment_subtype": position.investment_subtype if position.investment_subtype else None,
            "quantity": float(position.quantity),
            "entry_date": to_iso_date(position.entry_date) if position.entry_date else None,
            "entry_price": float(position.entry_price),
            "cost_basis": cost_basis,
            "current_price": float(current_price),
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_percent": unrealized_pnl_percent,
            # Add option-specific fields if available
            "strike_price": float(position.strike_price) if position.strike_price else None,
            "expiration_date": to_iso_date(position.expiration_date) if position.expiration_date else None,
            "underlying_symbol": position.underlying_symbol if position.underlying_symbol else None,
            "tags": position_tags_map.get(position.id, [])  # Position tags from new position tagging system
        })
    
    logger.info(f"[{request_id}] [{time.time() - start_time:.2f}s] Request complete, returning {len(positions_data)} positions")
        
    return {
        "positions": positions_data,
        "summary": {
            "total_positions": len(positions_data),
            "total_cost_basis": total_cost_basis,
            "total_market_value": total_market_value,
            "total_unrealized_pnl": total_unrealized_pnl
        }
    }


@router.post("/positions/restore-sector-tags")
async def restore_sector_tags(
    portfolio_id: UUID = Query(..., description="Portfolio UUID to restore tags for"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore sector tags for all positions in a portfolio.

    This endpoint:
    1. Fetches company profile data for all positions
    2. Creates sector tags (if they don't exist) based on company sector
    3. Removes existing sector tags and re-applies them
    4. Returns statistics about the operation

    Use cases:
    - User accidentally deleted sector tags
    - Initial setup of sector tags for existing portfolio
    - Refresh sector tags after company profile updates
    """
    from app.services.sector_tag_service import restore_sector_tags_for_portfolio

    # Verify portfolio ownership
    port_stmt = select(Portfolio).where(
        and_(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == (UUID(str(current_user.id)) if not isinstance(current_user.id, UUID) else current_user.id)
        )
    )
    port_result = await db.execute(port_stmt)
    portfolio = port_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Execute the restoration
    try:
        result = await restore_sector_tags_for_portfolio(
            db=db,
            portfolio_id=portfolio_id,
            user_id=current_user.id if isinstance(current_user.id, UUID) else UUID(str(current_user.id))
        )

        logger.info(
            f"Sector tags restored for portfolio {portfolio_id} by user {current_user.id}: "
            f"{result['positions_tagged']} positions tagged"
        )

        return {
            "success": True,
            "portfolio_id": str(portfolio_id),
            "portfolio_name": portfolio.name,
            **result
        }

    except Exception as e:
        logger.error(f"Error restoring sector tags for portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restore sector tags: {str(e)}"
        )


# Price Data Endpoints

@router.get("/prices/historical/{portfolio_id}")
async def get_historical_prices(
    portfolio_id: UUID,
    lookback_days: int = Query(150, description="Number of trading days"),
    include_factor_etfs: bool = Query(True, description="Include factor ETF prices"),
    date_format: str = Query("iso", description="Date format (iso|unix)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get historical price data for all portfolio positions.
    Returns daily OHLCV data with aligned dates.
    """
    async with db as session:
        # Verify portfolio ownership
        stmt = select(Portfolio).where(
            and_(
                Portfolio.id == (portfolio_id if isinstance(portfolio_id, UUID) else UUID(str(portfolio_id))),
                Portfolio.user_id == (UUID(str(current_user.id)) if not isinstance(current_user.id, UUID) else current_user.id)
            )
        ).options(selectinload(Portfolio.positions))
        
        result = await session.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        # Get unique symbols from portfolio
        symbols = list(set([pos.symbol for pos in portfolio.positions]))
        
        # Add factor ETFs if requested
        if include_factor_etfs:
            factor_etfs = ["SPY", "VTV", "VUG", "MTUM", "QUAL", "SLY", "USMV"]
            symbols.extend([etf for etf in factor_etfs if etf not in symbols])
        
        # Get historical prices for all symbols
        # Note: This is a simplified implementation using market data cache
        # In production, we'd have a proper historical prices table
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)
        
        symbols_data = {}
        
        for symbol in symbols:
            # Get real historical data from MarketDataCache
            cache_stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)
            
            cache_result = await session.execute(cache_stmt)
            market_data_rows = cache_result.scalars().all()
            
            if market_data_rows:
                # Build arrays from real historical data
                dates = []
                opens = []
                highs = []
                lows = []
                closes = []
                volumes = []
                
                for row in market_data_rows:
                    dates.append(to_iso_date(row.date) if date_format == "iso" else int(row.date.timestamp()))
                    
                    # Use real OHLCV data
                    close_price = float(row.close)
                    opens.append(float(row.open) if row.open else close_price)
                    highs.append(float(row.high) if row.high else close_price)
                    lows.append(float(row.low) if row.low else close_price)
                    closes.append(close_price)
                    volumes.append(int(row.volume) if row.volume else 0)
                
                if closes:
                    symbols_data[symbol] = {
                        "dates": dates,
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes,
                        "adjusted_close": closes,  # We don't have adjusted close, using regular close
                        "data_points": len(closes),
                        "source": "market_data_cache"
                    }
        
        # Build response
        trading_days = len(next(iter(symbols_data.values()))["dates"]) if symbols_data else 0
        
        return {
            "metadata": {
                "lookback_days": lookback_days,
                "start_date": to_iso_date(start_date),
                "end_date": to_iso_date(end_date),
                "trading_days_included": trading_days
            },
            "symbols": symbols_data
        }


@router.get("/prices/quotes")
async def get_market_quotes(
    symbols: str = Query(..., description="Comma-separated list of ticker symbols"),
    include_options: bool = Query(False, description="Include options chains (future)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get current market quotes for specified symbols.
    Returns real-time prices for position value updates.
    Added in v1.4.4 to support frontend requirements.
    """
    # Parse symbols
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    async with db as session:
        # Get quotes from market data cache
        quotes_data = []
        
        for symbol in symbol_list:
            # Get from cache first
            cache_stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol
            ).order_by(MarketDataCache.updated_at.desc())
            
            cache_result = await session.execute(cache_stmt)
            market_data = cache_result.scalars().first()
            
            if market_data:
                # Use available fields from MarketDataCache
                quotes_data.append({
                    "symbol": symbol,
                    "last_price": float(market_data.close),
                    "bid": float(market_data.close) - 0.01,  # Simulated bid
                    "ask": float(market_data.close) + 0.01,  # Simulated ask
                    "bid_size": 100,  # Default
                    "ask_size": 100,  # Default
                    "volume": int(market_data.volume) if market_data.volume else 0,
                    "day_change": 0,  # No previous close available in this model
                    "day_change_percent": 0,
                    "day_high": float(market_data.high) if market_data.high else float(market_data.close),
                    "day_low": float(market_data.low) if market_data.low else float(market_data.close),
                    "timestamp": to_utc_iso8601(market_data.updated_at)
                })
            else:
                # Try to fetch fresh data if not in cache
                service = MarketDataService()
                try:
                    price = await service.get_current_price(symbol)
                    if price:
                        quotes_data.append({
                            "symbol": symbol,
                            "last_price": float(price),
                            "bid": float(price) - 0.01,
                            "ask": float(price) + 0.01,
                            "bid_size": 100,
                            "ask_size": 100,
                            "volume": 0,
                            "day_change": 0,
                            "day_change_percent": 0,
                            "day_high": float(price),
                            "day_low": float(price),
                            "timestamp": to_utc_iso8601(utc_now())
                        })
                except Exception as e:
                    logger.warning(f"Failed to fetch quote for {symbol}: {e}")
        
        # Return structure matching API spec
        return {
            "quotes": quotes_data,
            "metadata": {
                "requested_symbols": symbol_list,
                "successful_quotes": len(quotes_data),
                "failed_quotes": len(symbol_list) - len(quotes_data),
                "timestamp": to_utc_iso8601(utc_now())
            }
        }


# Factor Data Endpoints

@router.get("/factors/etf-prices")
async def get_factor_etf_prices(
    lookback_days: int = Query(150, description="Number of trading days"),
    factors: Optional[str] = Query(None, description="Comma-separated factor names to filter"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get historical prices for factor ETFs used in the 7-factor risk model.
    Returns prices and returns for factor regression calculations.
    """
    # Define factor ETF mappings
    factor_etf_map = {
        "Market Beta": "SPY",
        "Value": "VTV",
        "Growth": "VUG",
        "Momentum": "MTUM",
        "Quality": "QUAL",
        "Size": "SLY",
        "Low Volatility": "USMV"
    }
    
    # Filter factors if specified
    if factors:
        factor_list = [f.strip() for f in factors.split(",")]
        factor_etf_map = {k: v for k, v in factor_etf_map.items() if k in factor_list}
    
    async with db as session:
        from datetime import timedelta
        
        # Get real ETF data from database
        factors_data = {}
        
        for factor_name, etf_symbol in factor_etf_map.items():
            # Get the most recent market data for this ETF
            cache_stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == etf_symbol
            ).order_by(MarketDataCache.updated_at.desc()).limit(1)
            
            cache_result = await session.execute(cache_stmt)
            market_data = cache_result.scalar_one_or_none()
            
            if market_data:
                # Return real market data
                factors_data[etf_symbol] = {
                    "factor_name": factor_name,
                    "symbol": etf_symbol,
                    "current_price": float(market_data.close),
                    "open": float(market_data.open) if market_data.open else float(market_data.close),
                    "high": float(market_data.high) if market_data.high else float(market_data.close),
                    "low": float(market_data.low) if market_data.low else float(market_data.close),
                    "volume": int(market_data.volume) if market_data.volume else 0,
                    "date": to_iso_date(market_data.date) if market_data.date else None,
                    "updated_at": to_utc_iso8601(market_data.updated_at),
                    "data_source": market_data.data_source,
                    "exchange": market_data.exchange,
                    "market_cap": float(market_data.market_cap) if market_data.market_cap else None
                }
        
        return {
            "metadata": {
                "factor_model": "7-factor",
                "etf_count": len(factors_data),
                "timestamp": to_utc_iso8601(utc_now())
            },
            "data": factors_data
        }


@router.get("/test-demo")
async def test_demo():
    """Simple test endpoint"""
    return {"message": "Demo endpoint works!"}


@router.get("/positions/top/{portfolio_id}")
async def get_top_positions(
    portfolio_id: UUID,
    limit: int = Query(20, le=50, description="Max positions to return"),
    sort_by: str = Query("market_value", regex="^(market_value|weight)$"),
    as_of_date: Optional[str] = Query(None, description="ISO date, max 180d lookback"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get top N positions sorted by market value or weight.
    
    API layer owns:
    - Sorting by market value/weight
    - Computing portfolio coverage percentage
    - Applying limit caps (limit<=50, as_of_date<=180d lookback)
    - Response shape: {symbol, name, qty, value, weight, sector} only
    - Rounding weight to 4 decimal places
    - Full meta object population
    
    Returns positions with coverage % and truncation metadata.
    """
    async with db as session:
        # Verify portfolio ownership
        portfolio_stmt = select(Portfolio).where(
            and_(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            )
        )
        portfolio_result = await session.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        # Use service layer to get top positions
        service = PortfolioDataService()
        try:
            result = await service.get_top_positions(
                session,
                portfolio_id,
                limit=limit,
                sort_by=sort_by,
                as_of_date=as_of_date
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting top positions: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


# Demo Portfolio Bridge Endpoint
# Note: This endpoint doesn't require authentication for testing
@router.get("/demo/{portfolio_type}", tags=["raw-data"])
async def get_demo_portfolio(portfolio_type: str):
    """
    Get demo portfolio data from report files.
    Currently only supports 'high-net-worth' portfolio.
    """
    import json
    import csv
    from pathlib import Path
    
    # For now, only support high-net-worth
    if portfolio_type != 'high-net-worth':
        raise HTTPException(
            status_code=404, 
            detail=f"Portfolio type '{portfolio_type}' not implemented. Only 'high-net-worth' is currently supported."
        )
    
    # Map portfolio type to folder name
    folder_map = {
        'high-net-worth': 'demo-high-net-worth-portfolio_2025-08-23'
    }
    
    folder_name = folder_map.get(portfolio_type)
    if not folder_name:
        raise HTTPException(status_code=404, detail="Portfolio type not found")
    
    # Construct path to reports folder
    current_file = Path(__file__)
    backend_dir = current_file.parent.parent.parent.parent  # Up to backend/
    reports_dir = backend_dir / "reports" / folder_name
    
    # Debug logging
    logger.info(f"Looking for reports in: {reports_dir}")
    logger.info(f"Directory exists: {reports_dir.exists()}")
    
    if not reports_dir.exists():
        raise HTTPException(
            status_code=500, 
            detail=f"Report directory not found: {reports_dir}"
        )
    
    # Read JSON file
    json_path = reports_dir / "portfolio_report.json"
    if not json_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"JSON report file not found: {json_path}"
        )
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read JSON file: {str(e)}"
        )
    
    # Read CSV file
    csv_path = reports_dir / "portfolio_report.csv"
    if not csv_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"CSV report file not found: {csv_path}"
        )
    
    positions = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            positions = list(reader)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read CSV file: {str(e)}"
        )
    
    # Extract relevant data
    portfolio_info = json_data.get("portfolio_info", {})
    position_exposures = json_data.get("calculation_engines", {}).get("position_exposures", {}).get("data", {})
    portfolio_snapshot = json_data.get("calculation_engines", {}).get("portfolio_snapshot", {}).get("data", {})
    
    return {
        "portfolio_type": portfolio_type,
        "portfolio_info": portfolio_info,
        "exposures": position_exposures,
        "snapshot": portfolio_snapshot,
        "positions": positions,
        "metadata": {
            "source": "report_files",
            "report_date": json_data.get("metadata", {}).get("report_date", ""),
            "position_count": len(positions)
        }
    }


@router.get("/company-profiles")
async def get_company_profiles(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols (e.g., 'AAPL,MSFT,GOOGL')"),
    position_ids: Optional[str] = Query(None, description="Comma-separated position IDs"),
    portfolio_id: Optional[UUID] = Query(None, description="Get profiles for all portfolio symbols"),
    fields: Optional[str] = Query(None, description="Comma-separated fields to include (default: all)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get company profiles. Exactly ONE of: symbols, position_ids, or portfolio_id required.

    Query Modes:
    - symbols: Direct symbol lookup (no ownership check - public data)
    - position_ids: Fetch profiles for specific positions (ownership required)
    - portfolio_id: Fetch profiles for all portfolio symbols (ownership required)

    Optional field filtering for performance optimization.
    """
    from uuid import UUID as UUID_TYPE

    # Parameter validation: Exactly one parameter must be provided
    params_provided = sum([
        symbols is not None,
        position_ids is not None,
        portfolio_id is not None
    ])

    if params_provided == 0:
        raise HTTPException(400, "One of symbols, position_ids, or portfolio_id required")
    if params_provided > 1:
        raise HTTPException(400, "Only one of symbols, position_ids, or portfolio_id allowed")

    # Resolve parameters to symbol list
    symbol_list = []
    query_type = ""
    position_symbol_map = None
    portfolio_id_str = None

    if position_ids:
        # Parse position IDs and fetch positions
        try:
            position_uuid_list = [UUID_TYPE(pid.strip()) for pid in position_ids.split(",")]
        except ValueError:
            raise HTTPException(400, "Invalid position ID format")

        # Fetch positions and verify ownership
        stmt = select(Position).where(Position.id.in_(position_uuid_list))
        result = await db.execute(stmt)
        positions = result.scalars().all()

        if not positions:
            raise HTTPException(404, "No positions found")

        # Verify all positions belong to user's portfolios
        portfolio_ids = {p.portfolio_id for p in positions}
        portfolio_stmt = select(Portfolio).where(
            and_(
                Portfolio.id.in_(portfolio_ids),
                Portfolio.user_id == (UUID_TYPE(str(current_user.id)) if not isinstance(current_user.id, UUID_TYPE) else current_user.id)
            )
        )
        portfolio_result = await db.execute(portfolio_stmt)
        user_portfolios = {p.id for p in portfolio_result.scalars().all()}

        unauthorized_positions = [p for p in positions if p.portfolio_id not in user_portfolios]
        if unauthorized_positions:
            raise HTTPException(403, f"Unauthorized access to positions")

        # Extract symbols and build map
        symbol_list = [p.symbol for p in positions]
        position_symbol_map = {str(p.id): p.symbol for p in positions}
        query_type = "positions"

    elif portfolio_id:
        # Fetch portfolio and verify ownership
        portfolio_uuid = portfolio_id if isinstance(portfolio_id, UUID_TYPE) else UUID_TYPE(str(portfolio_id))
        stmt = select(Portfolio).where(
            and_(
                Portfolio.id == portfolio_uuid,
                Portfolio.user_id == (UUID_TYPE(str(current_user.id)) if not isinstance(current_user.id, UUID_TYPE) else current_user.id)
            )
        ).options(selectinload(Portfolio.positions))

        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(404, "Portfolio not found")

        # Extract symbols
        symbol_list = [p.symbol for p in portfolio.positions]
        portfolio_id_str = str(portfolio_id)
        query_type = "portfolio"

    else:  # symbols
        # Parse comma-separated symbols (no ownership check - public data)
        symbol_list = [s.strip() for s in symbols.split(",")]
        query_type = "symbols"

    # Build database query with optional field filtering
    if fields:
        # Validate and build column list
        requested_fields = [f.strip() for f in fields.split(",")]

        # Get valid CompanyProfile columns
        valid_columns = [col.name for col in CompanyProfile.__table__.columns]
        invalid_fields = [f for f in requested_fields if f not in valid_columns]

        if invalid_fields:
            raise HTTPException(400, f"Invalid field names: {', '.join(invalid_fields)}")

        # Build SELECT with specific columns (always include symbol)
        if 'symbol' not in requested_fields:
            requested_fields.insert(0, 'symbol')

        columns = [getattr(CompanyProfile, field) for field in requested_fields]
        stmt = select(*columns).where(CompanyProfile.symbol.in_(symbol_list))

        # Execute and convert to dicts using mappings()
        result = await db.execute(stmt)
        profiles = [dict(row) for row in result.mappings()]

        fields_requested = requested_fields
    else:
        # Full model select
        stmt = select(CompanyProfile).where(CompanyProfile.symbol.in_(symbol_list))
        result = await db.execute(stmt)
        profile_models = result.scalars().all()

        # Convert models to dicts
        profiles = []
        for profile in profile_models:
            profile_dict = {
                col.name: getattr(profile, col.name)
                for col in CompanyProfile.__table__.columns
            }
            profiles.append(profile_dict)

        fields_requested = None

    # Build metadata
    returned_symbols = {p['symbol'] for p in profiles}
    missing_symbols = [s for s in symbol_list if s not in returned_symbols]

    meta = {
        "query_type": query_type,
        "requested_symbols": symbol_list,
        "returned_profiles": len(profiles),
        "missing_profiles": missing_symbols,
        "as_of": to_utc_iso8601(utc_now())
    }

    # Add conditional metadata fields
    if position_symbol_map:
        meta["position_ids"] = list(position_symbol_map.keys())
        meta["position_symbol_map"] = position_symbol_map

    if portfolio_id_str:
        meta["portfolio_id"] = portfolio_id_str

    if fields_requested:
        meta["fields_requested"] = fields_requested

    return {
        "profiles": profiles,
        "meta": meta
    }
