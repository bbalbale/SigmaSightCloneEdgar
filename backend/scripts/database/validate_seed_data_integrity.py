#!/usr/bin/env python
"""
Validate portfolio equity balances and exposure metrics.

Shows: Equity Balance, Long Exposure, Short Exposure, Gross Exposure, Net Exposure
Validates: Equity balance matches expected spec values (not position values for leveraged portfolios)

See backend/CLAUDE.md "Portfolio Equity & Exposure Definitions" for details.
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio, User
from app.models.positions import Position

# Expected equity balances (STARTING CAPITAL) from backend/CLAUDE.md
EXPECTED_EQUITY = {
    "demo_individual@sigmasight.com": Decimal("485000.00"),
    "demo_hnw@sigmasight.com": Decimal("2850000.00"),
    "demo_hedgefundstyle@sigmasight.com": Decimal("3200000.00"),
    "demo_familyoffice@sigmasight.com": {
        "Demo Family Office Public Growth": Decimal("1250000.00"),
        "Demo Family Office Private Opportunities": Decimal("950000.00"),
    }
}


async def validate():
    async with get_async_session() as db:
        # Get all portfolios
        portfolios = (await db.execute(
            select(Portfolio).where(Portfolio.deleted_at.is_(None))
        )).scalars().all()

        print("=" * 120)
        print("SEED DATA INTEGRITY VALIDATION")
        print("=" * 120)
        print()

        all_valid = True

        for portfolio in portfolios:
            # Get user to lookup expected equity
            user = (await db.execute(
                select(User).where(User.id == portfolio.user_id)
            )).scalar_one()

            # Get all positions
            positions = (await db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.deleted_at.is_(None)
                )
            )).scalars().all()

            if not positions:
                print(f"Portfolio: {portfolio.name}")
                print(f"  WARNING: No positions found")
                print()
                continue

            # Calculate exposures
            long_exposure = Decimal('0')
            short_exposure = Decimal('0')

            for pos in positions:
                value = pos.quantity * pos.entry_price
                if pos.quantity < 0:
                    short_exposure += abs(value)
                else:
                    long_exposure += value

            gross_exposure = long_exposure + short_exposure
            net_exposure = long_exposure - short_exposure

            # Get expected equity for this portfolio
            expected_equity_spec = EXPECTED_EQUITY.get(user.email)
            if isinstance(expected_equity_spec, dict):
                expected_equity = expected_equity_spec.get(portfolio.name)
            else:
                expected_equity = expected_equity_spec

            # Validate equity balance matches expected
            if expected_equity:
                equity_difference = portfolio.equity_balance - expected_equity
                tolerance = Decimal('1.0')  # Allow $1 difference for rounding
                is_valid = abs(equity_difference) < tolerance
            else:
                is_valid = True  # Skip validation if no expected value

            status = "PASS" if is_valid else "FAIL"
            symbol = "[OK]" if is_valid else "[FAIL]"

            # Display results
            print(f"{symbol} Portfolio: {portfolio.name}")
            print(f"    User:               {user.email}")
            print(f"    Equity Balance:     ${portfolio.equity_balance:,.2f}")
            if expected_equity:
                print(f"    Expected Equity:    ${expected_equity:,.2f}")
                print(f"    Equity Difference:  ${equity_difference:+,.2f}")
            print()
            print(f"    Long Exposure:      ${long_exposure:,.2f}")
            print(f"    Short Exposure:     ${short_exposure:,.2f}")
            print(f"    Gross Exposure:     ${gross_exposure:,.2f}")
            print(f"    Net Exposure:       ${net_exposure:,.2f}")

            if gross_exposure > 0 and portfolio.equity_balance > 0:
                leverage = gross_exposure / portfolio.equity_balance
                print(f"    Leverage Ratio:     {leverage:.2f}x")

            print(f"    Status:             {status}")
            print()

            if not is_valid:
                all_valid = False

        print("=" * 120)
        if all_valid:
            print("SUCCESS: All portfolios have correct equity balances")
        else:
            print("FAILURE: Some portfolios have incorrect equity balances")
            print("Run set_all_portfolio_equity_to_spec.py to correct")
        print("=" * 120)

        return all_valid


if __name__ == "__main__":
    try:
        result = asyncio.run(validate())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
