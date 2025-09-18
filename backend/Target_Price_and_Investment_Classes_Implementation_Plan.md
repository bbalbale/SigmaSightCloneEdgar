# Target Price and Investment Classes Implementation Plan

## Executive Summary
Implementation plan for adding three major features to SigmaSight:
1. **Target Prices**: Portfolio-specific target prices with expected return calculations
2. **Investment Classification**: Categorizing positions into PUBLIC, OPTIONS, and PRIVATE
3. **Private Investment Support**: Comprehensive tracking for private funds and investments

## Process Overview - How Target Prices Will Work

### Step 1: User Input
Users will input three target prices per position:
- **EOY Target**: Where they expect the position to be by year-end
- **Next Year Target**: 12-24 month price target
- **Downside Target**: Worst-case scenario price

This applies to ALL position types:
- **Long Positions**: Standard upside/downside targets
- **Short Positions**: Inverse targets (lower is better)
- **Options**: Underlying price targets + Greeks-based valuation
- **Private Investments**: NAV or multiple-based targets

### Step 2: Position-Level Calculations
For each position with targets, the system calculates:
- Expected return % for each scenario
- Position weight in portfolio
- Contribution to portfolio return
- Risk-adjusted returns (considering confidence levels)

### Step 3: Portfolio Aggregation
The system aggregates all positions to show:
- **Portfolio Expected Return (EOY)**: Weighted average of all EOY targets
- **Portfolio Expected Return (Next Year)**: Longer-term outlook
- **Portfolio Downside Risk**: Weighted downside scenario
- **Scenario Analysis**: Bull/Base/Bear cases with probabilities

### Step 4: Risk Analytics
Beyond simple aggregation, the system provides:
- Correlation-adjusted returns (positions moving together)
- Concentration risk warnings
- Confidence-weighted scenarios
- Coverage metrics (% of portfolio with targets)

### Step 5: Monitoring & Updates
Ongoing management includes:
- Staleness indicators for old targets
- Performance tracking vs targets
- Automatic recalculation as positions change
- Alert generation for significant deviations

## Key Design Principles
- **No Breaking Changes**: Existing system must continue working
- **Gradual Migration**: Nullable fields allow phased rollout
- **Portfolio Independence**: Each portfolio can have different targets for same security

## Database Schema Design

### 1. Position Model Extensions (Minimal Risk)
Add nullable fields to existing `positions` table:
```python
# Add to Position model - nullable ensures backwards compatibility
investment_class: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
investment_subtype: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
```

**Classification Logic:**
- `NULL` = PUBLIC equity (default, backwards compatible)
- Options identified by: `position_type IN (LC, LP, SC, SP)` OR `investment_class = 'OPTIONS'`
- Private identified by: `investment_class = 'PRIVATE'`

### 2. Portfolio Target Prices Table (Enhanced with Downside Scenarios)
```sql
CREATE TABLE portfolio_target_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,  -- Optional link to specific position
    symbol VARCHAR(20) NOT NULL,
    position_type VARCHAR(10),  -- LONG, SHORT, LC, LP, SC, SP, PRIVATE

    -- Target Prices
    target_price_eoy DECIMAL(12,4),
    target_price_next_year DECIMAL(12,4),
    downside_target_price DECIMAL(12,4),  -- NEW: Downside scenario

    -- Current Market Data
    current_price DECIMAL(12,4) NOT NULL,
    current_implied_vol DECIMAL(8,4),  -- For options

    -- Calculated Returns (auto-calculated)
    expected_return_eoy DECIMAL(8,4),  -- Calculated percentage
    expected_return_next_year DECIMAL(8,4),  -- Calculated percentage
    downside_return DECIMAL(8,4),  -- NEW: Downside return percentage

    -- Confidence Levels
    confidence_level VARCHAR(10),  -- HIGH, MEDIUM, LOW
    probability_eoy DECIMAL(5,2),  -- Probability of hitting EOY target (0-100)
    probability_next_year DECIMAL(5,2),  -- Probability of hitting next year target
    probability_downside DECIMAL(5,2),  -- Probability of downside scenario

    -- Risk Metrics
    position_weight DECIMAL(8,4),  -- Position weight in portfolio
    contribution_to_portfolio_return DECIMAL(8,4),  -- Weighted contribution
    contribution_to_portfolio_risk DECIMAL(8,4),  -- Risk contribution

    -- Metadata
    price_updated_at TIMESTAMP WITH TIME ZONE,
    analyst_notes TEXT,
    data_source VARCHAR(50),  -- USER_INPUT, ANALYST_CONSENSUS, MODEL
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(portfolio_id, symbol, position_type)  -- Allow same symbol with different position types
);
```

