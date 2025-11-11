#!/usr/bin/env python
"""
Set all demo portfolio equity balances to match specifications.

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

# Equity balance specifications (STARTING CAPITAL)
EQUITY_SPECS = {
    "demo_individual@sigmasight.com": Decimal("485000.00"),
    "demo_hnw@sigmasight.com": Decimal("2850000.00"),
    "demo_hedgefundstyle@sigmasight.com": Decimal("3200000.00"),  # 100% long + 50% short
    "demo_familyoffice@sigmasight.com": {
        "Demo Family Office Public Growth": Decimal("1250000.00"),
        "Demo Family Office Private Opportunities": Decimal("950000.00"),
    }
}


async def set_equity():
    async with get_async_session() as db:
        print("=" * 100)
        print("SETTING ALL PORTFOLIO EQUITY BALANCES TO SPECIFICATIONS")
        print("=" * 100)
        print()

        for email, equity_spec in EQUITY_SPECS.items():
            # Get user
            user = (await db.execute(
                select(User).where(User.email == email)
            )).scalar_one_or_none()

            if not user:
                print(f"[SKIP] User not found: {email}")
                continue

            # Get portfolios for this user
            portfolios = (await db.execute(
                select(Portfolio).where(Portfolio.user_id == user.id, Portfolio.deleted_at.is_(None))
            )).scalars().all()

            if isinstance(equity_spec, dict):
                # Family office has multiple portfolios
                for portfolio in portfolios:
                    target_equity = equity_spec.get(portfolio.name)
                    if target_equity:
                        old_equity = portfolio.equity_balance
                        portfolio.equity_balance = target_equity
                        print(f"{email}")
                        print(f"  Portfolio: {portfolio.name}")
                        print(f"  Old equity: ${old_equity:,.2f}")
                        print(f"  New equity: ${target_equity:,.2f}")
                        print()
            else:
                # Single portfolio users
                if portfolios:
                    portfolio = portfolios[0]
                    old_equity = portfolio.equity_balance
                    portfolio.equity_balance = equity_spec
                    print(f"{email}")
                    print(f"  Portfolio: {portfolio.name}")
                    print(f"  Old equity: ${old_equity:,.2f}")
                    print(f"  New equity: ${equity_spec:,.2f}")
                    print()

        print("Committing changes...")
        await db.commit()
        print()
        print("[DONE] All portfolio equity balances updated")
        print("=" * 100)


if __name__ == "__main__":
    asyncio.run(set_equity())
