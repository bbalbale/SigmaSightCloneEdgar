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
            meta = {"reason": "no_results"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "metadata": meta}

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
            meta = {"reason": "no_snapshot"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "metadata": meta}

        baseline = float(snapshot.total_value)
        if baseline == 0:
            # Avoid division by zero; percentage impacts would be undefined
            meta = {"reason": "no_snapshot"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "metadata": meta}

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
            meta = {"reason": "no_results"}
            if scenarios:
                meta["scenarios_requested"] = scenarios
            return {"available": False, "metadata": meta}

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

        result = {"available": True, "data": payload}
        if meta:
            result["metadata"] = meta
        return result

