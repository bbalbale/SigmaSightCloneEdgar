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

from app.core.logging import get_logger

logger = get_logger(__name__)


class FactorExposureService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_portfolio_exposures(self, portfolio_id: UUID) -> Dict:
        """
        Return the latest set of portfolio-level factor exposures.
        Accepts any available factors - doesn't require all active factors.
        Minimum requirement: at least one factor (preferably Market Beta).

        Phase 8.1 Task 13: Returns data_quality metrics when available=False
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
            # Compute data_quality when no active factors (configuration issue)
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_ACTIVE_FACTORS",
                message="No active style factors defined in system configuration",
                positions_analyzed=0,
                data_days=0
            )
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "data_quality": data_quality,
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
            # Compute data_quality when no calculations exist
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_FACTOR_CALCULATIONS",
                message="No factor calculations available for this portfolio",
                positions_analyzed=0,
                data_days=0
            )
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "data_quality": data_quality,
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
            # Compute data_quality when calculation exists but returned no factors
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_FACTOR_CALCULATIONS",
                message="Factor calculation exists but no factors were computed (likely all PRIVATE positions)",
                positions_analyzed=0,
                data_days=0
            )
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "data_quality": data_quality,
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

        # Fetch portfolio snapshot using latest available pattern
        from app.db.snapshot_helpers import get_latest_portfolio_snapshot
        from app.services.snapshot_refresh_service import check_and_trigger_refresh_if_needed

        # Get latest snapshot with staleness metadata
        snapshot, snapshot_metadata = await get_latest_portfolio_snapshot(self.db, portfolio_id)

        # DISABLED: On-demand recalculation causes 30-60s API timeouts
        # Ridge factor calculations are too expensive to run synchronously during API requests
        # Rely on batch processing instead - runs asynchronously and doesn't block API responses
        # See: snapshot_refresh_service.py for the expensive calculation logic
        # refresh_check = await check_and_trigger_refresh_if_needed(self.db, portfolio_id)

        logger.info(f"[SNAPSHOT] Snapshot found: {snapshot is not None}")
        if snapshot_metadata.get('is_stale'):
            logger.warning(
                f"WARNING: Serving stale snapshot for portfolio {portfolio_id}: "
                f"{snapshot_metadata.get('age_hours')} hours old"
            )

        # Store staleness metadata for response
        staleness_info = {
            'snapshot_date': snapshot_metadata.get('snapshot_date'),
            'age_hours': snapshot_metadata.get('age_hours'),
            'is_stale': snapshot_metadata.get('is_stale', False),
            'is_current': snapshot_metadata.get('is_current', False)
        }

        if snapshot:
            logger.info(f"[SNAPSHOT DATA] equity: {snapshot.equity_balance}, calc_beta: {snapshot.beta_calculated_90d}, provider_beta: {snapshot.beta_provider_1y}")
            equity_balance = float(snapshot.equity_balance) if snapshot.equity_balance else 0.0

            # Add Calculated Beta (90d OLS) if available
            if snapshot.beta_calculated_90d is not None:
                calculated_beta = float(snapshot.beta_calculated_90d)
                logger.info(f"[BETA] Adding Calculated Beta: {calculated_beta}")
                factors.append({
                    "name": "Market Beta (Calculated 90d)",
                    "beta": calculated_beta,
                    "exposure_dollar": calculated_beta * equity_balance if equity_balance > 0 else None
                })

            # Add Provider Beta (1y from company profiles) if available
            if snapshot.beta_provider_1y is not None:
                provider_beta = float(snapshot.beta_provider_1y)
                logger.info(f"[BETA] Adding Provider Beta: {provider_beta}")
                factors.append({
                    "name": "Market Beta (Provider 1y)",
                    "beta": provider_beta,
                    "exposure_dollar": provider_beta * equity_balance if equity_balance > 0 else None
                })

        logger.info(f"[COMPLETE] Total factors after adding snapshot betas: {len(factors)}")

        # Derive metadata with information about partial vs complete
        factor_model = f"{len(factors)}-factor" if factors else None
        calc_methods = {getattr(definition, "calculation_method", None) for _, definition in rows}
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
            "data_quality": staleness_info,  # Staleness metadata for latest-available pattern
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
            # Compute data_quality when no positions found
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_POSITIONS",
                message="No positions found in portfolio",
                positions_analyzed=0,
                data_days=0
            )
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "data_quality": data_quality,
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
            # Compute data_quality when no calculations exist
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_FACTOR_CALCULATIONS",
                message="No position factor calculations available",
                positions_analyzed=0,
                data_days=0
            )
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": None,
                "data_quality": data_quality,
                "total": 0,
                "limit": limit,
                "offset": offset,
                "positions": [],
                "metadata": {"reason": "no_calculation_available"},
            }

        # Check staleness and trigger refresh if needed
        from app.db.snapshot_helpers import calculate_data_age
        from app.services.snapshot_refresh_service import check_and_trigger_refresh_if_needed

        age_metrics = calculate_data_age(anchor_date)

        # Log staleness warning
        if age_metrics['is_stale']:
            logger.warning(
                f"WARNING: Serving stale position exposures for portfolio {portfolio_id}: "
                f"{age_metrics['age_hours']} hours old (from {anchor_date})"
            )

        # Trigger refresh if needed (auto-trigger with rate limiting)
        refresh_check = await check_and_trigger_refresh_if_needed(self.db, portfolio_id)

        # Store staleness metadata for response
        staleness_info = {
            'calculation_date': anchor_date,
            'age_hours': age_metrics['age_hours'],
            'is_stale': age_metrics['is_stale'],
            'is_current': age_metrics['is_current'],
            'should_recalculate': age_metrics.get('should_recalculate', False)
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
            # Compute data_quality when calculations exist but no positions match
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_FACTOR_CALCULATIONS",
                message="Factor calculations exist but no positions have exposures (likely all PRIVATE positions)",
                positions_analyzed=0,
                data_days=0
            )
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "calculation_date": anchor_date.isoformat(),
                "data_quality": data_quality,
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
            "data_quality": staleness_info,  # Latest-available pattern with staleness metadata
            "total": total,
            "limit": limit,
            "offset": offset,
            "positions": positions_payload,
        }

    async def _compute_data_quality(
        self,
        portfolio_id: UUID,
        flag: str,
        message: str,
        positions_analyzed: int,
        data_days: int
    ) -> Dict:
        """
        Compute data quality metrics for portfolio

        Phase 8.1 Task 13: Computes position counts to explain why calculations were skipped

        Args:
            portfolio_id: Portfolio UUID
            flag: Quality flag constant (e.g., NO_FACTOR_CALCULATIONS)
            message: Human-readable explanation
            positions_analyzed: Number of positions included in calculation
            data_days: Number of days of historical data used

        Returns:
            Dictionary with data_quality metrics matching DataQualityInfo schema
        """
        from sqlalchemy import or_

        # Count total positions in portfolio
        total_stmt = select(func.count(Position.id)).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.quantity != 0  # Only count active positions
            )
        )
        positions_total = (await self.db.execute(total_stmt)).scalar() or 0

        # Count PUBLIC positions (exclude PRIVATE investment_class per Phase 8.1)
        public_stmt = select(func.count(Position.id)).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.quantity != 0,
                or_(
                    Position.investment_class != 'PRIVATE',
                    Position.investment_class.is_(None)  # Include NULL (not yet classified)
                )
            )
        )
        public_positions = (await self.db.execute(public_stmt)).scalar() or 0

        # positions_skipped = total - analyzed
        positions_skipped = positions_total - positions_analyzed

        return {
            "flag": flag,
            "message": message,
            "positions_analyzed": positions_analyzed,
            "positions_total": positions_total,
            "positions_skipped": positions_skipped,
            "data_days": data_days
        }
