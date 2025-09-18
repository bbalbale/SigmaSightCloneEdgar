# Target Price and Investment Classes Implementation Plan

## Executive Summary
Implementation plan for adding three major features to SigmaSight:
1. **Target Prices**: Portfolio-specific target prices with expected return calculations
2. **Investment Classification**: Categorizing positions into PUBLIC, OPTIONS, and PRIVATE
3. **Private Investment Support**: Comprehensive tracking for private funds and investments

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

### 2. Portfolio Target Prices Table (New Table - No Conflicts)
```sql
CREATE TABLE portfolio_target_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    target_price_eoy DECIMAL(12,4),
    target_price_next_year DECIMAL(12,4),
    current_price DECIMAL(12,4) NOT NULL,
    expected_return_eoy DECIMAL(8,4),  -- Calculated percentage
    expected_return_next_year DECIMAL(8,4),  -- Calculated percentage
    price_updated_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(portfolio_id, symbol)
);
```

**Key Design Decisions:**
- Links to portfolio + symbol (not position_id) to allow targets for securities not yet owned
- One target per security per portfolio enforced by unique constraint
- Current price cached for performance, with timestamp for staleness check

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

## Risk Analysis and Mitigation

### Risk 1: Existing System Breakage
**Issue**: Adding fields to Position model could break existing queries
**Mitigation**:
- Make fields nullable (NULL = PUBLIC equity)
- No changes to existing API responses initially
- Test with demo portfolios before deployment

### Risk 2: Symbol Consistency
**Issue**: Symbol mismatch between positions and targets (e.g., "GOOGL" vs "GOOG")
**Mitigation**:
- Implement symbol normalization service
- For demo portfolios, we control symbol format
- Consider future enhancement: link to position_id as alternative

### Risk 3: Factor Analysis Disruption
**Issue**: Factor calculations might fail on private/option positions
**Mitigation**:
```python
# Simple exclusion logic in factor calculations
public_positions = [p for p in positions
                    if (p.investment_class is None or p.investment_class == 'PUBLIC')]
```

### Risk 4: Batch Processing Impact
**Issue**: Batch orchestrator expects specific position structure
**Mitigation**:
- Maintain backwards compatibility with nullable fields
- Test batch processing with modified schema before deployment
- Update batch processing to skip private investments where appropriate

### Risk 5: Performance Degradation
**Issue**: Additional joins for target prices could slow queries
**Mitigation**:
- Proper indexes on foreign keys and symbol columns
- Optional inclusion via API query parameters
- Lazy loading for target price data

### Risk 6: Data Migration Rollback
**Issue**: Difficult to rollback after users enter target prices
**Mitigation**:
- Two-phase deployment: schema first, features later
- Backup database before migration
- Keep audit trail of all changes

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
*Implementation Status: Phase 1 Complete - Ready for Testing*
