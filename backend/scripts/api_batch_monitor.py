#!/usr/bin/env python3
"""
API-Based Batch Monitoring Script

Trigger and monitor batch processing via REST API endpoints.
No SSH access required - works with both local and Railway deployments.

Usage:
    # Local development
    python scripts/api_batch_monitor.py

    # Railway production
    python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app

    # Specific portfolio
    python scripts/api_batch_monitor.py --portfolio-id <uuid>

    # Custom credentials
    python scripts/api_batch_monitor.py --email user@example.com --password yourpass
"""

import argparse
import sys
import time
from datetime import datetime
from typing import Optional

import requests


class BatchMonitor:
    """Monitor batch processing via API endpoints"""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.token: Optional[str] = None

    def authenticate(self) -> bool:
        """Authenticate and obtain JWT token"""
        print(f"🔐 Authenticating as {self.email}...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            self.token = data.get("access_token")

            if not self.token:
                print("❌ No access token in response")
                return False

            print("✅ Authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication failed: {e}")
            return False

    def get_headers(self) -> dict:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}

    def trigger_batch(self, portfolio_id: Optional[str] = None, force: bool = False) -> Optional[str]:
        """Trigger batch processing and return batch_run_id"""
        portfolio_str = portfolio_id if portfolio_id else "all portfolios"
        print(f"\n🚀 Triggering batch run for {portfolio_str}...")

        try:
            params = {}
            if portfolio_id:
                params["portfolio_id"] = portfolio_id
            if force:
                params["force"] = "true"

            response = requests.post(
                f"{self.base_url}/api/v1/admin/batch/run",
                headers=self.get_headers(),
                params=params,
                timeout=10
            )

            if response.status_code == 409:
                print("⚠️  Batch already running. Use --force to override.")
                return None

            response.raise_for_status()
            data = response.json()

            batch_run_id = data.get("batch_run_id")
            print(f"✅ Batch started: {batch_run_id}")
            print(f"📊 Poll URL: {data.get('poll_url')}")

            return batch_run_id

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to trigger batch: {e}")
            return None

    def get_status(self) -> Optional[dict]:
        """Get current batch status"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/batch/run/current",
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get status: {e}")
            return None

    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        mins, secs = divmod(int(seconds), 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    def monitor_progress(self, poll_interval: int = 3, max_duration: int = 600):
        """Monitor batch progress until completion"""
        print(f"\n📡 Monitoring progress (polling every {poll_interval}s)...")
        print("=" * 80)

        start_time = time.time()
        last_job = None
        last_progress = -1

        while True:
            # Check max duration
            elapsed = time.time() - start_time
            if elapsed > max_duration:
                print(f"\n⏰ Max monitoring duration ({max_duration}s) reached")
                break

            # Get current status
            status = self.get_status()
            if not status:
                print("\n❌ Failed to get status, stopping monitor")
                break

            # Check if idle (batch completed or not running)
            if status.get("status") == "idle":
                print("\n✅ Batch completed (status: idle)")
                break

            # Extract progress info
            batch_id = status.get("batch_run_id", "unknown")
            elapsed_sec = status.get("elapsed_seconds", 0)
            progress = status.get("progress_percent", 0)
            jobs = status.get("jobs", {})
            current_job = status.get("current_job", "")
            current_portfolio = status.get("current_portfolio", "")

            # Print update if progress changed or job changed
            if progress != last_progress or current_job != last_job:
                timestamp = datetime.now().strftime("%H:%M:%S")
                duration = self.format_duration(elapsed_sec)

                # Progress bar
                bar_length = 40
                filled = int(bar_length * progress / 100)
                bar = "█" * filled + "░" * (bar_length - filled)

                print(f"\r[{timestamp}] [{bar}] {progress:.1f}% | {duration} | "
                      f"{jobs.get('completed', 0)}/{jobs.get('total', 0)} jobs | "
                      f"{current_job[:40]}...", end="", flush=True)

                last_progress = progress
                last_job = current_job

            # Wait before next poll
            time.sleep(poll_interval)

        print("\n" + "=" * 80)

        # Show final summary
        final_status = self.get_status()
        if final_status and final_status.get("status") == "idle":
            print("\n📊 Batch Run Summary:")
            print(f"   Status: Completed")
            print(f"   Total Duration: {self.format_duration(elapsed)}")

    def run(self, portfolio_id: Optional[str] = None, force: bool = False,
            poll_interval: int = 3, max_duration: int = 600):
        """Run complete batch monitoring workflow"""
        # Authenticate
        if not self.authenticate():
            return False

        # Trigger batch
        batch_id = self.trigger_batch(portfolio_id, force)
        if not batch_id:
            return False

        # Monitor progress
        self.monitor_progress(poll_interval, max_duration)

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Trigger and monitor batch processing via API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local development (default)
  python scripts/api_batch_monitor.py

  # Railway production
  python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app

  # Specific portfolio
  python scripts/api_batch_monitor.py --portfolio-id 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe

  # Force run even if batch already running
  python scripts/api_batch_monitor.py --force

  # Custom polling interval
  python scripts/api_batch_monitor.py --poll-interval 5
        """
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of API server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--email",
        default="demo_individual@sigmasight.com",
        help="Email for authentication (default: demo_individual@sigmasight.com)"
    )
    parser.add_argument(
        "--password",
        default="demo12345",
        help="Password for authentication (default: demo12345)"
    )
    parser.add_argument(
        "--portfolio-id",
        help="Specific portfolio ID to process (default: all portfolios)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force batch run even if one is already running"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=3,
        help="Polling interval in seconds (default: 3)"
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=600,
        help="Maximum monitoring duration in seconds (default: 600)"
    )

    args = parser.parse_args()

    # Create monitor and run
    monitor = BatchMonitor(args.url, args.email, args.password)

    success = monitor.run(
        portfolio_id=args.portfolio_id,
        force=args.force,
        poll_interval=args.poll_interval,
        max_duration=args.max_duration
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
