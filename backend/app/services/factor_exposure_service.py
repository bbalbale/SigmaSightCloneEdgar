"""
Factor exposure retrieval service (read-only)

Provides portfolio-level and position-level factor exposures from
precomputed batch outputs stored in the database.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    FactorDefinition,
    FactorExposure,
    PositionFactorExposure,
    Position,
)

import logging

logger = logging.getLogger(__name__)


class FactorExposureService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_portfolio_exposures(self, portfolio_id: UUID) -> Dict:
        """
        Return the latest set of portfolio-level factor exposures.
        Accepts any available factors - doesn't require all active factors.
        Minimum requirement: at least one factor (preferably Market Beta).
        """
        # Get active style factors
        target_factors_stmt = (
            select(FactorDefinition.id, FactorDefinition.name, FactorDefinition.calculation_method)
            .where(and_(FactorDefinition.is_active.is_(True), FactorDefinition.factor_type == 'style'))
            .order_by(FactorDefinition.display_order.asc(), FactorDefinition.name.asc())
        )
        tf_res = await self.db.execute(target_factors_stmt)
        target_rows = tf_res.all()
        target_factor_ids = [row[0] for row in target_rows]
        target_count = len(target_factor_ids)

        if target_count == 0:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "factors": [],
                "metadata": {"reason": "no_calculation_available", "detail": "no_active_style_factors"},
            }

        # Find the latest date with ANY factor calculations (not requiring all)
        latest_date_stmt = (
            select(func.max(FactorExposure.calculation_date))
            .where(and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.factor_id.in_(target_factor_ids)
            ))
        )
        latest_date_res = await self.db.execute(latest_date_stmt)
        latest_date = latest_date_res.scalar_one_or_none()

        if latest_date is None:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "factors": [],
                "metadata": {"reason": "no_calculation_available", "detail": "no_factor_calculations"},
            }

        # Load ANY available factors for the latest date (flexible approach)
        stmt = (
            select(FactorExposure, FactorDefinition)
            .join(FactorDefinition, FactorExposure.factor_id == FactorDefinition.id)
            .where(
                and_(
                    FactorExposure.portfolio_id == portfolio_id,
                    FactorExposure.calculation_date == latest_date,
                    FactorExposure.factor_id.in_(target_factor_ids),
                )
            )
        )
        result = await self.db.execute(stmt)
        rows: List[Tuple[FactorExposure, FactorDefinition]] = list(result.all())

        if not rows:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "factors": [],
                "metadata": {"reason": "no_calculation_available"},
            }

        factors = []
        available_factor_names = []
        for exposure, definition in rows:
            factors.append(
                {
                    "name": definition.name,
                    "beta": float(exposure.exposure_value),
                    "exposure_dollar": float(exposure.exposure_dollar) if exposure.exposure_dollar is not None else None,
                }
            )
            available_factor_names.append(definition.name)

        # Order by FactorDefinition display_order then name
        order_map = {row[0]: idx for idx, row in enumerate(target_rows)}
        def _order_key(item: Dict):
            # find index by matching name from target_rows sequence
            for i, row in enumerate(target_rows):
                if row[1] == item["name"]:
                    return i
            return 999
        factors.sort(key=_order_key)

        # Derive metadata with information about partial vs complete
        factor_model = f"{len(factors)}-factor" if factors else None
        calc_methods = {getattr(defn, "calculation_method", None) for _, defn in rows}
        calc_method = next((m for m in calc_methods if m), None) or "ETF-proxy regression"
        
        # Check if we have Market Beta (minimum requirement)
        has_market_beta = "Market Beta" in available_factor_names
        # We now have 7 active factors (Short Interest is inactive)
        expected_factors = 7  # All active factors except Short Interest
        completeness = "partial" if len(factors) < expected_factors else "complete"

        return {
            "available": True,
            "portfolio_id": str(portfolio_id),
            "calculation_date": latest_date.isoformat(),
            "factors": factors,
            "metadata": {
                "factor_model": factor_model,
                "calculation_method": calc_method,
                "completeness": completeness,
                "total_active_factors": expected_factors,
                "factors_calculated": len(factors),
                "has_market_beta": has_market_beta,
            },
        }

    async def list_position_exposures(
        self,
        portfolio_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        symbols: Optional[List[str]] = None,
    ) -> Dict:
        """
        Return paginated position-level factor exposures for the latest
        calculation date available for this portfolio.
        Pagination is applied at the position level.
        """
        # Identify positions for this portfolio (optionally filtered by symbols)
        pos_stmt = select(Position.id, Position.symbol).where(Position.portfolio_id == portfolio_id)
        if symbols:
            pos_stmt = pos_stmt.where(Position.symbol.in_(symbols))
        pos_result = await self.db.execute(pos_stmt)
        all_positions = [(row[0], row[1]) for row in pos_result.all()]

        if not all_positions:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "total": 0,
                "limit": limit,
                "offset": offset,
                "positions": [],
                "metadata": {"reason": "no_calculation_available"},
            }

        pos_ids = [pid for pid, _ in all_positions]

        # Determine anchor calculation date (latest across any of these positions)
        date_stmt = (
            select(func.max(PositionFactorExposure.calculation_date))
            .where(PositionFactorExposure.position_id.in_(pos_ids))
        )
        date_result = await self.db.execute(date_stmt)
        anchor_date = date_result.scalar_one_or_none()

        if anchor_date is None:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "total": 0,
                "limit": limit,
                "offset": offset,
                "positions": [],
                "metadata": {"reason": "no_calculation_available"},
            }

        # Total distinct positions with exposures on anchor date
        total_stmt = (
            select(func.count(func.distinct(PositionFactorExposure.position_id)))
            .where(
                and_(
                    PositionFactorExposure.position_id.in_(pos_ids),
                    PositionFactorExposure.calculation_date == anchor_date,
                )
            )
        )
        total_result = await self.db.execute(total_stmt)
        total = int(total_result.scalar_one() or 0)

        if total == 0:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": anchor_date.isoformat(),
                "total": 0,
                "limit": limit,
                "offset": offset,
                "positions": [],
                "metadata": {"reason": "no_calculation_available"},
            }

        # Get page of position ids (stable order by symbol then id)
        page_pos_stmt = (
            select(Position.id, Position.symbol)
            .where(Position.id.in_(pos_ids))
            .order_by(Position.symbol.asc(), Position.id.asc())
            .offset(offset)
            .limit(limit)
        )
        page_result = await self.db.execute(page_pos_stmt)
        page_positions: List[Tuple[UUID, str]] = [(row[0], row[1]) for row in page_result.all()]
        page_pos_ids = [pid for pid, _ in page_positions]

        if not page_pos_ids:
            return {
                "available": True,
                "portfolio_id": str(portfolio_id),
                "calculation_date": anchor_date.isoformat(),
                "total": total,
                "limit": limit,
                "offset": offset,
                "positions": [],
            }

        # Determine target style factors (same selection as portfolio-level)
        target_factors_stmt = (
            select(FactorDefinition.id, FactorDefinition.name, FactorDefinition.calculation_method)
            .where(and_(FactorDefinition.is_active.is_(True), FactorDefinition.factor_type == 'style'))
            .order_by(FactorDefinition.display_order.asc(), FactorDefinition.name.asc())
        )
        tf_res2 = await self.db.execute(target_factors_stmt)
        target_rows2 = tf_res2.all()
        target_ids2 = [row[0] for row in target_rows2]

        # Load exposures for those positions on anchor date and join factor names (style set only)
        exp_stmt = (
            select(PositionFactorExposure, FactorDefinition)
            .join(FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id)
            .where(
                and_(
                    PositionFactorExposure.position_id.in_(page_pos_ids),
                    PositionFactorExposure.calculation_date == anchor_date,
                    PositionFactorExposure.factor_id.in_(target_ids2),
                )
            )
        )
        exp_result = await self.db.execute(exp_stmt)
        rows = exp_result.all()

        # Group exposures by position
        exposures_by_pos: Dict[UUID, Dict[str, float]] = {}
        for exp, fdef in rows:
            exposures_by_pos.setdefault(exp.position_id, {})[fdef.name] = float(exp.exposure_value)

        positions_payload = []
        symbol_by_pos = {pid: sym for pid, sym in page_positions}
        for pid in page_pos_ids:
            positions_payload.append(
                {
                    "position_id": str(pid),
                    "symbol": symbol_by_pos.get(pid, ""),
                    "exposures": exposures_by_pos.get(pid, {}),
                }
            )

        return {
            "available": True,
            "portfolio_id": str(portfolio_id),
            "calculation_date": anchor_date.isoformat(),
            "total": total,
            "limit": limit,
            "offset": offset,
            "positions": positions_payload,
        }
