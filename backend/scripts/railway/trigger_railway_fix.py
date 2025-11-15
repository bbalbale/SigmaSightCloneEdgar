#!/usr/bin/env python
"""
Trigger the full Railway data-fix workflow via HTTP.

This script logs in with demo credentials (override via CLI flags), calls the
`/admin/fix/fix-all` endpoint, and prints a detailed summary of each phase so
we can confirm clearing, seeding, and batch processing actually ran.
"""
import argparse
import sys
from typing import Dict, Any

import requests

DEFAULT_BASE_URL = "https://sigmasight-be-production.up.railway.app/api/v1"
DEFAULT_EMAIL = "demo_hnw@sigmasight.com"
DEFAULT_PASSWORD = "demo12345"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger Railway data fix via HTTP API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend base URL (default: %(default)s)")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Login email (default: %(default)s)")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Login password (default: %(default)s)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Timeout in seconds for the fix-all request (default: %(default)s)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date for batch backfill (YYYY-MM-DD), e.g., 2025-07-01",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional end date for batch processing (YYYY-MM-DD), defaults to today, e.g., 2025-11-12",
    )
    return parser.parse_args()


def login(base_url: str, email: str, password: str) -> str:
    print("\n1. Authenticating...")
    resp = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"ERROR: Login failed ({resp.status_code})")
        print(resp.text)
        sys.exit(1)

    token = resp.json().get("access_token")
    if not token:
        print("ERROR: Login response did not include an access_token")
        sys.exit(1)

    print("[OK] Authentication successful")
    return token


def trigger_fix(base_url: str, token: str, timeout: int, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    print("\n2. Triggering complete data fix...")
    if start_date or end_date:
        print(f"   Start Date: {start_date or 'auto-detect'}")
        print(f"   End Date: {end_date or 'today'}")

    headers = {"Authorization": f"Bearer {token}"}
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    # Start the job
    resp = requests.post(f"{base_url}/admin/fix/fix-all", headers=headers, params=params, timeout=30)

    if resp.status_code != 200:
        print(f"ERROR: Fix failed to start ({resp.status_code})")
        print(resp.text)
        sys.exit(1)

    payload = resp.json()
    if not payload.get("success"):
        print("ERROR: Fix endpoint returned success=false")
        print(payload)
        sys.exit(1)

    job_id = payload.get("job_id")
    print(f"[OK] Fix job started: {job_id}")
    print(f"\n3. Polling for job status (this can take 10-20 minutes)...")

    # Poll for job status
    import time
    max_wait_seconds = timeout
    poll_interval = 5  # Check every 5 seconds
    elapsed = 0

    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            status_resp = requests.get(
                f"{base_url}/admin/fix/jobs/{job_id}",
                headers=headers,
                timeout=10
            )

            if status_resp.status_code != 200:
                print(f"\nWARNING: Status check failed ({status_resp.status_code})")
                continue

            job_status = status_resp.json()
            status = job_status.get("status")
            progress = job_status.get("progress")

            # Show progress
            if progress:
                print(f"\r   Progress: {progress} (elapsed: {elapsed}s)", end="", flush=True)

            if status == "completed":
                print(f"\n[OK] Fix job completed successfully!")
                return job_status.get("result", {})

            elif status == "failed":
                error = job_status.get("error")
                print(f"\n[ERROR] Fix job failed: {error}")
                sys.exit(1)

        except requests.exceptions.RequestException as e:
            print(f"\nWARNING: Status check request failed: {e}")
            continue

    print(f"\n[ERROR] Job did not complete within {max_wait_seconds}s timeout")
    print(f"   Job ID: {job_id}")
    print(f"   Check status manually: {base_url}/admin/fix/jobs/{job_id}")
    sys.exit(1)


def print_summary(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 80)
    print("RAILWAY DATA FIX SUMMARY")
    print("=" * 80)

    clear_details = result.get("step1_clear", {})
    print("\nStep 1 - Clearing analytics tables")
    print(f"  Total cleared: {clear_details.get('total_deleted', 0)}")

    # Print per-table stats (all keys except special ones)
    special_keys = {'total_deleted', 'soft_deleted_positions', 'duplicate_positions', 'equity_resets'}
    table_stats = {k: v for k, v in clear_details.items() if k not in special_keys}
    if table_stats:
        for name, count in table_stats.items():
            print(f"    • {name}: {count}")

    print(f"  Soft-deleted positions removed: {clear_details.get('soft_deleted_positions', 0)}")
    print(f"  Duplicate positions removed: {clear_details.get('duplicate_positions', 0)}")
    print(f"  Equity balances reset: {clear_details.get('equity_resets', 0)}")

    seed_details = result.get("step2_seed", {})
    print("\nStep 2 - Seeding portfolios")
    total_portfolios = seed_details.get("total_portfolios")
    if total_portfolios is not None:
        print(f"  Total portfolios: {total_portfolios}")
    else:
        print("  (warning: seed step did not report portfolio count)")

    batch_details = result.get("step3_batch", {})
    print("\nStep 3 - Batch processing")
    if batch_details:
        print(f"  Message: {batch_details.get('message', 'Success')}")
        dates = batch_details.get("dates_processed")
        if dates:
            print(f"  Dates processed: {dates}")
    else:
        print("  (warning: batch step did not return details)")

    print("\nVerification checklist:")
    print("  1. Visit https://sigmasight-fe-production.up.railway.app")
    print("  2. Login with demo credentials")
    print("  3. Confirm holdings + P&L look correct (Demo HNW: 39 positions)")


def main():
    args = parse_args()
    print("=" * 80)
    print(f"RAILWAY PRODUCTION DATA FIX TRIGGER\nTarget: {args.base_url}")
    if args.start_date or args.end_date:
        print(f"Batch Date Range: {args.start_date or 'auto'} to {args.end_date or 'today'}")
    print("=" * 80)

    token = login(args.base_url, args.email, args.password)
    result = trigger_fix(args.base_url, token, args.timeout, args.start_date, args.end_date)
    print_summary(result)


if __name__ == "__main__":
    main()
