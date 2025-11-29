#!/usr/bin/env python3
import asyncio
import argparse
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_

from app.database import AsyncSessionLocal
from app.models.market_data import StressTestScenario, StressTestResult
from app.models.snapshots import PortfolioSnapshot


async def inspect(portfolio_id: UUID, scenarios: Optional[List[str]] = None) -> None:
    async with AsyncSessionLocal() as db:
        print(f"=== Inspecting stress test data for portfolio {portfolio_id} ===")

        scen_count = await db.scalar(select(func.count(StressTestScenario.id)))
        print(f"- StressTestScenario rows: {scen_count}")
        if scen_count == 0:
            print("  ⚠️ No scenarios found (seed required).")
            return

        all_results = await db.scalar(select(func.count(StressTestResult.id)))
        print(f"- StressTestResult rows (all portfolios): {all_results}")

        stmt_dates = (
            select(StressTestResult.calculation_date, func.count())
            .where(StressTestResult.portfolio_id == portfolio_id)
            .group_by(StressTestResult.calculation_date)
            .order_by(StressTestResult.calculation_date.desc())
        )
        if scenarios:
            stmt_dates = (
                stmt_dates.join(
                    StressTestScenario,
                    StressTestResult.scenario_id == StressTestScenario.id,
                )
                .where(StressTestScenario.scenario_id.in_(scenarios))
            )

        rows = (await db.execute(stmt_dates)).all()
        if not rows:
            print("  ❌ No StressTestResult rows for this portfolio (with current filter).")
            return

        print("- Result dates for this portfolio:")
        for d, c in rows:
            print(f"  • {d} → {c} rows")

        anchor_date = rows[0][0]
        print(f"- Anchor calculation_date: {anchor_date}")

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
        snap = (await db.execute(snap_stmt)).scalars().first()
        if not snap:
            print("  ⚠️ No PortfolioSnapshot on/<= anchor_date (reason=no_snapshot).")
        else:
            print(
                f"  ✓ Snapshot: {snap.snapshot_date} total_value={float(snap.total_value):,.2f}"
            )

        rows_stmt = (
            select(StressTestResult, StressTestScenario)
            .join(StressTestScenario, StressTestResult.scenario_id == StressTestScenario.id)
            .where(
                and_(
                    StressTestResult.portfolio_id == portfolio_id,
                    StressTestResult.calculation_date == anchor_date,
                )
            )
            .order_by(StressTestScenario.category.asc(), StressTestScenario.name.asc())
            .limit(10)
        )
        if scenarios:
            rows_stmt = rows_stmt.where(StressTestScenario.scenario_id.in_(scenarios))

        sample: List[Tuple[StressTestResult, StressTestScenario]] = list(
            (await db.execute(rows_stmt)).all()
        )
        print(f"- Sample rows @ {anchor_date} (up to 10):")
        if not sample:
            print("  (none)")
        for res, scen in sample:
            val = (
                float(res.correlated_pnl)
                if res.correlated_pnl is not None
                else 0.0
            )
            print(
                f"  • {scen.scenario_id:>20}  {scen.name:<28} correlated_pnl={val:,.2f}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Inspect stress test DB state for a portfolio."
    )
    parser.add_argument("--portfolio-id", required=True, help="Portfolio UUID")
    parser.add_argument(
        "--scenarios", help="CSV of scenario_ids to filter (optional)"
    )
    args = parser.parse_args()

    portfolio_id = UUID(args.portfolio_id)
    scenarios = (
        [s.strip() for s in args.scenarios.split(",")]
        if args.scenarios
        else None
    )

    asyncio.run(inspect(portfolio_id, scenarios))


if __name__ == "__main__":
    main()

