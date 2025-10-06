#!/usr/bin/env python3
"""
Railway Calculations Audit Script
Audits all calculation results tables populated by batch orchestration

Covers:
- Portfolio Snapshots
- Factor Exposures
- Position Correlations
- Position Greeks
- Interest Rate Betas
- Stress Test Results
- Batch Job Execution Metadata
"""
import os
import asyncio
from sqlalchemy import select, func, distinct, and_
from datetime import datetime
from typing import Dict, List

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


async def audit_portfolio_snapshots():
    """Audit portfolio snapshot coverage"""
    print("\n" + "=" * 80)
    print("PORTFOLIO SNAPSHOTS AUDIT")
    print("=" * 80)

    async with get_async_session() as db:
        # 1. Total snapshots
        result = await db.execute(select(func.count(PortfolioSnapshot.id)))
        total_snapshots = result.scalar()

        if total_snapshots == 0:
            print("❌ No portfolio snapshots found")
            print("   This indicates batch calculations have NOT been run.\n")
            return {
                "total_snapshots": 0,
                "portfolios_with_snapshots": 0,
                "date_range": None
            }

        print(f"📊 Total Snapshots: {total_snapshots:,}")

        # 2. Portfolios with snapshots
        result = await db.execute(
            select(func.count(distinct(PortfolioSnapshot.portfolio_id)))
        )
        portfolios_with_snapshots = result.scalar()
        print(f"📁 Portfolios with Snapshots: {portfolios_with_snapshots}")

        # 3. Date range
        result = await db.execute(
            select(
                func.min(PortfolioSnapshot.snapshot_date),
                func.max(PortfolioSnapshot.snapshot_date)
            )
        )
        min_date, max_date = result.first()

        if min_date and max_date:
            print(f"📅 Date Range: {min_date} to {max_date}")

            # Calculate days
            if min_date != max_date:
                days_diff = (max_date - min_date).days
                print(f"   Trading days captured: {total_snapshots // portfolios_with_snapshots if portfolios_with_snapshots else 0}")
                print(f"   Calendar days span: {days_diff}")

        # 4. Per-portfolio breakdown
        result = await db.execute(
            select(
                Portfolio.name,
                func.count(PortfolioSnapshot.id).label('snapshot_count'),
                func.min(PortfolioSnapshot.snapshot_date).label('first_date'),
                func.max(PortfolioSnapshot.snapshot_date).label('last_date')
            )
            .join(Portfolio, PortfolioSnapshot.portfolio_id == Portfolio.id)
            .group_by(Portfolio.name)
            .order_by(Portfolio.name)
        )

        print(f"\n📋 Per-Portfolio Snapshot Coverage:")
        print(f"{'PORTFOLIO':<40} {'COUNT':<8} {'FIRST DATE':<12} {'LAST DATE':<12}")
        print("-" * 80)

        for row in result:
            portfolio_name = row[0][:38] if row[0] else "Unknown"
            print(f"{portfolio_name:<40} {row[1]:<8} {row[2]!s:<12} {row[3]!s:<12}")

        return {
            "total_snapshots": total_snapshots,
            "portfolios_with_snapshots": portfolios_with_snapshots,
            "date_range": f"{min_date} to {max_date}" if min_date else None
        }


async def audit_factor_exposures():
    """Audit factor exposure calculation coverage"""
    print("\n" + "=" * 80)
    print("FACTOR EXPOSURES AUDIT (7-Factor Model)")
    print("=" * 80)

    async with get_async_session() as db:
        # 1. Total factor exposure records
        result = await db.execute(select(func.count(PositionFactorExposure.id)))
        total_exposures = result.scalar()

        if total_exposures == 0:
            print("❌ No factor exposures found")
            print("   Factor analysis has NOT been run.\n")
            return {
                "total_exposures": 0,
                "positions_with_factors": 0
            }

        print(f"📊 Total Factor Exposure Records: {total_exposures:,}")

        # 2. Positions with factor exposures
        result = await db.execute(
            select(func.count(distinct(PositionFactorExposure.position_id)))
        )
        positions_with_factors = result.scalar()
        print(f"📈 Positions with Factor Betas: {positions_with_factors}")

        # 3. Latest calculation dates
        result = await db.execute(
            select(
                func.min(PositionFactorExposure.calculation_date),
                func.max(PositionFactorExposure.calculation_date)
            )
        )
        min_date, max_date = result.first()
        print(f"📅 Calculation Date Range: {min_date} to {max_date}")

        # 4. Average R-squared (model fit quality)
        result = await db.execute(
            select(func.avg(PositionFactorExposure.r_squared))
        )
        avg_r_squared = result.scalar()
        if avg_r_squared:
            print(f"📐 Average R-squared: {float(avg_r_squared):.3f} (model fit quality)")

        # 5. Positions WITHOUT factor exposures
        result = await db.execute(
            select(func.count(Position.id))
            .where(Position.deleted_at.is_(None))
            .where(Position.exit_date.is_(None))
        )
        total_active_positions = result.scalar()

        missing = total_active_positions - positions_with_factors
        if missing > 0:
            print(f"\n⚠️  Positions Missing Factor Data: {missing}/{total_active_positions}")
        else:
            print(f"\n✅ All active positions have factor exposures")

        return {
            "total_exposures": total_exposures,
            "positions_with_factors": positions_with_factors,
            "avg_r_squared": float(avg_r_squared) if avg_r_squared else None,
            "total_active_positions": total_active_positions,
            "missing_factors": missing
        }


