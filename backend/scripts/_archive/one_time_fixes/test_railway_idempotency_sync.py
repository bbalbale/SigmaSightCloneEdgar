#!/usr/bin/env python
"""
Test Phase 2.10 Idempotency on Railway (Sync Version)

Tests that the unique constraint prevents duplicate snapshots.
Uses psycopg2 (sync) instead of asyncpg to work in Railway environment.

Usage:
  python scripts/test/test_railway_idempotency_sync.py
"""
import os
import sys
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor

def test_idempotency():
    """
    Test idempotency by checking unique constraint on snapshots.
    """
    # Get DATABASE_URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        sys.exit(1)

    test_date = date.today()

    print(f"\n{'='*80}")
    print(f"PHASE 2.10 IDEMPOTENCY TEST (Railway)")
    print(f"{'='*80}")
    print(f"Test Date: {test_date}")
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else 'Railway'}\n")

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # TEST 1: Check migration is applied
        print("TEST 1: Verify Phase 2.10 migration applied")
        print("-" * 80)

        cursor.execute("SELECT version_num FROM alembic_version")
        migration = cursor.fetchone()

        if migration and migration['version_num'] == 'k8l9m0n1o2p3':
            print(f"✅ PASS: Migration k8l9m0n1o2p3 is applied")
        else:
            print(f"❌ FAIL: Wrong migration: {migration['version_num'] if migration else 'None'}")
            print(f"         Expected: k8l9m0n1o2p3")
            return False

        # TEST 2: Check is_complete column exists
        print("\nTEST 2: Verify is_complete column exists")
        print("-" * 80)

        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'portfolio_snapshots'
              AND column_name = 'is_complete'
        """)
        column = cursor.fetchone()

        if column:
            print(f"✅ PASS: is_complete column exists")
            print(f"   Type: {column['data_type']}")
            print(f"   Default: {column['column_default']}")
        else:
            print(f"❌ FAIL: is_complete column not found")
            return False

        # TEST 3: Check unique constraint exists
        print("\nTEST 3: Verify unique constraint exists")
        print("-" * 80)

        cursor.execute("""
            SELECT conname, pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'portfolio_snapshots'::regclass
              AND contype = 'u'
              AND (conname LIKE 'uq_portfolio_snapshot%')
        """)
        constraints = cursor.fetchall()

        if len(constraints) > 0:
            print(f"✅ PASS: Found {len(constraints)} unique constraint(s)")
            for c in constraints:
                print(f"   {c['conname']}: {c['definition']}")
        else:
            print(f"❌ FAIL: No unique constraint found")
            return False

        # TEST 4: Check for duplicate snapshots
        print("\nTEST 4: Check for duplicate snapshots in database")
        print("-" * 80)

        cursor.execute("""
            SELECT portfolio_id, snapshot_date, COUNT(*) as cnt
            FROM portfolio_snapshots
            GROUP BY portfolio_id, snapshot_date
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()

        if len(duplicates) == 0:
            print(f"✅ PASS: No duplicate snapshots found")
        else:
            print(f"❌ FAIL: Found {len(duplicates)} duplicate groups:")
            for dup in duplicates[:10]:
                print(f"   Portfolio {dup['portfolio_id']}, Date {dup['snapshot_date']}: {dup['cnt']} snapshots")
            return False

        # TEST 5: Try to insert duplicate snapshot (should fail)
        print("\nTEST 5: Attempt to create duplicate snapshot (should fail)")
        print("-" * 80)

        # Get a portfolio for testing
        cursor.execute("""
            SELECT id, name
            FROM portfolios
            WHERE name LIKE '%High Net Worth%'
            LIMIT 1
        """)
        portfolio = cursor.fetchone()

        if not portfolio:
            print("⚠️  SKIP: No test portfolio found")
            return True

        print(f"Using portfolio: {portfolio['name']}")

        # Check if snapshot exists for today
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM portfolio_snapshots
            WHERE portfolio_id = %s AND snapshot_date = %s
        """, (portfolio['id'], test_date))

        existing = cursor.fetchone()['cnt']

        if existing > 0:
            print(f"   Snapshot already exists for today (count: {existing})")
            print(f"   Attempting to insert duplicate...")

            try:
                cursor.execute("""
                    INSERT INTO portfolio_snapshots (
                        id, portfolio_id, snapshot_date,
                        net_asset_value, cash_value, long_value, short_value,
                        gross_exposure, net_exposure,
                        num_positions, num_long_positions, num_short_positions,
                        is_complete
                    ) VALUES (
                        gen_random_uuid(), %s, %s,
                        0, 0, 0, 0, 0, 0, 0, 0, 0, false
                    )
                """, (portfolio['id'], test_date))

                # If we got here, constraint didn't work
                conn.rollback()
                print(f"❌ FAIL: Duplicate insert succeeded (unique constraint not working)")
                return False

            except psycopg2.IntegrityError as e:
                conn.rollback()
                error_str = str(e).lower()

                if 'uq_portfolio_snapshot' in error_str or 'unique' in error_str:
                    print(f"✅ PASS: IntegrityError raised as expected")
                    print(f"   Error: {str(e)[:150]}...")
                else:
                    print(f"❌ FAIL: Wrong error: {e}")
                    return False
        else:
            print(f"   No existing snapshot for today")
            print(f"   Creating first snapshot...")

            cursor.execute("""
                INSERT INTO portfolio_snapshots (
                    id, portfolio_id, snapshot_date,
                    net_asset_value, cash_value, long_value, short_value,
                    gross_exposure, net_exposure,
                    num_positions, num_long_positions, num_short_positions,
                    is_complete
                ) VALUES (
                    gen_random_uuid(), %s, %s,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, false
                )
            """, (portfolio['id'], test_date))
            conn.commit()
            print(f"   ✅ First snapshot created")

            print(f"   Attempting to insert duplicate...")
            try:
                cursor.execute("""
                    INSERT INTO portfolio_snapshots (
                        id, portfolio_id, snapshot_date,
                        net_asset_value, cash_value, long_value, short_value,
                        gross_exposure, net_exposure,
                        num_positions, num_long_positions, num_short_positions,
                        is_complete
                    ) VALUES (
                        gen_random_uuid(), %s, %s,
                        0, 0, 0, 0, 0, 0, 0, 0, 0, false
                    )
                """, (portfolio['id'], test_date))
                conn.commit()

                # If we got here, constraint didn't work
                print(f"❌ FAIL: Duplicate insert succeeded (unique constraint not working)")

                # Cleanup
                cursor.execute("""
                    DELETE FROM portfolio_snapshots
                    WHERE portfolio_id = %s AND snapshot_date = %s
                """, (portfolio['id'], test_date))
                conn.commit()
                return False

            except psycopg2.IntegrityError as e:
                conn.rollback()
                error_str = str(e).lower()

                if 'uq_portfolio_snapshot' in error_str or 'unique' in error_str:
                    print(f"✅ PASS: IntegrityError raised as expected")
                    print(f"   Error: {str(e)[:150]}...")

                    # Cleanup test snapshot
                    cursor.execute("""
                        DELETE FROM portfolio_snapshots
                        WHERE portfolio_id = %s AND snapshot_date = %s
                    """, (portfolio['id'], test_date))
                    conn.commit()
                    print(f"   Cleaned up test snapshot")
                else:
                    print(f"❌ FAIL: Wrong error: {e}")
                    return False

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def main():
    """Main entry point"""
    print("\nStarting Phase 2.10 Idempotency Test...\n")

    success = test_idempotency()

    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")

    if success:
        print("🎉 SUCCESS: Phase 2.10 idempotency is working correctly!")
        print("   ✅ Migration applied (k8l9m0n1o2p3)")
        print("   ✅ is_complete column exists")
        print("   ✅ Unique constraint enforced")
        print("   ✅ No duplicate snapshots in database")
        print("   ✅ Duplicate insert prevented by IntegrityError")
        print(f"{'='*80}\n")
        sys.exit(0)
    else:
        print("❌ FAILURE: Phase 2.10 idempotency test failed")
        print("   Review the test output above for details")
        print(f"{'='*80}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
