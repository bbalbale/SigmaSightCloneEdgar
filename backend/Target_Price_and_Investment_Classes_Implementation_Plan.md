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
- **Options**: Underlying price targets 
- **Private Investments**: NAV or multiple-based targets

### Step 2: Position-Level Calculations
For each position with targets, the system calculates:
- Expected return % for each scenario
- Position weight in portfolio
- Contribution to portfolio return
- 
### Step 3: Portfolio Aggregation
The system aggregates all positions to show:
- **Portfolio Expected Return (EOY)**: Weighted average of all EOY targets
- **Portfolio Expected Return (Next Year)**: Longer-term outlook
- **Portfolio Downside Risk**: Weighted downside scenario


### Step 4: Risk Analytics
Beyond simple aggregation, the system provides:
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

### 3. Private Investment Details Table (Optional functionality, not all portfolios will have private investemnts)
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


### Risk 76: Database Migration Failures
**Issue**: Alembic migrations could fail due to existing data or constraints
**Impact**: Incomplete schema changes, system in inconsistent state
**Mitigation**:
- Test migrations on copy of production database first
- Use nullable fields to avoid constraint violations
- Implement rollback scripts for each migration
- Add pre-migration validation checks

### Risk 7: Async/Sync Mixing in Aggregation Service
**Issue**: Portfolio aggregation service mixing async database calls with sync calculations
**Impact**: Greenlet errors, event loop blocking
**Mitigation**:
- Use async all the way through aggregation pipeline
- Implement sync calculation functions wrapped with `asyncio.to_thread()` for CPU-intensive work
- Follow existing async patterns from batch orchestrator
- Add comprehensive async/await testing

### Risk 8: API Rate Limiting for Bulk Updates
**Issue**: Bulk target price updates hitting market data API rate limits
**Impact**: Incomplete price refreshes, stale current prices
**Mitigation**:
- Implement queue-based price updates with rate limiting
- Cache current prices with TTL in Redis
- Batch API calls efficiently (use existing FMP bulk endpoint)
- Add circuit breaker pattern for API failures

### Risk 9: Circular Import Dependencies
**Issue**: New services importing from models while models import from services
**Impact**: ImportError at runtime, application fails to start
**Mitigation**:
- Keep calculation logic in separate service layer
- Use TYPE_CHECKING imports for type hints only
- Follow existing pattern: models → schemas → services → API
- Add import validation to test suite

### Risk 10: Memory Leaks in Large Portfolio Aggregations
**Issue**: Loading thousands of positions into memory for aggregation
**Impact**: OOM errors, server crashes
**Mitigation**:
- Implement streaming aggregation with async generators
- Use database-level aggregation where possible (SUM, AVG in SQL)
- Add memory profiling to test suite
- Implement pagination for large result sets

### Risk 11: Type Conversion Errors
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

## Design Comments/Details from Elliott

### 1. Target Price Pydantic Schemas

**File**: `app/schemas/target_prices.py`

**Purpose**: Shared data models for API requests/responses and service layer input/output

```python
# app/schemas/target_prices.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class TargetPriceCreate(BaseModel):
    target_price_eoy: Optional[float] = Field(None, gt=0, description="End of year target price")
    target_price_next_year: Optional[float] = Field(None, gt=0, description="Next year target price") 
    notes: Optional[str] = Field(None, max_length=500, description="User notes")

class TargetPriceResponse(BaseModel):
    id: UUID
    portfolio_id: UUID
    symbol: str
    target_price_eoy: Optional[float] = None
    target_price_next_year: Optional[float] = None
    current_price: Optional[float] = None
    expected_return_eoy: Optional[float] = None  # Calculated by service
    expected_return_next_year: Optional[float] = None  # Calculated by service
    price_updated_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class TargetPriceSummary(BaseModel):
    symbol: str
    target_price_eoy: Optional[float] = None
    expected_return_eoy: Optional[float] = None
    current_price: Optional[float] = None
    updated_at: datetime

class TargetPriceListResponse(BaseModel):
    portfolio_id: UUID
    targets: List[TargetPriceSummary]
    total_count: int

class PriceRefreshResponse(BaseModel):
    portfolio_id: UUID
    updated_count: int
    failed_symbols: List[str]
    timestamp: datetime

class TargetPriceDeleteResponse(BaseModel):
    message: str
    deleted_id: UUID
```

**Schema Usage**:
- **Service Layer**: Input/output types for all service methods
- **API Layer**: Request validation and response serialization
- **Shared Models**: Consistent data structures across layers

### 2. Target Price Service Layer

#### Service Architecture

**File**: `app/services/target_price_service.py`

**Purpose**: Centralize target price business logic, calculations, and data operations

#### Core Service Methods

