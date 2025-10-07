#!/usr/bin/env python3
"""
Railway Calculations Audit Script - VERBOSE VERSION
Audits all calculation results tables with detailed sample data
"""
import os
import asyncio
from sqlalchemy import select, func, distinct, and_, desc
from datetime import datetime
from typing import Dict, List
from decimal import Decimal

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver\n")

from app.database import get_async_session
from app.models.market_data import (
    PositionGreeks,
    PositionFactorExposure,
    PositionInterestRateBeta,
    StressTestResult
)
from app.models.snapshots import PortfolioSnapshot, BatchJob
from app.models.correlations import (
    CorrelationCalculation,
    PairwiseCorrelation,
    CorrelationCluster
)
from app.models.positions import Position
from app.models.users import Portfolio


def format_decimal(value, decimals=4):
    """Format decimal/float for display"""
    if value is None:
        return "N/A"
    if isinstance(value, (Decimal, float)):
        return f"{float(value):.{decimals}f}"
    return str(value)


async def get_all_portfolios():
    """Get all portfolios for iteration"""
    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio)
            .order_by(Portfolio.name)
        )
        return result.scalars().all()


async def audit_portfolio_snapshots_detailed(portfolio):
    """Detailed snapshot audit for a single portfolio"""
    async with get_async_session() as db:
        # Get all snapshots for this portfolio
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(5)  # Last 5 snapshots
        )
        snapshots = result.scalars().all()

        if not snapshots:
            return None

        output = []
        output.append(f"\n{'='*80}")
        output.append(f"📊 PORTFOLIO SNAPSHOTS: {portfolio.name}")
        output.append(f"{'='*80}")
        output.append(f"Total snapshots found: {len(snapshots)}")
        output.append("")

        # Show details of latest snapshot
        latest = snapshots[0]
        output.append(f"Latest Snapshot ({latest.snapshot_date}):")
        output.append(f"  Position Count: {latest.num_positions}")
        output.append(f"  Total Market Value: ${format_decimal(latest.total_value, 2)}")
        output.append(f"  Long Value: ${format_decimal(latest.long_value, 2)}")
        output.append(f"  Short Value: ${format_decimal(latest.short_value, 2)}")
        output.append(f"  Net Exposure: ${format_decimal(latest.net_exposure, 2)}")
        output.append(f"  Gross Exposure: ${format_decimal(latest.gross_exposure, 2)}")

        if latest.portfolio_delta:
            output.append(f"  Portfolio Delta: {format_decimal(latest.portfolio_delta, 2)}")
        if latest.portfolio_gamma:
            output.append(f"  Portfolio Gamma: {format_decimal(latest.portfolio_gamma, 4)}")
        if latest.portfolio_theta:
            output.append(f"  Portfolio Theta: {format_decimal(latest.portfolio_theta, 2)}")
        if latest.portfolio_vega:
            output.append(f"  Portfolio Vega: {format_decimal(latest.portfolio_vega, 2)}")

        # Show snapshot history
        if len(snapshots) > 1:
            output.append(f"\nSnapshot History (last {len(snapshots)}):")
            output.append(f"{'DATE':<12} {'POSITIONS':<10} {'MARKET VALUE':<15} {'NET EXPOSURE':<15}")
            output.append("-" * 80)
            for snap in snapshots:
                output.append(
                    f"{str(snap.snapshot_date):<12} "
                    f"{snap.num_positions:<10} "
                    f"${format_decimal(snap.total_value, 2):<14} "
                    f"${format_decimal(snap.net_exposure, 2):<14}"
                )

        return "\n".join(output)