**Enhanced Design Decisions:**
- Support for both symbol-level and position-specific targets
- Separate targets for longs vs shorts on same symbol
- Downside scenario tracking for risk management
- Probability assignments for scenario planning
- Position weight tracking for portfolio aggregation
- Audit trail with created_by field

### 3. Private Investment Details Table (Optional Enhancement)
```sql
CREATE TABLE private_investment_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL UNIQUE REFERENCES positions(id) ON DELETE CASCADE,
    investment_name VARCHAR(255),
    fund_manager VARCHAR(255),
    vintage_year INTEGER,
    commitment_amount DECIMAL(16,2),
    called_amount DECIMAL(16,2),
    distributed_amount DECIMAL(16,2),
    current_nav DECIMAL(16,2),
    target_multiple DECIMAL(6,2),
    target_irr DECIMAL(6,2),
    valuation_date DATE,
    expected_liquidity_date DATE,
    investment_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Portfolio-Level Target Price Aggregation

### Aggregation Service Design
```python
# app/services/portfolio_target_aggregator.py

class PortfolioTargetAggregator:
    """Aggregate position-level targets to portfolio expected returns"""

    async def calculate_portfolio_targets(self, portfolio_id: UUID):
        """
        Calculate portfolio-level expected returns from position targets

        Returns:
        - portfolio_expected_return_eoy: Weighted average EOY return
        - portfolio_expected_return_next_year: Weighted average next year return
        - portfolio_downside_return: Weighted downside scenario
        - scenario_analysis: Bull/Base/Bear case returns
        """

        # 1. Get all positions with targets
        positions_with_targets = await self.get_positions_with_targets(portfolio_id)

        # 2. Calculate position weights (market value / total portfolio value)
        position_weights = await self.calculate_position_weights(positions_with_targets)

        # 3. Handle different position types
        for position in positions_with_targets:
            if position.position_type in ['LONG']:
                # Standard calculation: (target - current) / current
                expected_return = (target_price - current_price) / current_price

            elif position.position_type in ['SHORT']:
                # Inverse calculation: (current - target) / current
                expected_return = (current_price - target_price) / current_price

            elif position.position_type in ['LC', 'LP', 'SC', 'SP']:
                # Options: Consider time decay, delta, and probability
                expected_return = await self.calculate_option_expected_return(
                    position, target_price, current_price, implied_vol, days_to_expiry
                )

            elif position.investment_class == 'PRIVATE':
                # Private investments: Use IRR or multiple-based returns
                expected_return = await self.calculate_private_expected_return(
                    position, target_valuation, current_nav
                )

        # 4. Weight returns by position size
        portfolio_return_eoy = sum(pos.weight * pos.expected_return_eoy)
        portfolio_return_next_year = sum(pos.weight * pos.expected_return_next_year)
        portfolio_downside = sum(pos.weight * pos.downside_return)

        # 5. Calculate confidence-weighted scenarios
        bull_case = sum(pos.weight * pos.target_return * pos.probability)
        base_case = portfolio_return_eoy
        bear_case = portfolio_downside

        return {
            "expected_return_eoy": portfolio_return_eoy,
            "expected_return_next_year": portfolio_return_next_year,
            "downside_return": portfolio_downside,
            "bull_case": bull_case,
            "base_case": base_case,
            "bear_case": bear_case,
            "confidence_weighted_return": self.calculate_confidence_weighted(positions_with_targets)
        }
