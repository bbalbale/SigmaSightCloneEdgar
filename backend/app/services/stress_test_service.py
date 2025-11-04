"""
Stress Test retrieval service (read-only)

Returns precomputed stress testing results for a portfolio using stored
StressTestResult and StressTestScenario rows with a snapshot baseline.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import StressTestResult, StressTestScenario
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position

import logging

logger = logging.getLogger(__name__)


class StressTestService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_portfolio_results(
        self,
        portfolio_id: UUID,
        *,
        scenarios: Optional[List[str]] = None,
    ) -> Dict:
        """
        Read-only retrieval of stress test results.

        Phase 8.1 Task 13: Returns data_quality metrics when available=False

        - Anchor on the latest calculation_date with available StressTestResult rows
          (if `scenarios` filter provided, anchor over the filtered subset).
        - Join StressTestScenario for id/name/description/severity/category
        - Compute impact percentage and new value using baseline PortfolioSnapshot.total_value
        - If no snapshots on/<= anchor date, return available=false (reason: no_snapshot)
        - Return available=false if no results (reason: no_results)
        - Sorting: category ASC, name ASC
        - percentage_impact in percentage points (e.g., -10.0 means -10%)
        - calculation_date is date-only (YYYY-MM-DD)
        - metadata.scenarios_requested is included only when filter provided
        - Reason precedence: if no results → no_results; if results but no snapshot → no_snapshot
        """
        # 1) Determine anchor calculation date
        anchor_stmt = (
            select(func.max(StressTestResult.calculation_date))
            .select_from(StressTestResult)
            .join(StressTestScenario, StressTestResult.scenario_id == StressTestScenario.id)
            .where(StressTestResult.portfolio_id == portfolio_id)
        )
        if scenarios:
            anchor_stmt = anchor_stmt.where(StressTestScenario.scenario_id.in_(scenarios))

        anchor_res = await self.db.execute(anchor_stmt)
        anchor_date = anchor_res.scalar_one_or_none()

        if anchor_date is None:
            # Compute data_quality when no stress test results found
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_STRESS_TEST_RESULTS",
                message="No stress test results available for this portfolio",
                positions_analyzed=0,
                data_days=0
            )
            meta = {"reason": "no_results"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "data_quality": data_quality, "metadata": meta}

        # 2) Baseline portfolio value from snapshot on/<= anchor date
        snap_stmt = (
            select(PortfolioSnapshot)
            .where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date <= anchor_date,
                )
            )
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snap_res = await self.db.execute(snap_stmt)
        snapshot = snap_res.scalars().first()
        if not snapshot:
            # Compute data_quality when no snapshot available
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_SNAPSHOT",
                message="No portfolio snapshot available for stress test calculation",
                positions_analyzed=0,
                data_days=0
            )
            meta = {"reason": "no_snapshot"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "data_quality": data_quality, "metadata": meta}

        baseline = float(snapshot.net_asset_value)
        if baseline == 0:
            # Avoid division by zero; percentage impacts would be undefined
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="ZERO_BASELINE",
                message="Portfolio snapshot has zero total value (cannot compute percentage impacts)",
                positions_analyzed=0,
                data_days=0
            )
            meta = {"reason": "no_snapshot"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "data_quality": data_quality, "metadata": meta}

        # 3) Load scenario results for the anchor date (with optional filter)
        rows_stmt = (
            select(StressTestResult, StressTestScenario)
            .join(StressTestScenario, StressTestResult.scenario_id == StressTestScenario.id)
            .where(
                and_(
                    StressTestResult.portfolio_id == portfolio_id,
                    StressTestResult.calculation_date == anchor_date,
                )
            )
        )
        if scenarios:
            rows_stmt = rows_stmt.where(StressTestScenario.scenario_id.in_(scenarios))

        rows_res = await self.db.execute(rows_stmt)
        rows: List[Tuple[StressTestResult, StressTestScenario]] = list(rows_res.all())

        if not rows:
            # Compute data_quality when results exist but no rows match filters
            data_quality = await self._compute_data_quality(
                portfolio_id=portfolio_id,
                flag="NO_MATCHING_RESULTS",
                message="Stress test results exist but no scenarios match the filter criteria",
                positions_analyzed=0,
                data_days=0
            )
            meta = {"reason": "no_results"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "data_quality": data_quality, "metadata": meta}

        # 4) Build scenario items
        items = []
        for res, scen in rows:
            dollar_impact = float(res.correlated_pnl) if res.correlated_pnl is not None else 0.0
            percentage_impact = (dollar_impact / baseline) * 100.0 if baseline != 0 else 0.0
            new_value = baseline + dollar_impact
            items.append(
                {
                    "id": scen.scenario_id,
                    "name": scen.name,
                    "description": scen.description,
                    "category": scen.category,
                    "impact_type": "correlated",
                    "impact": {
                        "dollar_impact": dollar_impact,
                        "percentage_impact": percentage_impact,
                        "new_portfolio_value": new_value,
                    },
                    "severity": scen.severity,
                }
            )

        # Sorting: category ASC, name ASC
        items.sort(key=lambda x: (x.get("category") or "", x.get("name") or ""))

        payload = {
            "scenarios": items,
            "portfolio_value": baseline,
            "calculation_date": anchor_date.isoformat(),
        }

        meta: Dict[str, object] = {}
        if scenarios:
            meta["scenarios_requested"] = scenarios

        result = {
            "available": True,
            "data": payload,
            "data_quality": None  # Phase 8.1: Future enhancement to compute quality metrics when available=True
        }
        if meta:
            result["metadata"] = meta
        return result

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

        Phase 8.1 Task 13: Computes position counts to explain why stress tests were skipped

        Args:
            portfolio_id: Portfolio UUID
            flag: Quality flag constant (e.g., NO_STRESS_TEST_RESULTS)
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

