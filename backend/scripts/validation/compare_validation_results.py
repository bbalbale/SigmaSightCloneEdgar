#!/usr/bin/env python
"""
Compare Validation Results

This script compares the newly calculated V2 batch results against the
captured baseline to validate that V2 produces consistent calculations.

Usage:
    python scripts/validation/compare_validation_results.py

Output:
    - Console summary with PASS/FAIL counts
    - Detailed report: PlanningDocs/validation_comparison_report.txt

Tolerances:
    - P&L fields (equity_balance, daily_pnl, etc.): ±$0.01
    - Beta values: ±0.0001
    - Percentages: ±0.0001
    - Correlation values: ±0.0001
"""
import sys
import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# CRITICAL: Windows + asyncpg compatibility fix - MUST be before any async imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Railway DATABASE_URL
DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

# Date range for validation
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 1, 12)

# Paths
BASELINE_FILE = Path(__file__).parent.parent.parent.parent / "PlanningDocs" / f"baseline_validation_{START_DATE}_to_{END_DATE}.json"
REPORT_FILE = Path(__file__).parent.parent.parent.parent / "PlanningDocs" / "validation_comparison_report.txt"

# Tolerances
DOLLAR_TOLERANCE = 0.01  # ±$0.01
BETA_TOLERANCE = 0.0001  # ±0.0001
PERCENT_TOLERANCE = 0.0001  # ±0.0001

# Fields and their tolerances
SNAPSHOT_DOLLAR_FIELDS = [
    "net_asset_value", "cash_value", "long_value", "short_value",
    "gross_exposure", "net_exposure", "daily_pnl", "cumulative_pnl",
    "daily_realized_pnl", "cumulative_realized_pnl", "daily_capital_flow",
    "cumulative_capital_flow", "equity_balance", "portfolio_delta",
    "portfolio_gamma", "portfolio_theta", "portfolio_vega",
    "target_price_upside_eoy_dollars", "target_price_upside_next_year_dollars",
    "target_price_downside_dollars",
]

SNAPSHOT_BETA_FIELDS = [
    "daily_return", "realized_volatility_21d", "realized_volatility_63d",
    "expected_volatility_21d", "volatility_percentile",
    "beta_calculated_90d", "beta_calculated_90d_r_squared",
    "beta_provider_1y", "beta_portfolio_regression",
    "hhi", "effective_num_positions", "top_3_concentration", "top_10_concentration",
    "target_price_return_eoy", "target_price_return_next_year",
    "target_price_downside_return", "target_price_coverage_pct",
]

SNAPSHOT_INT_FIELDS = [
    "num_positions", "num_long_positions", "num_short_positions",
    "beta_calculated_90d_observations", "target_price_positions_count",
    "target_price_total_positions",
]


class ComparisonResult:
    """Stores comparison results for reporting."""

    def __init__(self):
        self.matches = 0
        self.mismatches = []
        self.missing_in_new = []
        self.extra_in_new = []

    def add_match(self):
        self.matches += 1

    def add_mismatch(self, context: str, field: str, old_val: Any, new_val: Any, tolerance: float):
        self.mismatches.append({
            "context": context,
            "field": field,
            "old": old_val,
            "new": new_val,
            "tolerance": tolerance,
            "diff": abs(float(old_val or 0) - float(new_val or 0)) if old_val is not None and new_val is not None else None,
        })

    def add_missing(self, context: str, description: str):
        self.missing_in_new.append({"context": context, "description": description})

    def add_extra(self, context: str, description: str):
        self.extra_in_new.append({"context": context, "description": description})

    @property
    def total_comparisons(self) -> int:
        return self.matches + len(self.mismatches)

    @property
    def success_rate(self) -> float:
        if self.total_comparisons == 0:
            return 100.0
        return (self.matches / self.total_comparisons) * 100