```python
class TargetPriceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data_service = MarketDataService()
    
    async def create_or_update_target(
        self, 
        portfolio_id: UUID, 
        symbol: str, 
        target_data: TargetPriceCreate
    ) -> TargetPriceResponse:
        """Create or update target price with automatic return calculations"""
        
    async def get_target_price(
        self, 
        portfolio_id: UUID, 
        symbol: str
    ) -> Optional[TargetPriceResponse]:
        """Get target price for specific symbol"""
        
    async def list_portfolio_target_prices(
        self, 
        portfolio_id: UUID, 
        limit: Optional[int] = 50
    ) -> TargetPriceListResponse:
        """List all target prices for portfolio"""
        
    async def delete_target_price(
        self, 
        portfolio_id: UUID, 
        symbol: str
    ) -> bool:
        """Delete target price for symbol"""
        
    async def refresh_current_target_prices(
        self, 
        portfolio_id: UUID, 
        symbols: Optional[List[str]] = None
    ) -> PriceRefreshResponse:
        """Refresh current prices for target prices and recalculate returns"""
        
    async def calculate_expected_returns(
        self, 
        target_price: TargetPrice
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate EOY and next year expected returns"""
        
    async def _fetch_current_price(
        self, 
        symbol: str
    ) -> Optional[float]:
        """Private helper: Fetch current price from market data service"""
```

#### Business Logic Responsibilities

**1. Return Calculations**
- Calculate expected return percentages from current price to target prices
- Handle edge cases (negative prices, missing data)
- Update calculated fields automatically

**2. Price Data Management** 
- Fetch current prices from MarketDataService
- Cache price data with timestamps
- Handle market data service failures gracefully

**3. Data Validation**
- Validate target prices are positive
- Ensure portfolio ownership
- Symbol normalization and validation

**4. Error Handling**
- Market data unavailable scenarios
- Portfolio access control
- Invalid input validation

#### Service Dependencies

- `MarketDataService` - Real-time price fetching
- `AsyncSession` - Database operations
- `Portfolio` model - Ownership verification
- `TargetPrice` model - CRUD operations

### 3. Target Price API Spec

#### API Architecture with Service Layer

**File**: `app/api/v1/target_prices.py`

**Service Integration**: All endpoints use `TargetPriceService` for business logic

**Schema Reference**: See section 1 "Target Price Pydantic Schemas" for all data models

#### API Endpoints

### Create/Update Target Price
**Endpoint**: `POST /api/v1/target-prices/portfolios/{portfolio_id}/symbols/{symbol}`  
**Status**: 🎯 Planned  
**File**: `app/api/v1/target_prices.py`  
**Function**: `create_or_update_target_price()`  
**Service Method**: `target_service.create_or_update_target()`

**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Create or update target price for a symbol with automatic expected return calculations"  

**Service Layer Responsibilities**:
- Validate portfolio ownership  
- Fetch current market price via MarketDataService
- Calculate expected returns using business logic
- Handle database upsert operations
- Return calculated response

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Path `symbol` (string): Stock symbol (e.g., "AAPL")  
- Body (TargetPriceCreate): Target prices and notes  

**Response** (TargetPriceResponse): Complete target with calculated returns

### Get Target Price  
**Endpoint**: `GET /api/v1/target-prices/portfolios/{portfolio_id}/symbols/{symbol}`  
**Status**: 🎯 Planned  
**Function**: `get_target_price()`  
**Service Method**: `target_service.get_target_price()`

**Authentication**: Required  
**OpenAPI Description**: "Retrieve target price and calculated expected returns for a symbol"  

**Service Layer Responsibilities**:
- Validate portfolio ownership
- Fetch target price data 
- Calculate current expected returns
- Handle not found scenarios

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Path `symbol` (string): Stock symbol  

**Response** (TargetPriceResponse): Target price with current calculations

### List Portfolio Target Prices
**Endpoint**: `GET /api/v1/target-prices/portfolios/{portfolio_id}`  
**Status**: 🎯 Planned  
**Function**: `list_target_prices()`  
**Service Method**: `target_service.list_portfolio_target_prices()`

**Authentication**: Required  
**OpenAPI Description**: "List all target prices for a portfolio with expected return calculations"  

**Service Layer Responsibilities**:
- Validate portfolio ownership
- Fetch all target prices for portfolio
- Calculate expected returns for each symbol
- Apply pagination and sorting

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Query `limit` (int, optional): Max results (default: 50)  

**Response** (TargetPriceListResponse): List of target price summaries

### Delete Target Price
**Endpoint**: `DELETE /api/v1/target-prices/portfolios/{portfolio_id}/symbols/{symbol}`  
**Status**: 🎯 Planned  
**Function**: `delete_target_price()`  
**Service Method**: `target_service.delete_target_price()`

**Authentication**: Required  
**OpenAPI Description**: "Delete target price for a symbol"  

**Service Layer Responsibilities**:
- Validate portfolio ownership
- Verify target exists
- Perform delete operation
- Return confirmation

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Path `symbol` (string): Stock symbol  

**Response** (TargetPriceDeleteResponse): Deletion confirmation

### Refresh Current Prices
**Endpoint**: `POST /api/v1/target-prices/portfolios/{portfolio_id}/refresh-prices`  
**Status**: 🎯 Planned  
**Function**: `refresh_current_prices()`  
**Service Method**: `target_service.refresh_current_target_prices()`

