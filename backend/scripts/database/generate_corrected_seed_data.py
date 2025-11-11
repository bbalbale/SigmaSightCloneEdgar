#!/usr/bin/env python
"""
Generate Corrected Seed Data with June 30, 2025 Prices

This script reads the current position data from the database and generates
Python code snippets that can be copy-pasted into seed_demo_portfolios.py
to update the entry_price values with actual June 30, 2025 market prices.

Output file: backend/scripts/database/corrected_seed_data.txt
"""
import asyncio
import sys
from pathlib import Path
from datetime import date

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position

PORTFOLIOS_TO_EXPORT = [
    ('demo_individual@sigmasight.com', 'Individual Investor'),
    ('demo_hnw@sigmasight.com', 'High Net Worth'),
    ('demo_hedgefundstyle@sigmasight.com', 'Hedge Fund Style'),
    ('demo_familyoffice@sigmasight.com', 'Family Office Public Growth'),
    ('demo_familyoffice@sigmasight.com', 'Family Office Private Opportunities'),
]


async def generate_seed_data():
    """Generate corrected seed data with actual June 30, 2025 prices"""

    output_file = project_root / "scripts" / "database" / "corrected_seed_data.txt"

    async with get_async_session() as db:
        with open(output_file, 'w') as f:
            f.write("=" * 100 + "\n")
            f.write("CORRECTED SEED DATA - June 30, 2025 Actual Market Prices\n")
            f.write("=" * 100 + "\n\n")
            f.write("Copy-paste these position arrays into backend/app/db/seed_demo_portfolios.py\n")
            f.write("to replace the existing hardcoded entry_price values.\n\n")

            for email, portfolio_name_partial in PORTFOLIOS_TO_EXPORT:
                # Get user
                user = (await db.execute(
                    select(User).where(User.email == email)
                )).scalar_one_or_none()

                if not user:
                    f.write(f"\n[ERROR] User not found: {email}\n\n")
                    continue

                # Get portfolio (handle multiple portfolios for family office)
                portfolios = (await db.execute(
                    select(Portfolio).where(
                        Portfolio.user_id == user.id,
                        Portfolio.deleted_at.is_(None)
                    )
                )).scalars().all()

                portfolio = None
                for p in portfolios:
                    if portfolio_name_partial.lower() in p.name.lower():
                        portfolio = p
                        break

                if not portfolio:
                    f.write(f"\n[ERROR] Portfolio not found for {email} matching '{portfolio_name_partial}'\n\n")
                    continue

                # Get all positions
                positions = (await db.execute(
                    select(Position).where(
                        Position.portfolio_id == portfolio.id,
                        Position.deleted_at.is_(None)
                    ).order_by(Position.symbol)
                )).scalars().all()

                f.write("\n" + "=" * 100 + "\n")
                f.write(f"Portfolio: {portfolio.name}\n")
                f.write(f"User: {email}\n")
                f.write(f"Positions: {len(positions)}\n")
                f.write("=" * 100 + "\n\n")
                f.write('"positions": [\n')

                for pos in positions:
                    # Build position dictionary
                    entry_date_str = pos.entry_date.strftime('%Y, %m, %d')  # e.g., "2025, 6, 30"

                    # Basic position data
                    line = f'    {{"symbol": "{pos.symbol}", '
                    line += f'"quantity": Decimal("{pos.quantity}"), '
                    line += f'"entry_price": Decimal("{pos.entry_price}"), '
                    line += f'"entry_date": date({entry_date_str})'

                    # Add tags placeholder (will need manual review)
                    line += ', "tags": []'  # TODO: Add actual tags

                    # Add option-specific fields if present
                    if pos.underlying_symbol:
                        line += f', "underlying": "{pos.underlying_symbol}"'
                        line += f', "strike": Decimal("{pos.strike_price}")'
                        expiry_str = pos.expiration_date.strftime('%Y, %m, %d')
                        line += f', "expiry": date({expiry_str})'

                        # Determine option type from position_type
                        if pos.position_type.value in ['LC', 'SC']:
                            option_type = 'C'
                        elif pos.position_type.value in ['LP', 'SP']:
                            option_type = 'P'
                        else:
                            option_type = 'C'  # Default
                        line += f', "option_type": "{option_type}"'

                    line += '},\n'
                    f.write(line)

                f.write(']\n\n')

            f.write("\n" + "=" * 100 + "\n")
            f.write("END OF CORRECTED SEED DATA\n")
            f.write("=" * 100 + "\n")

    print(f"Corrected seed data written to: {output_file}")
    print("Review the file and copy-paste position arrays into seed_demo_portfolios.py")


if __name__ == "__main__":
    asyncio.run(generate_seed_data())
