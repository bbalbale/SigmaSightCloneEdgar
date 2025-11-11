"""
Demo Family Office User Seeding - Multi-Portfolio Implementation
Creates demo_familyoffice user with 2 portfolios (Public Growth + Private Opportunities)
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
from app.models.positions import Position, PositionType
from app.models.tags_v2 import TagV2
from app.services.position_tag_service import PositionTagService

logger = get_logger(__name__)

def generate_deterministic_uuid(seed_string: str) -> UUID:
    """Generate consistent UUID from seed string - DEVELOPMENT ONLY

    Creates the same UUID on every machine for the same input string.
    This ensures all developers get identical portfolio IDs for demo data.
    """
    hash_hex = hashlib.md5(seed_string.encode()).hexdigest()
    return UUID(hash_hex)

# Demo family office user
DEMO_FAMILY_OFFICE_USER = {
    "email": "demo_familyoffice@sigmasight.com",
    "full_name": "Demo Family Office Manager",
    "password": "demo12345",
    "strategy": "Family office with dedicated public growth and private alternatives mandates"
}

# Demo family office portfolios (2 portfolios)
DEMO_FAMILY_OFFICE_PORTFOLIOS = [
    {
        "user_email": "demo_familyoffice@sigmasight.com",
        "portfolio_id_seed": "demo_familyoffice@sigmasight.com_public_growth",
        "portfolio_name": "Demo Family Office Public Growth",
        "account_name": "Public Growth",
        "account_type": "taxable",
        "description": "Public markets growth sleeve for the family office combining thematic ETFs with quality compounders and defensive yield.",
        "net_asset_value": 1250000,
        "equity_balance": Decimal("1250000.00"),
        "positions": [
            # Thematic ETFs
            {"symbol": "XLK", "quantity": Decimal("600"), "entry_price": Decimal("180.00"), "entry_date": date(2024, 3, 15), "tags": ["Thematic Growth", "Tech Allocation"]},
            {"symbol": "SMH", "quantity": Decimal("500"), "entry_price": Decimal("210.00"), "entry_date": date(2024, 3, 18), "tags": ["Thematic Growth", "Semiconductors"]},
            {"symbol": "IGV", "quantity": Decimal("400"), "entry_price": Decimal("330.00"), "entry_date": date(2024, 3, 20), "tags": ["Thematic Growth", "Software"]},
            {"symbol": "XLY", "quantity": Decimal("450"), "entry_price": Decimal("185.00"), "entry_date": date(2024, 3, 25), "tags": ["Consumer Discretionary", "Cyclical Tilt"]},

            # Quality Compounders
            {"symbol": "COST", "quantity": Decimal("220"), "entry_price": Decimal("720.00"), "entry_date": date(2024, 4, 2), "tags": ["Quality Compounder", "Defensive Growth"]},
            {"symbol": "AVGO", "quantity": Decimal("140"), "entry_price": Decimal("1350.00"), "entry_date": date(2024, 4, 5), "tags": ["Quality Compounder", "Semiconductors"]},
            {"symbol": "ASML", "quantity": Decimal("160"), "entry_price": Decimal("960.00"), "entry_date": date(2024, 4, 8), "tags": ["Quality Compounder", "International"]},
            {"symbol": "LULU", "quantity": Decimal("300"), "entry_price": Decimal("380.00"), "entry_date": date(2024, 4, 12), "tags": ["Consumer Discretionary", "Lifestyle Brand"]},

            # Defensive Yield
            {"symbol": "NEE", "quantity": Decimal("500"), "entry_price": Decimal("70.00"), "entry_date": date(2024, 4, 15), "tags": ["Defensive Yield", "Clean Energy"]},
            {"symbol": "SCHD", "quantity": Decimal("650"), "entry_price": Decimal("75.00"), "entry_date": date(2024, 4, 18), "tags": ["Defensive Yield", "Dividend Growth"]},

            # Options Overlay
            {"symbol": "JEPQ", "quantity": Decimal("700"), "entry_price": Decimal("54.00"), "entry_date": date(2024, 4, 22), "tags": ["Options Overlay", "Income"]},

            # Liquidity Reserve
            {"symbol": "BIL", "quantity": Decimal("900"), "entry_price": Decimal("91.50"), "entry_date": date(2024, 4, 25), "tags": ["Liquidity Reserve", "Cash Management"]},
        ]
    },
    {
        "user_email": "demo_familyoffice@sigmasight.com",
        "portfolio_id_seed": "demo_familyoffice@sigmasight.com_private_opportunities",
        "portfolio_name": "Demo Family Office Private Opportunities",
        "account_name": "Private Opportunities",
        "account_type": "taxable",
        "description": "Private market and real asset sleeve emphasizing income, diversification, and inflation protection.",
        "net_asset_value": 950000,
        "equity_balance": Decimal("950000.00"),
        "positions": [
            # Private Credit & PE
            {"symbol": "FO_PRIVATE_CREDIT", "quantity": Decimal("1"), "entry_price": Decimal("225000.00"), "entry_date": date(2023, 9, 1), "tags": ["Private Credit", "Income"]},
            {"symbol": "FO_GROWTH_PE", "quantity": Decimal("1"), "entry_price": Decimal("210000.00"), "entry_date": date(2023, 9, 1), "tags": ["Private Equity", "Growth"]},
            {"symbol": "FO_VC_SECONDARIES", "quantity": Decimal("1"), "entry_price": Decimal("145000.00"), "entry_date": date(2023, 10, 1), "tags": ["Venture Capital", "Secondaries"]},

            # Real Assets
            {"symbol": "FO_REAL_ASSET_REIT", "quantity": Decimal("1"), "entry_price": Decimal("110000.00"), "entry_date": date(2023, 10, 15), "tags": ["Private REIT", "Real Assets"]},
            {"symbol": "FO_INFRASTRUCTURE", "quantity": Decimal("1"), "entry_price": Decimal("90000.00"), "entry_date": date(2023, 11, 1), "tags": ["Infrastructure", "Inflation Protection"]},
            {"symbol": "FO_HOME_RENTAL", "quantity": Decimal("1"), "entry_price": Decimal("85000.00"), "entry_date": date(2023, 11, 20), "tags": ["Real Estate", "Rental Portfolio"]},

            # Impact & Alternatives
            {"symbol": "FO_IMPACT_LENDING", "quantity": Decimal("1"), "entry_price": Decimal("55000.00"), "entry_date": date(2024, 1, 5), "tags": ["Impact Investing", "Sustainable"]},
            {"symbol": "FO_ART_COLLECTIVE", "quantity": Decimal("1"), "entry_price": Decimal("30000.00"), "entry_date": date(2024, 2, 1), "tags": ["Alternative Assets", "Art"]},
            {"symbol": "FO_CRYPTO_DIGITAL", "quantity": Decimal("1"), "entry_price": Decimal("30000.00"), "entry_date": date(2024, 2, 15), "tags": ["Alternative Assets", "Digital Assets"]},
        ]
    }
]


async def seed_demo_familyoffice(session: AsyncSession) -> Dict[str, Any]:
    """
    Seed demo family office user with 2 portfolios.

    Returns:
        Dict with seeding statistics
    """
    stats = {
        "user_created": False,
        "portfolios_created": 0,
        "positions_created": 0,
        "tags_created": 0,
        "position_tags_created": 0,
        "errors": []
    }

    try:
        # 1. Check if user already exists
        logger.info(f"Checking for existing user: {DEMO_FAMILY_OFFICE_USER['email']}")
        existing_user = await session.execute(
            select(User).where(User.email == DEMO_FAMILY_OFFICE_USER['email'])
        )
        user = existing_user.scalar_one_or_none()

        if user:
            logger.info(f"User {DEMO_FAMILY_OFFICE_USER['email']} already exists, will add portfolios if missing")
        else:
            # Create user
            logger.info(f"Creating demo family office user: {DEMO_FAMILY_OFFICE_USER['email']}")
            user = User(
                id=generate_deterministic_uuid(DEMO_FAMILY_OFFICE_USER['email']),
                email=DEMO_FAMILY_OFFICE_USER['email'],
                full_name=DEMO_FAMILY_OFFICE_USER['full_name'],
                hashed_password=get_password_hash(DEMO_FAMILY_OFFICE_USER['password']),
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(user)
            await session.flush()
            stats["user_created"] = True
            logger.info(f"Created user: {user.email}")

        # 2. Create portfolios
        position_tag_service = PositionTagService(session)

        for portfolio_data in DEMO_FAMILY_OFFICE_PORTFOLIOS:
            # Check if portfolio already exists
            portfolio_id = generate_deterministic_uuid(portfolio_data['portfolio_id_seed'])
            existing_portfolio = await session.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = existing_portfolio.scalar_one_or_none()

            if portfolio:
                logger.info(f"Portfolio {portfolio_data['portfolio_name']} already exists, skipping")
                continue

            # Create portfolio with new fields for multi-portfolio support
            logger.info(f"Creating portfolio: {portfolio_data['portfolio_name']}")
            portfolio = Portfolio(
                id=portfolio_id,
                user_id=user.id,
                name=portfolio_data['portfolio_name'],
                account_name=portfolio_data['account_name'],  # NEW: For multi-portfolio
                account_type=portfolio_data['account_type'],  # NEW: For multi-portfolio
                description=portfolio_data['description'],
                equity_balance=portfolio_data['equity_balance'],
                is_active=True,  # NEW: For multi-portfolio
                created_at=datetime.utcnow()
            )
            session.add(portfolio)
            await session.flush()
            stats["portfolios_created"] += 1
            logger.info(f"Created portfolio: {portfolio.name}")

            # 3. Create positions
            for position_data in portfolio_data['positions']:
                # Determine position type and investment class
                symbol = position_data['symbol']
                if symbol.startswith('FO_'):
                    # Private investment
                    position_type = PositionType.LONG
                    investment_class = "PRIVATE"
                else:
                    # Public equity/ETF
                    position_type = PositionType.LONG
                    investment_class = "PUBLIC"

                logger.info(f"  Creating position: {symbol} ({position_data['quantity']} shares)")
                position = Position(
                    id=uuid4(),
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    quantity=position_data['quantity'],
                    entry_price=position_data['entry_price'],
                    entry_date=position_data['entry_date'],
                    position_type=position_type,
                    investment_class=investment_class,
                    created_at=datetime.utcnow()
                )
                session.add(position)
                await session.flush()
                stats["positions_created"] += 1

                # 4. Create and apply tags
                for tag_name in position_data.get('tags', []):
                    # Check if tag exists
                    existing_tag = await session.execute(
                        select(TagV2).where(TagV2.name == tag_name)
                    )
                    tag = existing_tag.scalar_one_or_none()

                    if not tag:
                        # Create tag
                        tag = TagV2(
                            id=uuid4(),
                            name=tag_name,
                            user_id=user.id,
                            created_at=datetime.utcnow()
                        )
                        session.add(tag)
                        await session.flush()
                        stats["tags_created"] += 1
                        logger.info(f"    Created tag: {tag_name}")

                    # Apply tag to position
                    await position_tag_service.assign_tag_to_position(position.id, tag.id)
                    stats["position_tags_created"] += 1

        # Commit all changes
        await session.commit()
        logger.info("Demo family office seeding complete!")
        logger.info(f"   User created: {stats['user_created']}")
        logger.info(f"   Portfolios created: {stats['portfolios_created']}")
        logger.info(f"   Positions created: {stats['positions_created']}")
        logger.info(f"   Tags created: {stats['tags_created']}")
        logger.info(f"   Position tags created: {stats['position_tags_created']}")

        return stats

    except Exception as e:
        await session.rollback()
        error_msg = f"Error seeding demo family office: {e}"
        logger.error(error_msg)
        stats["errors"].append(error_msg)
        raise


async def main():
    """Main entry point for running seed script directly"""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        stats = await seed_demo_familyoffice(session)

        print("\n" + "="*60)
        print("DEMO FAMILY OFFICE SEEDING RESULTS")
        print("="*60)
        print(f"User Created: {stats['user_created']}")
        print(f"Portfolios Created: {stats['portfolios_created']}")
        print(f"Positions Created: {stats['positions_created']}")
        print(f"Tags Created: {stats['tags_created']}")
        print(f"Position Tags Created: {stats['position_tags_created']}")
        if stats['errors']:
            print(f"\nErrors: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"  - {error}")
        else:
            print("\nSeeding completed successfully!")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