async def audit_factor_exposures_detailed(portfolio):
    """Detailed factor exposure audit for a single portfolio"""
    from app.models.market_data import FactorDefinition

    async with get_async_session() as db:
        # Get positions for this portfolio
        result = await db.execute(
            select(Position.id, Position.symbol)
            .where(Position.portfolio_id == portfolio.id)
            .where(Position.deleted_at.is_(None))
            .where(Position.exit_date.is_(None))
        )
        positions_list = result.all()
        if not positions_list:
            return None

        positions_map = {pid: symbol for pid, symbol in positions_list}
        position_ids = list(positions_map.keys())

        # Get factor exposures with factor names
        result = await db.execute(
            select(
                PositionFactorExposure.position_id,
                PositionFactorExposure.exposure_value,
                PositionFactorExposure.calculation_date,
                FactorDefinition.name
            )
            .join(FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id)
            .where(PositionFactorExposure.position_id.in_(position_ids))
            .order_by(PositionFactorExposure.calculation_date.desc())
        )
        exposures_data = result.all()

        if not exposures_data:
            return None

        output = []
        output.append(f"\n{'='*80}")
        output.append(f"📈 FACTOR EXPOSURES: {portfolio.name}")
        output.append(f"{'='*80}")
        output.append(f"Total exposure records: {len(exposures_data)}")
        output.append("")

        # Pivot data: group by position_id and latest date, collect factors
        from collections import defaultdict
        by_position = defaultdict(lambda: {"factors": {}, "date": None})

        for pos_id, exp_val, calc_date, factor_name in exposures_data:
            if by_position[pos_id]["date"] is None or calc_date >= by_position[pos_id]["date"]:
                if calc_date > by_position[pos_id]["date"] if by_position[pos_id]["date"] else True:
                    by_position[pos_id]["date"] = calc_date
                    by_position[pos_id]["factors"] = {}
                by_position[pos_id]["factors"][factor_name] = exp_val

        # Show sample positions (limit to 20)
        output.append(f"Factor Exposures by Position (sample, latest calculation):")
        output.append("")
        output.append(f"{'SYMBOL':<12} {'FACTORS':<60} {'DATE':<12}")
        output.append("-" * 88)

        count = 0
        for pos_id in sorted(by_position.keys(), key=lambda x: positions_map.get(x, "")):
            if count >= 20:  # Limit to 20 positions
                output.append(f"... and {len(by_position) - 20} more positions")
                break

            symbol = positions_map.get(pos_id, "Unknown")[:11]
            pos_data = by_position[pos_id]

            # Format factors as "Factor: value" pairs
            factor_str = ", ".join([
                f"{fname[:3]}: {format_decimal(fval, 2)}"
                for fname, fval in sorted(pos_data["factors"].items())
            ])[:59]

            output.append(
                f"{symbol:<12} {factor_str:<60} {str(pos_data['date']):<12}"
            )
            count += 1

        return "\n".join(output)


async def audit_correlations_detailed(portfolio):
    """Detailed correlation audit for a single portfolio"""
    async with get_async_session() as db:
        # Get correlation calculations for this portfolio
        result = await db.execute(
            select(CorrelationCalculation)
            .where(CorrelationCalculation.portfolio_id == portfolio.id)
            .order_by(CorrelationCalculation.calculation_date.desc())
            .limit(1)
        )
        calc = result.scalar_one_or_none()

        if not calc:
            return None

        # Get pairwise correlations for this calculation
        result = await db.execute(
            select(PairwiseCorrelation)
            .where(PairwiseCorrelation.correlation_calculation_id == calc.id)
            .order_by(func.abs(PairwiseCorrelation.correlation_value).desc())
            .limit(20)  # Top 20 strongest correlations
        )
        pairs = result.scalars().all()

        output = []
        output.append(f"\n{'='*80}")
        output.append(f"🔗 CORRELATION ANALYSIS: {portfolio.name}")
        output.append(f"{'='*80}")
        output.append(f"Calculation Date: {calc.calculation_date}")
        output.append(f"Duration Days: {calc.duration_days}")
        output.append(f"Positions Included: {calc.positions_included}")
        output.append("")

        if pairs:
            output.append(f"Top 20 Strongest Correlations (by absolute value):")
            output.append(f"{'SYMBOL 1':<12} {'SYMBOL 2':<12} {'CORRELATION':<12} {'DATA POINTS':<12}")
            output.append("-" * 80)

            for pair in pairs:
                output.append(
                    f"{pair.symbol_1:<12} "
                    f"{pair.symbol_2:<12} "
                    f"{format_decimal(pair.correlation_value, 4):<12} "
                    f"{pair.data_points:<12}"
                )

        # Get clusters
        from app.models.correlations import CorrelationClusterPosition
        result = await db.execute(
            select(CorrelationCluster)
            .where(CorrelationCluster.correlation_calculation_id == calc.id)
        )
        clusters = result.scalars().all()

        if clusters:
            output.append(f"\nCorrelation Clusters ({len(clusters)} found):")
            for cluster in clusters:
                # Get symbols for this cluster
                result = await db.execute(
                    select(CorrelationClusterPosition.symbol)
                    .where(CorrelationClusterPosition.cluster_id == cluster.id)
                    .limit(5)
                )
                symbols = [s for (s,) in result.all()]

                # Count total positions
                result = await db.execute(
                    select(func.count(CorrelationClusterPosition.id))
                    .where(CorrelationClusterPosition.cluster_id == cluster.id)
                )
                total_positions = result.scalar()

                symbols_str = ", ".join(symbols)
                if total_positions > 5:
                    symbols_str += f" ... (+{total_positions - 5} more)"
                output.append(f"  {cluster.nickname}: {symbols_str}")
                output.append(f"    Avg Correlation: {format_decimal(cluster.avg_correlation, 4)}")

        return "\n".join(output)


