"""
Demo Portfolio Seeding - CORRECTED DATA with June 30, 2025 Actual Market Prices
Creates the demo portfolios with correct position data from corrected_seed_data.txt
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4, UUID
import hashlib
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.core.auth import get_password_hash
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.tags_v2 import TagV2
from app.services.position_tag_service import PositionTagService

logger = get_logger(__name__)

OCC_OPTION_PATTERN = re.compile(r'^[A-Z]{1,6}\d{6}([CP])\d{8}$')


def _extract_option_flag(symbol: str) -> Optional[str]:
    """Return 'C' or 'P' if symbol matches OCC option format."""
    match = OCC_OPTION_PATTERN.match(symbol.upper())
    if match:
        return match.group(1)
    return None

def generate_deterministic_uuid(seed_string: str) -> UUID:
    """Generate consistent UUID from seed string - DEVELOPMENT ONLY

    Creates the same UUID on every machine for the same input string.
    This ensures all developers get identical portfolio IDs for demo data.

    Args:
        seed_string: String to use as seed for UUID generation

    Returns:
        UUID object that will be identical across all machines

    Note:
        This is for development consistency only. Production should use uuid4()
        for proper randomization and security.
    """
    # Create MD5 hash of seed string and format as UUID
    hash_hex = hashlib.md5(seed_string.encode()).hexdigest()
    return UUID(hash_hex)

# Demo users as specified in DATABASE_DESIGN_ADDENDUM_V1.4.1.md
DEMO_USERS = [
    {
        "username": "demo_individual",
        "email": "demo_individual@sigmasight.com",
        "full_name": "Demo Individual Investor",
        "password": "demo12345",
        "strategy": "Balanced portfolio with mutual funds and growth stocks"
    },
    {
        "username": "demo_hnw",
        "email": "demo_hnw@sigmasight.com",
        "full_name": "Demo High Net Worth Investor",
        "password": "demo12345",
        "strategy": "Sophisticated portfolio with private investments and alternatives"
    },
    {
        "username": "demo_hedgefundstyle",
        "email": "demo_hedgefundstyle@sigmasight.com",
        "full_name": "Demo Hedge Fund Style Investor",
        "password": "demo12345",
        "strategy": "Long/short equity with options overlay and volatility trading"
    },
    {
        "username": "demo_familyoffice",
        "email": "demo_familyoffice@sigmasight.com",
        "full_name": "Demo Family Office Manager",
        "password": "demo12345",
        "strategy": "Family office with dedicated public growth and private alternatives mandates"
    }
]

# Demo portfolio specifications with CORRECTED June 30, 2025 market prices
DEMO_PORTFOLIOS = [
    {
        "user_email": "demo_individual@sigmasight.com",
        "portfolio_id_seed": "demo_individual@sigmasight.com_portfolio",
        "portfolio_name": "Demo Individual Investor Portfolio",
        "description": "Individual investor with 401k, IRA, and taxable accounts. Core holdings with growth tilt, heavy mutual fund allocation.",
        "net_asset_value": 485000,
        "equity_balance": Decimal("485000.00"),
        "positions": [
            {"symbol": "AAPL", "quantity": Decimal("80.9000"), "entry_price": Decimal("204.9374"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "AMZN", "quantity": Decimal("102.8800"), "entry_price": Decimal("219.3900"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "BND", "quantity": Decimal("298.6600"), "entry_price": Decimal("72.4414"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FCNTX", "quantity": Decimal("4597.7900"), "entry_price": Decimal("23.3300"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FMAGX", "quantity": Decimal("3677.8300"), "entry_price": Decimal("15.6700"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FXNAX", "quantity": Decimal("4137.3100"), "entry_price": Decimal("10.3446"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GOOGL", "quantity": Decimal("108.8700"), "entry_price": Decimal("176.0725"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "JNJ", "quantity": Decimal("99.8800"), "entry_price": Decimal("151.6370"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "JPM", "quantity": Decimal("80.9000"), "entry_price": Decimal("287.1241"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "MSFT", "quantity": Decimal("42.9500"), "entry_price": Decimal("496.5937"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "NVDA", "quantity": Decimal("23.9700"), "entry_price": Decimal("157.9811"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "TSLA", "quantity": Decimal("65.9200"), "entry_price": Decimal("317.6600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "V", "quantity": Decimal("46.9400"), "entry_price": Decimal("354.4264"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "VNQ", "quantity": Decimal("201.7700"), "entry_price": Decimal("88.2174"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "VTI", "quantity": Decimal("146.8300"), "entry_price": Decimal("303.0875"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "VTIAX", "quantity": Decimal("919.9500"), "entry_price": Decimal("36.9219"), "entry_date": date(2025, 6, 30), "tags": []},
        ]
    },
    {
        "user_email": "demo_hnw@sigmasight.com",
        "portfolio_id_seed": "demo_hnw@sigmasight.com_portfolio",
        "portfolio_name": "Demo High Net Worth Investor Portfolio",
        "description": "High net worth individual with access to private investments. Diversified across public markets with alternative investments.",
        "net_asset_value": 2850000,
        "equity_balance": Decimal("2850000.00"),
        "positions": [
            {"symbol": "A16Z_VC_FUND", "quantity": Decimal("1.0100"), "entry_price": Decimal("126529.9000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "AAPL", "quantity": Decimal("307.6500"), "entry_price": Decimal("204.9374"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "AMZN", "quantity": Decimal("369.8000"), "entry_price": Decimal("219.3900"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "ART_COLLECTIBLES", "quantity": Decimal("1.0100"), "entry_price": Decimal("25305.9800"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "BRK-B", "quantity": Decimal("138.5400"), "entry_price": Decimal("485.7700"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "BX_PRIVATE_EQUITY", "quantity": Decimal("1.0100"), "entry_price": Decimal("253058.8600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "CRYPTO_BTC_ETH", "quantity": Decimal("1.0100"), "entry_price": Decimal("37958.9700"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "DJP", "quantity": Decimal("1462.9100"), "entry_price": Decimal("33.9800"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GLD", "quantity": Decimal("250.6000"), "entry_price": Decimal("304.8300"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GOOGL", "quantity": Decimal("38.7100"), "entry_price": Decimal("176.0725"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GOOGL", "quantity": Decimal("385.0800"), "entry_price": Decimal("176.0725"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GOOGL", "quantity": Decimal("38.7100"), "entry_price": Decimal("176.0725"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GOOGL", "quantity": Decimal("38.7100"), "entry_price": Decimal("176.0725"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "HD", "quantity": Decimal("96.7700"), "entry_price": Decimal("364.5717"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "HOME_EQUITY", "quantity": Decimal("1.0300"), "entry_price": Decimal("253059.8000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "JNJ", "quantity": Decimal("238.3700"), "entry_price": Decimal("151.6370"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "JPM", "quantity": Decimal("269.9500"), "entry_price": Decimal("287.1241"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "META", "quantity": Decimal("69.2600"), "entry_price": Decimal("737.5922"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "MONEY_MARKET", "quantity": Decimal("1.0100"), "entry_price": Decimal("50611.9600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "MSFT", "quantity": Decimal("77.4200"), "entry_price": Decimal("496.5937"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "MSFT", "quantity": Decimal("77.4200"), "entry_price": Decimal("496.5937"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "MSFT", "quantity": Decimal("77.4200"), "entry_price": Decimal("496.5937"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "MSFT", "quantity": Decimal("153.8200"), "entry_price": Decimal("496.5937"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "NVDA", "quantity": Decimal("19.3500"), "entry_price": Decimal("157.9811"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "NVDA", "quantity": Decimal("53.9800"), "entry_price": Decimal("157.9811"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "PG", "quantity": Decimal("192.5300"), "entry_price": Decimal("157.1390"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "QQQ", "quantity": Decimal("346.3600"), "entry_price": Decimal("551.0012"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "RENTAL_CONDO", "quantity": Decimal("1.0100"), "entry_price": Decimal("126529.9000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "RENTAL_SFH", "quantity": Decimal("1.0100"), "entry_price": Decimal("126529.9000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "SPY", "quantity": Decimal("307.6500"), "entry_price": Decimal("616.1418"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "STARWOOD_REIT", "quantity": Decimal("1.0100"), "entry_price": Decimal("126529.9000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "TREASURY_BILLS", "quantity": Decimal("1.0100"), "entry_price": Decimal("25305.9800"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "TSLA", "quantity": Decimal("58.0600"), "entry_price": Decimal("317.6600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "TSLA", "quantity": Decimal("58.0600"), "entry_price": Decimal("317.6600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "TSLA", "quantity": Decimal("58.0600"), "entry_price": Decimal("317.6600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "TWO_SIGMA_FUND", "quantity": Decimal("1.0100"), "entry_price": Decimal("126529.9000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "UNH", "quantity": Decimal("65.1900"), "entry_price": Decimal("310.0142"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "V", "quantity": Decimal("131.4100"), "entry_price": Decimal("354.4264"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "VTI", "quantity": Decimal("616.3300"), "entry_price": Decimal("303.0875"), "entry_date": date(2025, 6, 30), "tags": []},
        ]
    },
    {
        "user_email": "demo_hedgefundstyle@sigmasight.com",
        "portfolio_id_seed": "demo_hedgefundstyle@sigmasight.com_portfolio",
        "portfolio_name": "Demo Hedge Fund Style Investor Portfolio",
        "description": "Sophisticated trader with derivatives access. Market-neutral with volatility trading and options overlay.",
        "net_asset_value": 3200000,
        "equity_balance": Decimal("3200000.00"),
        "positions": [
            {"symbol": "AAPL", "quantity": Decimal("1332.5100"), "entry_price": Decimal("204.9374"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "AAPL250815P00200000", "quantity": Decimal("-188.3900"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "AAPL", "strike": Decimal("200.0000"), "expiry": date(2025, 8, 15), "option_type": "P"},
            {"symbol": "AMD", "quantity": Decimal("1066.0100"), "entry_price": Decimal("141.9000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "AMZN", "quantity": Decimal("1243.6700"), "entry_price": Decimal("219.3900"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "BRK-B", "quantity": Decimal("533.0000"), "entry_price": Decimal("485.7700"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "C", "quantity": Decimal("-1273.8600"), "entry_price": Decimal("84.0626"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "F", "quantity": Decimal("-8392.8800"), "entry_price": Decimal("10.5838"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GE", "quantity": Decimal("-671.5800"), "entry_price": Decimal("256.7010"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "GOOGL", "quantity": Decimal("1599.0100"), "entry_price": Decimal("176.0725"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "JNJ", "quantity": Decimal("710.6700"), "entry_price": Decimal("151.6370"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "JPM", "quantity": Decimal("888.3400"), "entry_price": Decimal("287.1241"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "META", "quantity": Decimal("888.3400"), "entry_price": Decimal("737.5922"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "META250919P00450000", "quantity": Decimal("-94.6800"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "META", "strike": Decimal("450.0000"), "expiry": date(2025, 9, 19), "option_type": "P"},
            {"symbol": "MSFT", "quantity": Decimal("888.3400"), "entry_price": Decimal("496.5937"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "MSFT250919P00380000", "quantity": Decimal("-151.3000"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "MSFT", "strike": Decimal("380.0000"), "expiry": date(2025, 9, 19), "option_type": "P"},
            {"symbol": "NFLX", "quantity": Decimal("-503.6900"), "entry_price": Decimal("1339.1300"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "NVDA", "quantity": Decimal("710.6700"), "entry_price": Decimal("157.9811"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "NVDA251017C00800000", "quantity": Decimal("94.6900"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "NVDA", "strike": Decimal("800.0000"), "expiry": date(2025, 10, 17), "option_type": "C"},
            {"symbol": "PTON", "quantity": Decimal("-2517.4700"), "entry_price": Decimal("6.9400"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "QQQ250815C00420000", "quantity": Decimal("283.0900"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "QQQ", "strike": Decimal("420.0000"), "expiry": date(2025, 8, 15), "option_type": "C"},
            {"symbol": "ROKU", "quantity": Decimal("-1511.0700"), "entry_price": Decimal("87.8900"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "SHOP", "quantity": Decimal("-839.4800"), "entry_price": Decimal("115.3500"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "SPY250919C00460000", "quantity": Decimal("377.7800"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "SPY", "strike": Decimal("460.0000"), "expiry": date(2025, 9, 19), "option_type": "C"},
            {"symbol": "TSLA", "quantity": Decimal("710.6700"), "entry_price": Decimal("317.6600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "TSLA250815C00300000", "quantity": Decimal("-113.2300"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "TSLA", "strike": Decimal("300.0000"), "expiry": date(2025, 8, 15), "option_type": "C"},
            {"symbol": "UNH", "quantity": Decimal("177.6600"), "entry_price": Decimal("310.0142"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "V", "quantity": Decimal("310.4300"), "entry_price": Decimal("354.4264"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "VIX250716C00025000", "quantity": Decimal("566.1900"), "entry_price": Decimal("0.0000"), "entry_date": date(2025, 6, 30), "tags": [], "underlying": "VIX", "strike": Decimal("25.0000"), "expiry": date(2025, 7, 16), "option_type": "C"},
            {"symbol": "XOM", "quantity": Decimal("-1677.9900"), "entry_price": Decimal("106.8061"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "ZM", "quantity": Decimal("-1677.9900"), "entry_price": Decimal("77.9800"), "entry_date": date(2025, 6, 30), "tags": []},
        ]
    },
    {
        "user_email": "demo_familyoffice@sigmasight.com",
        "portfolio_id_seed": "demo_familyoffice@sigmasight.com_public_growth",
        "portfolio_name": "Demo Family Office Public Growth",
        "description": "Public markets growth sleeve for the family office combining thematic ETFs with quality compounders and defensive yield.",
        "total_value": 1250000,
        "equity_balance": Decimal("1250000.00"),
        "positions": [
            {"symbol": "ASML", "quantity": Decimal("189.0000"), "entry_price": Decimal("797.9467"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "AVGO", "quantity": Decimal("166.0000"), "entry_price": Decimal("275.1785"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "BIL", "quantity": Decimal("1089.0000"), "entry_price": Decimal("90.1800"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "COST", "quantity": Decimal("260.0000"), "entry_price": Decimal("987.1738"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "IGV", "quantity": Decimal("473.0000"), "entry_price": Decimal("109.5000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "JEPQ", "quantity": Decimal("827.0000"), "entry_price": Decimal("52.2119"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "LULU", "quantity": Decimal("355.0000"), "entry_price": Decimal("237.5800"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "NEE", "quantity": Decimal("592.0000"), "entry_price": Decimal("68.8873"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "SCHD", "quantity": Decimal("769.0000"), "entry_price": Decimal("26.2485"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "SMH", "quantity": Decimal("592.0000"), "entry_price": Decimal("278.8800"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "XLK", "quantity": Decimal("710.0000"), "entry_price": Decimal("252.9050"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "XLY", "quantity": Decimal("532.0000"), "entry_price": Decimal("216.9474"), "entry_date": date(2025, 6, 30), "tags": []},
        ]
    },
    {
        "user_email": "demo_familyoffice@sigmasight.com",
        "portfolio_id_seed": "demo_familyoffice@sigmasight.com_private_opportunities",
        "portfolio_name": "Demo Family Office Private Opportunities",
        "description": "Private market and real asset sleeve emphasizing income, diversification, and inflation protection.",
        "total_value": 950000,
        "equity_balance": Decimal("950000.00"),
        "positions": [
            {"symbol": "FO_ART_COLLECTIVE", "quantity": Decimal("1.0000"), "entry_price": Decimal("29081.6300"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_CRYPTO_DIGITAL", "quantity": Decimal("1.0000"), "entry_price": Decimal("29081.6300"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_GROWTH_PE", "quantity": Decimal("1.0000"), "entry_price": Decimal("203571.4300"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_HOME_RENTAL", "quantity": Decimal("1.0000"), "entry_price": Decimal("82397.9600"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_IMPACT_LENDING", "quantity": Decimal("1.0000"), "entry_price": Decimal("53316.3300"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_INFRASTRUCTURE", "quantity": Decimal("1.0000"), "entry_price": Decimal("87244.9000"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_PRIVATE_CREDIT", "quantity": Decimal("1.0000"), "entry_price": Decimal("218112.2500"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_REAL_ASSET_REIT", "quantity": Decimal("1.0000"), "entry_price": Decimal("106632.6500"), "entry_date": date(2025, 6, 30), "tags": []},
            {"symbol": "FO_VC_SECONDARIES", "quantity": Decimal("1.0000"), "entry_price": Decimal("140561.2200"), "entry_date": date(2025, 6, 30), "tags": []},
        ]
    }
]

async def create_demo_users(db: AsyncSession) -> None:
    """Create all demo users if they don't exist"""
    logger.info("Creating demo users...")

    for user_data in DEMO_USERS:
        # Check if user already exists
        stmt = select(User).where(User.email == user_data["email"])
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.info(f"Demo user already exists: {user_data['email']}")
            continue

        # Create new demo user with deterministic ID for development consistency
        hashed_password = get_password_hash(user_data["password"])
        user = User(
            id=generate_deterministic_uuid(f"{user_data['email']}_user"),
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password=hashed_password,
            is_active=True
        )

        db.add(user)
        logger.info(f"Created demo user: {user_data['email']} ({user_data['strategy']})")

    # Log credentials for reference
    logger.info("Demo user credentials:")
    for user_data in DEMO_USERS:
        logger.info(f"  Email: {user_data['email']} | Password: {user_data['password']}")

