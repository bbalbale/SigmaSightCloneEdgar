"""
Create 3 test portfolios with symbols NOT in the current symbol universe.

Each portfolio has ~20 symbols:
- 4 symbols likely IN universe (common ETFs/stocks for baseline)
- 16 symbols likely NOT in universe (smaller caps, ADRs, niche ETFs)

Run on Railway:
    railway run python scripts/create_test_portfolios.py

This will create portfolios for user: elliott.ng+testscotty@gmail.com
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
import random

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType

# Test user email - change if needed
TEST_USER_EMAIL = "elliott.ng+testscotty@gmail.com"

# Portfolio 1: "Universe Test Alpha" - Healthcare/Biotech focus
PORTFOLIO_1 = {
    "name": "Universe Test Alpha",
    "positions": [
        # Likely IN universe (4)
        {"symbol": "SPY", "quantity": 50, "entry_price": 450.00},
        {"symbol": "QQQ", "quantity": 30, "entry_price": 380.00},
        {"symbol": "XLV", "quantity": 100, "entry_price": 135.00},  # Healthcare ETF
        {"symbol": "IBB", "quantity": 80, "entry_price": 130.00},   # Biotech ETF
        # Likely NOT in universe (16) - Smaller biotech/healthcare
        {"symbol": "EXAS", "quantity": 150, "entry_price": 65.00},   # Exact Sciences
        {"symbol": "HZNP", "quantity": 200, "entry_price": 95.00},   # Horizon Therapeutics
        {"symbol": "SGEN", "quantity": 100, "entry_price": 175.00},  # Seagen
        {"symbol": "ALNY", "quantity": 75, "entry_price": 190.00},   # Alnylam Pharma
        {"symbol": "SRPT", "quantity": 60, "entry_price": 115.00},   # Sarepta
        {"symbol": "BMRN", "quantity": 120, "entry_price": 88.00},   # BioMarin
        {"symbol": "NBIX", "quantity": 90, "entry_price": 105.00},   # Neurocrine
        {"symbol": "INCY", "quantity": 140, "entry_price": 72.00},   # Incyte
        {"symbol": "UTHR", "quantity": 50, "entry_price": 225.00},   # United Therapeutics
        {"symbol": "EXEL", "quantity": 300, "entry_price": 18.00},   # Exelixis
        {"symbol": "IONS", "quantity": 180, "entry_price": 42.00},   # Ionis Pharma
        {"symbol": "RARE", "quantity": 100, "entry_price": 38.00},   # Ultragenyx
        {"symbol": "FOLD", "quantity": 400, "entry_price": 12.00},   # Amicus Therapeutics
        {"symbol": "ARWR", "quantity": 200, "entry_price": 28.00},   # Arrowhead Research
        {"symbol": "NTRA", "quantity": 150, "entry_price": 48.00},   # Natera
        {"symbol": "HALO", "quantity": 250, "entry_price": 42.00},   # Halozyme
    ]
}

# Portfolio 2: "Universe Test Beta" - International/ADR focus
PORTFOLIO_2 = {
    "name": "Universe Test Beta",
    "positions": [
        # Likely IN universe (4)
        {"symbol": "EFA", "quantity": 100, "entry_price": 72.00},   # Intl Developed ETF
        {"symbol": "VWO", "quantity": 150, "entry_price": 42.00},   # Emerging Markets ETF
        {"symbol": "BABA", "quantity": 80, "entry_price": 85.00},   # Alibaba (might be in)
        {"symbol": "TSM", "quantity": 60, "entry_price": 95.00},    # Taiwan Semi (might be in)
        # Likely NOT in universe (16) - International ADRs
        {"symbol": "SE", "quantity": 120, "entry_price": 55.00},     # Sea Limited
        {"symbol": "MELI", "quantity": 20, "entry_price": 1250.00},  # MercadoLibre
        {"symbol": "GRAB", "quantity": 800, "entry_price": 3.50},    # Grab Holdings
        {"symbol": "CPNG", "quantity": 300, "entry_price": 18.00},   # Coupang
        {"symbol": "BIDU", "quantity": 100, "entry_price": 110.00},  # Baidu
        {"symbol": "JD", "quantity": 150, "entry_price": 35.00},     # JD.com
        {"symbol": "PDD", "quantity": 80, "entry_price": 95.00},     # Pinduoduo
        {"symbol": "BILI", "quantity": 200, "entry_price": 18.00},   # Bilibili
        {"symbol": "NIO", "quantity": 400, "entry_price": 8.00},     # NIO
        {"symbol": "XPEV", "quantity": 350, "entry_price": 9.00},    # XPeng
        {"symbol": "LI", "quantity": 250, "entry_price": 28.00},     # Li Auto
        {"symbol": "VNET", "quantity": 600, "entry_price": 4.00},    # VNET Group
        {"symbol": "TME", "quantity": 500, "entry_price": 7.50},     # Tencent Music
        {"symbol": "ATHM", "quantity": 100, "entry_price": 25.00},   # Autohome
        {"symbol": "YUMC", "quantity": 80, "entry_price": 130.00},   # Yum China
        {"symbol": "HTHT", "quantity": 150, "entry_price": 38.00},   # Huazhu Group
    ]
}

# Portfolio 3: "Universe Test Gamma" - Small Cap/Specialty focus
PORTFOLIO_3 = {
    "name": "Universe Test Gamma",
    "positions": [
        # Likely IN universe (4)
        {"symbol": "IWM", "quantity": 80, "entry_price": 195.00},    # Russell 2000 ETF
        {"symbol": "VB", "quantity": 60, "entry_price": 205.00},     # Vanguard Small Cap
        {"symbol": "ARKK", "quantity": 150, "entry_price": 45.00},   # ARK Innovation (might be in)
        {"symbol": "XBI", "quantity": 100, "entry_price": 85.00},    # Biotech ETF
        # Likely NOT in universe (16) - Small caps, specialty
        {"symbol": "UPST", "quantity": 150, "entry_price": 28.00},   # Upstart
        {"symbol": "AFRM", "quantity": 200, "entry_price": 15.00},   # Affirm
        {"symbol": "SOFI", "quantity": 400, "entry_price": 8.00},    # SoFi
        {"symbol": "HOOD", "quantity": 350, "entry_price": 10.00},   # Robinhood
        {"symbol": "COIN", "quantity": 50, "entry_price": 85.00},    # Coinbase
        {"symbol": "RBLX", "quantity": 120, "entry_price": 38.00},   # Roblox
        {"symbol": "U", "quantity": 80, "entry_price": 32.00},       # Unity
        {"symbol": "PATH", "quantity": 250, "entry_price": 15.00},   # UiPath
        {"symbol": "DDOG", "quantity": 60, "entry_price": 95.00},    # Datadog
        {"symbol": "NET", "quantity": 100, "entry_price": 65.00},    # Cloudflare
        {"symbol": "ZS", "quantity": 40, "entry_price": 175.00},     # Zscaler
        {"symbol": "CRWD", "quantity": 35, "entry_price": 150.00},   # CrowdStrike
        {"symbol": "OKTA", "quantity": 70, "entry_price": 85.00},    # Okta
        {"symbol": "MDB", "quantity": 30, "entry_price": 280.00},    # MongoDB
        {"symbol": "SNOW", "quantity": 45, "entry_price": 165.00},   # Snowflake
        {"symbol": "PLTR", "quantity": 300, "entry_price": 18.00},   # Palantir
    ]
}

ALL_PORTFOLIOS = [PORTFOLIO_1, PORTFOLIO_2, PORTFOLIO_3]


async def create_test_portfolios():
    """Create all 3 test portfolios for the test user."""
    async with AsyncSessionLocal() as db:
        # Find the test user
        result = await db.execute(
            select(User).where(User.email == TEST_USER_EMAIL)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"ERROR: User {TEST_USER_EMAIL} not found!")
            print("Please create this user first via the onboarding flow.")
            return

        print(f"Found user: {user.email} (ID: {user.id})")

        created_portfolios = []

        for portfolio_data in ALL_PORTFOLIOS:
            portfolio_name = portfolio_data["name"]

            # Check if portfolio already exists
            existing = await db.execute(
                select(Portfolio).where(
                    Portfolio.user_id == user.id,
                    Portfolio.name == portfolio_name
                )
            )
            if existing.scalar_one_or_none():
                print(f"Portfolio '{portfolio_name}' already exists, skipping...")
                continue

            # Create portfolio
            portfolio = Portfolio(
                id=uuid4(),
                user_id=user.id,
                name=portfolio_name,
                description=f"Test portfolio for batch processing validation - {portfolio_name}",
                equity_balance=Decimal("5000000.00"),  # $5M
            )
            db.add(portfolio)
            await db.flush()  # Get the portfolio ID

            print(f"\nCreated portfolio: {portfolio_name} (ID: {portfolio.id})")

            # Create positions
            symbols_created = []
            for pos_data in portfolio_data["positions"]:
                # Random entry date in last 6 months
                days_ago = random.randint(30, 180)
                entry_date = date.today() - timedelta(days=days_ago)

                position = Position(
                    id=uuid4(),
                    portfolio_id=portfolio.id,
                    symbol=pos_data["symbol"],
                    position_type=PositionType.LONG,
                    quantity=Decimal(str(pos_data["quantity"])),
                    entry_price=Decimal(str(pos_data["entry_price"])),
                    entry_date=entry_date,
                    investment_class="PUBLIC",
                )
                db.add(position)
                symbols_created.append(pos_data["symbol"])

            print(f"  Created {len(symbols_created)} positions: {', '.join(symbols_created)}")
            created_portfolios.append(portfolio_name)

        await db.commit()

        print(f"\n{'='*60}")
        print(f"DONE! Created {len(created_portfolios)} portfolios:")
        for name in created_portfolios:
            print(f"  - {name}")
        print(f"\nNext steps:")
        print(f"1. Go to the app and trigger batch processing for each portfolio")
        print(f"2. Or use the admin API: POST /api/v1/admin/batch/run?portfolio_id=<id>")
        print(f"3. Monitor Railway logs for symbol universe additions")


if __name__ == "__main__":
    asyncio.run(create_test_portfolios())