```

### Options-Specific Target Price Calculations
```python
async def calculate_option_expected_return(self, option_position, target_underlying_price, current_underlying_price, iv, days_to_expiry):
    """
    Calculate expected return for options considering:
    - Delta movement from underlying price change
    - Theta decay over time period
    - Vega impact from IV changes
    - Probability of being ITM at expiry
    """

    if option_position.position_type == 'LC':  # Long Call
        # Calculate option value at target price
        target_option_value = black_scholes_call(
            S=target_underlying_price,
            K=option_position.strike_price,
            T=days_to_target/365,
            r=risk_free_rate,
            sigma=iv
        )
        current_option_value = option_position.current_price
        return (target_option_value - current_option_value) / current_option_value

    # Similar for LP, SC, SP...
```

## Risk Analysis and Mitigation

### Risk 1: Symbol Consistency
**Issue**: Symbol mismatch between positions and targets (e.g., "GOOGL" vs "GOOG")
**Mitigation**:
- Implement symbol normalization service
- For demo portfolios, we control symbol format
- Consider future enhancement: link to position_id as alternative

### Risk 2: Factor Analysis Disruption
**Issue**: Factor calculations might fail on private/option positions
**Mitigation**:
```python
# Simple exclusion logic in factor calculations
public_positions = [p for p in positions 
                    if (p.investment_class is None or p.investment_class == 'PUBLIC')]
```

### Risk 3: Batch Processing Impact
**Issue**: Batch orchestrator expects specific position structure
**Mitigation**:
- Maintain backwards compatibility with nullable fields
- Test batch processing with modified schema before deployment
- Update batch processing to skip private investments where appropriate

### Risk 4: Performance Degradation
**Issue**: Additional joins for target prices could slow queries
**Mitigation**:
- Proper indexes on foreign keys and symbol columns
- Optional inclusion via API query parameters
- Lazy loading for target price data

### Risk 5: Data Migration Rollback
**Issue**: Difficult to rollback after users enter target prices
**Mitigation**:
- Two-phase deployment: schema first, features later
- Backup database before migration
- Keep audit trail of all changes

## Code Implementation Risks

### Risk 6: Option Calculation Complexity
**Issue**: Complex Black-Scholes calculations for options target valuations may fail or produce incorrect results
**Impact**: Incorrect expected returns for option positions, affecting portfolio aggregation
**Mitigation**:
- Use proven mibian library (already in codebase) for Greeks calculations
- Implement fallback to simple linear approximation if Greeks unavailable
- Add validation checks for reasonable option values (0 < price < underlying)
- Unit tests for edge cases (near expiry, deep ITM/OTM)

### Risk 7: Database Migration Failures
**Issue**: Alembic migrations could fail due to existing data or constraints
**Impact**: Incomplete schema changes, system in inconsistent state
**Mitigation**:
- Test migrations on copy of production database first
- Use nullable fields to avoid constraint violations
- Implement rollback scripts for each migration
- Add pre-migration validation checks

### Risk 8: Async/Sync Mixing in Aggregation Service
**Issue**: Portfolio aggregation service mixing async database calls with sync calculations
**Impact**: Greenlet errors, event loop blocking
**Mitigation**:
- Use async all the way through aggregation pipeline
- Implement sync calculation functions wrapped with `asyncio.to_thread()` for CPU-intensive work
- Follow existing async patterns from batch orchestrator
- Add comprehensive async/await testing

### Risk 9: API Rate Limiting for Bulk Updates
**Issue**: Bulk target price updates hitting market data API rate limits
**Impact**: Incomplete price refreshes, stale current prices
**Mitigation**:
- Implement queue-based price updates with rate limiting
- Cache current prices with TTL in Redis
- Batch API calls efficiently (use existing FMP bulk endpoint)
- Add circuit breaker pattern for API failures

### Risk 10: Circular Import Dependencies
**Issue**: New services importing from models while models import from services
**Impact**: ImportError at runtime, application fails to start
**Mitigation**:
- Keep calculation logic in separate service layer
- Use TYPE_CHECKING imports for type hints only
- Follow existing pattern: models → schemas → services → API
- Add import validation to test suite

### Risk 11: Memory Leaks in Large Portfolio Aggregations
**Issue**: Loading thousands of positions into memory for aggregation
**Impact**: OOM errors, server crashes
**Mitigation**:
- Implement streaming aggregation with async generators
- Use database-level aggregation where possible (SUM, AVG in SQL)
- Add memory profiling to test suite
- Implement pagination for large result sets

### Risk 12: Type Conversion Errors
**Issue**: UUID/string conversions, Decimal/float mismatches in calculations
**Impact**: Runtime errors, incorrect calculations
**Mitigation**:
- Use Pydantic models for all API inputs/outputs
- Implement explicit type conversions in service layer
- Add type checking with mypy
- Follow existing UUID handling patterns from codebase

### Risk 13: Transaction Isolation Issues
**Issue**: Concurrent updates to same portfolio's targets causing race conditions
**Impact**: Data inconsistency, lost updates
**Mitigation**:
- Use database-level UPSERT with ON CONFLICT clause
- Implement optimistic locking with version fields
- Use SELECT FOR UPDATE in critical sections
- Add transaction retry logic for deadlocks

### Risk 14: Cache Invalidation Complexity
**Issue**: Stale cached portfolio aggregations after target updates
**Impact**: Users see outdated expected returns
**Mitigation**:
- Implement cache invalidation on target price updates
- Use cache tags for granular invalidation
- Add cache versioning for breaking changes
- Monitor cache hit/miss ratios

### Risk 15: Testing Data Corruption
**Issue**: Test suite modifying demo portfolio data
**Impact**: Subsequent tests fail, demo data unusable
**Mitigation**:
- Use database transactions with rollback in tests
- Create separate test portfolios (prefix with 'test_')
- Implement database snapshot/restore for test runs
- Add data integrity checks to test teardown

## User Input Workflow for Target Prices

### Input Methods

#### 1. Individual Position Entry (UI Form)
```typescript
// Frontend form for single position target
interface TargetPriceInput {
  symbol: string;
  positionType: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP' | 'PRIVATE';

