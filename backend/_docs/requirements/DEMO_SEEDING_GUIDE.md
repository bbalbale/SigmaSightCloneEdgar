# ~~Section 1.5~~ Demo Data Seeding - Usage Guide

> ⚠️ **CURRENT STATUS (2025-08-26 15:45 PST)**: Demo seeding is fully operational with 3 portfolios and 63 positions. This is actively used for development and testing. See [TODO1.md](../../TODO1.md) Section 1.5 for implementation details.

## Overview
~~Section 1.5~~ **Demo data seeding** provides complete demo data seeding for SigmaSight, creating 3 sophisticated portfolios with all data required for batch processing framework.

## Implementation Status: ✅ COMPLETE

### What's Included
- **3 Demo Portfolios** from Ben Mock Portfolios.md
- **63 Total Positions** across stocks, ETFs, mutual funds, options, shorts
- **Security Master Data** for factor analysis (sectors, industries, classifications)
- **Initial Price Cache** for market value calculations
- **8 Factor Definitions** for risk analysis
- **Complete Database Validation** 

## Quick Start

### 1. Basic Demo Seeding (Recommended)
```bash
# Safe seeding - adds demo data without destroying existing data
python scripts/database/reset_and_seed.py seed
```

### 2. Complete Reset (DESTRUCTIVE - Development Only)
```bash
# DANGER: Drops all tables and recreates with demo data
python scripts/database/reset_and_seed.py reset --confirm
```

### 3. Validate Demo Environment
```bash
# Check if demo data is properly seeded
python scripts/database/reset_and_seed.py validate
```

### 4. Individual Seeding Components
```bash
# Run just the orchestration script
python scripts/database/seed_database.py

# Run individual components
python app/db/seed_demo_portfolios.py
python app/db/seed_security_master.py
python app/db/seed_initial_prices.py
```

## Demo Portfolios Created

### 1. Balanced Individual Investor ($485K)
- **User**: demo_individual@sigmasight.com / demo12345
- **16 Positions**: 9 stocks + 4 mutual funds + 3 ETFs
- **Strategy**: Core holdings with growth tilt, mutual fund heavy
- **Tags**: "Core Holdings", "Tech Growth", "Dividend Income"

### 2. Sophisticated High Net Worth ($2.85M)
- **User**: demo_hnw@sigmasight.com / demo12345  
- **17 Positions**: 15 large-cap stocks + 2 alternative ETFs
- **Strategy**: Diversified blue chips with alternatives
- **Tags**: "Blue Chip", "Alternative Assets", "Risk Hedge"

### 3. Long/Short Equity Hedge Fund Style ($3.2M)
- **User**: demo_hedgefundstyle@sigmasight.com / demo12345
- **30 Positions**: 13 longs + 9 shorts + 8 options
- **Strategy**: Market-neutral with options overlay
- **Tags**: "Long Momentum", "Short Value Traps", "Options Overlay"

## Data Completeness

### ✅ Batch Processing Prerequisites Met
- **Batch Job 1**: All positions have market data and values
- **Batch Job 2**: Options positions have Greeks prerequisites  
- **Batch Job 3**: All symbols have sector/industry classifications
- **Batch Job 4**: Portfolio aggregation data ready
- **Batch Job 5**: Correlation analysis ready

### ✅ Complete Position Data
- Symbol, quantity, entry_price, entry_date ✅
- Position types (LONG/SHORT/LC/LP/SC/SP) ✅
- Options: strike_price, expiration_date ✅
- Market values and unrealized P&L ✅
- Strategy tags and classifications ✅

### ✅ Security Master Data
- 30+ unique securities with classifications
- Sector, industry, market_cap data
- Security types: stock, etf, mutual_fund, index
- Exchange and country information

### ✅ Market Data Cache
- Current prices for all positions
- Mock OHLCV data for calculations
- Historical price foundation (30 days)
- Multiple data source support

## Architecture

### Seeding Pipeline
```
1. Core Infrastructure
   ├── Factor Definitions (8 factors)
   └── Demo Users (3 accounts)

2. Demo Portfolio Structure  
   ├── Portfolio Records
   ├── Position Records (63 positions)
   └── Tag Associations

3. Batch Processing Prerequisites
   ├── Security Master Data
   └── Initial Price Cache
```

### Dependencies
- **Database**: PostgreSQL with Alembic migrations
- **APIs**: Section 1.4.9 market data providers (FMP/Polygon/FRED)
- **Models**: User, Portfolio, Position, Tag, MarketDataCache
- **Calculations**: Section 1.4.1 market value functions

## Validation

After seeding, the system validates:
- ✅ 3 demo users created
- ✅ 3 demo portfolios created  
- ✅ 63+ positions with complete data
- ✅ 8 factor definitions
- ✅ 30+ securities with market data
- ✅ 80%+ positions have market values

## Integration with Batch Processing

Once Section 1.6 Batch Processing Framework is implemented:

1. **Daily Market Data Updates** - Batch Job 1 will update all demo position prices
2. **Greeks Calculations** - Batch Job 2 will calculate options Greeks
3. **Factor Exposures** - Batch Job 3 will analyze portfolio factor loadings
4. **Portfolio Snapshots** - Batch Job 4 will create daily analytics snapshots
5. **Correlation Analysis** - Batch Job 5 will perform position correlation analysis

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure you're in the project root directory
2. **Database Connection**: Check .env file has correct DATABASE_URL
3. **Missing Users**: Run `python scripts/database/seed_database.py` first
4. **API Errors**: Demo seeding uses mock data, so API failures are handled gracefully

### Reset Process
If demo environment gets corrupted:
```bash
# Complete reset (DESTRUCTIVE)
python scripts/database/reset_and_seed.py reset --confirm

# Or safer incremental approach
python scripts/database/seed_database.py
```

## Development Notes

### File Structure
```
app/db/
├── seed_factors.py          # 8 factor definitions
├── seed_demo_portfolios.py  # 3 portfolios with 63 positions
├── seed_security_master.py  # Security classifications
└── seed_initial_prices.py   # Price cache bootstrap

scripts/database/
├── seed_database.py         # Master orchestration
├── (seed_demo_users.py removed) # consolidated into seed_database.py
└── reset_and_seed.py        # Reset & validation utilities
```

### Production Readiness
- **API Integration**: Replace mock prices with live Section 1.4.9 API calls
- **Historical Data**: Extend price history for better factor calculations  
- **Error Handling**: Production-grade retry logic and error recovery
- **Performance**: Batch API calls and optimize database operations

## Success Criteria ✅

Section 1.5 Demo Data Seeding is **COMPLETE** when:
- ✅ 3 realistic demo portfolios created with 63 positions
- ✅ All batch processing prerequisites satisfied  
- ✅ Market data cache populated with current prices
- ✅ Security master data provides factor analysis foundation
- ✅ Portfolio ready for immediate batch processing once framework is implemented
- ✅ Clean reset/validation utilities for development workflow

**Status**: ✅ **PRODUCTION READY** - Demo environment enables full SigmaSight feature demonstration