async def audit_correlations():
    """Audit correlation calculation coverage"""
    print("\n" + "=" * 80)
    print("CORRELATION ANALYSIS AUDIT")
    print("=" * 80)

    async with get_async_session() as db:
        # 1. Correlation calculations (summary records)
        result = await db.execute(select(func.count(CorrelationCalculation.id)))
        total_calc_records = result.scalar()

        if total_calc_records == 0:
            print("❌ No correlation calculations found")
            print("   Correlation analysis has NOT been run.\n")
            return {
                "calculation_records": 0,
                "pairwise_correlations": 0,
                "clusters": 0
            }

        print(f"📊 Correlation Calculation Records: {total_calc_records:,}")

        # 2. Pairwise correlations
        result = await db.execute(select(func.count(PairwiseCorrelation.id)))
        total_pairwise = result.scalar()
        print(f"🔗 Pairwise Correlations: {total_pairwise:,}")

        # 3. Correlation clusters
        result = await db.execute(select(func.count(CorrelationCluster.id)))
        total_clusters = result.scalar()
        print(f"📦 Correlation Clusters: {total_clusters}")

        # 4. Latest calculation dates
        result = await db.execute(
            select(
                func.min(CorrelationCalculation.calculation_date),
                func.max(CorrelationCalculation.calculation_date)
            )
        )
        min_date, max_date = result.first()
        if min_date:
            print(f"📅 Calculation Date Range: {min_date} to {max_date}")

        # 5. Per-portfolio correlation coverage
        result = await db.execute(
            select(
                Portfolio.name,
                func.count(CorrelationCalculation.id).label('calc_count'),
                func.max(CorrelationCalculation.calculation_date).label('latest_calc')
            )
            .join(Portfolio, CorrelationCalculation.portfolio_id == Portfolio.id)
            .group_by(Portfolio.name)
            .order_by(Portfolio.name)
        )

        print(f"\n📋 Per-Portfolio Correlation Coverage:")
        print(f"{'PORTFOLIO':<40} {'CALCS':<8} {'LATEST DATE':<12}")
        print("-" * 65)

        for row in result:
            portfolio_name = row[0][:38] if row[0] else "Unknown"
            print(f"{portfolio_name:<40} {row[1]:<8} {row[2]!s:<12}")

        return {
            "calculation_records": total_calc_records,
            "pairwise_correlations": total_pairwise,
            "clusters": total_clusters
        }


async def audit_greeks():
    """Audit options Greeks coverage"""
    print("\n" + "=" * 80)
    print("POSITION GREEKS AUDIT")
    print("=" * 80)

    async with get_async_session() as db:
        # 1. Total Greeks records
        result = await db.execute(select(func.count(PositionGreeks.id)))
        total_greeks = result.scalar()

        if total_greeks == 0:
            print("❌ No Greeks calculations found")
            print("   Options Greeks analysis has NOT been run.")
            print("   (Expected - Greeks calculation is DISABLED due to no options feed)\n")
            return {
                "total_greeks": 0,
                "positions_with_greeks": 0
            }

        print(f"📊 Total Greeks Records: {total_greeks:,}")

        # 2. Positions with Greeks
        result = await db.execute(
            select(func.count(distinct(PositionGreeks.position_id)))
        )
        positions_with_greeks = result.scalar()
        print(f"📈 Positions with Greeks: {positions_with_greeks}")

        # 3. Latest calculation dates
        result = await db.execute(
            select(
                func.min(PositionGreeks.calculation_date),
                func.max(PositionGreeks.calculation_date)
            )
        )
        min_date, max_date = result.first()
        if min_date:
            print(f"📅 Calculation Date Range: {min_date} to {max_date}")

        return {
            "total_greeks": total_greeks,
            "positions_with_greeks": positions_with_greeks
        }


