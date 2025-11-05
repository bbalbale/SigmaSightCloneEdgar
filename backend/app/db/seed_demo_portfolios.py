"""
Demo Portfolio Seeding - Section 1.5 Implementation
Creates the 3 demo portfolios from Ben Mock Portfolios.md with complete position data
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

# Demo portfolio specifications from Ben Mock Portfolios.md
DEMO_PORTFOLIOS = [
    {
        "user_email": "demo_individual@sigmasight.com",
        "portfolio_id_seed": "demo_individual@sigmasight.com_portfolio",
        "portfolio_name": "Demo Individual Investor Portfolio",
        "description": "Individual investor with 401k, IRA, and taxable accounts. Core holdings with growth tilt, heavy mutual fund allocation.",
        "net_asset_value": 485000,
        "equity_balance": Decimal("485000.00"),  # Total portfolio value as equity
        "positions": [
            # Individual Stocks (32% allocation - $155,000)
            {"symbol": "AAPL", "quantity": Decimal("85"), "entry_price": Decimal("225.00"), "entry_date": date(2024, 1, 15), "tags": ["Core Holdings", "Tech Growth"]},
            {"symbol": "MSFT", "quantity": Decimal("45"), "entry_price": Decimal("420.00"), "entry_date": date(2024, 1, 16), "tags": ["Core Holdings", "Tech Growth"]},
            {"symbol": "AMZN", "quantity": Decimal("110"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 18), "tags": ["Core Holdings", "Tech Growth"]},
            {"symbol": "GOOGL", "quantity": Decimal("115"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 20), "tags": ["Core Holdings", "Tech Growth"]},
            {"symbol": "TSLA", "quantity": Decimal("70"), "entry_price": Decimal("255.00"), "entry_date": date(2024, 1, 22), "tags": ["Tech Growth"]},
            {"symbol": "NVDA", "quantity": Decimal("25"), "entry_price": Decimal("700.00"), "entry_date": date(2024, 1, 25), "tags": ["Tech Growth"]},
            {"symbol": "JNJ", "quantity": Decimal("105"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 2, 1), "tags": ["Dividend Income"]},
            {"symbol": "JPM", "quantity": Decimal("85"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 2, 5), "tags": ["Dividend Income"]},
            {"symbol": "V", "quantity": Decimal("50"), "entry_price": Decimal("268.00"), "entry_date": date(2024, 2, 8), "tags": ["Core Holdings"]},

            # Mutual Funds - Using reasonable share prices for calculation
            # FXNAX: $87,300 at ~$20/share = 4365 shares
            {"symbol": "FXNAX", "quantity": Decimal("4365"), "entry_price": Decimal("20.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings", "Large Cap Growth"]},
            # FCNTX: $72,750 at ~$15/share = 4850 shares
            {"symbol": "FCNTX", "quantity": Decimal("4850"), "entry_price": Decimal("15.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings", "Large Cap Blend"]},
            # FMAGX: $58,200 at ~$15/share = 3880 shares
            {"symbol": "FMAGX", "quantity": Decimal("3880"), "entry_price": Decimal("15.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings", "International"]},
            # VTIAX: $29,100 at ~$30/share = 970 shares
            {"symbol": "VTIAX", "quantity": Decimal("970"), "entry_price": Decimal("30.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings", "International"]},

            # ETFs
            # VTI: $38,800 at ~$250/share = 155 shares
            {"symbol": "VTI", "quantity": Decimal("155"), "entry_price": Decimal("250.00"), "entry_date": date(2023, 11, 20), "tags": ["Core Holdings", "Total Market"]},
            # BND: $24,250 at ~$77/share = 315 shares
            {"symbol": "BND", "quantity": Decimal("315"), "entry_price": Decimal("77.00"), "entry_date": date(2023, 11, 20), "tags": ["Core Holdings", "Bonds"]},
            # VNQ: $19,400 at ~$95/share = 204 shares
            {"symbol": "VNQ", "quantity": Decimal("204"), "entry_price": Decimal("95.00"), "entry_date": date(2023, 11, 20), "tags": ["Core Holdings", "REITs"]},
        ]
    },
    {
        "user_email": "demo_hnw@sigmasight.com",
        "portfolio_id_seed": "demo_hnw@sigmasight.com_portfolio",
        "portfolio_name": "Demo High Net Worth Investor Portfolio",
        "description": "High net worth individual with access to private investments. Diversified across public markets with alternative investments.",
        "net_asset_value": 2850000,
        "equity_balance": Decimal("2850000.00"),  # Total portfolio value as equity
        "positions": [
            # Core ETF Holdings
            {"symbol": "SPY", "quantity": Decimal("400"), "entry_price": Decimal("530.00"), "entry_date": date(2024, 1, 5), "tags": ["Blue Chip", "Core Index"]},
            {"symbol": "QQQ", "quantity": Decimal("450"), "entry_price": Decimal("420.00"), "entry_date": date(2024, 1, 5), "tags": ["Blue Chip", "Tech Index"]},
            {"symbol": "VTI", "quantity": Decimal("800"), "entry_price": Decimal("230.00"), "entry_date": date(2024, 1, 5), "tags": ["Blue Chip", "Total Market"]},

            # Large Cap Holdings
            {"symbol": "AAPL", "quantity": Decimal("400"), "entry_price": Decimal("225.00"), "entry_date": date(2024, 1, 10), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "MSFT", "quantity": Decimal("200"), "entry_price": Decimal("420.00"), "entry_date": date(2024, 1, 10), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "AMZN", "quantity": Decimal("480"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 12), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "GOOGL", "quantity": Decimal("500"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 12), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "BRK-B", "quantity": Decimal("180"), "entry_price": Decimal("440.00"), "entry_date": date(2024, 1, 15), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "JPM", "quantity": Decimal("350"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 15), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "JNJ", "quantity": Decimal("310"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 18), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "NVDA", "quantity": Decimal("70"), "entry_price": Decimal("700.00"), "entry_date": date(2024, 1, 20), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "META", "quantity": Decimal("90"), "entry_price": Decimal("530.00"), "entry_date": date(2024, 1, 20), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "UNH", "quantity": Decimal("85"), "entry_price": Decimal("545.00"), "entry_date": date(2024, 1, 22), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "V", "quantity": Decimal("170"), "entry_price": Decimal("268.00"), "entry_date": date(2024, 1, 22), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "HD", "quantity": Decimal("125"), "entry_price": Decimal("350.00"), "entry_date": date(2024, 1, 25), "tags": ["Blue Chip", "Individual Stock"]},
            {"symbol": "PG", "quantity": Decimal("250"), "entry_price": Decimal("165.00"), "entry_date": date(2024, 1, 25), "tags": ["Blue Chip", "Individual Stock"]},

            # Alternative Assets
            {"symbol": "GLD", "quantity": Decimal("325"), "entry_price": Decimal("219.23"), "entry_date": date(2024, 2, 1), "tags": ["Alternative Assets", "Risk Hedge", "Gold"]},
            {"symbol": "DJP", "quantity": Decimal("1900"), "entry_price": Decimal("30.00"), "entry_date": date(2024, 2, 1), "tags": ["Alternative Assets", "Risk Hedge", "Commodities"]},

            # Private Investment Funds (25% allocation as per Ben Mock Portfolios.md)
            {"symbol": "BX_PRIVATE_EQUITY", "quantity": Decimal("1"), "entry_price": Decimal("285000.00"), "entry_date": date(2023, 6, 1), "tags": ["Private Investments", "Private Equity"]},
            {"symbol": "A16Z_VC_FUND", "quantity": Decimal("1"), "entry_price": Decimal("142500.00"), "entry_date": date(2023, 6, 1), "tags": ["Private Investments", "Venture Capital"]},
            {"symbol": "STARWOOD_REIT", "quantity": Decimal("1"), "entry_price": Decimal("142500.00"), "entry_date": date(2023, 6, 1), "tags": ["Private Investments", "Private REIT"]},
            {"symbol": "TWO_SIGMA_FUND", "quantity": Decimal("1"), "entry_price": Decimal("142500.00"), "entry_date": date(2023, 6, 1), "tags": ["Private Investments", "Hedge Fund"]},

            # Real Estate (20% allocation - $570K)
            {"symbol": "HOME_EQUITY", "quantity": Decimal("1"), "entry_price": Decimal("285000.00"), "entry_date": date(2023, 1, 15), "tags": ["Real Estate", "Primary Residence"]},
            {"symbol": "RENTAL_CONDO", "quantity": Decimal("1"), "entry_price": Decimal("142500.00"), "entry_date": date(2022, 6, 1), "tags": ["Real Estate", "Rental Property"]},
            {"symbol": "RENTAL_SFH", "quantity": Decimal("1"), "entry_price": Decimal("142500.00"), "entry_date": date(2021, 9, 1), "tags": ["Real Estate", "Rental Property"]},

            # Cryptocurrency (1.5% allocation - $42.75K)
            {"symbol": "CRYPTO_BTC_ETH", "quantity": Decimal("1"), "entry_price": Decimal("42750.00"), "entry_date": date(2023, 3, 1), "tags": ["Alternative Assets", "Cryptocurrency"]},

            # Art/Collectibles (1% allocation - $28.5K)
            {"symbol": "ART_COLLECTIBLES", "quantity": Decimal("1"), "entry_price": Decimal("28500.00"), "entry_date": date(2022, 11, 1), "tags": ["Alternative Assets", "Art"]},

            # Cash & Fixed Income (3% allocation - $85.5K)
            {"symbol": "MONEY_MARKET", "quantity": Decimal("1"), "entry_price": Decimal("57000.00"), "entry_date": date(2024, 1, 1), "tags": ["Cash", "Money Market"]},
            {"symbol": "TREASURY_BILLS", "quantity": Decimal("1"), "entry_price": Decimal("28500.00"), "entry_date": date(2024, 1, 1), "tags": ["Cash", "Fixed Income"]},
        ]
    },
    {
        "user_email": "demo_hedgefundstyle@sigmasight.com",
        "portfolio_id_seed": "demo_hedgefundstyle@sigmasight.com_portfolio",
        "portfolio_name": "Demo Hedge Fund Style Investor Portfolio",
        "description": "Sophisticated trader with derivatives access. Market-neutral with volatility trading and options overlay.",
        "net_asset_value": 3200000,
        "equity_balance": Decimal("3200000.00"),  # Total portfolio NAV as equity
        "positions": [
            # Long Positions - Growth/Momentum
            {"symbol": "NVDA", "quantity": Decimal("800"), "entry_price": Decimal("700.00"), "entry_date": date(2024, 1, 5), "tags": ["Long Momentum", "AI Play"]},
            {"symbol": "MSFT", "quantity": Decimal("1000"), "entry_price": Decimal("420.00"), "entry_date": date(2024, 1, 5), "tags": ["Long Momentum", "Cloud Dominance"]},
            {"symbol": "AAPL", "quantity": Decimal("1500"), "entry_price": Decimal("225.00"), "entry_date": date(2024, 1, 8), "tags": ["Long Momentum", "Ecosystem Moat"]},
            {"symbol": "GOOGL", "quantity": Decimal("1800"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 8), "tags": ["Long Momentum", "AI & Search"]},
            {"symbol": "META", "quantity": Decimal("1000"), "entry_price": Decimal("265.00"), "entry_date": date(2024, 1, 10), "tags": ["Long Momentum", "Metaverse"]},
            {"symbol": "AMZN", "quantity": Decimal("1400"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 10), "tags": ["Long Momentum", "AWS Growth"]},
            {"symbol": "TSLA", "quantity": Decimal("800"), "entry_price": Decimal("255.00"), "entry_date": date(2024, 1, 12), "tags": ["Long Momentum", "EV Revolution"]},
            {"symbol": "AMD", "quantity": Decimal("1200"), "entry_price": Decimal("162.00"), "entry_date": date(2024, 1, 12), "tags": ["Long Momentum", "Data Center"]},

            # Long Positions - Quality/Value
            {"symbol": "BRK-B", "quantity": Decimal("600"), "entry_price": Decimal("440.00"), "entry_date": date(2024, 1, 15), "tags": ["Long Value", "Quality"]},
            {"symbol": "JPM", "quantity": Decimal("1000"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 15), "tags": ["Long Value", "Bank Quality"]},
            {"symbol": "JNJ", "quantity": Decimal("800"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 18), "tags": ["Long Value", "Healthcare Defensive"]},
            {"symbol": "UNH", "quantity": Decimal("200"), "entry_price": Decimal("545.00"), "entry_date": date(2024, 1, 18), "tags": ["Long Value", "Healthcare Quality"]},
            {"symbol": "V", "quantity": Decimal("350"), "entry_price": Decimal("268.00"), "entry_date": date(2024, 1, 20), "tags": ["Long Value", "Payment Network"]},
            
            # Short Positions - Overvalued Growth
            {"symbol": "NFLX", "quantity": Decimal("-600"), "entry_price": Decimal("490.00"), "entry_date": date(2024, 1, 25), "tags": ["Short Value Traps"]},
            {"symbol": "SHOP", "quantity": Decimal("-1000"), "entry_price": Decimal("195.00"), "entry_date": date(2024, 1, 25), "tags": ["Short Value Traps"]},
            {"symbol": "ZM", "quantity": Decimal("-2000"), "entry_price": Decimal("70.00"), "entry_date": date(2024, 1, 28), "tags": ["Short Value Traps"]},
            {"symbol": "PTON", "quantity": Decimal("-3000"), "entry_price": Decimal("40.00"), "entry_date": date(2024, 1, 28), "tags": ["Short Value Traps"]},
            {"symbol": "ROKU", "quantity": Decimal("-1800"), "entry_price": Decimal("60.00"), "entry_date": date(2024, 1, 30), "tags": ["Short Value Traps"]},
            
            # Short Positions - Cyclical/Value
            {"symbol": "XOM", "quantity": Decimal("-2000"), "entry_price": Decimal("110.00"), "entry_date": date(2024, 2, 1), "tags": ["Short Value Traps"]},
            {"symbol": "F", "quantity": Decimal("-10000"), "entry_price": Decimal("12.00"), "entry_date": date(2024, 2, 1), "tags": ["Short Value Traps"]},
            {"symbol": "GE", "quantity": Decimal("-800"), "entry_price": Decimal("140.00"), "entry_date": date(2024, 2, 5), "tags": ["Short Value Traps"]},
            {"symbol": "C", "quantity": Decimal("-2000"), "entry_price": Decimal("55.00"), "entry_date": date(2024, 2, 5), "tags": ["Short Value Traps"]},
            
            # Options Positions - Long Calls (Upside/Volatility)
            {"symbol": "SPY250919C00460000", "quantity": Decimal("200"), "entry_price": Decimal("7.00"), "entry_date": date(2024, 1, 10), "tags": ["Options Overlay"], "underlying": "SPY", "strike": Decimal("460.00"), "expiry": date(2025, 9, 19), "option_type": "C"},
            {"symbol": "QQQ250815C00420000", "quantity": Decimal("150"), "entry_price": Decimal("7.00"), "entry_date": date(2024, 1, 10), "tags": ["Options Overlay"], "underlying": "QQQ", "strike": Decimal("420.00"), "expiry": date(2025, 8, 15), "option_type": "C"},
            {"symbol": "VIX250716C00025000", "quantity": Decimal("300"), "entry_price": Decimal("2.50"), "entry_date": date(2024, 1, 15), "tags": ["Options Overlay"], "underlying": "VIX", "strike": Decimal("25.00"), "expiry": date(2025, 7, 16), "option_type": "C"},
            {"symbol": "NVDA251017C00800000", "quantity": Decimal("50"), "entry_price": Decimal("12.50"), "entry_date": date(2024, 1, 15), "tags": ["Options Overlay"], "underlying": "NVDA", "strike": Decimal("800.00"), "expiry": date(2025, 10, 17), "option_type": "C"},
            
            # Options Positions - Short Puts (Premium Collection)
            {"symbol": "AAPL250815P00200000", "quantity": Decimal("-100"), "entry_price": Decimal("4.50"), "entry_date": date(2024, 1, 20), "tags": ["Options Overlay"], "underlying": "AAPL", "strike": Decimal("200.00"), "expiry": date(2025, 8, 15), "option_type": "P"},
            {"symbol": "MSFT250919P00380000", "quantity": Decimal("-80"), "entry_price": Decimal("5.00"), "entry_date": date(2024, 1, 20), "tags": ["Options Overlay"], "underlying": "MSFT", "strike": Decimal("380.00"), "expiry": date(2025, 9, 19), "option_type": "P"},
            {"symbol": "TSLA250815C00300000", "quantity": Decimal("-60"), "entry_price": Decimal("8.00"), "entry_date": date(2024, 1, 25), "tags": ["Options Overlay"], "underlying": "TSLA", "strike": Decimal("300.00"), "expiry": date(2025, 8, 15), "option_type": "C"},
            {"symbol": "META250919P00450000", "quantity": Decimal("-50"), "entry_price": Decimal("7.50"), "entry_date": date(2024, 1, 25), "tags": ["Options Overlay"], "underlying": "META", "strike": Decimal("450.00"), "expiry": date(2025, 9, 19), "option_type": "P"},
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
            {"symbol": "XLK", "quantity": Decimal("600"), "entry_price": Decimal("180.00"), "entry_date": date(2024, 3, 15), "tags": ["Thematic Growth", "Tech Allocation"]},
            {"symbol": "SMH", "quantity": Decimal("500"), "entry_price": Decimal("210.00"), "entry_date": date(2024, 3, 18), "tags": ["Thematic Growth", "Semiconductors"]},
            {"symbol": "IGV", "quantity": Decimal("400"), "entry_price": Decimal("330.00"), "entry_date": date(2024, 3, 20), "tags": ["Thematic Growth", "Software"]},
            {"symbol": "XLY", "quantity": Decimal("450"), "entry_price": Decimal("185.00"), "entry_date": date(2024, 3, 25), "tags": ["Consumer Discretionary", "Cyclical Tilt"]},
            {"symbol": "COST", "quantity": Decimal("220"), "entry_price": Decimal("720.00"), "entry_date": date(2024, 4, 2), "tags": ["Quality Compounder", "Defensive Growth"]},
            {"symbol": "AVGO", "quantity": Decimal("140"), "entry_price": Decimal("1350.00"), "entry_date": date(2024, 4, 5), "tags": ["Quality Compounder", "Semiconductors"]},
            {"symbol": "ASML", "quantity": Decimal("160"), "entry_price": Decimal("960.00"), "entry_date": date(2024, 4, 8), "tags": ["Quality Compounder", "International"]},
            {"symbol": "LULU", "quantity": Decimal("300"), "entry_price": Decimal("380.00"), "entry_date": date(2024, 4, 12), "tags": ["Consumer Discretionary", "Lifestyle Brand"]},
            {"symbol": "NEE", "quantity": Decimal("500"), "entry_price": Decimal("70.00"), "entry_date": date(2024, 4, 15), "tags": ["Defensive Yield", "Clean Energy"]},
            {"symbol": "SCHD", "quantity": Decimal("650"), "entry_price": Decimal("75.00"), "entry_date": date(2024, 4, 18), "tags": ["Defensive Yield", "Dividend Growth"]},
            {"symbol": "JEPQ", "quantity": Decimal("700"), "entry_price": Decimal("54.00"), "entry_date": date(2024, 4, 22), "tags": ["Options Overlay", "Income"]},
            {"symbol": "BIL", "quantity": Decimal("900"), "entry_price": Decimal("91.50"), "entry_date": date(2024, 4, 25), "tags": ["Liquidity Reserve", "Cash Management"]},
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
            {"symbol": "FO_PRIVATE_CREDIT_FUND", "quantity": Decimal("1"), "entry_price": Decimal("225000.00"), "entry_date": date(2023, 9, 1), "tags": ["Private Credit", "Income"]},
            {"symbol": "FO_GROWTH_PE_FUND", "quantity": Decimal("1"), "entry_price": Decimal("210000.00"), "entry_date": date(2023, 9, 1), "tags": ["Private Equity", "Growth"]},
            {"symbol": "FO_VC_SECONDARIES_FUND", "quantity": Decimal("1"), "entry_price": Decimal("145000.00"), "entry_date": date(2023, 10, 1), "tags": ["Venture Capital", "Secondaries"]},
            {"symbol": "FO_REAL_ASSET_REIT", "quantity": Decimal("1"), "entry_price": Decimal("110000.00"), "entry_date": date(2023, 10, 15), "tags": ["Private REIT", "Real Assets"]},
            {"symbol": "FO_INFRASTRUCTURE_FUND", "quantity": Decimal("1"), "entry_price": Decimal("90000.00"), "entry_date": date(2023, 11, 1), "tags": ["Infrastructure", "Inflation Protection"]},
            {"symbol": "FO_HOME_RENTAL_PORTFOLIO", "quantity": Decimal("1"), "entry_price": Decimal("85000.00"), "entry_date": date(2023, 11, 20), "tags": ["Real Estate", "Rental Portfolio"]},
            {"symbol": "FO_IMPACT_LENDING_FUND", "quantity": Decimal("1"), "entry_price": Decimal("55000.00"), "entry_date": date(2024, 1, 5), "tags": ["Impact Investing", "Sustainable"]},
            {"symbol": "FO_ART_COLLECTIVE", "quantity": Decimal("1"), "entry_price": Decimal("30000.00"), "entry_date": date(2024, 2, 1), "tags": ["Alternative Assets", "Art"]},
            {"symbol": "FO_CRYPTO_DIGITAL_TRUST", "quantity": Decimal("1"), "entry_price": Decimal("30000.00"), "entry_date": date(2024, 2, 15), "tags": ["Alternative Assets", "Digital Assets"]},
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
    # New patterns (Phase 8.1): HOME_, RENTAL_, ART_, CRYPTO_, TREASURY, MONEY_MARKET
    private_patterns = [
        'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',  # Original
        'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET'  # New (Phase 8.1)
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

# Note: Tag backfill function removed due to SQLAlchemy async relationship access issues
# The function _add_missing_tags_to_positions would be here if async relationships worked properly

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
            logger.info(f"✅ Updated portfolio {existing_portfolio.name} with {missing_count} new positions")
        else:
            logger.info(f"Portfolio already has all {expected_positions} positions - no update needed")
            # Note: Tag backfill disabled due to SQLAlchemy async relationship access issues
            # Tags work correctly for newly created positions
            
        return existing_portfolio
    
    # Create portfolio with deterministic ID for development consistency
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=user.id,
        name=portfolio_data["portfolio_name"],
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
    """Seed all demo portfolios from Ben Mock Portfolios.md"""
    logger.info("🏗️ Seeding demo portfolios...")
    
    portfolios_created = 0
    total_positions = 0
    
    for portfolio_data in DEMO_PORTFOLIOS:
        portfolio = await create_demo_portfolio(db, portfolio_data)
        portfolios_created += 1
        total_positions += len(portfolio_data["positions"])
    
    logger.info(f"✅ Created {portfolios_created} demo portfolios with {total_positions} total positions")
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
