"""
Apply database corrections to seed_demo_portfolios.py file.

This script updates the entry prices in the seed file to match the corrected database values.
"""

import re
from decimal import Decimal

# Corrected entry prices from database (exported from export_corrected_seed_data.py)
CORRECTIONS = {
    "Demo Individual Investor Portfolio": {
        "VTI": Decimal("250.29"),
        "VNQ": Decimal("95.10"),
    },
    "Demo High Net Worth Investor Portfolio": {
        "AAPL": Decimal("169.20"),
        "AMZN": Decimal("127.84"),
        "BRK-B": Decimal("330.87"),
        "DJP": Decimal("22.56"),
        "GLD": Decimal("164.86"),
        "GOOGL": Decimal("120.32"),  # Main position (500 shares)
        "HD": Decimal("263.19"),
        "JNJ": Decimal("120.32"),
        "JPM": Decimal("127.84"),
        "META": Decimal("398.55"),
        "MSFT": Decimal("315.83"),  # Main position (200 shares) - will need special handling for 4 MSFT positions
        "NVDA": Decimal("526.39"),  # Main position (70 shares)
        "PG": Decimal("124.08"),
        "QQQ": Decimal("315.83"),
        "SPY": Decimal("398.55"),
        "TSLA": Decimal("188.00"),
        "UNH": Decimal("409.83"),
        "V": Decimal("201.53"),
        "VTI": Decimal("172.96"),
    },
    "Demo Hedge Fund Style Investor Portfolio": {
        # Long stocks
        "NVDA": Decimal("1061.22"),
        "MSFT": Decimal("636.73"),
        "AAPL": Decimal("341.11"),
        "GOOGL": Decimal("242.57"),
        "META": Decimal("401.75"),
        "AMZN": Decimal("257.73"),
        "TSLA": Decimal("386.59"),
        "AMD": Decimal("245.60"),
        "BRK-B": Decimal("667.05"),
        "JPM": Decimal("257.73"),
        "JNJ": Decimal("242.57"),
        "UNH": Decimal("826.24"),
        "V": Decimal("406.30"),
        # Short stocks
        "NFLX": Decimal("773.50"),
        "SHOP": Decimal("307.82"),
        "ZM": Decimal("110.50"),
        "PTON": Decimal("63.14"),
        "ROKU": Decimal("94.71"),
        "XOM": Decimal("173.64"),
        "F": Decimal("18.94"),
        "GE": Decimal("221.00"),
        "C": Decimal("86.82"),
        # Options - all set to 0
        "SPY250919C00460000": Decimal("0.00"),
        "QQQ250815C00420000": Decimal("0.00"),
        "VIX250716C00025000": Decimal("0.00"),
        "NVDA251017C00800000": Decimal("0.00"),
        "AAPL250815P00200000": Decimal("0.00"),
        "MSFT250919P00380000": Decimal("0.00"),
        "TSLA250815C00300000": Decimal("0.00"),
        "META250919P00450000": Decimal("0.00"),
    }
}


def update_seed_file():
    """Update seed_demo_portfolios.py with corrected entry prices."""

    with open("app/db/seed_demo_portfolios.py", "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    updated_lines = []

    current_portfolio = None
    changes_made = 0

    for i, line in enumerate(lines):
        # Track which portfolio we're in
        if '"portfolio_name":' in line:
            for portfolio_name in CORRECTIONS.keys():
                if f'"{portfolio_name}"' in line:
                    current_portfolio = portfolio_name
                    print(f"\nProcessing: {portfolio_name}")
                    break

        # Check if this is a position line with a symbol we need to correct
        if current_portfolio and '"symbol":' in line:
            symbol_match = re.search(r'"symbol":\s*"([^"]+)"', line)
            if symbol_match:
                symbol = symbol_match.group(1)

                if symbol in CORRECTIONS[current_portfolio]:
                    new_price = CORRECTIONS[current_portfolio][symbol]

                    # Look ahead to find the entry_price line (usually within next 5 lines)
                    for j in range(i, min(i + 10, len(lines))):
                        if '"entry_price":' in lines[j]:
                            old_price_match = re.search(r'Decimal\("([^"]+)"\)', lines[j])
                            if old_price_match:
                                old_price = old_price_match.group(1)

                                # Replace the entry price
                                lines[j] = re.sub(
                                    r'Decimal\("([^"]+)"\)',
                                    f'Decimal("{new_price}")',
                                    lines[j]
                                )

                                print(f"  {symbol:25s}: ${old_price:>10s} -> ${str(new_price):>10s}")
                                changes_made += 1
                            break

        updated_lines.append(lines[i])

    # Write updated content
    with open("app/db/seed_demo_portfolios.py", "w", encoding="utf-8") as f:
        f.write("\n".join(updated_lines))

    print(f"\nApplied {changes_made} corrections to seed_demo_portfolios.py")
    return changes_made


if __name__ == "__main__":
    print("="*100)
    print("UPDATING SEED FILE WITH CORRECTED ENTRY PRICES")
    print("="*100)

    changes = update_seed_file()

    print("\n" + "="*100)
    print(f"COMPLETE - {changes} entry prices updated")
    print("="*100)
    print("\nNext: Reseed database to verify corrections")