async def get_user_by_email(db: AsyncSession, email: str) -> User:
    """Get user by email"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"Demo user not found: {email}. Run scripts/seed_database.py first.")
    return user

async def get_or_create_tag(db: AsyncSession, user_id: str, tag_name: str) -> TagV2:
    """Get existing tag or create new one"""
    result = await db.execute(select(TagV2).where(TagV2.user_id == user_id, TagV2.name == tag_name, TagV2.is_archived == False))
    tag = result.scalar_one_or_none()

    if not tag:
        tag = TagV2(user_id=user_id, name=tag_name, color="#4A90E2")
        db.add(tag)
        await db.flush()

    return tag

def determine_position_type(
    symbol: str,
    quantity: Decimal,
    option_type: Optional[str] = None,
    investment_class: Optional[str] = None
) -> PositionType:
    """Determine position type using option metadata when available."""
    normalized_quantity = quantity or Decimal("0")
    normalized_class = investment_class or determine_investment_class(symbol)

    if normalized_class == 'OPTIONS':
        option_hint = option_type.upper() if option_type else None
        if option_hint in ('CALL', 'PUT'):
            option_flag = 'C' if option_hint == 'CALL' else 'P'
        elif option_hint in ('C', 'P'):
            option_flag = option_hint
        else:
            option_flag = _extract_option_flag(symbol)

        if option_flag:
            is_call = option_flag == 'C'
            if normalized_quantity >= 0:
                return PositionType.LC if is_call else PositionType.LP
            return PositionType.SC if is_call else PositionType.SP

    return PositionType.LONG if normalized_quantity >= 0 else PositionType.SHORT

def determine_investment_class(symbol: str) -> str:
    """Determine investment class from symbol

    Returns:
        'OPTIONS' for options (symbols with expiry/strike pattern)
        'PRIVATE' for private investment funds (Phase 8.1 Task 3a: enhanced to catch all 11 SYNTHETIC_SYMBOLS)
        'PUBLIC' for regular stocks and ETFs
    """
    # Check for private investment patterns FIRST (enhanced to catch all 11 SYNTHETIC_SYMBOLS)
    # This prevents private symbols with 'C' or 'P' from being misclassified as options
    # Original patterns: PRIVATE, FUND, _VC_, _PE_, REIT, SIGMA
    # New patterns (Phase 8.1): HOME_, RENTAL_, ART_, CRYPTO_, TREASURY, MONEY_MARKET, FO_
    private_patterns = [
        'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',  # Original
        'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET', 'FO_'  # New (Phase 8.1)
    ]
    symbol_upper = symbol.upper()
    if any(pattern in symbol_upper for pattern in private_patterns):
        return 'PRIVATE'

    # OCC option format: SYMBOL + YYMMDD + C/P + STRIKE (e.g., SPY250919C00460000)
    if _extract_option_flag(symbol_upper):
        return 'OPTIONS'

    # Everything else is public equity (stocks, ETFs, mutual funds)
    else:
        return 'PUBLIC'

def determine_investment_subtype(symbol: str) -> str:
    """Determine investment subtype for private investments"""
    symbol_upper = symbol.upper()
    if 'PRIVATE_EQUITY' in symbol_upper or 'BX' in symbol_upper:
        return 'PRIVATE_EQUITY'
    elif 'VC' in symbol_upper or 'A16Z' in symbol_upper:
        return 'VENTURE_CAPITAL'
    elif 'REIT' in symbol_upper or 'STARWOOD' in symbol_upper:
        return 'PRIVATE_REIT'
    elif 'FUND' in symbol_upper or 'SIGMA' in symbol_upper:
        return 'HEDGE_FUND'
    return None

async def _add_positions_to_portfolio(db: AsyncSession, portfolio: Portfolio, position_data_list: List[Dict[str, Any]], user: User, existing_symbols: set = None) -> int:
    """Helper function to add positions to a portfolio, avoiding duplicates"""
    if existing_symbols is None:
        existing_symbols = set()

    position_count = 0
    position_tag_service = PositionTagService(db)
    for pos_data in position_data_list:
        symbol = pos_data["symbol"]

        # Skip if position already exists
        if symbol in existing_symbols:
            continue

        # Determine investment class
        investment_class = determine_investment_class(symbol)

        # Determine position type using investment class & option metadata
        position_type = determine_position_type(
            symbol,
            pos_data["quantity"],
            option_type=pos_data.get("option_type"),
            investment_class=investment_class
        )

        # Determine investment subtype for private investments
        investment_subtype = None
        if investment_class == 'PRIVATE':
            investment_subtype = determine_investment_subtype(symbol)

        # Create position with deterministic ID for development consistency
        position = Position(
            id=generate_deterministic_uuid(f"{portfolio.id}_{symbol}_{pos_data['entry_date']}"),
            portfolio_id=portfolio.id,
            symbol=symbol,
            position_type=position_type,
            quantity=pos_data["quantity"],
            entry_price=pos_data["entry_price"],
            entry_date=pos_data["entry_date"],
            investment_class=investment_class,
            investment_subtype=investment_subtype,
        )

        # Add options-specific fields if present
        if "underlying" in pos_data:
            position.underlying_symbol = pos_data["underlying"]
            position.strike_price = pos_data["strike"]
            position.expiration_date = pos_data["expiry"]

        db.add(position)
        await db.flush()  # Get position ID

        # Assign tags directly to the position using the new tagging system
        if pos_data.get("tags"):
            tag_ids = []
            for tag_name in pos_data.get("tags", []):
                tag = await get_or_create_tag(db, user.id, tag_name)
                tag_ids.append(tag.id)

            if tag_ids:
                await position_tag_service.bulk_assign_tags(
                    position_id=position.id,
                    tag_ids=tag_ids,
                    assigned_by=user.id,
                    replace_existing=False
                )

        # AUTO-TAG: Apply sector tag based on company profile
        from app.services.sector_tag_service import apply_sector_tag_to_position
        try:
            sector_tag_result = await apply_sector_tag_to_position(
                db=db,
                position_id=position.id,
                user_id=user.id
            )
            if sector_tag_result["success"]:
                logger.debug(
                    f"Auto-tagged position {symbol} with sector tag '{sector_tag_result['tag_name']}'"
                )
        except Exception as e:
            logger.warning(f"Failed to auto-tag position {symbol} with sector: {e}")
            # Continue even if sector tagging fails - it's not critical

        position_count += 1
        existing_symbols.add(symbol)  # Track newly added positions

    return position_count

async def create_demo_portfolio(db: AsyncSession, portfolio_data: Dict[str, Any]) -> Portfolio:
    """Create a single demo portfolio with all positions"""
    logger.info(f"Creating portfolio: {portfolio_data['portfolio_name']}")

    # Get user
    user = await get_user_by_email(db, portfolio_data["user_email"])

    # Determine deterministic portfolio ID to support multiple portfolios per user
    portfolio_seed = portfolio_data.get("portfolio_id_seed") or f"{user.email}_{portfolio_data['portfolio_name']}"
    portfolio_id = generate_deterministic_uuid(portfolio_seed)

    # Check if this specific portfolio already exists
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    existing_portfolio = result.scalar_one_or_none()

    if existing_portfolio:
        logger.info(f"Portfolio already exists for user {user.email}: {existing_portfolio.name}")

        # Update equity_balance if provided and different
        if "equity_balance" in portfolio_data and existing_portfolio.equity_balance != portfolio_data["equity_balance"]:
            logger.info(f"Updating equity_balance from {existing_portfolio.equity_balance} to {portfolio_data['equity_balance']}")
            existing_portfolio.equity_balance = portfolio_data["equity_balance"]
            db.add(existing_portfolio)
            await db.flush()

        # Count existing positions
        position_result = await db.execute(
            select(Position).where(Position.portfolio_id == existing_portfolio.id)
        )
        existing_positions = position_result.scalars().all()
        existing_symbols = {pos.symbol for pos in existing_positions}
        logger.info(f"Portfolio has {len(existing_positions)} existing positions")

        # Add missing positions to existing portfolio
        expected_positions = len(portfolio_data["positions"])
        missing_count = expected_positions - len(existing_positions)

        if missing_count > 0:
            logger.info(f"Adding {missing_count} missing positions to existing portfolio")
            await _add_positions_to_portfolio(db, existing_portfolio, portfolio_data["positions"], user, existing_symbols)
            logger.info(f"[OK] Updated portfolio {existing_portfolio.name} with {missing_count} new positions")
        else:
            logger.info(f"Portfolio already has all {expected_positions} positions - no update needed")

        return existing_portfolio

    # Create portfolio with deterministic ID for development consistency
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=user.id,
        name=portfolio_data["portfolio_name"],
        account_name=portfolio_data["portfolio_name"],  # Required: use portfolio name as account name
        account_type='taxable',  # Default account type for demo portfolios
        description=portfolio_data["description"],
        equity_balance=portfolio_data.get("equity_balance")  # Set equity for risk calculations
    )
    db.add(portfolio)
    await db.flush()  # Get portfolio ID

    # Create positions using helper function
    position_count = await _add_positions_to_portfolio(db, portfolio, portfolio_data["positions"], user)

    logger.info(f"Created portfolio {portfolio_data['portfolio_name']} with {position_count} positions")
    return portfolio

async def seed_demo_portfolios(db: AsyncSession) -> None:
    """Seed all demo portfolios from corrected_seed_data.txt"""
    logger.info("🏗️ Seeding demo portfolios with CORRECTED June 30, 2025 market prices...")

    portfolios_created = 0
    total_positions = 0

    for portfolio_data in DEMO_PORTFOLIOS:
        portfolio = await create_demo_portfolio(db, portfolio_data)
        portfolios_created += 1
        total_positions += len(portfolio_data["positions"])

    logger.info(f"[OK] Created {portfolios_created} demo portfolios with {total_positions} total positions")
    logger.info("🎯 Demo portfolios ready for batch processing framework!")

async def main():
    """Main function for testing"""
    from app.database import get_async_session

    async with get_async_session() as db:
        try:
            await seed_demo_portfolios(db)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Seeding failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