  // Three key targets
  targetPriceEOY: number | null;
  targetPriceNextYear: number | null;
  downsideTarget: number | null;

  // Optional confidence/probability
  confidenceLevel?: 'HIGH' | 'MEDIUM' | 'LOW';
  probabilityEOY?: number;  // 0-100
  probabilityDownside?: number;  // 0-100

  // Notes for context
  analystNotes?: string;
}
```

#### 2. Bulk CSV Upload
```csv
symbol,position_type,qty,current_price,target_eoy,target_next_year,downside,confidence,prob_eoy,prob_downside,notes
AAPL,LONG,1000,150.00,180.00,200.00,130.00,HIGH,75,20,Strong iPhone cycle expected
GOOGL,LONG,500,140.00,160.00,180.00,120.00,MEDIUM,60,30,AI monetization upside
SPY,SHORT,200,440.00,400.00,380.00,460.00,MEDIUM,50,40,Hedging recession risk
TSLA,LC,10,250.00,300.00,350.00,200.00,LOW,40,60,Volatility play
PrivateFundA,PRIVATE,1,1000000,,,1500000,800000,HIGH,70,25,2.5x target multiple
```

#### 3. API Integration for Automated Updates
```python
# Endpoint for bulk updates from external systems
POST /api/v1/portfolios/{portfolio_id}/target-prices/bulk
{
  "targets": [
    {
      "symbol": "AAPL",
      "position_type": "LONG",
      "target_price_eoy": 180.00,
      "target_price_next_year": 200.00,
      "downside_target_price": 130.00,
      "confidence_level": "HIGH",
      "data_source": "ANALYST_MODEL"
    }
  ]
}
```

### Aggregation Display

#### Portfolio Summary View
```json
{
  "portfolio_id": "uuid",
  "current_value": 1000000,
  "expected_returns": {
    "eoy": {
      "return_pct": 15.2,
      "expected_value": 1152000,
      "confidence_weighted": 12.8  // Adjusted by probability
    },
    "next_year": {
      "return_pct": 28.5,
      "expected_value": 1285000,
      "confidence_weighted": 22.1
    },
    "downside": {
      "return_pct": -18.3,
      "expected_value": 817000,
      "probability": 25
    }
  },
  "scenario_analysis": {
    "bull_case": {"return": 35.0, "value": 1350000},
    "base_case": {"return": 15.2, "value": 1152000},
    "bear_case": {"return": -18.3, "value": 817000}
  },
  "positions_with_targets": 45,
  "positions_without_targets": 8,
  "coverage_ratio": 0.85
}
```

## Prioritized Implementation Risk Mitigation

### Critical (Must Address Before Deployment)
1. **Database Migration Safety** (Risk 7)
   - Test all migrations on staging first
   - Use nullable fields everywhere
   - Have rollback scripts ready

2. **Async Pattern Consistency** (Risk 8)
   - Follow existing batch orchestrator patterns
   - No sync/async mixing
   - Comprehensive async testing

3. **Type Safety** (Risk 12)
   - Pydantic models for all I/O
   - Explicit UUID/Decimal conversions
   - mypy type checking in CI

### Important (Address During Development)
4. **Option Calculations** (Risk 6)
   - Use existing mibian library
   - Implement validation bounds
   - Graceful fallbacks for failures

5. **Import Dependencies** (Risk 10)
   - Maintain clean layer separation
   - TYPE_CHECKING for hints only
   - Import validation tests

6. **Transaction Integrity** (Risk 13)
   - UPSERT with ON CONFLICT
   - Proper isolation levels
   - Retry logic for deadlocks

### Performance (Address Before Scaling)
7. **Memory Management** (Risk 11)
   - Streaming aggregations
   - Database-level calculations
   - Pagination for large sets

8. **Caching Strategy** (Risk 14)
   - Clear invalidation rules
   - Cache versioning
   - Monitoring metrics

9. **API Rate Limits** (Risk 9)
   - Queue-based updates
   - Efficient batching
   - Circuit breakers

## Implementation Phases

### Phase 1: Safe Schema Changes (Week 1)
1. Create Alembic migration for nullable Position fields
2. Create new tables (portfolio_target_prices, private_investment_details)
3. Deploy and verify no impact on existing functionality
4. Run full test suite

### Phase 2: Data Classification (Week 1-2)
1. Classify existing demo positions:
   - LONG/SHORT → PUBLIC/STOCK
   - LC/LP/SC/SP → OPTIONS/LISTED_OPTION
2. Verify batch calculations still work
3. Update factor analysis to exclude non-public positions

### Phase 3: Target Price Implementation (Week 2)
1. Create target price calculation service
2. Implement expected return calculations
3. Build APIs for target price management
4. Test with demo portfolios

### Phase 4: API Development (Week 2-3)
```python
# Target Price APIs
GET  /api/v1/portfolios/{portfolio_id}/target-prices
POST /api/v1/portfolios/{portfolio_id}/target-prices
DELETE /api/v1/portfolios/{portfolio_id}/target-prices/{symbol}
GET  /api/v1/portfolios/{portfolio_id}/expected-returns

