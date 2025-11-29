#!/usr/bin/env python3
"""
Populate target prices for non-option symbols in demo portfolios from CSV file.

Usage:
    python scripts/data_operations/populate_target_prices.py --csv-file data/target_prices_import.csv [--dry-run]

Features:
- Reads target price data from CSV file
- Finds matching non-option positions across all portfolios
- Creates target price records using current market prices
- Supports dry-run mode to preview changes
- Uses downside_target_price_eoy as downside_target_price (current schema)
- Maps CSV columns to current TargetPrice model fields

CSV Format Expected:
symbol,target_price_eoy,target_price_next_year,downside_target_price_eoy,downside_target_price_next_year

Note: downside_target_price_next_year is in CSV for future use but not currently used
"""

import asyncio
import csv
import argparse
import sys
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from uuid import UUID

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.users import Portfolio
from app.models.target_prices import TargetPrice
from app.models.market_data import MarketDataCache
from app.core.logging import get_logger
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)


class TargetPricePopulator:
    """Populates target prices from CSV data"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.target_data: Dict[str, Dict] = {}
        self.portfolios: List[Portfolio] = []
        self.positions_by_symbol: Dict[str, List[Position]] = {}
        
    async def load_csv_data(self, csv_file_path: str) -> None:
        """Load target price data from CSV file"""
        logger.info(f"Loading target price data from {csv_file_path}")
        
        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                symbol = row['symbol'].strip().upper()
                self.target_data[symbol] = {
                    'target_price_eoy': Decimal(str(row['target_price_eoy'])),
                    'target_price_next_year': Decimal(str(row['target_price_next_year'])),
                    'downside_target_price': Decimal(str(row['downside_target_price_eoy'])),
                    # Note: downside_target_price_next_year not used in current schema
                }
        
        logger.info(f"Loaded target prices for {len(self.target_data)} symbols")
        
    async def load_portfolios_and_positions(self, db) -> None:
        """Load demo portfolios and their non-option positions"""
        logger.info("Loading demo portfolios and positions...")
        
        # Get all portfolios
        result = await db.execute(
            select(Portfolio)
            .options(selectinload(Portfolio.positions))
        )
        self.portfolios = result.scalars().all()
        
        # Filter non-option positions and group by symbol
        for portfolio in self.portfolios:
            for position in portfolio.positions:
                # Skip options (they have long symbol names with expiration/strike info)
                if self._is_option_symbol(position.symbol):
                    continue
                    
                # Skip private positions (no market data)
                if position.investment_class == 'PRIVATE':
                    continue
                
                symbol = position.symbol.upper()
                if symbol not in self.positions_by_symbol:
                    self.positions_by_symbol[symbol] = []
                self.positions_by_symbol[symbol].append(position)
        
        logger.info(f"Found {len(self.portfolios)} portfolios")
        logger.info(f"Found {sum(len(positions) for positions in self.positions_by_symbol.values())} non-option positions")
        logger.info(f"Covering {len(self.positions_by_symbol)} unique symbols")
        
    def _is_option_symbol(self, symbol: str) -> bool:
        """Check if symbol represents an option (long format with strike/expiration)"""
        # Options typically have format like: AAPL250815P00200000
        return len(symbol) > 15 or any(char in symbol for char in ['C00', 'P00'])
        
    async def get_current_prices(self, db) -> Dict[str, Decimal]:
        """Get current market prices for all symbols"""
        logger.info("Fetching current market prices...")
        
        symbols = list(self.positions_by_symbol.keys())
        current_prices = {}
        
        # Get latest price for each symbol
        for symbol in symbols:
            result = await db.execute(
                select(MarketDataCache.close)
                .where(MarketDataCache.symbol == symbol)
                .order_by(MarketDataCache.date.desc())
                .limit(1)
            )
            price = result.scalar_one_or_none()
            if price:
                current_prices[symbol] = Decimal(str(price))
            else:
                logger.warning(f"No current price found for {symbol}")
        
        logger.info(f"Found current prices for {len(current_prices)} symbols")
        return current_prices
        
    async def create_target_prices(self, db) -> Tuple[int, List[str]]:
        """Create target price records for matching positions"""
        current_prices = await self.get_current_prices(db)
        created_count = 0
        warnings = []
        
        logger.info("Creating target price records...")
        
        for symbol, positions in self.positions_by_symbol.items():
            if symbol not in self.target_data:
                continue
                
            if symbol not in current_prices:
                warnings.append(f"No current price for {symbol}, skipping")
                continue
                
            target_info = self.target_data[symbol]
            current_price = current_prices[symbol]
            
            for position in positions:
                # Check if target price already exists
                position_type_str = position.position_type.value if position.position_type else 'LONG'
                existing = await db.execute(
                    select(TargetPrice)
                    .where(and_(
                        TargetPrice.portfolio_id == position.portfolio_id,
                        TargetPrice.symbol == symbol,
                        TargetPrice.position_type == position_type_str
                    ))
                )
                
                if existing.scalar_one_or_none():
                    warnings.append(f"Target price already exists for {symbol} in portfolio {position.portfolio_id}")
                    continue
                
                # Create new target price
                target_price = TargetPrice(
                    portfolio_id=position.portfolio_id,
                    position_id=position.id,
                    symbol=symbol,
                    position_type=position_type_str,
                    target_price_eoy=target_info['target_price_eoy'],
                    target_price_next_year=target_info['target_price_next_year'],
                    downside_target_price=target_info['downside_target_price'],
                    current_price=current_price,
                    data_source='USER_INPUT',
                    analyst_notes=f'Imported from CSV'
                )
                
                # Calculate expected returns
                target_price.calculate_expected_returns()
                
                if not self.dry_run:
                    db.add(target_price)
                    
                created_count += 1
                
                logger.info(
                    f"{'[DRY RUN] ' if self.dry_run else ''}Created target price for {symbol} "
                    f"in portfolio {position.portfolio.name if hasattr(position, 'portfolio') else position.portfolio_id}"
                )
        
        if not self.dry_run:
            await db.commit()
            logger.info(f"Committed {created_count} target price records to database")
        else:
            logger.info(f"DRY RUN: Would create {created_count} target price records")
            
        return created_count, warnings
        
    async def print_summary(self) -> None:
        """Print summary of what will be processed"""
        print("\n" + "="*60)
        print("TARGET PRICE POPULATION SUMMARY")
        print("="*60)
        
        print(f"\n📊 CSV Data:")
        print(f"   Symbols in CSV: {len(self.target_data)}")
        
        print(f"\n🎯 Portfolio Analysis:")
        for portfolio in self.portfolios:
            portfolio_positions = [
                pos for positions in self.positions_by_symbol.values() 
                for pos in positions if pos.portfolio_id == portfolio.id
            ]
            print(f"   {portfolio.name}: {len(portfolio_positions)} non-option positions")
        
        print(f"\n🔍 Symbol Matching:")
        csv_symbols = set(self.target_data.keys())
        position_symbols = set(self.positions_by_symbol.keys())
        matching_symbols = csv_symbols & position_symbols
        
        print(f"   CSV symbols: {len(csv_symbols)}")
        print(f"   Position symbols: {len(position_symbols)}")
        print(f"   Matching symbols: {len(matching_symbols)}")
        
        if matching_symbols:
            print(f"   Matches: {', '.join(sorted(matching_symbols))}")
        
        missing_from_positions = csv_symbols - position_symbols
        if missing_from_positions:
            print(f"   CSV symbols not in positions: {', '.join(sorted(missing_from_positions))}")
            
        missing_from_csv = position_symbols - csv_symbols
        if missing_from_csv:
            print(f"   Position symbols not in CSV: {', '.join(sorted(missing_from_csv))}")
        
        total_records = sum(
            len(self.positions_by_symbol.get(symbol, []))
            for symbol in matching_symbols
        )
        print(f"\n📝 Expected target price records: {total_records}")
        print("="*60)


async def main():
    parser = argparse.ArgumentParser(description="Populate target prices from CSV")
    parser.add_argument(
        "--csv-file", 
        required=True, 
        help="Path to CSV file with target price data"
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
    
    if not Path(args.csv_file).exists():
        print(f"❌ CSV file not found: {args.csv_file}")
        return 1
    
    print(f"🎯 Target Price Populator")
    print(f"CSV File: {args.csv_file}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    
    populator = TargetPricePopulator(dry_run=dry_run)
    
    try:
        # Load CSV data
        await populator.load_csv_data(args.csv_file)
        
        # Connect to database and process
        async with AsyncSessionLocal() as db:
            await populator.load_portfolios_and_positions(db)
            await populator.print_summary()
            
            if dry_run:
                print(f"\n💡 This was a DRY RUN. Use --execute to actually create target prices.")
            else:
                print(f"\n⚠️  EXECUTING: Creating target prices in database...")
                
            created, warnings = await populator.create_target_prices(db)
            
            print(f"\n📊 Results:")
            print(f"   Created: {created} target price records")
            if warnings:
                print(f"   Warnings: {len(warnings)}")
                for warning in warnings[:10]:  # Show first 10 warnings
                    print(f"     - {warning}")
                if len(warnings) > 10:
                    print(f"     ... and {len(warnings) - 10} more warnings")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error populating target prices: {e}")
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))