def values_match(old_val: Any, new_val: Any, tolerance: float) -> bool:
    """Check if two values match within tolerance."""
    # Handle None cases
    if old_val is None and new_val is None:
        return True
    if old_val is None or new_val is None:
        return False

    # Convert to float for comparison
    try:
        old_float = float(old_val)
        new_float = float(new_val)
        return abs(old_float - new_float) <= tolerance
    except (TypeError, ValueError):
        # Fall back to string comparison for non-numeric
        return str(old_val) == str(new_val)


def load_baseline() -> dict:
    """Load the baseline JSON file."""
    with open(BASELINE_FILE, "r") as f:
        return json.load(f)


async def fetch_current_snapshots(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> Dict[str, Dict]:
    """Fetch current portfolio_snapshots and index by (portfolio_id, date)."""
    from app.models.snapshots import PortfolioSnapshot

    result = await session.execute(
        select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                PortfolioSnapshot.snapshot_date >= start_date,
                PortfolioSnapshot.snapshot_date <= end_date,
            )
        )
    )
    snapshots = result.scalars().all()

    indexed = {}
    for s in snapshots:
        key = f"{s.portfolio_id}_{s.snapshot_date.isoformat()}"
        indexed[key] = {
            "id": str(s.id),
            "portfolio_id": str(s.portfolio_id),
            "snapshot_date": s.snapshot_date.isoformat(),
            "net_asset_value": float(s.net_asset_value) if s.net_asset_value else None,
            "cash_value": float(s.cash_value) if s.cash_value else None,
            "long_value": float(s.long_value) if s.long_value else None,
            "short_value": float(s.short_value) if s.short_value else None,
            "gross_exposure": float(s.gross_exposure) if s.gross_exposure else None,
            "net_exposure": float(s.net_exposure) if s.net_exposure else None,
            "daily_pnl": float(s.daily_pnl) if s.daily_pnl else None,
            "daily_return": float(s.daily_return) if s.daily_return else None,
            "cumulative_pnl": float(s.cumulative_pnl) if s.cumulative_pnl else None,
            "daily_realized_pnl": float(s.daily_realized_pnl) if s.daily_realized_pnl else None,
            "cumulative_realized_pnl": float(s.cumulative_realized_pnl) if s.cumulative_realized_pnl else None,
            "daily_capital_flow": float(s.daily_capital_flow) if s.daily_capital_flow else None,
            "cumulative_capital_flow": float(s.cumulative_capital_flow) if s.cumulative_capital_flow else None,
            "portfolio_delta": float(s.portfolio_delta) if s.portfolio_delta else None,
            "portfolio_gamma": float(s.portfolio_gamma) if s.portfolio_gamma else None,
            "portfolio_theta": float(s.portfolio_theta) if s.portfolio_theta else None,
            "portfolio_vega": float(s.portfolio_vega) if s.portfolio_vega else None,
            "num_positions": s.num_positions,
            "num_long_positions": s.num_long_positions,
            "num_short_positions": s.num_short_positions,
            "equity_balance": float(s.equity_balance) if s.equity_balance else None,
            "realized_volatility_21d": float(s.realized_volatility_21d) if s.realized_volatility_21d else None,
            "realized_volatility_63d": float(s.realized_volatility_63d) if s.realized_volatility_63d else None,
            "expected_volatility_21d": float(s.expected_volatility_21d) if s.expected_volatility_21d else None,
            "volatility_trend": s.volatility_trend,
            "volatility_percentile": float(s.volatility_percentile) if s.volatility_percentile else None,
            "beta_calculated_90d": float(s.beta_calculated_90d) if s.beta_calculated_90d else None,
            "beta_calculated_90d_r_squared": float(s.beta_calculated_90d_r_squared) if s.beta_calculated_90d_r_squared else None,
            "beta_calculated_90d_observations": s.beta_calculated_90d_observations,
            "beta_provider_1y": float(s.beta_provider_1y) if s.beta_provider_1y else None,
            "beta_portfolio_regression": float(s.beta_portfolio_regression) if s.beta_portfolio_regression else None,
            "hhi": float(s.hhi) if s.hhi else None,
            "effective_num_positions": float(s.effective_num_positions) if s.effective_num_positions else None,
            "top_3_concentration": float(s.top_3_concentration) if s.top_3_concentration else None,
            "top_10_concentration": float(s.top_10_concentration) if s.top_10_concentration else None,
            "target_price_return_eoy": float(s.target_price_return_eoy) if s.target_price_return_eoy else None,
            "target_price_return_next_year": float(s.target_price_return_next_year) if s.target_price_return_next_year else None,
            "target_price_downside_return": float(s.target_price_downside_return) if s.target_price_downside_return else None,
            "target_price_upside_eoy_dollars": float(s.target_price_upside_eoy_dollars) if s.target_price_upside_eoy_dollars else None,
            "target_price_upside_next_year_dollars": float(s.target_price_upside_next_year_dollars) if s.target_price_upside_next_year_dollars else None,
            "target_price_downside_dollars": float(s.target_price_downside_dollars) if s.target_price_downside_dollars else None,
            "target_price_coverage_pct": float(s.target_price_coverage_pct) if s.target_price_coverage_pct else None,
            "target_price_positions_count": s.target_price_positions_count,
            "target_price_total_positions": s.target_price_total_positions,
            "is_complete": s.is_complete,
        }

    return indexed


