"""
Utility functions for working with ticker symbols across the application.

Centralizes handling of synthetic/private symbols, option contracts,
and provider-specific normalization so we keep behaviour consistent
between the batch processor, position workflows, and the legacy command
center validation.
"""
from __future__ import annotations

from typing import Tuple

# Synthetic/placeholder symbols that should never trigger market-data calls.
SYNTHETIC_SYMBOLS = {
    "HOME_EQUITY",
    "TREASURY_BILLS",
    "CRYPTO_BTC_ETH",
    "TWO_SIGMA_FUND",
    "A16Z_VC_FUND",
    "STARWOOD_REIT",
    "BX_PRIVATE_EQUITY",
    "RENTAL_SFH",
    "ART_COLLECTIBLES",
    "RENTAL_CONDO",
    "MONEY_MARKET",
}

# Prefixes we use for private or synthetic positions (fund-of funds, etc.).
SYNTHETIC_PREFIXES = ("FO_", "EQ")


def normalize_symbol(symbol: str) -> str:
    """Return the canonical uppercase ticker representation."""
    return symbol.strip().upper() if symbol else ""


def to_provider_symbol(symbol_upper: str) -> str:
    """
    Convert our canonical symbol into the provider-friendly variant.

    YFinance (and many other providers) expect dots to be replaced by
    hyphens (e.g., BRK.B -> BRK-B). Keep everything uppercase to match
    cache keys and provider expectations.
    """
    return symbol_upper.replace(".", "-")


def is_synthetic_symbol(symbol: str) -> bool:
    """
    Return True for any symbol representing a private/synthetic holding.
    """
    upper = normalize_symbol(symbol)
    if not upper:
        return False

    if upper in SYNTHETIC_SYMBOLS:
        return True

    return any(upper.startswith(prefix) for prefix in SYNTHETIC_PREFIXES)


def is_option_symbol(symbol: str) -> bool:
    """
    Detect OCC-style option contracts (e.g., NVDA251017C00800000).

    Format: <root><YYMMDD><C|P><strike padded to 8 digits>
    """
    upper = normalize_symbol(symbol)
    if len(upper) < 15:
        return False

    body = upper[-15:]
    return (
        body[:6].isdigit()
        and body[6] in {"C", "P"}
        and body[7:].isdigit()
    )


def should_skip_symbol(symbol: str) -> Tuple[bool, str]:
    """
    Determine whether the symbol should be skipped before hitting providers.

    Returns:
        (skip: bool, reason: str)
    """
    upper = normalize_symbol(symbol)
    if not upper:
        return True, "Empty symbol"

    if is_synthetic_symbol(upper):
        return True, "Synthetic/private symbol"

    if is_option_symbol(upper):
        return True, "Option contract"

    return False, ""