async def audit_interest_rate_betas():
    """Audit interest rate beta coverage"""
    print("\n" + "=" * 80)
    print("INTEREST RATE BETAS AUDIT")
    print("=" * 80)

    async with get_async_session() as db:
        # 1. Total IR beta records
        result = await db.execute(select(func.count(PositionInterestRateBeta.id)))
        total_ir_betas = result.scalar()

        if total_ir_betas == 0:
            print("❌ No interest rate beta calculations found")
            print("   IR beta analysis has NOT been run.\n")
            return {
                "total_ir_betas": 0,
                "positions_with_ir_beta": 0
            }

        print(f"📊 Total IR Beta Records: {total_ir_betas:,}")

        # 2. Positions with IR betas
        result = await db.execute(
            select(func.count(distinct(PositionInterestRateBeta.position_id)))
        )
        positions_with_ir_beta = result.scalar()
        print(f"📈 Positions with IR Beta: {positions_with_ir_beta}")

        # 3. Latest calculation dates
        result = await db.execute(
            select(
                func.min(PositionInterestRateBeta.calculation_date),
                func.max(PositionInterestRateBeta.calculation_date)
            )
        )
        min_date, max_date = result.first()
        if min_date:
            print(f"📅 Calculation Date Range: {min_date} to {max_date}")

        return {
            "total_ir_betas": total_ir_betas,
            "positions_with_ir_beta": positions_with_ir_beta
        }


async def audit_stress_tests():
    """Audit stress test results coverage"""
    print("\n" + "=" * 80)
    print("STRESS TEST RESULTS AUDIT")
    print("=" * 80)

    try:
        async with get_async_session() as db:
            # 1. Total stress test results
            result = await db.execute(select(func.count(StressTestResult.id)))
            total_results = result.scalar()

            if total_results == 0:
                print("❌ No stress test results found")
                print("   Stress testing has NOT been run.\n")
                return {
                    "total_results": 0,
                    "portfolios_tested": 0
                }

            print(f"📊 Total Stress Test Results: {total_results:,}")

            # 2. Portfolios with stress tests
            result = await db.execute(
                select(func.count(distinct(StressTestResult.portfolio_id)))
            )
            portfolios_tested = result.scalar()
            print(f"📁 Portfolios Tested: {portfolios_tested}")

            # 3. Latest calculation dates
            result = await db.execute(
                select(
                    func.min(StressTestResult.calculation_date),
                    func.max(StressTestResult.calculation_date)
                )
            )
            min_date, max_date = result.first()
            if min_date:
                print(f"📅 Test Date Range: {min_date} to {max_date}")

            return {
                "total_results": total_results,
                "portfolios_tested": portfolios_tested
            }

    except Exception as e:
        error_str = str(e)
        if "does not exist" in error_str or "no such table" in error_str:
            print("❌ stress_test_results table DOES NOT EXIST")
            print("   This is a KNOWN ISSUE per TODO1.md Section 1.6.14")
            print("   Table needs to be created via Alembic migration\n")
            return {
                "total_results": 0,
                "table_exists": False,
                "error": "Table missing"
            }
        else:
            print(f"❌ Error querying stress test results: {error_str}\n")
            return {
                "total_results": 0,
                "error": error_str
            }


async def audit_batch_jobs():
    """Audit batch job execution history"""
    print("\n" + "=" * 80)
    print("BATCH JOB EXECUTION HISTORY")
    print("=" * 80)

    async with get_async_session() as db:
        # 1. Total batch job records
        result = await db.execute(select(func.count(BatchJob.id)))
        total_jobs = result.scalar()

        if total_jobs == 0:
            print("❌ No batch job execution records found")
            print("   No batch processing history available.\n")
            return {
                "total_jobs": 0,
                "successful_jobs": 0,
                "failed_jobs": 0
            }

        print(f"📊 Total Batch Job Records: {total_jobs:,}")

        # 2. Success/failure breakdown
        result = await db.execute(
            select(
                BatchJob.status,
                func.count(BatchJob.id).label('count')
            )
            .group_by(BatchJob.status)
        )

        print(f"\n📈 Job Status Breakdown:")
        status_counts = {}
        for row in result:
            status = row[0] or "unknown"
            count = row[1]
            status_counts[status] = count
            print(f"   {status}: {count:,}")

        # 3. Recent job runs (last 10)
        result = await db.execute(
            select(BatchJob)
            .order_by(BatchJob.started_at.desc())
            .limit(10)
        )
        recent_jobs = result.scalars().all()

        if recent_jobs:
            print(f"\n📋 Recent Batch Jobs (last 10):")
            print(f"{'JOB NAME':<30} {'STATUS':<12} {'STARTED':<20} {'DURATION':<10}")
            print("-" * 80)

            for job in recent_jobs:
                job_name = job.job_name[:28] if job.job_name else "Unknown"
                status = job.status or "unknown"
                started = job.started_at.strftime("%Y-%m-%d %H:%M:%S") if job.started_at else "N/A"
                duration = f"{job.duration_seconds:.2f}s" if job.duration_seconds else "N/A"
                print(f"{job_name:<30} {status:<12} {started:<20} {duration:<10}")

        return {
            "total_jobs": total_jobs,
            "successful_jobs": status_counts.get("completed", 0),
            "failed_jobs": status_counts.get("failed", 0),
            "status_breakdown": status_counts
        }