def compare_snapshots(baseline_snapshots: List[dict], current_snapshots: Dict[str, Dict], result: ComparisonResult):
    """Compare baseline snapshots against current snapshots."""
    baseline_keys = set()

    for old_snap in baseline_snapshots:
        portfolio_id = old_snap["portfolio_id"]
        snap_date = old_snap["snapshot_date"]
        key = f"{portfolio_id}_{snap_date}"
        baseline_keys.add(key)
        context = f"Snapshot {portfolio_id[:8]}.../{snap_date}"

        if key not in current_snapshots:
            result.add_missing(context, f"Snapshot not found in new data")
            continue

        new_snap = current_snapshots[key]

        # Compare dollar fields
        for field in SNAPSHOT_DOLLAR_FIELDS:
            old_val = old_snap.get(field)
            new_val = new_snap.get(field)
            if values_match(old_val, new_val, DOLLAR_TOLERANCE):
                result.add_match()
            else:
                result.add_mismatch(context, field, old_val, new_val, DOLLAR_TOLERANCE)

        # Compare beta/percentage fields
        for field in SNAPSHOT_BETA_FIELDS:
            old_val = old_snap.get(field)
            new_val = new_snap.get(field)
            if values_match(old_val, new_val, BETA_TOLERANCE):
                result.add_match()
            else:
                result.add_mismatch(context, field, old_val, new_val, BETA_TOLERANCE)

        # Compare integer fields (exact match)
        for field in SNAPSHOT_INT_FIELDS:
            old_val = old_snap.get(field)
            new_val = new_snap.get(field)
            if old_val == new_val:
                result.add_match()
            else:
                result.add_mismatch(context, field, old_val, new_val, 0)

    # Check for extra snapshots in new data
    for key in current_snapshots:
        if key not in baseline_keys:
            result.add_extra("Snapshot", f"Extra snapshot: {key}")


