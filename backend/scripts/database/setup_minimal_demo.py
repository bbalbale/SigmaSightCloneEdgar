#!/usr/bin/env python3
"""
Bulletproof Demo User Setup - Avoids All Async/Sync Issues
Creates minimal demo users and portfolios without complex relationships
"""
import asyncio
import uuid
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
from passlib.context import CryptContext
from dotenv import load_dotenv

from app.models.users import User, Portfolio

# Load environment
load_dotenv()

# Password hashing
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# Demo users configuration
DEMO_USERS = [
    {
        "email": "demo_individual@sigmasight.com",
        "full_name": "Demo Individual Investor",
        "password": "demo12345",
        "portfolio_name": "Demo Individual Investor Portfolio",
        "portfolio_desc": "Balanced growth portfolio for individual investor"
    },
    {
        "email": "demo_hnw@sigmasight.com", 
        "full_name": "Demo High Net Worth Investor",
        "password": "demo12345",
        "portfolio_name": "Demo High Net Worth Investor Portfolio",
        "portfolio_desc": "Sophisticated portfolio with alternatives and private investments"
    },
    {
        "email": "demo_hedgefundstyle@sigmasight.com",
        "full_name": "Demo Hedge Fund Style Investor",
        "password": "demo12345",
        "portfolio_name": "Demo Hedge Fund Style Investor Portfolio", 
        "portfolio_desc": "Long/short equity with options overlay"
    }
]


async def check_database_connection(engine) -> bool:
    """Test database connectivity"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def user_exists(db: AsyncSession, email: str) -> bool:
    """Check if user already exists"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none() is not None


async def create_single_user_portfolio(db: AsyncSession, user_data: dict) -> tuple[Optional[User], Optional[Portfolio]]:
    """
    Create a single user and portfolio with proper async handling
    Returns (user, portfolio) or (None, None) on error
    """
    try:
        # Create user
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password=pwd_context.hash(user_data["password"]),
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(user)
        
        # Create portfolio
        portfolio_id = uuid.uuid4()
        portfolio = Portfolio(
            id=portfolio_id,
            user_id=user_id,
            name=user_data["portfolio_name"],
            description=user_data["portfolio_desc"],
            currency='USD',
            created_at=datetime.now(timezone.utc)
        )
        db.add(portfolio)
        
        # Commit both together
        await db.commit()
        
        return user, portfolio
        
    except Exception as e:
        print(f"❌ Failed to create user {user_data['email']}: {e}")
        await db.rollback()
        return None, None


async def setup_demo_users():
    """Main setup function - creates demo users safely"""
    
    # Validate database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
        
    # Create async engine
    engine = create_async_engine(database_url)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # Test connection first
        print("🔍 Testing database connection...")
        if not await check_database_connection(engine):
            return False
        print("✅ Database connection successful")
        
        # Check existing users
        print("\n🔍 Checking for existing demo users...")
        async with session_factory() as db:
            existing_count = 0
            for user_data in DEMO_USERS:
                if await user_exists(db, user_data["email"]):
                    existing_count += 1
                    print(f"✅ {user_data['email']} already exists")
            
            if existing_count == len(DEMO_USERS):
                print(f"\n✅ All {len(DEMO_USERS)} demo users already exist")
                return True
                
            # Create missing users
            print(f"\n🔨 Creating {len(DEMO_USERS) - existing_count} missing demo users...")
            created_count = 0
            
            for user_data in DEMO_USERS:
                if not await user_exists(db, user_data["email"]):
                    # Create new session for each user to avoid conflicts
                    async with session_factory() as user_db:
                        user, portfolio = await create_single_user_portfolio(user_db, user_data)
                        if user and portfolio:
                            created_count += 1
                            print(f"✅ Created {user_data['email']} with portfolio")
                        else:
                            print(f"❌ Failed to create {user_data['email']}")
            
            print(f"\n🎉 Setup complete!")
            print(f"✅ Created {created_count} new users")
            print(f"✅ Total demo users: {existing_count + created_count}")
            
            # Display login information
            print(f"\n📝 Demo Login Credentials:")
            for user_data in DEMO_USERS:
                print(f"   • {user_data['email']} / {user_data['password']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
        
    finally:
        await engine.dispose()


async def verify_setup():
    """Verify all demo users and portfolios were created correctly"""
    database_url = os.getenv('DATABASE_URL')
    engine = create_async_engine(database_url)
    
    try:
        async with engine.connect() as conn:
            # Count users
            result = await conn.execute(text("SELECT COUNT(*) FROM users WHERE email LIKE '%@sigmasight.com'"))
            user_count = result.scalar()
            
            # Count portfolios
            result = await conn.execute(text("SELECT COUNT(*) FROM portfolios"))
            portfolio_count = result.scalar()
            
            # Get user details
            result = await conn.execute(text("SELECT email, full_name FROM users WHERE email LIKE '%@sigmasight.com'"))
            users = result.fetchall()
            
            print(f"\n📊 Verification Results:")
            print(f"✅ Demo users: {user_count}")
            print(f"✅ Total portfolios: {portfolio_count}")
            print(f"\n👥 Demo Users:")
            for user in users:
                print(f"   • {user.email} ({user.full_name})")
                
            return user_count == 3
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        await engine.dispose()


def main():
    """Main entry point"""
    print("🚀 SigmaSight Demo User Setup")
    print("=" * 50)
    
    # Run setup
    success = asyncio.run(setup_demo_users())
    
    if success:
        # Run verification
        print("\n🔍 Verifying setup...")
        verified = asyncio.run(verify_setup())
        
        if verified:
            print("\n🎉 Demo user setup completed successfully!")
            print("🌐 You can now start the server and use the demo accounts")
            sys.exit(0)
        else:
            print("\n⚠️ Setup completed but verification failed")
            sys.exit(1)
    else:
        print("\n❌ Demo user setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()