async def main():
    """Main audit orchestration"""
    import json

    print("=" * 80)
    print("🔍 RAILWAY CALCULATIONS AUDIT")
    print("=" * 80)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"Date: {timestamp}\n")
    print("This script audits all calculation results tables populated by")
    print("batch orchestration to assess what calculations have been run.\n")

    results = {}

    # Run all audits
    results["portfolio_snapshots"] = await audit_portfolio_snapshots()
    results["factor_exposures"] = await audit_factor_exposures()
    results["correlations"] = await audit_correlations()
    results["greeks"] = await audit_greeks()
    results["interest_rate_betas"] = await audit_interest_rate_betas()
    results["stress_tests"] = await audit_stress_tests()
    results["batch_jobs"] = await audit_batch_jobs()

    # Summary
    print("\n" + "=" * 80)
    print("📊 AUDIT SUMMARY")
    print("=" * 80)

    summary_lines = [
        f"Portfolio Snapshots: {results['portfolio_snapshots']['total_snapshots']:,} records",
        f"Factor Exposures: {results['factor_exposures']['total_exposures']:,} records",
        f"Correlations: {results['correlations']['calculation_records']:,} calculations, {results['correlations']['pairwise_correlations']:,} pairs",
        f"Greeks: {results['greeks']['total_greeks']:,} records (DISABLED - expected 0)",
        f"Interest Rate Betas: {results['interest_rate_betas']['total_ir_betas']:,} records",
        f"Stress Tests: {results['stress_tests'].get('total_results', 0):,} results",
        f"Batch Jobs: {results['batch_jobs']['total_jobs']:,} execution records"
    ]

    for line in summary_lines:
        print(line)

    # Overall assessment
    print("\n" + "=" * 80)
    print("🎯 OVERALL ASSESSMENT")
    print("=" * 80)

    has_snapshots = results['portfolio_snapshots']['total_snapshots'] > 0
    has_factors = results['factor_exposures']['total_exposures'] > 0
    has_correlations = results['correlations']['calculation_records'] > 0
    has_batch_history = results['batch_jobs']['total_jobs'] > 0

    assessment = ""
    if has_snapshots and has_factors and has_correlations:
        assessment = "BATCH CALCULATIONS ARE RUNNING"
        assessment_detail = "All critical calculation engines have produced results."
        print("✅ BATCH CALCULATIONS ARE RUNNING")
        print("   All critical calculation engines have produced results.")
    elif has_batch_history:
        assessment = "PARTIAL BATCH EXECUTION"
        assessment_detail = "Batch jobs have run, but some calculations are incomplete."
        print("⚠️  PARTIAL BATCH EXECUTION")
        print("   Batch jobs have run, but some calculations are incomplete.")
    else:
        assessment = "NO BATCH CALCULATIONS DETECTED"
        assessment_detail = "Database contains only seed data + market data sync. Batch orchestration has NOT been executed on Railway."
        print("❌ NO BATCH CALCULATIONS DETECTED")
        print("   Database contains only seed data + market data sync.")
        print("   Batch orchestration has NOT been executed on Railway.")

    # Save JSON results
    json_filename = "railway_calculations_audit_results.json"
    results["metadata"] = {
        "timestamp": timestamp,
        "assessment": assessment,
        "assessment_detail": assessment_detail
    }

    with open(json_filename, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Save text report
    txt_filename = "railway_calculations_audit_report.txt"
    with open(txt_filename, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("RAILWAY CALCULATIONS AUDIT REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Date: {timestamp}\n\n")

        f.write("SUMMARY:\n")
        f.write("-" * 80 + "\n")
        for line in summary_lines:
            f.write(line + "\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("OVERALL ASSESSMENT:\n")
        f.write("=" * 80 + "\n")
        f.write(f"{assessment}\n")
        f.write(f"{assessment_detail}\n")

    print(f"\n✅ Calculation audit complete!")
    print(f"   - JSON results: {json_filename}")
    print(f"   - Text report: {txt_filename}")
    print(f"   Timestamp: {timestamp}")


if __name__ == "__main__":
    asyncio.run(main())
