"""
Reusable async ticker validation utilities.

Shared between the batch processor and the command‑center style symbol
checks so we keep behaviour (synthetic/option filtering, provider fallbacks,
and caching) aligned across the codebase.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta, datetime
from typing import Iterable, Set, Tuple, Dict, Optional

from app.clients import market_data_factory, DataType
from app.core.datetime_utils import utc_now
from app.services.symbol_utils import (
    normalize_symbol,
    to_provider_symbol,
    should_skip_symbol,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = timedelta(hours=12)
_validation_cache: Dict[str, Tuple[bool, str, datetime]] = {}
_cache_lock = asyncio.Lock()
_semaphore = asyncio.Semaphore(5)  # avoid hammering providers


async def _fetch_with_provider(symbol_upper: str, days_back: int = 5) -> Tuple[bool, str]:
    """
    Query the configured market-data provider for a small historical slice.

    Returns a tuple (valid, message).
    """
    provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)
    if not provider:
        logger.warning("No stock provider configured; skipping validation for %s", symbol_upper)
        return True, "Validation skipped (no provider)"

    fetch_symbol = to_provider_symbol(symbol_upper)

    try:
        data = await provider.get_historical_prices(fetch_symbol, days=days_back)
        if data:
            return True, ""
        logger.info("Provider returned no data for symbol %s", symbol_upper)
        return False, "Symbol not found in provider data"
    except Exception as exc:
        # Treat provider failures as non-blocking warnings; the batch run can
        # still proceed and later phases will surface issues if the symbol is
        # truly invalid.
        logger.warning("Validation request failed for %s: %s", symbol_upper, exc)
        return True, f"Validation skipped: {exc}"


def _cache_lookup(symbol_upper: str) -> Optional[Tuple[bool, str]]:
    """Return cached validation result if still fresh."""
    entry = _validation_cache.get(symbol_upper)
    if not entry:
        return None

    valid, message, timestamp = entry
    if utc_now() - timestamp < _CACHE_TTL:
        return valid, message

    # Expired -> drop from cache
    del _validation_cache[symbol_upper]
    return None


async def validate_symbol(
    symbol: str,
    *,
    treat_synthetic_as_valid: bool = False,
    days_back: int = 5,
) -> Tuple[bool, str]:
    """
    Validate a single symbol against provider data with caching.

    Args:
        symbol: Input symbol (any casing)
        treat_synthetic_as_valid: When True, synthetic/private symbols return
            (True, reason) so legacy flows can allow them while surfacing a note.
        days_back: Historical window to request when checking providers.

    Returns:
        (is_valid, message) tuple.
    """
    symbol_upper = normalize_symbol(symbol)

    skip, reason = should_skip_symbol(symbol_upper)
    if skip:
        if treat_synthetic_as_valid and "Synthetic" in reason:
            return True, reason
        return False, reason

    cached = _cache_lookup(symbol_upper)
    if cached is not None:
        return cached

    async with _cache_lock:
        # Double-check cache now that we hold the lock
        cached = _cache_lookup(symbol_upper)
        if cached is not None:
            return cached

        async with _semaphore:
            valid, message = await _fetch_with_provider(symbol_upper, days_back=days_back)

        _validation_cache[symbol_upper] = (valid, message, utc_now())
        return valid, message


async def validate_symbols(
    symbols: Iterable[str],
    *,
    treat_synthetic_as_valid: bool = False,
    days_back: int = 5,
) -> Tuple[Set[str], Set[str]]:
    """
    Validate a collection of symbols concurrently.

    Returns:
        (valid_symbols, invalid_symbols)
    """
    ordered: list[str] = []
    seen: Set[str] = set()
    for symbol in symbols:
        normalized = normalize_symbol(symbol)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)

    if not ordered:
        return set(), set()

    tasks = [
        validate_symbol(
            symbol,
            treat_synthetic_as_valid=treat_synthetic_as_valid,
            days_back=days_back,
        )
        for symbol in ordered
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_symbols: Set[str] = set()
    invalid_symbols: Set[str] = set()

    for symbol, outcome in zip(ordered, results):
        if isinstance(outcome, Exception):
            logger.warning("Validation error for %s: %s", symbol, outcome)
            valid_symbols.add(symbol)  # Non-blocking failure
            continue

        is_valid, message = outcome
        if is_valid:
            valid_symbols.add(symbol)
        else:
            invalid_symbols.add(symbol)
            if message:
                logger.info("Skipping symbol %s: %s", symbol, message)

    return valid_symbols, invalid_symbols