def generate_report(result: ComparisonResult, baseline: dict) -> str:
    """Generate a detailed comparison report."""
    lines = []
    lines.append("=" * 80)
    lines.append("V2 BATCH VALIDATION COMPARISON REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.utcnow().isoformat()}")
    lines.append(f"Baseline captured: {baseline['metadata']['captured_at']}")
    lines.append(f"Date range: {baseline['metadata']['start_date']} to {baseline['metadata']['end_date']}")
    lines.append("")

    # Summary
    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total field comparisons: {result.total_comparisons}")
    lines.append(f"Matches: {result.matches}")
    lines.append(f"Mismatches: {len(result.mismatches)}")
    lines.append(f"Missing in new data: {len(result.missing_in_new)}")
    lines.append(f"Extra in new data: {len(result.extra_in_new)}")
    lines.append(f"Success rate: {result.success_rate:.2f}%")
    lines.append("")

    if result.success_rate >= 99.99:
        lines.append("[PASS] VALIDATION PASSED - V2 batch produces consistent results")
    else:
        lines.append("[FAIL] VALIDATION FAILED - V2 batch produces different results")
    lines.append("")

    # Mismatches
    if result.mismatches:
        lines.append("-" * 80)
        lines.append("MISMATCHES")
        lines.append("-" * 80)
        for m in result.mismatches[:100]:  # Limit to first 100
            lines.append(f"  {m['context']}")
            lines.append(f"    Field: {m['field']}")
            lines.append(f"    Old: {m['old']}")
            lines.append(f"    New: {m['new']}")
            if m['diff'] is not None:
                lines.append(f"    Diff: {m['diff']:.6f} (tolerance: {m['tolerance']})")
            lines.append("")

        if len(result.mismatches) > 100:
            lines.append(f"  ... and {len(result.mismatches) - 100} more mismatches")
        lines.append("")

    # Missing
    if result.missing_in_new:
        lines.append("-" * 80)
        lines.append("MISSING IN NEW DATA")
        lines.append("-" * 80)
        for m in result.missing_in_new[:50]:
            lines.append(f"  {m['context']}: {m['description']}")
        if len(result.missing_in_new) > 50:
            lines.append(f"  ... and {len(result.missing_in_new) - 50} more missing")
        lines.append("")

    # Extra
    if result.extra_in_new:
        lines.append("-" * 80)
        lines.append("EXTRA IN NEW DATA")
        lines.append("-" * 80)
        for m in result.extra_in_new[:50]:
            lines.append(f"  {m['context']}: {m['description']}")
        if len(result.extra_in_new) > 50:
            lines.append(f"  ... and {len(result.extra_in_new) - 50} more extra")
        lines.append("")

    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


async def main():
    """Main entry point."""
    print("=" * 70)
    print("COMPARE VALIDATION RESULTS")
    print("=" * 70)
    print(f"Baseline file: {BASELINE_FILE}")
    print()

    # Check baseline exists
    if not BASELINE_FILE.exists():
        print(f"[ERROR] Baseline file not found: {BASELINE_FILE}")
        print("Run capture_current_baseline.py first.")
        return

    # Load baseline
    print("Loading baseline...")
    baseline = load_baseline()
    print(f"  Portfolios: {len(baseline['portfolios'])}")
    print(f"  Snapshots: {len(baseline['portfolio_snapshots'])}")
    print()

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    result = ComparisonResult()

    async with async_session() as session:
        # Get portfolio IDs from baseline
        portfolio_ids = list(baseline["portfolios"].keys())

        # Fetch current snapshots
        print("Fetching current snapshots from database...")
        current_snapshots = await fetch_current_snapshots(session, portfolio_ids, START_DATE, END_DATE)
        print(f"  Found {len(current_snapshots)} current snapshots")
        print()

        # Compare snapshots
        print("Comparing portfolio_snapshots...")
        compare_snapshots(baseline["portfolio_snapshots"], current_snapshots, result)
        print(f"  Compared {result.total_comparisons} fields")
        print()

    # Print summary
    print("=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print(f"Total field comparisons: {result.total_comparisons}")
    print(f"Matches: {result.matches}")
    print(f"Mismatches: {len(result.mismatches)}")
    print(f"Missing in new data: {len(result.missing_in_new)}")
    print(f"Extra in new data: {len(result.extra_in_new)}")
    print(f"Success rate: {result.success_rate:.2f}%")
    print()

    if result.success_rate >= 99.99:
        print("[PASS] VALIDATION PASSED - V2 batch produces consistent results")
    else:
        print("[FAIL] VALIDATION FAILED - V2 batch produces different results")

    # Show first few mismatches
    if result.mismatches:
        print()
        print("First 5 mismatches:")
        for m in result.mismatches[:5]:
            print(f"  {m['context']} - {m['field']}")
            print(f"    Old: {m['old']}, New: {m['new']}")

    # Generate and save report
    report = generate_report(result, baseline)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    print()
    print(f"Detailed report saved to: {REPORT_FILE}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
