#!/usr/bin/env python
"""
Update all entry dates to June 30, 2025.

This makes all positions appear to be acquired on June 30, 2025,
which aligns with the entry price adjustment.
"""

import re
from pathlib import Path

def update_entry_dates():
    """Update all entry_date fields to June 30, 2025."""
    seed_file = Path(__file__).parents[2] / "app" / "db" / "seed_demo_portfolios.py"

    with open(seed_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match entry_date with any date value
    # "entry_date": date(2024, 1, 15)
    # "entry_date": date(2023, 12, 15)
    pattern = r'"entry_date":\s*date\(\d{4},\s*\d{1,2},\s*\d{1,2}\)'
    replacement = '"entry_date": date(2025, 6, 30)'

    # Replace all entry dates
    new_content = re.sub(pattern, replacement, content)

    # Count replacements
    old_dates = re.findall(pattern, content)
    replacements = len(old_dates)

    # Write back
    with open(seed_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Updated {seed_file}")
    print(f"Replaced {replacements} entry dates to June 30, 2025")

if __name__ == "__main__":
    update_entry_dates()
