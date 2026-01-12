"""
Railway Concurrency Test Script

Tests whether Railway can handle concurrent batch workers + API traffic,
simulating what V2 batch architecture will require:
- 3 concurrent "batch workers" (symbol batch, portfolio refresh, onboarding)
- 20+ concurrent user API requests
- Sustained load over 30-60 seconds

Usage:
    # Test against Railway production
    uv run python scripts/test_railway_concurrency.py --url https://sigmasight-be-production.up.railway.app

    # Test against local
    uv run python scripts/test_railway_concurrency.py --url http://localhost:8000

    # With custom concurrency
    uv run python scripts/test_railway_concurrency.py --batch-workers 5 --api-users 50

Requirements:
    pip install aiohttp  (already in project deps)
"""

import asyncio
import argparse
import time
import sys
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)


@dataclass
class TestConfig:
    base_url: str
    token: Optional[str] = None
    batch_workers: int = 3
    api_users: int = 20
    batch_iterations: int = 10
    api_iterations: int = 5
    delay_between_requests: float = 0.1


@dataclass
class TestResults:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    errors: list = field(default_factory=list)
    latencies: list = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def requests_per_second(self) -> float:
        return self.total_requests / self.duration if self.duration > 0 else 0

    @property
    def avg_latency_ms(self) -> float:
        return (sum(self.latencies) / len(self.latencies) * 1000) if self.latencies else 0

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx] * 1000

    @property
    def max_latency_ms(self) -> float:
        return max(self.latencies) * 1000 if self.latencies else 0

    @property
    def error_rate(self) -> float:
        return (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0


async def make_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    results: TestResults,
    headers: dict = None,
    params: dict = None,
    name: str = ""
) -> bool:
    """Make a single HTTP request and record results."""
    start = time.time()
    try:
        async with session.request(method, url, headers=headers, params=params, timeout=30) as resp:
            await resp.text()  # Consume response
            latency = time.time() - start
            results.latencies.append(latency)
            results.total_requests += 1

            if resp.status < 400:
                results.successful_requests += 1
                return True
            else:
                results.failed_requests += 1
                error_msg = f"{name}: HTTP {resp.status} on {url}"
                if len(results.errors) < 20:  # Cap error collection
                    results.errors.append(error_msg)
                return False

    except asyncio.TimeoutError:
        results.total_requests += 1
        results.failed_requests += 1
        results.errors.append(f"{name}: Timeout on {url}")
        return False
    except Exception as e:
        results.total_requests += 1
        results.failed_requests += 1
        results.errors.append(f"{name}: {type(e).__name__}: {str(e)[:100]}")
        return False


async def simulate_batch_worker(
    session: aiohttp.ClientSession,
    config: TestConfig,
    results: TestResults,
    worker_id: int
):
    """
    Simulate a batch worker doing DB-heavy operations.

    This mimics what symbol batch or portfolio refresh would do:
    - Multiple sequential requests
    - Some delay between (simulating processing)
    - Heavier endpoints that touch the database
    """
    worker_name = f"BatchWorker-{worker_id}"
    headers = {"Authorization": f"Bearer {config.token}"} if config.token else {}

    # Endpoints that simulate batch work (DB reads)
    batch_endpoints = [
        "/api/v1/health",  # Light - health check
        "/api/v1/data/prices/quotes?symbols=AAPL,GOOGL,MSFT,AMZN,NVDA",  # Medium - price lookup
    ]

    # Add authenticated endpoints if we have a token
    if config.token:
        batch_endpoints.extend([
            "/api/v1/portfolios",  # Medium - list portfolios
            "/api/v1/auth/me",  # Light - auth check
        ])

    for i in range(config.batch_iterations):
        for endpoint in batch_endpoints:
            url = f"{config.base_url}{endpoint}"
            await make_request(session, "GET", url, results, headers=headers, name=worker_name)
            await asyncio.sleep(config.delay_between_requests)

    print(f"  {worker_name} completed {config.batch_iterations} iterations")