async def audit_stress_tests_detailed(portfolio):
    """Detailed stress test audit for a single portfolio"""
    from app.models.market_data import StressTestScenario

    async with get_async_session() as db:
        try:
            # Get stress test results with scenario names
            result = await db.execute(
                select(
                    StressTestResult.calculation_date,
                    StressTestResult.direct_pnl,
                    StressTestResult.correlated_pnl,
                    StressTestScenario.name.label('scenario_name')
                )
                .join(StressTestScenario, StressTestResult.scenario_id == StressTestScenario.id)
                .where(StressTestResult.portfolio_id == portfolio.id)
                .order_by(StressTestResult.calculation_date.desc())
                .limit(30)  # Recent tests
            )
            results_data = result.all()

            if not results_data:
                return None

            output = []
            output.append(f"\n{'='*80}")
            output.append(f"⚠️  STRESS TEST RESULTS: {portfolio.name}")
            output.append(f"{'='*80}")
            output.append(f"Total stress test results: {len(results_data)}")
            output.append("")

            # Group by scenario and show latest
            by_scenario = {}
            for calc_date, direct_pnl, correlated_pnl, scenario_name in results_data:
                if scenario_name not in by_scenario:
                    by_scenario[scenario_name] = (calc_date, direct_pnl, correlated_pnl)

            output.append(f"Stress Test Scenarios (latest results):")
            output.append("")
            output.append(f"{'SCENARIO':<32} {'DIRECT P&L':<15} {'CORR P&L':<15} {'DATE':<12}")
            output.append("-" * 80)

            for scenario_name in sorted(by_scenario.keys()):
                calc_date, direct_pnl, correlated_pnl = by_scenario[scenario_name]
                output.append(
                    f"{scenario_name[:30]:<32} "
                    f"${format_decimal(direct_pnl, 2):<14} "
                    f"${format_decimal(correlated_pnl, 2):<14} "
                    f"{str(calc_date):<12}"
                )

            return "\n".join(output)

        except Exception as e:
            if "does not exist" in str(e) or "no such table" in str(e):
                return None
            raise


async def audit_greeks_detailed(portfolio):
    """Detailed Greeks audit for a single portfolio"""
    async with get_async_session() as db:
        # Get positions for this portfolio
        result = await db.execute(
            select(Position.id, Position.symbol)
            .where(Position.portfolio_id == portfolio.id)
            .where(Position.deleted_at.is_(None))
            .where(Position.exit_date.is_(None))
            .where(Position.strike_price.isnot(None))  # Options only
        )
        positions_map = {pid: symbol for pid, symbol in result.all()}

        if not positions_map:
            return None

        # Get Greeks for these positions
        result = await db.execute(
            select(PositionGreeks)
            .where(PositionGreeks.position_id.in_(positions_map.keys()))
            .order_by(PositionGreeks.calculation_date.desc())
            .limit(30)
        )
        greeks = result.scalars().all()

        if not greeks:
            return None

        output = []
        output.append(f"\n{'='*80}")
        output.append(f"📐 OPTIONS GREEKS: {portfolio.name}")
        output.append(f"{'='*80}")
        output.append(f"Total Greeks records: {len(greeks)}")
        output.append("")

        # Group by position and show latest
        by_position = {}
        for greek in greeks:
            if greek.position_id not in by_position:
                by_position[greek.position_id] = greek

        output.append(f"Options Greeks by Position (latest calculation):")
        output.append("")
        output.append(f"{'SYMBOL':<12} {'DELTA':<10} {'GAMMA':<10} {'THETA':<10} {'VEGA':<10} {'RHO':<10} {'DATE':<12}")
        output.append("-" * 80)

        for pos_id in sorted(by_position.keys(), key=lambda x: positions_map.get(x, "")):
            greek = by_position[pos_id]
            symbol = positions_map.get(pos_id, "Unknown")[:11]
            output.append(
                f"{symbol:<12} "
                f"{format_decimal(greek.delta, 4):<10} "
                f"{format_decimal(greek.gamma, 4):<10} "
                f"{format_decimal(greek.theta, 4):<10} "
                f"{format_decimal(greek.vega, 4):<10} "
                f"{format_decimal(greek.rho, 4):<10} "
                f"{str(greek.calculation_date):<12}"
            )

        return "\n".join(output)


