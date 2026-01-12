"""
V2 Batch Architecture

Two-cron system with instant onboarding:
- Symbol Batch (9:00 PM ET): Fetches prices and calculates factors for all symbols
- Portfolio Refresh (9:30 PM ET): Creates snapshots for portfolios using cached data
- Symbol Onboarding (instant): Processes new symbols on-demand

Key Benefits:
- O(symbols) instead of O(users x symbols x dates)
- Instant onboarding (< 5 seconds vs 15-30 minutes)
- Separate failure domains for symbol vs portfolio processing
"""

from app.batch.v2.symbol_batch_runner import (
    run_symbol_batch,
    get_last_symbol_batch_date,
)
from app.batch.v2.portfolio_refresh_runner import (
    run_portfolio_refresh,
    get_last_portfolio_refresh_date,
)
from app.batch.v2.symbol_onboarding import (
    symbol_onboarding_queue,
    SymbolOnboardingQueue,
    OnboardingJob,
)

__all__ = [
    # Symbol Batch
    "run_symbol_batch",
    "get_last_symbol_batch_date",
    # Portfolio Refresh
    "run_portfolio_refresh",
    "get_last_portfolio_refresh_date",
    # Symbol Onboarding
    "symbol_onboarding_queue",
    "SymbolOnboardingQueue",
    "OnboardingJob",
]
