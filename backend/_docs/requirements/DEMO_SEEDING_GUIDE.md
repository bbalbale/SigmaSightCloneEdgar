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

### Idempotency Guarantee ✅

**Safe to run multiple times** - Demo seeding is fully idempotent:
- Uses deterministic UUIDs for demo users and portfolios
- Checks for existing records before inserting
- Adds missing positions without duplicating existing ones
- Updates market data cache with latest prices
- **Does NOT** delete or modify existing user data outside demo accounts

**What happens on re-run**:
```python
# First run:  Creates 3 users, 3 portfolios, 63 positions ✅
# Second run: Skips existing records, adds 0 new positions ✅
# Third run:  Same behavior - idempotent ✅

# Safe to use on existing dev DB with real user data - demo data is isolated
```

### 1. Basic Demo Seeding (Recommended)
```bash
# Safe seeding - adds demo data without destroying existing data
# Safe to run multiple times - fully idempotent
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

### Per-Portfolio Position Counts
- **Portfolio 1**: 16 positions (Balanced Individual Investor)
- **Portfolio 2**: 17 positions (Sophisticated High Net Worth)
- **Portfolio 3**: 30 positions (Long/Short Equity Hedge Fund Style)
- **Total**: 63 positions across all 3 portfolios

### 1. Balanced Individual Investor ($485K)
- **User**: demo_individual@sigmasight.com / demo12345
- **16 Positions**: 9 stocks + 4 mutual funds + 3 ETFs
- **Strategy**: Core holdings with growth tilt, mutual fund heavy
- **Tags**: "Core Holdings", "Tech Growth", "Dividend Income"
- **Market Data**: 100% coverage (all equities and ETFs have tickers)

### 2. Sophisticated High Net Worth ($2.85M)
- **User**: demo_hnw@sigmasight.com / demo12345
- **17 Positions**: 15 large-cap stocks + 2 alternative ETFs
- **Strategy**: Diversified blue chips with alternatives
- **Tags**: "Blue Chip", "Alternative Assets", "Risk Hedge"
- **Market Data**: 100% coverage (all equities and ETFs have tickers)

### 3. Long/Short Equity Hedge Fund Style ($3.2M)
- **User**: demo_hedgefundstyle@sigmasight.com / demo12345
- **30 Positions**: 13 longs + 9 shorts + 8 options
- **Strategy**: Market-neutral with options overlay
- **Tags**: "Long Momentum", "Short Value Traps", "Options Overlay"
- **Market Data**: ~80% coverage (options don't receive historical prices during seeding)

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

**Static Dictionary Coverage**:
- **Core equities and ETFs**: Full sector/industry/market_cap data from static dictionary
- **Real tickers** (AAPL, MSFT, SPY, etc.): Complete classifications
- **30+ unique securities** with at least basic metadata

**Synthetic Ticker Handling** ⚠️:
Many demo tickers are **synthetic placeholders** used for demonstration purposes:

| Ticker Type | Examples | Sector Data | Impact on Analytics |
|-------------|----------|-------------|---------------------|
| **Real Equities** | AAPL, MSFT, NVDA | ✅ Complete | Ready for factor analysis |
| **Real ETFs** | SPY, QQQ, GLD | ✅ Complete | Ready for factor analysis |
| **Mutual Funds** | VFIAX, FXAIX | ⚠️ Partial | May show "Unknown" sector |
| **Private Assets** | REAL_ESTATE_1, PRIVATE_EQUITY_FUND | ❌ Placeholder | Shows "Unknown" until manual enrichment |
| **Options** | AAPL_CALL_170_2024, SPY_PUT_450 | ❌ Derived from underlying | Sector inherited from underlying security |

**"Unknown" Sector Data**:
```sql
-- Many positions will have placeholder metadata:
SELECT symbol, sector, industry FROM security_master
WHERE sector = 'Unknown' OR sector IS NULL;