async def simulate_api_user(
    session: aiohttp.ClientSession,
    config: TestConfig,
    results: TestResults,
    user_id: int
):
    """
    Simulate a regular user making API calls.

    This mimics frontend traffic during batch operations.
    """
    user_name = f"APIUser-{user_id}"
    headers = {"Authorization": f"Bearer {config.token}"} if config.token else {}

    # Typical user endpoints
    user_endpoints = [
        "/api/v1/health",
    ]

    if config.token:
        user_endpoints.extend([
            "/api/v1/auth/me",
            "/api/v1/portfolios",
        ])

    for i in range(config.api_iterations):
        for endpoint in user_endpoints:
            url = f"{config.base_url}{endpoint}"
            await make_request(session, "GET", url, results, headers=headers, name=user_name)
            # Users have variable timing
            await asyncio.sleep(config.delay_between_requests * (0.5 + user_id % 3 * 0.5))

    # Only print every 5th user to reduce noise
    if user_id % 5 == 0:
        print(f"  {user_name} completed")


async def run_health_check(session: aiohttp.ClientSession, config: TestConfig) -> bool:
    """Verify the server is reachable before running tests."""
    try:
        async with session.get(f"{config.base_url}/api/v1/health", timeout=10) as resp:
            if resp.status == 200:
                print(f"Health check passed: {config.base_url}")
                return True
            else:
                print(f"Health check failed: HTTP {resp.status}")
                return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


async def run_concurrency_test(config: TestConfig) -> TestResults:
    """
    Run the full concurrency test.

    Simulates V2 batch architecture load:
    - Multiple batch workers running simultaneously
    - Concurrent user API traffic
    - Sustained over time
    """
    results = TestResults()

    # Configure connection pooling similar to what Railway would see
    connector = aiohttp.TCPConnector(
        limit=100,  # Max concurrent connections
        limit_per_host=50,  # Max per host
        ttl_dns_cache=300,
    )

    timeout = aiohttp.ClientTimeout(total=60, connect=10)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Health check first
        print("\n[1/3] Running health check...")
        if not await run_health_check(session, config):
            print("ERROR: Server not reachable. Aborting test.")
            return results

        # Build task list
        print(f"\n[2/3] Starting concurrency test...")
        print(f"  - {config.batch_workers} batch workers")
        print(f"  - {config.api_users} concurrent API users")
        print(f"  - {config.batch_iterations} iterations per batch worker")
        print(f"  - {config.api_iterations} iterations per API user")

        tasks = []

        # Batch workers (simulate symbol batch, portfolio refresh, onboarding)
        for i in range(config.batch_workers):
            tasks.append(simulate_batch_worker(session, config, results, i))

        # API users (simulate normal frontend traffic)
        for i in range(config.api_users):
            tasks.append(simulate_api_user(session, config, results, i))

        # Run all tasks concurrently
        results.start_time = time.time()
        print(f"\n[3/3] Running {len(tasks)} concurrent tasks...\n")

        await asyncio.gather(*tasks, return_exceptions=True)

        results.end_time = time.time()

    return results


