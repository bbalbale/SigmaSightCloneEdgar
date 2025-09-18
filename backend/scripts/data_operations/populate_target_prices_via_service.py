#!/usr/bin/env python3
"""
Populate target prices using the existing TargetPriceService CSV import functionality.

Usage:
    python scripts/data_operations/populate_target_prices_via_service.py --csv-file data/target_prices_import.csv [--dry-run]

Features:
- Uses TargetPriceService.import_from_csv() - the same method as the API
- Reads CSV in exact format expected by service: symbol,position_type,target_eoy,target_next_year,downside,current_price
- Creates target price records for all portfolios that have matching symbols
- Supports dry-run mode to preview changes without database writes
- Proper Decimal precision handling to avoid floating point artifacts
- Returns actual service response format: {created, updated, errors, total}

CSV Format (matches service expectations):
symbol,position_type,target_eoy,target_next_year,downside,current_price
AAPL,LONG,261.38,300.59,200.00,180.00
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, List
from uuid import UUID
from decimal import Decimal

# Ensure we can import from backend package
script_dir = Path(__file__).parent
backend_dir = script_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.services.target_price_service import TargetPriceService
from app.core.logging import get_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)


class TargetPriceImporter:
    """Import target prices using the service layer"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.service = TargetPriceService()
        
    async def import_for_all_portfolios(self, csv_file_path: str) -> None:
        """Import target prices for all portfolios from CSV file"""
        
        # Resolve CSV file path relative to backend directory
        if not Path(csv_file_path).is_absolute():
            csv_file_path = backend_dir / csv_file_path
            
        if not Path(csv_file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
            
        logger.info(f"Reading CSV file: {csv_file_path}")
        
        # Read CSV content
        with open(csv_file_path, 'r') as file:
            csv_content = file.read()
            
        async with AsyncSessionLocal() as db:
            # Get all portfolios
            result = await db.execute(
                select(Portfolio).options(selectinload(Portfolio.positions))
            )
            portfolios = result.scalars().all()
            
            print(f"\n🎯 Target Price Import Summary")
            print(f"CSV File: {csv_file_path}")
            print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
            print(f"Portfolios: {len(portfolios)}")
            
            total_created = 0
            total_updated = 0
            all_errors = []
            
            for portfolio in portfolios:
                print(f"\n📊 Processing: {portfolio.name}")
                print(f"Portfolio ID: {portfolio.id}")
                
                if self.dry_run:
                    # In dry-run mode, we'll parse and validate but not call the service
                    result = await self._dry_run_analysis(db, portfolio.id, csv_content)
                    print(f"   Would create: {result['would_create']}")
                    print(f"   Would update: {result['would_update']}")  
                    print(f"   Potential errors: {len(result['errors'])}")
                    if result['errors']:
                        for error in result['errors'][:3]:  # Show first 3 errors
                            print(f"     - {error}")
                        if len(result['errors']) > 3:
                            print(f"     ... and {len(result['errors']) - 3} more")
                else:
                    # Execute the actual import
                    try:
                        result = await self.service.import_from_csv(
                            db=db,
                            portfolio_id=portfolio.id,
                            csv_content=csv_content,
                            update_existing=False,  # Don't overwrite existing records
                            user_id=None  # System import
                        )
                        
                        print(f"   ✅ Created: {result['created']}")
                        print(f"   ✅ Updated: {result['updated']}")
                        print(f"   ⚠️  Errors: {len(result['errors'])}")
                        
                        total_created += result['created']
                        total_updated += result['updated'] 
                        all_errors.extend(result['errors'])
                        
                        if result['errors']:
                            for error in result['errors'][:2]:  # Show first 2 errors per portfolio
                                print(f"     - {error}")
                                
                    except Exception as e:
                        error_msg = f"Failed to import for portfolio {portfolio.name}: {e}"
                        print(f"   ❌ {error_msg}")
                        all_errors.append(error_msg)
            
            # Final summary
            print(f"\n{'='*60}")
            print(f"📈 FINAL RESULTS")
            print(f"{'='*60}")
            
            if self.dry_run:
                print("This was a DRY RUN - no changes made to database")
                print("Use --execute to actually create target prices")
            else:
                print(f"Total created: {total_created}")
                print(f"Total updated: {total_updated}")
                print(f"Total errors: {len(all_errors)}")
                
                if all_errors:
                    print(f"\nError summary:")
                    for error in all_errors[:10]:  # Show first 10 errors
                        print(f"  - {error}")
                    if len(all_errors) > 10:
                        print(f"  ... and {len(all_errors) - 10} more errors")
    
    async def _dry_run_analysis(self, db, portfolio_id: UUID, csv_content: str) -> Dict:
        """Analyze what would happen without making changes"""
        import csv
        import io
        from app.models.target_prices import TargetPrice
        from sqlalchemy import and_
        
        reader = csv.DictReader(io.StringIO(csv_content))
        would_create = 0
        would_update = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
            try:
                symbol = row.get('symbol', '').strip().upper()
                position_type = row.get('position_type', 'LONG').strip().upper()
                
                if not symbol:
                    errors.append(f"Row {row_num}: Missing symbol")
                    continue
                
                # Check if target price already exists
                existing = await db.execute(
                    select(TargetPrice)
                    .where(and_(
                        TargetPrice.portfolio_id == portfolio_id,
                        TargetPrice.symbol == symbol,
                        TargetPrice.position_type == position_type
                    ))
                )
                
                if existing.scalar_one_or_none():
                    errors.append(f"Row {row_num}: Target price already exists for {symbol}")
                else:
                    # Validate required fields
                    try:
                        if row.get('target_eoy'):
                            Decimal(row['target_eoy'])
                        if row.get('target_next_year'):
                            Decimal(row['target_next_year'])
                        if row.get('downside'):
                            Decimal(row['downside'])
                        if row.get('current_price'):
                            Decimal(row['current_price'])
                        would_create += 1
                    except (ValueError, TypeError) as e:
                        errors.append(f"Row {row_num}: Invalid numeric value - {e}")
                        
            except Exception as e:
                errors.append(f"Row {row_num}: Error processing row - {e}")
                
        return {
            'would_create': would_create,
            'would_update': would_update,
            'errors': errors
        }


async def main():
    parser = argparse.ArgumentParser(description="Import target prices using TargetPriceService")
    parser.add_argument(
        "--csv-file", 
        required=True, 
        help="Path to CSV file with target price data (relative to backend/ directory)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        default=True,
        help="Preview changes without writing to database (default: True)"
    )
    parser.add_argument(
        "--execute", 
        action="store_true", 
        help="Actually write changes to database (overrides --dry-run)"
    )
    
    args = parser.parse_args()
    
    # Determine if this is a dry run
    dry_run = not args.execute
    
    print(f"🎯 Target Price Service Importer")
    print(f"Working directory: {Path.cwd()}")
    print(f"Backend directory: {backend_dir}")
    
    importer = TargetPriceImporter(dry_run=dry_run)
    
    try:
        await importer.import_for_all_portfolios(args.csv_file)
        return 0
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))