-- Expected for:
- Synthetic private assets (REAL_ESTATE_1, VENTURE_CAPITAL_A)
- Options contracts (sector inherited from underlying)
- Uncommon mutual funds not in static dictionary
```

**Expectations for Analytics**:
- **Factor Analysis**: Works for real equities/ETFs, degrades gracefully for synthetic assets
- **Sector Breakdown**: Shows "Unknown" category for ~20-30% of positions (private assets + options)
- **Industry Correlation**: Only available for positions with complete metadata

**Manual Enrichment Process** (If Needed):
```bash
# After seeding, update synthetic positions with real data
python scripts/database/enrich_security_master.py --ticker REAL_ESTATE_1 \
  --sector "Real Estate" \
  --industry "REITs" \
  --market_cap 500000000

# Or bulk import from CSV
python scripts/database/bulk_enrich_securities.py --csv custom_securities.csv
```

### ✅ Market Data Cache

**Coverage Expectations**:
- **Target**: 80% market-value coverage (threshold for validation passing)
- **Actual**: ~82% coverage after seeding completes
- **Excluded from coverage**: Options contracts (remaining ~20% of inventory)

**What Gets Historical Prices**:
```
✅ Equities (AAPL, MSFT, NVDA):     30 days of historical data via YFinance
✅ ETFs (SPY, QQQ, GLD):             30 days of historical data via YFinance
✅ Mutual Funds (VFIAX, FXAIX):      30 days of historical data via YFinance
❌ Options Contracts:                 NO historical prices during seeding
❌ Synthetic Private Assets:          NO historical prices (placeholder values)
```

**Options Contract Handling** ⚠️:

Options positions (8 in Portfolio #3) are **excluded from historical price seeding**:

| Aspect | Status | Reasoning |
|--------|--------|-----------|
| **Entry Price** | ✅ Set in position definition | Used for P&L baseline |
| **Current Price** | ❌ Not seeded | Requires implied vol surface + pricing model |
| **Historical Prices** | ❌ Not seeded | Options pricing needs Black-Scholes or similar |
| **Greeks** | ⚠️ Computed during batch processing | Uses `mibian` library with current market data |

**Impact on Analytics**:
```python
# Portfolio #3 breakdown (30 positions):
- 22 equity positions: 100% market-value coverage ✅
- 8 options positions:  0% market-value coverage ❌
# Overall coverage: (22/30) * 100% = 73%... but validation uses value-weighted:
# Value-weighted coverage: ~82% (options are smaller % of total value)
```

**Why 80% Threshold?**:
- Allows for options inventory without blocking validation
- Focuses on liquid positions with available market data
- Options Greeks computed later by batch processing, not during seeding
- Provides realistic demo environment without requiring options pricing infrastructure

**Options Pricing Strategy** (Post-Seeding):
```bash
# Options get priced during first batch processing run:
python scripts/run_batch_calculations.py

# Batch Job 2 (Greeks Calculation) will:
# 1. Fetch underlying stock price (AAPL, SPY, etc.)
# 2. Fetch implied volatility from Polygon API
# 3. Compute option value using Black-Scholes (mibian library)
# 4. Store Greeks (delta, gamma, theta, vega, rho) in position_greeks table
```

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

#### Required Infrastructure
- **Database**: PostgreSQL with Alembic migrations (local or Docker)
- **Network Access**: Required for historical price fetching (see below)
- **Models**: User, Portfolio, Position, Tag, MarketDataCache
- **Calculations**: Section 1.4.1 market value functions

#### External Data Dependencies ⚠️ **CRITICAL**

**YFinance Provider** (Hard Network Dependency):
- **Used For**: Historical price data via `app/db/fetch_historical_data.py`
- **Called By**: `seed_initial_prices.py` through `market_data_factory`
- **Network Required**: Yes - downloads historical prices from Yahoo Finance
- **Failure Mode**: If network unavailable or YFinance provider not registered, seeding will stall with unset market values

**Impact of Network Failure**:
```python
# Without network access or YFinance provider:
- Historical prices: ❌ NOT populated
- Market values: ❌ Remain NULL in database
- P&L calculations: ❌ Cannot compute (missing current_price)
- Batch processing: ⚠️ Partial failure (Greeks work, factor analysis fails)
```

**Offline Fallback Plan** (Recommended for Fresh Environments):

Option A: **Pre-Seeded Price Cache** (Preferred)
```bash
# 1. Generate price cache on machine with network access
python scripts/database/export_price_cache.py > price_cache.json

# 2. Transfer price_cache.json to offline environment

