"""Rate limiter implementation for API calls."""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """Token bucket rate limiter implementation.
    
    This implements a token bucket algorithm for rate limiting API calls.
    Tokens are added at a fixed rate, and each API call consumes one token.
    If no tokens are available, the caller must wait.
    """
    
    capacity: int  # Maximum number of tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    
    def __post_init__(self):
        """Initialize with full bucket."""
        self.tokens = float(self.capacity)
        self.last_refill = time.time()
    
    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
            
        Returns:
            float: Time waited in seconds
        """
        async with self._lock:
            wait_time = 0.0
            
            while True:
                # Refill tokens based on time elapsed
                now = time.time()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.capacity,
                    self.tokens + (elapsed * self.refill_rate)
                )
                self.last_refill = now
                
                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return wait_time
                
                # Calculate wait time needed
                tokens_needed = tokens - self.tokens
                wait_needed = tokens_needed / self.refill_rate
                
                # Wait for tokens to refill
                await asyncio.sleep(wait_needed)
                wait_time += wait_needed


class PolygonRateLimiter:
    """Rate limiter specifically for Polygon.io API.
    
    Plan limits:
    - Free tier: 5 API calls per minute
    - Starter: 100 API calls per minute
    - Developer: 1,000 API calls per minute
    - Advanced: 10,000 API calls per minute
    """
    
    # Plan configurations
    PLANS = {
        'free': 5,
        'starter': 100,
        'developer': 1000,
        'advanced': 10000
    }
    
    def __init__(self, plan: str = 'free', requests_per_minute: int = None):
        """Initialize rate limiter.
        
        Args:
            plan: Plan name ('free', 'starter', 'developer', 'advanced')
            requests_per_minute: Override API rate limit (optional)
        """
        # Use provided rate or get from plan
        if requests_per_minute is None:
            requests_per_minute = self.PLANS.get(plan, self.PLANS['free'])
        
        self.plan = plan
        self.requests_per_minute = requests_per_minute
        self.bucket = TokenBucket(
            capacity=requests_per_minute,
            refill_rate=requests_per_minute / 60  # Convert to per-second rate
        )
        self.backoff = ExponentialBackoff()
        logger.info(f"Initialized Polygon rate limiter: {plan} plan ({requests_per_minute} req/min)")
        self._request_count = 0
        self._start_time = time.time()
    
    async def acquire(self) -> None:
        """Wait if necessary to respect rate limits."""
        wait_time = await self.bucket.acquire()
        self._request_count += 1
        
        if wait_time > 0:
            elapsed = time.time() - self._start_time
            print(f"Rate limit: waited {wait_time:.2f}s (request #{self._request_count}, "
                  f"avg rate: {self._request_count/elapsed:.2f} req/s)")
    
    @property
    def stats(self) -> dict:
        """Get rate limiter statistics."""
        elapsed = time.time() - self._start_time
        return {
            "total_requests": self._request_count,
            "elapsed_time": elapsed,
            "average_rate": self._request_count / elapsed if elapsed > 0 else 0,
            "current_tokens": self.bucket.tokens
        }


class ExponentialBackoff:
    """Exponential backoff for handling rate limit errors."""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 300.0,  # 5 minutes
        factor: float = 2.0
    ):
        """Initialize backoff strategy.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            factor: Multiplication factor for each retry
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.factor = factor
        self.attempt = 0
    
    async def wait(self) -> float:
        """Wait with exponential backoff.
        
        Returns:
            float: Time waited in seconds
        """
        if self.attempt == 0:
            self.attempt += 1
            return 0.0
        
        # Calculate delay: base * (factor ^ attempt)
        delay = min(
            self.base_delay * (self.factor ** (self.attempt - 1)),
            self.max_delay
        )
        
        print(f"Backoff: waiting {delay:.1f}s (attempt #{self.attempt})")
        await asyncio.sleep(delay)
        self.attempt += 1
        
        return delay
    
    def reset(self):
        """Reset backoff to initial state."""
        self.attempt = 0


class FMPQuotaTracker:
    """Daily quota tracker for FMP API (250 calls/day limit)"""

    def __init__(self, daily_limit: int = 250):
        """Initialize FMP quota tracker

        Args:
            daily_limit: Maximum number of API calls per day
        """
        self.daily_limit = daily_limit
        self._calls_today = 0
        self._last_reset = datetime.now().date()
        self._lock = asyncio.Lock()

        logger.info(f"Initialized FMP quota tracker: {daily_limit} calls/day")

    async def can_make_request(self) -> bool:
        """Check if we can make another FMP request without exceeding daily quota

        Returns:
            True if under quota, False if quota exceeded
        """
        async with self._lock:
            # Reset counter if it's a new day
            today = datetime.now().date()
            if today > self._last_reset:
                logger.info(f"FMP quota reset: New day ({today}), resetting counter from {self._calls_today}")
                self._calls_today = 0
                self._last_reset = today

            return self._calls_today < self.daily_limit

    async def record_request(self) -> None:
        """Record an FMP API request"""
        async with self._lock:
            # Reset counter if it's a new day
            today = datetime.now().date()
            if today > self._last_reset:
                self._calls_today = 0
                self._last_reset = today

            self._calls_today += 1
            remaining = self.daily_limit - self._calls_today

            if remaining <= 10:
                logger.warning(f"FMP quota warning: Only {remaining} calls remaining today")
            elif self._calls_today % 50 == 0:
                logger.info(f"FMP quota update: {self._calls_today}/{self.daily_limit} calls used today")

    async def acquire(self) -> bool:
        """Try to acquire permission for an FMP request

        Returns:
            True if request allowed, False if quota exceeded
        """
        if not await self.can_make_request():
            logger.error(f"FMP daily quota exceeded: {self._calls_today}/{self.daily_limit}")
            return False

        await self.record_request()
        return True

    @property
    def stats(self) -> dict:
        """Get quota statistics"""
        return {
            "calls_today": self._calls_today,
            "daily_limit": self.daily_limit,
            "remaining": self.daily_limit - self._calls_today,
            "last_reset": str(self._last_reset),
            "quota_used_percent": (self._calls_today / self.daily_limit) * 100
        }


# Import settings at module level to get plan configuration
from app.config import settings

# Global rate limiter instance for Polygon API
polygon_rate_limiter = PolygonRateLimiter(plan=settings.POLYGON_PLAN)

# Global quota tracker for FMP API (250 calls per day)
fmp_quota_tracker = FMPQuotaTracker(daily_limit=250)