# Investment Classification APIs  
GET  /api/v1/portfolios/{portfolio_id}/positions/by-class
PATCH /api/v1/positions/{position_id}/classification

# Private Investment APIs
POST /api/v1/positions/{position_id}/private-details
GET  /api/v1/portfolios/{portfolio_id}/private-investments
```

### Phase 5: CSV Import (Future Enhancement)
```csv
# Proposed CSV format
symbol,quantity,entry_price,investment_class,target_eoy,target_next_year
AAPL,100,150.00,PUBLIC,200.00,250.00
MyPrivateFund,1,1000000,PRIVATE,,1500000
```

## Migration SQL Scripts

### Migration 1: Add Classification Fields
```sql
-- Add nullable classification fields
ALTER TABLE positions 
ADD COLUMN investment_class VARCHAR(20),
ADD COLUMN investment_subtype VARCHAR(30);

-- Add indexes for performance
CREATE INDEX idx_positions_investment_class ON positions(investment_class);
```

### Migration 2: Create Target Prices Table
```sql
-- Create portfolio target prices table
CREATE TABLE portfolio_target_prices (
    -- Schema as defined above
);

-- Add indexes
CREATE INDEX idx_target_prices_portfolio ON portfolio_target_prices(portfolio_id);
CREATE INDEX idx_target_prices_symbol ON portfolio_target_prices(symbol);
```

### Migration 3: Classify Existing Positions
```sql
-- Classify stock positions
UPDATE positions 
SET investment_class = 'PUBLIC', 
    investment_subtype = 'STOCK'