# 3. Import cache before seeding
python scripts/database/import_price_cache.py price_cache.json

# 4. Run seeding (will use cached prices)
python scripts/database/seed_database.py
```

Option B: **Mock Price Fallback**
```python
# In seed_initial_prices.py, enable mock mode:
USE_MOCK_PRICES = True  # Fallback to $100 per share for all securities

# Trade-off: Seeding completes, but P&L calculations are unrealistic
```

**Stress Testing Scenarios**:
- **Config File**: `app/config/stress_scenarios.json` (required)
- **Called By**: `scripts/database/seed_stress_scenarios.py`
- **Failure Mode**: If config missing, stress scenario seeding fails silently
- **Validation**: Check for existence before running `seed_database.py`

## Validation

### Exact Validation Thresholds

After seeding, the validation script checks:
- ✅ **≥3 users** (actual: exactly 3 demo users)
- ✅ **≥3 portfolios** (actual: exactly 3 demo portfolios)
- ✅ **≥50 positions** (actual: 63 positions = 16 + 17 + 30)
- ✅ **8 factor definitions** (exact requirement, no minimum)
- ✅ **≥30 market-data rows** (actual: ~40-50 unique securities)
- ✅ **≥80% positions have market values** (options excluded from coverage calculation)

**Passing Validation**: All 6 thresholds must pass. If any threshold fails, seeding is considered incomplete.

**What "Pass" Looks Like**:
```bash
$ python scripts/database/reset_and_seed.py validate

✅ Users: 3 (≥3 required)
✅ Portfolios: 3 (≥3 required)
✅ Positions: 63 (≥50 required)
✅ Factors: 8 (8 required)
✅ Market Data: 42 securities (≥30 required)
✅ Market Value Coverage: 82% (≥80% required)

Demo environment: VALID ✅
```

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

## Analytics Module Considerations

### Market Value Coverage Assumptions ⚠️

**Problem**: Some analytics modules may assume 100% market-value coverage, but demo data only guarantees 80%+.

**Affected Modules**:
```python
# ❌ BREAKS: Assumes all positions have current_price
def calculate_total_portfolio_value(positions):
    return sum(p.quantity * p.current_price for p in positions)
    # Will fail if current_price is None for options

# ✅ SAFE: Handles missing prices gracefully
def calculate_total_portfolio_value(positions):
    return sum(
        p.quantity * (p.current_price or p.entry_price or 0)
        for p in positions
    )
```

**Audit Checklist** (For Analytics Modules):

1. **Portfolio Value Calculations**:
   - [ ] Check for `current_price IS NULL` before multiplication
   - [ ] Fallback to `entry_price` for positions without market data
   - [ ] Log warning for missing prices, don't raise exception

2. **Sector/Industry Breakdowns**:
   - [ ] Handle `sector = 'Unknown'` or `sector IS NULL`
   - [ ] Group synthetic positions into "Other" or "Private Assets" category
   - [ ] Don't assume every position has complete security master data

3. **P&L Calculations**:
   - [ ] Skip positions with missing `current_price` (can't compute unrealized P&L)
   - [ ] Report coverage percentage alongside P&L totals
   - [ ] Allow partial P&L calculations (e.g., "78% of positions have P&L data")

4. **Factor Exposure Analysis**:
   - [ ] Only compute factor loadings for positions with sector/industry data
   - [ ] Exclude options from factor calculations (inherit from underlying if needed)
   - [ ] Report number of positions excluded due to missing metadata

**Recommended Pattern**:
```python
# app/calculations/portfolio_value.py

def calculate_portfolio_metrics(portfolio_id: UUID) -> dict:
    """Calculate portfolio metrics with graceful degradation."""
    positions = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )

    total_positions = len(positions)
    priced_positions = [p for p in positions if p.current_price is not None]
    coverage_pct = len(priced_positions) / total_positions * 100

    # Only calculate value for positions with prices
    total_value = sum(
        p.quantity * p.current_price
        for p in priced_positions
    )

    return {
        "total_value": total_value,
        "positions_count": total_positions,
        "priced_positions": len(priced_positions),
        "coverage_percent": round(coverage_pct, 1),
        "missing_prices": total_positions - len(priced_positions),
        # Include coverage warning if below threshold
        "data_quality_warning": coverage_pct < 80
    }
