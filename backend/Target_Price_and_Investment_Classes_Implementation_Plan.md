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

---
*Last Updated: 2025-01-11*
*Status: Planning Phase*