WHERE position_type IN ('LONG', 'SHORT')
  AND investment_class IS NULL;

-- Classify options
UPDATE positions 
SET investment_class = 'OPTIONS',
    investment_subtype = 'LISTED_OPTION'  
WHERE position_type IN ('LC', 'LP', 'SC', 'SP')
  AND investment_class IS NULL;
```

## Testing Strategy

### Pre-Deployment Tests
```bash
# Backup database
pg_dump $DATABASE_URL > backup_before_targets.sql

# Verify current system health
cd backend
uv run python scripts/verify_setup.py
uv run python scripts/check_database_content.py

# Run existing test suite
uv run pytest tests/

# Test batch processing
uv run python scripts/run_batch_calculations.py
```

### Post-Migration Tests
1. Verify all existing APIs return same data
2. Confirm batch calculations complete successfully
3. Test factor analysis excludes non-public positions
4. Validate target price calculations
5. Check performance metrics

## Success Criteria
- ✅ No breaking changes to existing functionality
- ✅ Demo portfolios continue working
- ✅ Batch processing runs without errors
- ✅ Factor analysis correctly excludes non-public positions
- ✅ Target prices calculate expected returns correctly
- ✅ APIs handle portfolio-specific targets properly
- ✅ Performance remains within acceptable limits

## Open Questions for Future Consideration
1. Should we implement approval workflow for private investment valuations?
2. How to handle corporate actions affecting symbols (mergers, ticker changes)?
3. Should target prices support multiple time horizons beyond EOY/next year?
4. Integration with chat interface for portfolio upload?

## Next Steps
1. Review and approve this plan
2. Create Alembic migrations
3. Implement services and APIs
4. Test with demo data
5. Document API changes
6. Plan frontend integration

## Design Comments from Elliott

### 1. Target Price Service Layer

### 2. Target Price API Spec

#### Pydantic Schema Definitions
```python
# app/schemas/target_prices.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class TargetPriceCreate(BaseModel):
    """Create/Update target price request"""
    target_price_eoy: Optional[float] = Field(None, gt=0, description="End of year target price")
    target_price_next_year: Optional[float] = Field(None, gt=0, description="Next year target price")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")

class TargetPriceResponse(BaseModel):
    """Individual symbol target price response"""
    portfolio_id: UUID
    symbol: str
    target_price_eoy: Optional[float] = None
    target_price_next_year: Optional[float] = None
    current_price: Optional[float] = None
    expected_return_eoy: Optional[float] = None  # Calculated percentage
    expected_return_next_year: Optional[float] = None  # Calculated percentage
    price_updated_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class TargetPriceSummary(BaseModel):
    """Summary for list endpoint"""
    symbol: str
    target_price_eoy: Optional[float] = None
    expected_return_eoy: Optional[float] = None
    current_price: Optional[float] = None
    updated_at: datetime

class TargetPriceListResponse(BaseModel):
    """List of all targets for a portfolio"""
    portfolio_id: UUID
    targets: list[TargetPriceSummary]
    count: int

class TargetPriceDeleteResponse(BaseModel):
    """Delete confirmation"""
    status: str = "deleted"
    symbol: str
    portfolio_id: UUID
