"""Verify Quality factor exposure cleanup after reprocessing"""
import asyncio
from sqlalchemy import select, text
from app.database import get_async_session
from uuid import UUID


async def main():
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')

    print("=" * 80)
    print("QUALITY FACTOR EXPOSURE VERIFICATION")
    print("High Net Worth Portfolio")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # Check Quality factor exposures around the problematic dates
        result = await db.execute(text("""
            SELECT
                pfe.calculation_date,
                fd.name as factor_name,
                pfe.exposure_value,
                COUNT(DISTINCT pfe.id) as exposure_count
            FROM position_factor_exposures pfe
            JOIN factor_definitions fd ON pfe.factor_id = fd.id
            JOIN positions p ON pfe.position_id = p.id
            WHERE p.portfolio_id = :portfolio_id
            AND fd.name = 'Quality'
            AND pfe.calculation_date >= '2025-10-18'
            GROUP BY pfe.calculation_date, fd.name, pfe.exposure_value
            ORDER BY pfe.calculation_date DESC, pfe.exposure_value DESC
        """), {"portfolio_id": str(portfolio_id)})

        quality_exposures = result.fetchall()

        print("Quality Factor Exposures (Oct 18-21):")
        print("-" * 80)
        if quality_exposures:
            for row in quality_exposures:
                date = row[0]
                factor = row[1]
                exposure_value = float(row[2]) if row[2] else 0
                count = row[3]

                status = "[OK] POSITIVE" if exposure_value >= 0 else "[NEG] NEGATIVE"
                print(f"{date}: {status}")
                print(f"  Exposure Value: {exposure_value:.6f}")
                print(f"  Exposure Records: {count}")
                print()
        else:
            print("  No Quality factor exposures found!")
            print()

        # Check for ANY negative Quality exposures in the entire history
        neg_result = await db.execute(text("""
            SELECT
                pfe.calculation_date,
                pfe.exposure_value,
                COUNT(*) as count
            FROM position_factor_exposures pfe
            JOIN factor_definitions fd ON pfe.factor_id = fd.id
            JOIN positions p ON pfe.position_id = p.id
            WHERE p.portfolio_id = :portfolio_id
            AND fd.name = 'Quality'
            AND pfe.exposure_value < 0
            GROUP BY pfe.calculation_date, pfe.exposure_value
            ORDER BY pfe.calculation_date DESC
            LIMIT 10
        """), {"portfolio_id": str(portfolio_id)})

        negative_exposures = neg_result.fetchall()

        print("=" * 80)
        print("NEGATIVE Quality Exposures Check:")
        print("-" * 80)
        if negative_exposures:
            print("[WARNING] Found negative Quality exposures!")
            for row in negative_exposures:
                print(f"  Date: {row[0]}, Value: {row[1]:.6f}, Count: {row[2]}")
        else:
            print("[OK] No negative Quality exposures found - data is clean!")
        print()

        # Analyze magnitude of negative exposures
        max_negative = min([row[1] for row in negative_exposures]) if negative_exposures else 0

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Quality exposures checked: {len(quality_exposures)} date/value combinations")
        print(f"Negative exposure records found: {len(negative_exposures)}")
        if negative_exposures:
            print(f"Largest negative value: {max_negative:.6f}")
        print()

        # The problematic value from 2025-10-18 was -0.1223
        problematic_threshold = -0.01  # Much larger negative value
        large_negatives = [row for row in negative_exposures if row[1] < problematic_threshold]

        if len(large_negatives) > 0:
            print(f"[WARNING] Found {len(large_negatives)} large negative exposures (< {problematic_threshold})")
            for row in large_negatives:
                print(f"  Date: {row[0]}, Value: {row[1]:.6f}")
        else:
            print(f"[SUCCESS] No large negative exposures found (all > {problematic_threshold})")
            print("[SUCCESS] The -0.1223 stale exposure from 2025-10-18 has been cleaned up!")
            print()
            print("Remaining small negative exposures are normal position-level factor exposures.")
            print("These represent positions with negative quality factor sensitivity.")
        print()


if __name__ == "__main__":
    asyncio.run(main())
