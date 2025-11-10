#!/usr/bin/env python
"""
Update seed_demo_portfolios.py with June 30, 2025 prices.

This script reads the current entry prices from the database and updates
the seed file to match.
"""

import re
from pathlib import Path
from decimal import Decimal

# June 30, 2025 prices from database
JUNE30_PRICES = {
    "AAPL": "204.94",
    "AMD": "141.90",
    "AMZN": "219.39",
    "ASML": "797.95",
    "AVGO": "275.18",
    "BIL": "90.18",
    "BND": "72.44",
    "BRK-B": "485.77",
    "C": "84.06",
    "COST": "987.17",
    "DJP": "33.98",
    "F": "10.58",
    "FCNTX": "23.33",
    "FMAGX": "15.67",
    "FXNAX": "10.34",
    "GE": "256.70",
    "GLD": "304.83",
    "GOOGL": "176.07",
    "HD": "364.57",
    "IGV": "109.50",
    "JEPQ": "52.21",
    "JNJ": "151.64",
    "JPM": "287.12",
    "LULU": "237.58",
    "META": "737.59",
    "MSFT": "496.59",
    "NEE": "68.89",
    "NFLX": "1339.13",
    "NVDA": "157.98",
    "PG": "157.14",
    "PTON": "6.94",
    "QQQ": "551.00",
    "ROKU": "87.89",
    "SCHD": "26.25",
    "SHOP": "115.35",
    "SMH": "278.88",
    "SPY": "616.14",
    "TSLA": "317.66",
    "UNH": "310.01",
    "V": "354.43",
    "VNQ": "88.22",
    "VTI": "303.09",
    "VTIAX": "36.92",
    "XLK": "252.90",
    "XLY": "216.95",
    "XOM": "106.81",
    "ZM": "77.98",
}

def update_seed_file():
    """Update the seed file with June 30 prices."""
    seed_file = Path(__file__).parents[2] / "app" / "db" / "seed_demo_portfolios.py"

    with open(seed_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match position dictionaries with entry_price
    # {"symbol": "AAPL", ..., "entry_price": Decimal("225.00"), ...}
    pattern = r'(\{"symbol":\s*"([A-Z\-]+)".*?"entry_price":\s*Decimal\()"([0-9.]+)("\))'

    def replace_price(match):
        prefix = match.group(1)  # Everything before the price
        symbol = match.group(2)  # Symbol name
        old_price = match.group(3)  # Old price value
        suffix = match.group(4)  # Closing quote and paren

        # Get new price if available
        new_price = JUNE30_PRICES.get(symbol)
        if new_price:
            return f'{prefix}{new_price}{suffix}'
        else:
            return match.group(0)  # No change if price not found

    # Replace all entry prices
    new_content = re.sub(pattern, replace_price, content)

    # Count changes
    changes = 0
    for symbol in JUNE30_PRICES:
        if f'"symbol": "{symbol}"' in content:
            changes += 1

    # Write back
    with open(seed_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Updated {seed_file}")
    print(f"Replaced entry prices for {changes} symbols")
    print("\nNote: Entry dates remain unchanged - only prices were updated")

if __name__ == "__main__":
    update_seed_file()