```

**Testing Strategy**:
```bash
# After seeding, run analytics audit:
python scripts/audit/test_analytics_with_demo_data.py

# Expected output:
# ✅ Portfolio value calculation: handles missing prices
# ✅ Sector breakdown: handles Unknown sectors
# ✅ P&L calculation: graceful degradation
# ⚠️ Factor analysis: 22/30 positions (73%) - options excluded
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

---

## Document Updates (2025-10-29)

This guide was enhanced based on feedback from AI coding agents to address operational gaps and deployment readiness.

### Updates Summary

**1. Exact Validation Thresholds** _(Section: Validation)_
- Added precise thresholds: ≥3 users, ≥3 portfolios, ≥50 positions, 8 factors, ≥30 market-data rows, ≥80% coverage
- Provided example validation output showing what a "pass" looks like
- Clarified that all 6 thresholds must pass for validation to succeed

**2. Per-Portfolio Position Counts** _(Section: Demo Portfolios Created)_
- Explicitly listed position counts: 16, 17, 30 (total: 63)
- Added market data coverage percentages per portfolio
- Clarified that Portfolio #3 has ~80% coverage due to options positions

**3. YFinance Network Dependency** _(Section: Dependencies)_
- Documented hard network dependency for historical price fetching
- Explained failure modes when network unavailable or YFinance provider not registered
- Provided two offline fallback options:
  - Option A: Pre-seeded price cache (export/import workflow)
  - Option B: Mock price fallback (unrealistic but functional)

**4. Stress Scenarios Config Dependency** _(Section: Dependencies)_
- Documented required `app/config/stress_scenarios.json` file
- Explained that missing config causes silent failure in stress scenario seeding
- Recommended validation before running seed_database.py

**5. Security Master Enrichment** _(Section: Security Master Data)_
- Added comprehensive table showing real vs synthetic ticker handling
- Explained "Unknown" sector data expectations (20-30% of positions)
- Provided manual enrichment process for custom securities
- Set expectations for analytics modules regarding incomplete metadata

**6. Options Coverage Expectations** _(Section: Market Data Cache)_
- Clarified 80% market-value coverage threshold (not 100%)
- Documented that options don't receive historical prices during seeding
- Explained value-weighted coverage calculation (82% actual)
- Detailed post-seeding options pricing strategy via batch processing

**7. Idempotency Guarantees** _(Section: Quick Start)_
- Documented that seeding is safe to run multiple times
- Explained deterministic UUID strategy for demo data
- Clarified behavior on re-runs (skips existing, adds missing)
- Confirmed isolation from non-demo user data

**8. Analytics Module Considerations** _(New Section)_
- Added comprehensive audit checklist for analytics modules
- Documented common failure patterns when assuming 100% coverage
- Provided recommended graceful degradation pattern
- Included testing strategy for validating analytics with demo data

### Key Takeaways for Future Development

**For Fresh Environments**:
1. Ensure network access OR prepare offline price cache before seeding
2. Verify `app/config/stress_scenarios.json` exists
3. Expect 80% coverage, not 100% - design analytics modules accordingly
4. Run validation script to confirm all 6 thresholds pass

**For Analytics Development**:
1. Always handle `current_price IS NULL` gracefully
2. Use fallback to `entry_price` or skip positions with missing data
3. Report coverage percentages alongside calculated metrics
4. Test with demo data containing synthetic positions and options

**For Production Deployment**:
1. Replace YFinance with production-grade data providers
2. Implement retry logic for network failures
3. Extend historical price coverage beyond 30 days
4. Add monitoring for market-value coverage degradation

### Questions Addressed

- **"What does a passing validation look like?"** → See exact thresholds and example output in Validation section
- **"Will seeding break if I run it twice?"** → No - fully idempotent, safe for re-runs
- **"Why are some positions missing prices?"** → Options excluded by design, 80% threshold intentional
- **"What if I don't have network access?"** → Use offline price cache fallback (Option A in Dependencies)
- **"Why do I see 'Unknown' sectors?"** → Synthetic positions expected, see Security Master Data section
- **"How do I test analytics modules?"** → Use audit checklist and testing strategy in Analytics Module Considerations