def print_results(results: TestResults, config: TestConfig):
    """Print formatted test results."""
    print("\n" + "=" * 60)
    print("RAILWAY CONCURRENCY TEST RESULTS")
    print("=" * 60)

    print(f"\nConfiguration:")
    print(f"  Target URL:      {config.base_url}")
    print(f"  Batch Workers:   {config.batch_workers}")
    print(f"  API Users:       {config.api_users}")
    print(f"  Authenticated:   {'Yes' if config.token else 'No (limited endpoints)'}")

    print(f"\nResults:")
    print(f"  Duration:        {results.duration:.2f} seconds")
    print(f"  Total Requests:  {results.total_requests}")
    print(f"  Successful:      {results.successful_requests}")
    print(f"  Failed:          {results.failed_requests}")
    print(f"  Error Rate:      {results.error_rate:.2f}%")

    print(f"\nPerformance:")
    print(f"  Requests/sec:    {results.requests_per_second:.2f}")
    print(f"  Avg Latency:     {results.avg_latency_ms:.2f} ms")
    print(f"  P95 Latency:     {results.p95_latency_ms:.2f} ms")
    print(f"  Max Latency:     {results.max_latency_ms:.2f} ms")

    # Assessment
    print(f"\nAssessment:")
    issues = []

    if results.error_rate > 5:
        issues.append(f"HIGH ERROR RATE ({results.error_rate:.1f}%) - Railway may be overloaded")
    elif results.error_rate > 1:
        issues.append(f"Elevated error rate ({results.error_rate:.1f}%) - monitor closely")

    if results.p95_latency_ms > 5000:
        issues.append(f"HIGH P95 LATENCY ({results.p95_latency_ms:.0f}ms) - requests queueing")
    elif results.p95_latency_ms > 2000:
        issues.append(f"Elevated P95 latency ({results.p95_latency_ms:.0f}ms)")

    if results.max_latency_ms > 30000:
        issues.append(f"TIMEOUT-LEVEL MAX LATENCY ({results.max_latency_ms:.0f}ms)")

    if issues:
        print("  CONCERNS:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  PASSED - Railway handles this concurrency level well")
        print(f"    - Error rate under 1%")
        print(f"    - P95 latency acceptable")
        print(f"    - V2 batch architecture should work")

    # Show errors if any
    if results.errors:
        print(f"\nSample Errors (first {min(10, len(results.errors))}):")
        for error in results.errors[:10]:
            print(f"    - {error}")

    print("\n" + "=" * 60)


def get_token_interactively() -> Optional[str]:
    """Prompt for auth token if user wants authenticated testing."""
    print("\nAuthenticated testing allows testing more endpoints (portfolios, analytics).")
    print("To get a token: Login to the app, open DevTools > Network, find an API call,")
    print("and copy the Authorization header value (without 'Bearer ').\n")

    response = input("Do you have an auth token to test with? [y/N]: ").strip().lower()
    if response == 'y':
        token = input("Paste token: ").strip()
        if token.startswith("Bearer "):
            token = token[7:]
        return token if token else None
    return None


async def main():
    parser = argparse.ArgumentParser(
        description="Test Railway concurrency for V2 batch architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test Railway production
  python scripts/test_railway_concurrency.py --url https://sigmasight-be-production.up.railway.app

  # Test local with more load
  python scripts/test_railway_concurrency.py --url http://localhost:8000 --batch-workers 5 --api-users 50

  # Quick test
  python scripts/test_railway_concurrency.py --url http://localhost:8000 --batch-workers 2 --api-users 10
        """
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL to test (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Auth token for authenticated endpoints (optional)"
    )
    parser.add_argument(
        "--batch-workers",
        type=int,
        default=3,
        help="Number of simulated batch workers (default: 3)"
    )
    parser.add_argument(
        "--api-users",
        type=int,
        default=20,
        help="Number of simulated concurrent API users (default: 20)"
    )
    parser.add_argument(
        "--batch-iterations",
        type=int,
        default=10,
        help="Iterations per batch worker (default: 10)"
    )
    parser.add_argument(
        "--api-iterations",
        type=int,
        default=5,
        help="Iterations per API user (default: 5)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for auth token interactively"
    )

    args = parser.parse_args()

    # Get token
    token = args.token
    if args.interactive and not token:
        token = get_token_interactively()

    config = TestConfig(
        base_url=args.url.rstrip("/"),
        token=token,
        batch_workers=args.batch_workers,
        api_users=args.api_users,
        batch_iterations=args.batch_iterations,
        api_iterations=args.api_iterations,
    )

    print("\n" + "=" * 60)
    print("RAILWAY CONCURRENCY TEST")
    print(f"Testing: {config.base_url}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    results = await run_concurrency_test(config)
    print_results(results, config)

    # Exit with error code if test failed
    if results.error_rate > 5:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