async def main():
    """Main audit orchestration - VERBOSE"""
    import json

    print("=" * 80)
    print("🔍 RAILWAY CALCULATIONS AUDIT - VERBOSE MODE")
    print("=" * 80)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"Date: {timestamp}\n")
    print("Detailed audit with sample data from each calculation engine\n")

    # Collect all output
    all_output = []
    all_output.append("=" * 80)
    all_output.append("RAILWAY CALCULATIONS AUDIT - DETAILED REPORT")
    all_output.append("=" * 80)
    all_output.append(f"Generated: {timestamp}\n")

    # Get all portfolios
    portfolios = await get_all_portfolios()
    print(f"Found {len(portfolios)} portfolios to audit\n")

    summary = {
        "portfolios_audited": len(portfolios),
        "timestamp": timestamp,
        "details_by_portfolio": {}
    }

    # Audit each portfolio
    for portfolio in portfolios:
        print(f"\n{'#' * 80}")
        print(f"# PORTFOLIO: {portfolio.name}")
        print(f"# ID: {portfolio.id}")
        print(f"{'#' * 80}\n")

        portfolio_output = []
        portfolio_output.append(f"\n\n{'#' * 80}")
        portfolio_output.append(f"# PORTFOLIO: {portfolio.name}")
        portfolio_output.append(f"# ID: {portfolio.id}")
        portfolio_output.append(f"{'#' * 80}")

        portfolio_summary = {
            "name": portfolio.name,
            "id": str(portfolio.id),
            "engines": {}
        }

        # 1. Snapshots
        print("  Auditing snapshots...")
        snapshots_output = await audit_portfolio_snapshots_detailed(portfolio)
        if snapshots_output:
            portfolio_output.append(snapshots_output)
            portfolio_summary["engines"]["snapshots"] = "✅ Data found"
        else:
            portfolio_output.append(f"\n📊 PORTFOLIO SNAPSHOTS: No data found")
            portfolio_summary["engines"]["snapshots"] = "❌ No data"

        # 2. Factor Exposures
        print("  Auditing factor exposures...")
        factors_output = await audit_factor_exposures_detailed(portfolio)
        if factors_output:
            portfolio_output.append(factors_output)
            portfolio_summary["engines"]["factor_exposures"] = "✅ Data found"
        else:
            portfolio_output.append(f"\n📈 FACTOR EXPOSURES: No data found")
            portfolio_summary["engines"]["factor_exposures"] = "❌ No data"

        # 3. Correlations
        print("  Auditing correlations...")
        correlations_output = await audit_correlations_detailed(portfolio)
        if correlations_output:
            portfolio_output.append(correlations_output)
            portfolio_summary["engines"]["correlations"] = "✅ Data found"
        else:
            portfolio_output.append(f"\n🔗 CORRELATION ANALYSIS: No data found")
            portfolio_summary["engines"]["correlations"] = "❌ No data"

        # 4. Stress Tests
        print("  Auditing stress tests...")
        stress_output = await audit_stress_tests_detailed(portfolio)
        if stress_output:
            portfolio_output.append(stress_output)
            portfolio_summary["engines"]["stress_tests"] = "✅ Data found"
        else:
            portfolio_output.append(f"\n⚠️  STRESS TEST RESULTS: No data found (table may not exist)")
            portfolio_summary["engines"]["stress_tests"] = "❌ No data"

        # 5. Greeks
        print("  Auditing options Greeks...")
        greeks_output = await audit_greeks_detailed(portfolio)
        if greeks_output:
            portfolio_output.append(greeks_output)
            portfolio_summary["engines"]["greeks"] = "✅ Data found"
        else:
            portfolio_output.append(f"\n📐 OPTIONS GREEKS: No data found (expected - disabled)")
            portfolio_summary["engines"]["greeks"] = "❌ No data (expected)"

        all_output.extend(portfolio_output)
        summary["details_by_portfolio"][portfolio.name] = portfolio_summary

    # Overall summary section
    all_output.append("\n\n" + "=" * 80)
    all_output.append("OVERALL SUMMARY")
    all_output.append("=" * 80)
    all_output.append(f"Portfolios Audited: {len(portfolios)}")
    all_output.append("")

    for portfolio_name, details in summary["details_by_portfolio"].items():
        all_output.append(f"\n{portfolio_name}:")
        for engine, status in details["engines"].items():
            all_output.append(f"  {engine}: {status}")

    # Save detailed text report
    txt_filename = "railway_calculations_audit_report.txt"
    with open(txt_filename, "w") as f:
        f.write("\n".join(all_output))

    # Save JSON summary
    json_filename = "railway_calculations_audit_results.json"
    with open(json_filename, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n" + "=" * 80)
    print(f"✅ Verbose audit complete!")
    print(f"   - Detailed text report: {txt_filename}")
    print(f"   - JSON summary: {json_filename}")
    print(f"   Timestamp: {timestamp}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
