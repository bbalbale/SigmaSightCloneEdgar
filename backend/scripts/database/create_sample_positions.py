#!/usr/bin/env python3
"""
Create sample positions for testing factor calculations
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position, PositionType
from sqlalchemy import select


async def create_sample_positions():
    """Create sample positions for testing"""
    print("Creating Sample Positions for Testing")
    print("=" * 40)
    
    async with AsyncSessionLocal() as db:
        # Get the first portfolio
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ No portfolios found")
            return False
        
        print(f"Adding positions to: {portfolio.name}")
        
        # Sample positions with various asset types
        sample_positions = [
            # Large cap tech stocks
            {"symbol": "AAPL", "type": PositionType.LONG, "quantity": 100, "price": 180.00},
            {"symbol": "MSFT", "type": PositionType.LONG, "quantity": 50, "price": 340.00},
            {"symbol": "GOOGL", "type": PositionType.LONG, "quantity": 25, "price": 130.00},
            
            # Financial sector
            {"symbol": "JPM", "type": PositionType.LONG, "quantity": 75, "price": 145.00},
            {"symbol": "BAC", "type": PositionType.LONG, "quantity": 200, "price": 35.00},
            
            # Value stocks
            {"symbol": "BRK.B", "type": PositionType.LONG, "quantity": 30, "price": 400.00},
            {"symbol": "JNJ", "type": PositionType.LONG, "quantity": 80, "price": 160.00},
            
            # Small/mid cap
            {"symbol": "RBLX", "type": PositionType.LONG, "quantity": 150, "price": 45.00},
            
            # Short positions
            {"symbol": "TSLA", "type": PositionType.SHORT, "quantity": -50, "price": 250.00},
            
            # Sample options positions
            {"symbol": "SPY", "type": PositionType.LC, "quantity": 5, "price": 8.50, 
             "underlying": "SPY", "strike": 420.00, "expiry": date.today() + timedelta(days=30)},
            {"symbol": "QQQ", "type": PositionType.LP, "quantity": 3, "price": 12.00,
             "underlying": "QQQ", "strike": 350.00, "expiry": date.today() + timedelta(days=45)},
        ]
        
        positions_created = 0
        entry_date = date.today() - timedelta(days=10)  # Entered 10 days ago
        
        for pos_data in sample_positions:
            try:
                position = Position(
                    portfolio_id=portfolio.id,
                    symbol=pos_data["symbol"],
                    position_type=pos_data["type"],
                    quantity=Decimal(str(pos_data["quantity"])),
                    entry_price=Decimal(str(pos_data["price"])),
                    entry_date=entry_date,
                    last_price=Decimal(str(pos_data["price"])),  # Initialize with entry price
                    
                    # Options-specific fields
                    underlying_symbol=pos_data.get("underlying"),
                    strike_price=Decimal(str(pos_data["strike"])) if pos_data.get("strike") else None,
                    expiration_date=pos_data.get("expiry")
                )
                
                db.add(position)
                positions_created += 1
                
                print(f"✓ Created: {pos_data['symbol']} ({pos_data['type'].value}) - {pos_data['quantity']} @ ${pos_data['price']}")
                
            except Exception as e:
                print(f"❌ Error creating position {pos_data['symbol']}: {str(e)}")
        
        # Commit all positions
        try:
            await db.commit()
            print(f"\n✅ Successfully created {positions_created} sample positions")
            print(f"Portfolio: {portfolio.name} (ID: {portfolio.id})")
            
            # Calculate rough portfolio value
            total_value = sum(
                abs(pos["quantity"]) * pos["price"] * (100 if pos["type"] in [PositionType.LC, PositionType.LP] else 1)
                for pos in sample_positions
            )
            print(f"Approximate portfolio value: ${total_value:,.2f}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error committing positions: {str(e)}")
            await db.rollback()
            return False


if __name__ == "__main__":
    success = asyncio.run(create_sample_positions())
    sys.exit(0 if success else 1)