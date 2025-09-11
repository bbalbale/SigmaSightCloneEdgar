#!/usr/bin/env python
"""
List all portfolios with their IDs and owners.

This is a utility script to quickly find portfolio IDs needed for
batch processing and report generation.

Usage:
    uv run python scripts/list_portfolios.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_async_session
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.users import Portfolio, User
from app.models.positions import Position


async def list_portfolios(verbose: bool = False):
    """List all portfolios with their IDs and basic information."""
    
    print("\n" + "="*60)
    print("PORTFOLIO LISTING")
    print("="*60)
    
    async with get_async_session() as db:
        # Query portfolios with user info and position counts
        stmt = select(Portfolio).options(
            selectinload(Portfolio.user),
            selectinload(Portfolio.positions)
        ).where(
            Portfolio.deleted_at.is_(None)
        ).order_by(Portfolio.created_at)
        
        result = await db.execute(stmt)
        portfolios = result.scalars().all()
        
        if not portfolios:
            print("\n❌ No portfolios found in database!")
            print("\nTo create demo portfolios, run:")
            print("  uv run python scripts/seed_database.py")
            return
        
        print(f"\nFound {len(portfolios)} portfolio(s):\n")
        
        for i, portfolio in enumerate(portfolios, 1):
            print(f"{i}. {portfolio.name or 'Unnamed Portfolio'}")
            print(f"   ID: {portfolio.id}")
            print(f"   Owner: {portfolio.user.email if portfolio.user else 'No owner'}")
            
            # Count active positions
            active_positions = [p for p in portfolio.positions 
                               if p.deleted_at is None and p.exit_date is None]
            print(f"   Positions: {len(active_positions)} active")
            
            if verbose and active_positions:
                # Show position breakdown
                long_count = sum(1 for p in active_positions 
                                if p.position_type and p.position_type.value == "LONG")
                short_count = sum(1 for p in active_positions 
                                 if p.position_type and p.position_type.value == "SHORT")
                options_count = sum(1 for p in active_positions 
                                   if p.position_type and p.position_type.value in ["LC", "LP", "SC", "SP"])
                
                print(f"     - Stocks: {long_count} long, {short_count} short")
                print(f"     - Options: {options_count}")
            
            print(f"   Created: {portfolio.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    
    print("-"*60)
    print("\n📝 To use these IDs in commands:\n")
    print("  # Run batch for specific portfolio:")
    print("  uv run python scripts/run_batch_with_reports.py --portfolio <ID>")
    print()
    print("  # Generate report for specific portfolio:")
    print("  uv run python -m app.cli.report_generator_cli generate --portfolio-id <ID>")
    print()
    print("  # Example with first portfolio ID:")
    if portfolios:
        first_id = str(portfolios[0].id)
        print(f"  uv run python scripts/run_batch_with_reports.py --portfolio {first_id}")
    
    print("\n" + "="*60 + "\n")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="List all portfolios with their IDs")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed position breakdown"
    )
    
    args = parser.parse_args()
    
    try:
        await list_portfolios(verbose=args.verbose)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure:")
        print("1. Docker is running: docker ps")
        print("2. Database is up: docker-compose up -d")
        print("3. Schema is created: uv run alembic upgrade head")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())