```

#### API Endpoints

### Set/Update Target Price for Symbol
**Endpoint**: `PUT /api/v1/portfolios/{portfolio_id}/target-prices/{symbol}`  
**Status**: 🎯 Planned  
**File**: `app/api/v1/target_prices.py` (to be created)  
**Function**: `set_target_price()`  
**Frontend Proxy Path**: `/api/proxy/api/v1/portfolios/{portfolio_id}/target-prices/{symbol}`  

**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Set or update target price for a specific symbol within a portfolio. Automatically calculates expected returns based on current market price."  
**Database Access**: Direct ORM (PostgreSQL upsert with ON CONFLICT)  
- Tables: `portfolio_target_prices` (create/update), `market_data_cache` (current price lookup)  
**Service Layer**: None (direct ORM in endpoint)  

**Purpose**: Allow users to set investment targets for individual symbols with automatic expected return calculations.  
**Implementation Notes**: Uses PostgreSQL UPSERT; fetches current price from market_data_cache; calculates expected returns inline.  

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Path `symbol` (string): Stock/ETF symbol (e.g., "AAPL")  
- Body (TargetPriceCreate): Optional target prices and notes  

**Response** (TargetPriceResponse): Complete target price data with calculated expected returns

### Get Target Price for Symbol
**Endpoint**: `GET /api/v1/portfolios/{portfolio_id}/target-prices/{symbol}`  
**Status**: 🎯 Planned  
**File**: `app/api/v1/target_prices.py` (to be created)  
**Function**: `get_target_price()`  
**Frontend Proxy Path**: `/api/proxy/api/v1/portfolios/{portfolio_id}/target-prices/{symbol}`  

**Authentication**: Required  
**OpenAPI Description**: "Retrieve target price and expected return calculations for a specific symbol in the portfolio."  
**Database Access**: Direct ORM query with calculated fields  
**Service Layer**: None (simple read operation)  

**Purpose**: Fetch current target price and calculated expected returns for a specific symbol.  
**Implementation Notes**: Single SELECT query; calculates expected returns in Python; returns 404 if target not found.  

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Path `symbol` (string): Stock/ETF symbol  

**Response** (TargetPriceResponse): Complete target price data with expected returns

### Delete Target Price for Symbol
**Endpoint**: `DELETE /api/v1/portfolios/{portfolio_id}/target-prices/{symbol}`  
**Status**: 🎯 Planned  
**File**: `app/api/v1/target_prices.py` (to be created)  
**Function**: `delete_target_price()`  
**Frontend Proxy Path**: `/api/proxy/api/v1/portfolios/{portfolio_id}/target-prices/{symbol}`  

**Authentication**: Required  
**OpenAPI Description**: "Remove target price for a specific symbol from the portfolio."  
**Database Access**: Direct ORM (simple DELETE operation)  
**Service Layer**: None  

**Purpose**: Remove target price tracking for a symbol.  
**Implementation Notes**: Single DELETE query; returns 404 if target not found; confirms deletion in response.  

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Path `symbol` (string): Stock/ETF symbol  

**Response** (TargetPriceDeleteResponse): Deletion confirmation with identifiers

### List All Target Prices for Portfolio
**Endpoint**: `GET /api/v1/portfolios/{portfolio_id}/target-prices`  
**Status**: 🎯 Planned  
**File**: `app/api/v1/target_prices.py` (to be created)  
**Function**: `list_target_prices()`  
**Frontend Proxy Path**: `/api/proxy/api/v1/portfolios/{portfolio_id}/target-prices`  

**Authentication**: Required  
**OpenAPI Description**: "Retrieve all symbols with target prices set for the portfolio, including expected return calculations."  
**Database Access**: Direct ORM query with optional LIMIT  
**Service Layer**: None (read-only aggregation)  

**Purpose**: Portfolio overview of all symbols with target prices for dashboard display.  
**Implementation Notes**: Single SELECT with WHERE clause; calculates expected returns for each symbol; supports pagination.  

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Query `limit` (int, optional): Maximum number of results (default: 50)  

**Response** (TargetPriceListResponse): Array of target price summaries with metadata

### 3. Investment Classification Service Layer

### 4. Investment Classification APIs

### 5. Update Demo Seeding Script 

---
*Last Updated: 2025-09-17*
*Status: Enhanced Planning Phase - Ready for Implementation*
*Added: Comprehensive risk analysis, user workflows, and portfolio aggregation logic*