**Authentication**: Required  
**OpenAPI Description**: "Refresh current prices for all or specified symbols and recalculate returns"  

**Service Layer Responsibilities**:
- Validate portfolio ownership
- Fetch current prices from MarketDataService
- Update price data and timestamps
- Recalculate all expected returns
- Handle market data failures gracefully

**Parameters**:  
- Path `portfolio_id` (UUID): Portfolio identifier  
- Query `symbols` (List[str], optional): Specific symbols to refresh  

**Response** (PriceRefreshResponse): Refresh operation summary

### 4. Investment Classification Service Layer

### 5. Investment Classification APIs

### 6. Update Demo Seeding Script

---

# TODO List

## Phase 1: Target Price Implementation

### 1.1 Database Model Implementation ✅ COMPLETED
- [x] Created `app/models/target_prices.py` with TargetPrice model
- [x] Defined table schema with proper field types (UUID, Decimal, Text)
- [x] Added portfolio foreign key relationship with CASCADE delete
- [x] Implemented unique constraint on (portfolio_id, symbol)
- [x] Added comprehensive indexing for performance:
  - Primary key index on id
  - Foreign key index on portfolio_id
  - Composite index on (portfolio_id, symbol)
  - Symbol index for cross-portfolio queries
  - Updated_at index for time-based queries
- [x] Implemented calculate_expected_returns() method on model
- [x] Added relationship to Portfolio model in users.py
- [x] Updated models/__init__.py to export TargetPrice

### 1.2 Database Migration ✅ COMPLETED
- [x] Updated database.py to import TargetPrice model for Alembic detection
- [x] Generated Alembic migration: `8a69d30cdfbd_add_portfolio_target_prices_table.py`
- [x] Verified migration includes all table constraints and indexes
- [x] Confirmed migration has proper upgrade/downgrade functions

### 1.3 Pydantic Schemas Implementation ✅ COMPLETED
- [x] Created `app/schemas/target_prices.py` with comprehensive schema definitions
- [x] Implemented TargetPriceCreate schema with validation
- [x] Implemented TargetPriceUpdate schema for partial updates
- [x] Implemented TargetPriceResponse schema with full model data
- [x] Implemented TargetPriceSummary schema for list endpoints
- [x] Implemented TargetPriceListResponse for portfolio-level queries
- [x] Implemented TargetPriceDeleteResponse for delete confirmations
- [x] Implemented TargetPriceErrorResponse for error handling
- [x] Added field validation for positive prices using Pydantic validators
- [x] Added comprehensive examples and documentation strings

### 1.4 API Endpoints Implementation ✅ COMPLETED
- [x] Created `app/api/v1/target_prices.py` with complete CRUD operations
- [x] Implemented portfolio ownership verification helper function
- [x] Implemented current price fetching integration with MarketDataService
- [x] Created GET `/target-prices/portfolios/{portfolio_id}` - List target prices
- [x] Created GET `/target-prices/portfolios/{portfolio_id}/symbols/{symbol}` - Get specific target
- [x] Created POST `/target-prices/portfolios/{portfolio_id}/symbols/{symbol}` - Create/update target
- [x] Created PUT `/target-prices/portfolios/{portfolio_id}/symbols/{symbol}` - Update existing target
- [x] Created DELETE `/target-prices/portfolios/{portfolio_id}/symbols/{symbol}` - Delete target
- [x] Created POST `/target-prices/portfolios/{portfolio_id}/refresh-prices` - Refresh current prices
- [x] Added comprehensive error handling with proper HTTP status codes
- [x] Added authentication and authorization on all endpoints
- [x] Integrated automatic return calculations on create/update operations

### 1.5 Router Integration ✅ COMPLETED
- [x] Updated `app/api/v1/router.py` to import target_prices module
- [x] Registered target_prices.router in main API router
- [x] Added proper routing prefix and tags configuration

### 1.6 Market Data Integration ✅ COMPLETED
- [x] Updated get_current_price_for_symbol() to use existing MarketDataService
- [x] Integrated with MarketDataService.fetch_current_prices() method
- [x] Added proper error handling for market data fetch failures
- [x] Implemented automatic price updates with timestamp tracking

### 1.7 Implementation Features Summary ✅ COMPLETED
- [x] Direct ORM implementation (no service layer as per design decision)
- [x] Real-time price fetching via Polygon API integration
- [x] Automatic expected return calculations (EOY and next year)
- [x] Comprehensive input validation and error responses
- [x] Portfolio-scoped security with ownership verification
- [x] Symbol-level API design for maximum flexibility
- [x] Support for partial updates and bulk price refresh operations
- [x] Complete OpenAPI documentation with examples

## Phase 2: Investment Classification Implementation
*Status: Not Started*

## Phase 3: Demo Data Seeding
*Status: Not Started*

---
*Last Updated: 2025-09-17*
*Status: Enhanced Planning Phase - Ready for Implementation*
*Implementation Status: Phase 1 Complete - Ready for Testing*
