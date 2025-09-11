"""
Demo Portfolio Seeding - Section 1.5 Implementation
Creates the 3 demo portfolios from Ben Mock Portfolios.md with complete position data
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4, UUID
import hashlib
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.core.auth import get_password_hash
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType, Tag, TagType

logger = get_logger(__name__)

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
    }
]

# Demo portfolio specifications from Ben Mock Portfolios.md
DEMO_PORTFOLIOS = [
    {
        "user_email": "demo_individual@sigmasight.com",
        "portfolio_name": "Demo Individual Investor Portfolio",
        "description": "Individual investor with 401k, IRA, and taxable accounts. Core holdings with growth tilt, heavy mutual fund allocation.",
        "total_value": 485000,
        "equity_balance": Decimal("600000.00"),  # User-provided NAV for risk calculations
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
            
            # Mutual Funds (25% allocation - $121,350)
            {"symbol": "FXNAX", "quantity": Decimal("4365"), "entry_price": Decimal("20.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings"]},
            {"symbol": "FCNTX", "quantity": Decimal("4853"), "entry_price": Decimal("15.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings"]},
            {"symbol": "FMAGX", "quantity": Decimal("3880"), "entry_price": Decimal("15.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings"]},
            {"symbol": "VTIAX", "quantity": Decimal("970"), "entry_price": Decimal("30.00"), "entry_date": date(2023, 12, 15), "tags": ["Core Holdings"]},
            
            # ETFs (14% allocation - $67,850)
            {"symbol": "VTI", "quantity": Decimal("155"), "entry_price": Decimal("250.00"), "entry_date": date(2023, 11, 20), "tags": ["Core Holdings"]},
            {"symbol": "BND", "quantity": Decimal("315"), "entry_price": Decimal("77.00"), "entry_date": date(2023, 11, 20), "tags": ["Core Holdings"]},
            {"symbol": "VNQ", "quantity": Decimal("205"), "entry_price": Decimal("95.00"), "entry_date": date(2023, 11, 20), "tags": ["Core Holdings"]},
        ]
    },
    {
        "user_email": "demo_hnw@sigmasight.com", 
        "portfolio_name": "Demo High Net Worth Investor Portfolio",
        "description": "High net worth individual with access to private investments. Diversified across public markets with alternative investments.",
        "total_value": 2850000,
        "equity_balance": Decimal("2000000.00"),  # User-provided NAV for risk calculations
        "positions": [
            # Core ETF Holdings
            {"symbol": "SPY", "quantity": Decimal("400"), "entry_price": Decimal("530.00"), "entry_date": date(2024, 1, 5), "tags": ["Blue Chip"]},
            {"symbol": "QQQ", "quantity": Decimal("450"), "entry_price": Decimal("420.00"), "entry_date": date(2024, 1, 5), "tags": ["Blue Chip"]},
            
            # Large Cap Holdings
            {"symbol": "AAPL", "quantity": Decimal("400"), "entry_price": Decimal("225.00"), "entry_date": date(2024, 1, 10), "tags": ["Blue Chip"]},
            {"symbol": "MSFT", "quantity": Decimal("200"), "entry_price": Decimal("420.00"), "entry_date": date(2024, 1, 10), "tags": ["Blue Chip"]},
            {"symbol": "AMZN", "quantity": Decimal("480"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 12), "tags": ["Blue Chip"]},
            {"symbol": "GOOGL", "quantity": Decimal("500"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 12), "tags": ["Blue Chip"]},
            {"symbol": "BRK-B", "quantity": Decimal("180"), "entry_price": Decimal("440.00"), "entry_date": date(2024, 1, 15), "tags": ["Blue Chip"]},
            {"symbol": "JPM", "quantity": Decimal("350"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 15), "tags": ["Blue Chip"]},
            {"symbol": "JNJ", "quantity": Decimal("310"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 18), "tags": ["Blue Chip"]},
            {"symbol": "NVDA", "quantity": Decimal("70"), "entry_price": Decimal("700.00"), "entry_date": date(2024, 1, 20), "tags": ["Blue Chip"]},
            {"symbol": "META", "quantity": Decimal("90"), "entry_price": Decimal("530.00"), "entry_date": date(2024, 1, 20), "tags": ["Blue Chip"]},
            {"symbol": "UNH", "quantity": Decimal("85"), "entry_price": Decimal("545.00"), "entry_date": date(2024, 1, 22), "tags": ["Blue Chip"]},
            {"symbol": "V", "quantity": Decimal("170"), "entry_price": Decimal("268.00"), "entry_date": date(2024, 1, 22), "tags": ["Blue Chip"]},
            {"symbol": "HD", "quantity": Decimal("125"), "entry_price": Decimal("350.00"), "entry_date": date(2024, 1, 25), "tags": ["Blue Chip"]},
            {"symbol": "PG", "quantity": Decimal("250"), "entry_price": Decimal("165.00"), "entry_date": date(2024, 1, 25), "tags": ["Blue Chip"]},
            
            # Alternative Assets
            {"symbol": "GLD", "quantity": Decimal("325"), "entry_price": Decimal("219.23"), "entry_date": date(2024, 2, 1), "tags": ["Alternative Assets", "Risk Hedge"]},
            {"symbol": "DJP", "quantity": Decimal("1900"), "entry_price": Decimal("30.00"), "entry_date": date(2024, 2, 1), "tags": ["Alternative Assets", "Risk Hedge"]},
        ]
    },
    {
        "user_email": "demo_hedgefundstyle@sigmasight.com",
        "portfolio_name": "Demo Hedge Fund Style Investor Portfolio", 
        "description": "Sophisticated trader with derivatives access. Market-neutral with volatility trading and options overlay.",
        "total_value": 3200000,
        "equity_balance": Decimal("4000000.00"),  # User-provided NAV for risk calculations
        "positions": [
            # Long Positions - Growth/Momentum
            {"symbol": "NVDA", "quantity": Decimal("800"), "entry_price": Decimal("700.00"), "entry_date": date(2024, 1, 5), "tags": ["Long Momentum"]},
            {"symbol": "MSFT", "quantity": Decimal("1000"), "entry_price": Decimal("420.00"), "entry_date": date(2024, 1, 5), "tags": ["Long Momentum"]},
            {"symbol": "AAPL", "quantity": Decimal("1500"), "entry_price": Decimal("225.00"), "entry_date": date(2024, 1, 8), "tags": ["Long Momentum"]},
            {"symbol": "GOOGL", "quantity": Decimal("1800"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 8), "tags": ["Long Momentum"]},
            {"symbol": "META", "quantity": Decimal("1000"), "entry_price": Decimal("265.00"), "entry_date": date(2024, 1, 10), "tags": ["Long Momentum"]},
            {"symbol": "AMZN", "quantity": Decimal("1400"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 10), "tags": ["Long Momentum"]},
            {"symbol": "TSLA", "quantity": Decimal("800"), "entry_price": Decimal("255.00"), "entry_date": date(2024, 1, 12), "tags": ["Long Momentum"]},
            {"symbol": "AMD", "quantity": Decimal("1200"), "entry_price": Decimal("162.00"), "entry_date": date(2024, 1, 12), "tags": ["Long Momentum"]},
            
            # Long Positions - Quality/Value 
            {"symbol": "BRK-B", "quantity": Decimal("600"), "entry_price": Decimal("440.00"), "entry_date": date(2024, 1, 15), "tags": ["Long Momentum"]},
            {"symbol": "JPM", "quantity": Decimal("1000"), "entry_price": Decimal("170.00"), "entry_date": date(2024, 1, 15), "tags": ["Long Momentum"]},
            {"symbol": "JNJ", "quantity": Decimal("800"), "entry_price": Decimal("160.00"), "entry_date": date(2024, 1, 18), "tags": ["Long Momentum"]},
            {"symbol": "UNH", "quantity": Decimal("200"), "entry_price": Decimal("545.00"), "entry_date": date(2024, 1, 18), "tags": ["Long Momentum"]},
            {"symbol": "V", "quantity": Decimal("350"), "entry_price": Decimal("268.00"), "entry_date": date(2024, 1, 20), "tags": ["Long Momentum"]},
            
            # Short Positions - Overvalued Growth
            {"symbol": "NFLX", "quantity": Decimal("-600"), "entry_price": Decimal("490.00"), "entry_date": date(2024, 1, 25), "tags": ["Short Value Traps"]},
            {"symbol": "SHOP", "quantity": Decimal("-1000"), "entry_price": Decimal("195.00"), "entry_date": date(2024, 1, 25), "tags": ["Short Value Traps"]},
            {"symbol": "ZOOM", "quantity": Decimal("-2000"), "entry_price": Decimal("70.00"), "entry_date": date(2024, 1, 28), "tags": ["Short Value Traps"]},
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

async def get_or_create_tag(db: AsyncSession, user_id: str, tag_name: str) -> Tag:
    """Get existing tag or create new one"""
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id, Tag.name == tag_name)
    )
    tag = result.scalar_one_or_none()
    
    if not tag:
        tag = Tag(
            id=generate_deterministic_uuid(f"{user_id}_{tag_name}_tag"),
            user_id=user_id,
            name=tag_name,
            tag_type=TagType.STRATEGY if tag_name in ["Long Momentum", "Short Value Traps", "Options Overlay"] else TagType.REGULAR
        )
        db.add(tag)
    
    return tag

def determine_position_type(symbol: str, quantity: Decimal) -> PositionType:
    """Determine position type from symbol and quantity"""
    if len(symbol) > 10 and any(char in symbol for char in ['C', 'P']):  # Options symbol
        is_call = 'C' in symbol[-9:]  # Check last 9 chars for option type
        if quantity > 0:
            return PositionType.LC if is_call else PositionType.LP
        else:
            return PositionType.SC if is_call else PositionType.SP
    else:  # Stock symbol
        return PositionType.LONG if quantity > 0 else PositionType.SHORT

async def _add_positions_to_portfolio(db: AsyncSession, portfolio: Portfolio, position_data_list: List[Dict[str, Any]], user: User, existing_symbols: set = None) -> int:
    """Helper function to add positions to a portfolio, avoiding duplicates"""
    if existing_symbols is None:
        existing_symbols = set()
    
    position_count = 0
    for pos_data in position_data_list:
        symbol = pos_data["symbol"]
        
        # Skip if position already exists
        if symbol in existing_symbols:
            continue
        
        # Determine position type
        position_type = determine_position_type(symbol, pos_data["quantity"])
        
        # Create position with deterministic ID for development consistency
        position = Position(
            id=generate_deterministic_uuid(f"{portfolio.id}_{symbol}_{pos_data['entry_date']}"),
            portfolio_id=portfolio.id,
            symbol=symbol,
            position_type=position_type,
            quantity=pos_data["quantity"],
            entry_price=pos_data["entry_price"],
            entry_date=pos_data["entry_date"],
        )
        
        # Add options-specific fields if present
        if "underlying" in pos_data:
            position.underlying_symbol = pos_data["underlying"]
            position.strike_price = pos_data["strike"]
            position.expiration_date = pos_data["expiry"]
        
        db.add(position)
        await db.flush()  # Get position ID
        
        # Create and associate tags (manual relationship via association table)
        if pos_data.get("tags"):
            await db.flush()  # Ensure position is saved first
            for tag_name in pos_data.get("tags", []):
                tag = await get_or_create_tag(db, user.id, tag_name)
                await db.flush()  # Ensure tag is saved
                
                # Manually insert into association table to avoid async issues
                from sqlalchemy import text
                await db.execute(
                    text("INSERT INTO position_tags (position_id, tag_id) VALUES (:pos_id, :tag_id) ON CONFLICT DO NOTHING"),
                    {"pos_id": position.id, "tag_id": tag.id}
                )
            
            await db.flush()  # Commit the tag relationships
        
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
    
    # Check if user already has ANY portfolio (one portfolio per user constraint)
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    existing_portfolio = result.scalar_one_or_none()
    
    if existing_portfolio:
        logger.info(f"User {user.email} already has portfolio: {existing_portfolio.name}")
        
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
        id=generate_deterministic_uuid(f"{user.email}_portfolio"),
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