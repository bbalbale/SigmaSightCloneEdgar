# Onboarding Pipeline Comparison

**Created**: 2025-10-29
**Purpose**: Compare demo seeding vs. new user onboarding pipelines to identify missing processing steps

---

## Executive Summary

**⚠️ CRITICAL GAP IDENTIFIED**: The new user onboarding pipeline is missing **two essential data preparation steps** that are present in demo seeding:

1. **Security Master Enrichment** - Sector/industry/market cap data for symbols
2. **Initial Price Cache Bootstrap** - Historical price data for positions

Without these steps, new user portfolios will experience:
- ❌ Factor analysis failures (no sector data → ERR_BATCH_002)
- ❌ P&L calculation failures (no historical prices → NULL market values)
- ❌ Portfolio value calculations degraded to using entry prices only
- ❌ ~20-30% of analytics features non-functional

**Recommendation**: Add these two preprocessing steps to the user onboarding flow BEFORE batch processing runs.

---

## Pipeline Comparison

### Demo Seeding Pipeline (DEMO_SEEDING_GUIDE.md)

**File**: `scripts/database/seed_database.py`

```python
# Step 1: Core Infrastructure
await seed_factors(db)              # 8 factor definitions
await create_demo_users(db)         # 3 demo users

# Step 2: Demo Portfolio Structure
await seed_demo_portfolios(db)      # Portfolios, positions, tags

# Step 3: Batch Processing Prerequisites ⭐ CRITICAL
await seed_scenarios_from_config()  # Stress test scenarios
await seed_security_master(db)      # ⭐ Security classifications
await seed_initial_prices(db)       # ⭐ Price cache bootstrap

# Step 4: Batch Processing (separate call)
# User runs: python scripts/run_batch_calculations.py
```

**Total Time**: ~2-5 minutes (depends on network for YFinance historical data)

**Data Populated**:
- ✅ Factor definitions (8 factors)
- ✅ Demo users (3 accounts)
- ✅ Portfolios & positions (63 total positions)
- ✅ Tags (3-5 tags per portfolio)
- ✅ Stress scenarios (from config file)
- ✅ Security master data (~40-50 securities with sector/industry/market cap)
- ✅ Historical prices (30 days for all equities/ETFs via YFinance)
- ✅ Market value calculations ready
- ✅ P&L calculations ready

---

### New User Onboarding Pipeline (USER_PORTFOLIO_ONBOARDING_DESIGN.md)

**API Endpoints**:
```
POST /api/v1/onboarding/register
POST /api/v1/onboarding/create-portfolio
POST /api/v1/portfolio/{portfolio_id}/calculate
```

**Implementation Flow**:

```python
# Step 1: User Registration
await onboarding_service.register_user(
    email, password, full_name, invite_code
)

# Step 2: Portfolio Creation (<5s)
await onboarding_service.create_portfolio_with_csv(
    user_id, portfolio_name, equity_balance, csv_file
)
# Populates:
# - Portfolio record
# - Position records (from CSV)
# - Tag associations (if present in CSV)

# Step 3: Batch Processing Trigger (30-60s)
# User calls: POST /api/v1/portfolio/{id}/calculate
await batch_orchestrator.run_daily_batch_sequence(portfolio_id)
```

**Total Time**: <5s for portfolio creation + 30-60s for batch processing

**Data Populated**:
- ✅ User account
- ✅ Portfolio record
- ✅ Position records (from CSV)
- ✅ Tag associations
- ❌ **Security master data NOT populated**
- ❌ **Historical prices NOT populated**
- ⚠️ Batch processing will fail or degrade without these prerequisites

---

## Missing Steps Analysis

### Missing Step #1: Security Master Enrichment

**What It Does** (`app/db/seed_security_master.py`):
- Looks up sector, industry, market_cap for each symbol
- Uses static dictionary for common symbols (AAPL, MSFT, SPY, etc.)
- Inserts "Unknown" placeholders for synthetic/uncommon symbols
- Enables factor analysis (Batch Job 3)

**Impact on New User Portfolios**:

| Without Security Master | With Security Master |
|------------------------|---------------------|
| ❌ Factor analysis fails (ERR_BATCH_002) | ✅ Factor loadings calculated |
| ❌ Sector breakdown shows "N/A" | ✅ Sector pie chart populated |
| ❌ Industry correlation unavailable | ✅ Industry correlation matrix |
| ⚠️ ~20-30% analytics degraded | ✅ Full analytics functional |

**Example Failure**:
```python
# Batch Job 3: Factor Exposures
# Without security master data:
for position in positions:
    sector = security_master.get(position.symbol).sector
    # sector = None → factor loading calculation fails
    # ERR_BATCH_002: Factor analysis incomplete
```

**Required For**:
- ✅ Factor exposure analysis (Batch Job 3)
- ✅ Sector/industry breakdowns
- ✅ Market cap stratification
- ✅ Style box positioning
- ✅ Diversification scores

---

### Missing Step #2: Initial Price Cache Bootstrap

**What It Does** (`app/db/seed_initial_prices.py`):
- Fetches 30 days of historical prices via YFinance API
- Populates market_data_cache table
- Enables P&L calculations
- Provides baseline for market value calculations

**Network Dependency**: Hard dependency on YFinance provider (see DEMO_SEEDING_GUIDE.md Section "External Data Dependencies")

**Impact on New User Portfolios**:

| Without Price Cache | With Price Cache |
|--------------------|------------------|
| ❌ P&L calculations fail (current_price = NULL) | ✅ Unrealized P&L calculated |
| ❌ Market value = entry_price fallback only | ✅ Current market value accurate |
| ❌ Historical charts empty | ✅ 30-day performance chart |
| ⚠️ Portfolio value stale | ✅ Real-time valuation |

**Example Failure**:
```python
# Portfolio value calculation
for position in positions:
    market_value = position.quantity * position.current_price
    # current_price = None → fails
    # Fallback: market_value = position.quantity * position.entry_price
    # Result: Portfolio shows entry values, not current market values
```

**Required For**:
- ✅ P&L calculations (unrealized gains/losses)
- ✅ Portfolio value calculations (current market value)
- ✅ Historical performance charts
- ✅ Batch Job 1 baseline (market data updates)

---

## Batch Processing Assumptions

The `batch_orchestrator_v2.run_daily_batch_sequence()` assumes certain prerequisites exist:

**Batch Job 1: Market Data Updates**
- ✅ Assumes: baseline historical prices exist
- ❌ Without: No starting point for incremental updates
- 🔧 Fix: Run `seed_initial_prices()` first

**Batch Job 2: Position Greeks (Options)**
- ✅ Assumes: underlying symbol prices available
- ⚠️ Without: Greeks calculations fail for options
- 🔧 Fix: Run `seed_initial_prices()` for underlying symbols

**Batch Job 3: Factor Analysis**
- ✅ Assumes: security master data populated
- ❌ Without: Factor loadings cannot be calculated
- 🔧 Fix: Run `seed_security_master()` first

**Batch Job 4: Portfolio Snapshots**
- ✅ Assumes: current market values available
- ⚠️ Without: Snapshot uses entry prices (stale data)
- 🔧 Fix: Run `seed_initial_prices()` first

**Batch Job 5: Correlation Analysis**
- ✅ Assumes: historical prices for all positions
- ⚠️ Without: Correlation matrix incomplete
- 🔧 Fix: Run `seed_initial_prices()` first

---

## Recommendations

### Recommendation #1: Add Preprocessing Step to Onboarding

**Modify**: `app/services/onboarding_service.py`

**Add Method**:
```python
async def prepare_portfolio_for_batch(
    self,
    portfolio_id: UUID,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Prepare portfolio for batch processing by populating prerequisites.

    This mirrors the demo seeding Step 3 but for a single portfolio.

    Steps:
    1. Extract unique symbols from portfolio positions
    2. Seed security master data for those symbols
    3. Bootstrap initial price cache for those symbols
    4. Return readiness status

    Returns:
        {
            "security_master_populated": int,  # Number of symbols enriched
            "price_cache_populated": int,      # Number of symbols with prices
            "coverage_percent": float,         # % of positions with complete data
            "ready_for_batch": bool            # True if >80% coverage
        }
    """
    # Step 1: Get all symbols from portfolio
    symbols = await self._get_portfolio_symbols(portfolio_id, db)

    # Step 2: Enrich security master
    from app.db.seed_security_master import enrich_symbols
    security_results = await enrich_symbols(db, symbols)

    # Step 3: Bootstrap prices
    from app.db.seed_initial_prices import bootstrap_symbols
    price_results = await bootstrap_symbols(db, symbols)

    # Step 4: Calculate coverage
    coverage = (price_results["success_count"] / len(symbols)) * 100

    return {
        "security_master_populated": security_results["enriched_count"],
        "price_cache_populated": price_results["success_count"],
        "coverage_percent": round(coverage, 1),
        "ready_for_batch": coverage >= 80.0
    }
```

**Update API Endpoint**:
```python
# app/api/v1/onboarding.py

@router.post("/create-portfolio", status_code=201)
async def create_portfolio(
    portfolio_name: str,
    equity_balance: Decimal,
    csv_file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create portfolio and prepare for batch processing.

    Steps:
    1. Validate CSV and create portfolio
    2. Import positions from CSV
    3. Prepare portfolio data (NEW - security master + price cache)
    4. Return portfolio_id and readiness status
    """
    # Step 1-2: Existing implementation
    result = await onboarding_service.create_portfolio_with_csv(...)

    # Step 3: NEW - Prepare for batch processing
    prep_result = await onboarding_service.prepare_portfolio_for_batch(
        portfolio_id=result["portfolio_id"],
        db=db
    )

    return {
        "portfolio_id": result["portfolio_id"],
        "positions_imported": result["positions_count"],
        "data_preparation": prep_result,  # NEW
        "message": "Portfolio created. Run calculations when ready.",
        "calculate_url": f"/api/v1/portfolio/{result['portfolio_id']}/calculate"
    }
```

---

### Recommendation #2: Update Batch Endpoint to Check Prerequisites

**Modify**: `app/api/v1/analytics/portfolio.py`

```python
@router.post("/{portfolio_id}/calculate", status_code=202)
async def trigger_calculations(
    portfolio_id: UUID,
    force: bool = False,  # NEW - allow forcing despite warnings
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Trigger batch calculations with prerequisite checks.

    Validates data readiness before running expensive calculations.
    """
    # Check ownership
    portfolio = await verify_portfolio_ownership(portfolio_id, current_user.id, db)

    # NEW - Check prerequisites
    from app.services.onboarding_service import OnboardingService
    onboarding = OnboardingService()

    readiness = await onboarding.check_batch_readiness(portfolio_id, db)

    if not readiness["ready"] and not force:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "ERR_BATCH_005",
                    "message": "Portfolio data incomplete. Prepare portfolio first.",
                    "details": readiness,
                    "suggestion": "Call POST /api/v1/onboarding/create-portfolio to populate prerequisites"
                }
            }
        )

    # Proceed with batch processing
    batch_run_id = await trigger_batch_orchestrator(portfolio_id)

    return {
        "status": "started",
        "batch_run_id": batch_run_id,
        ...
    }
```

---

### Recommendation #3: Update Documentation

**File**: `USER_PORTFOLIO_ONBOARDING_DESIGN.md`

**Add Section 4.6**: Batch Processing Prerequisites

```markdown
## 4.6 Batch Processing Prerequisites

**Context**: The batch orchestrator requires certain data to be populated before calculations can run successfully. The demo seeding pipeline (DEMO_SEEDING_GUIDE.md) includes explicit preprocessing steps that are NOT currently in the user onboarding flow.

### Required Prerequisites

| Prerequisite | Purpose | Impact if Missing |
|-------------|---------|-------------------|
| **Security Master Data** | Sector/industry/market cap for symbols | Factor analysis fails (ERR_BATCH_002) |
| **Historical Price Cache** | 30 days of price history | P&L calculations fail, market values stale |
| **Factor Definitions** | 8 risk factors (SIZE, VALUE, etc.) | Factor exposure calculations fail |
| **Stress Scenarios** | Market stress scenarios | Stress testing unavailable |

### Implementation Approach

**Option A: Automatic Preprocessing** (Recommended)

Modify `POST /api/v1/onboarding/create-portfolio` to automatically call:
1. `seed_security_master()` for portfolio symbols
2. `seed_initial_prices()` for portfolio symbols

This adds ~10-30 seconds to portfolio creation but ensures batch processing succeeds.

**Option B: Manual Preprocessing**

Add new endpoint: `POST /api/v1/portfolio/{id}/prepare-for-batch`

Users must call this before triggering calculations. Provides more control but adds complexity.

**Decision**: Use Option A for Phase 1 MVP (simpler UX, fewer support issues).
```

**Update Section 3.2 Response**:
```json
{
  "portfolio_id": "a3209353-9ed5-4885-81e8-d4bbc995f96c",
  "positions_imported": 47,
  "data_preparation": {  // NEW
    "security_master_populated": 42,
    "price_cache_populated": 38,
    "coverage_percent": 81.0,
    "ready_for_batch": true
  },
  "message": "Portfolio created and ready for calculations.",
  "calculate_url": "/api/v1/portfolio/a3209353-9ed5-4885-81e8-d4bbc995f96c/calculate"
}
```

---

## Justification Analysis

### Should We Include Security Master Enrichment?

**✅ YES - Include in User Onboarding**

**Reasons**:
1. **Required for analytics**: 20-30% of features depend on sector data
2. **Consistent with demo**: Demo portfolios get this automatically
3. **User expectation**: Users expect factor analysis to work
4. **Data quality**: Prevents "Unknown" sectors in production
5. **Minimal cost**: Static dictionary lookup is fast (<1s for 50 symbols)

**Implementation**: Call `seed_security_master(symbols)` during portfolio creation

---

### Should We Include Price Cache Bootstrap?

**✅ YES - Include in User Onboarding**

**Reasons**:
1. **Required for P&L**: Can't calculate unrealized gains without current prices
2. **Required for valuation**: Portfolio value calculations need market prices
3. **Baseline for batch**: Batch Job 1 needs starting point for incremental updates
4. **User expectation**: Users expect to see current portfolio value immediately
5. **Network dependency**: Same YFinance dependency exists in both flows

**Caveats**:
- Network required (10-30s for YFinance API calls)
- Could fail for offline/restricted environments
- 80% coverage threshold acceptable (options excluded)

**Implementation**: Call `seed_initial_prices(symbols)` during portfolio creation with graceful degradation

**Fallback Strategy** (if network fails):
```python
# If YFinance unavailable, use entry prices as baseline
# Set flag: portfolio.needs_price_update = True
# Display warning: "Market data unavailable. Using entry prices."
# Retry during next batch processing run
```

---

## Additional System Prerequisites (Global, Not Per-User)

### System-Wide Reference Data

After reviewing `BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md`, I identified two additional data requirements:

**1. Factor Definitions (8 factors)**
**2. Stress Test Scenarios (18 scenarios)**

**Analysis**: These are **system-wide** reference data, NOT user-specific:

```python
# app/models/market_data.py

class FactorDefinition(Base):
    """Global factor definitions - no user_id or portfolio_id"""
    name: Mapped[str] = mapped_column(String(50), unique=True)  # System-wide
    # No foreign keys - shared by all users

class StressTestScenario(Base):
    """Global stress scenarios - no user_id or portfolio_id"""
    scenario_id: Mapped[str] = mapped_column(String(50), unique=True)  # System-wide
    # No foreign keys - shared by all users
```

**Conclusion**: These do NOT need to be included in per-user onboarding because:
- ✅ Seeded once during **initial system setup** (not per-user)
- ✅ Global reference data shared by all users
- ✅ Should already exist when onboarding starts
- ❌ NOT created per-user like positions or portfolios

**Recommendation**: Add **validation check** at system startup to ensure these prerequisites exist.

### Validation Check for System Prerequisites

**Add to startup validation**:

```python
# app/main.py or app/core/startup.py

async def validate_system_prerequisites():
    """Ensure global reference data exists before allowing user onboarding."""
    async with get_async_session() as db:
        # Check factor definitions
        factor_count = await db.execute(
            select(func.count(FactorDefinition.id))
        )
        if factor_count.scalar() < 8:
            raise RuntimeError(
                "System not initialized: Factor definitions missing. "
                "Run: python scripts/database/seed_database.py"
            )

        # Check stress test scenarios
        scenario_count = await db.execute(
            select(func.count(StressTestScenario.id))
        )
        if scenario_count.scalar() < 18:
            raise RuntimeError(
                "System not initialized: Stress test scenarios missing. "
                "Run: python scripts/database/seed_database.py"
            )

        logger.info("✅ System prerequisites validated (8 factors, 18 scenarios)")
```

**When to run this**:
- ✅ On API server startup
- ✅ Before processing first user onboarding request
- ✅ In deployment health checks

**What happens if missing**:
- ❌ API server refuses to start
- ❌ User onboarding endpoint returns 503 Service Unavailable
- ❌ Error message directs admin to run initial setup scripts

---

## Conclusion

**Summary**: The new user onboarding pipeline is missing two critical **per-user** preprocessing steps that are present in demo seeding:

1. **Security Master Enrichment** - Required for factor analysis, sector breakdowns
2. **Price Cache Bootstrap** - Required for P&L calculations, portfolio valuation

**Impact**: Without these steps, ~20-30% of analytics features will fail or degrade for new user portfolios.

**Recommendation**: Add `prepare_portfolio_for_batch()` method that runs during portfolio creation, mirroring demo seeding Step 3.

**Next Steps**:
1. Implement `prepare_portfolio_for_batch()` in OnboardingService
2. Update `POST /api/v1/onboarding/create-portfolio` to call preprocessing
3. Add prerequisite checks to `POST /api/v1/portfolio/{id}/calculate`
4. Update USER_PORTFOLIO_ONBOARDING_DESIGN.md with preprocessing section
5. Add integration tests verifying batch processing works for new user portfolios
6. Document graceful degradation strategy for network failures

**Timeline**: 2-3 days to implement and test preprocessing integration.

**Risk if not addressed**: New users will experience analytics failures and degraded functionality compared to demo portfolios, leading to support burden and poor first impressions.

---

## Other Data Not Required for Onboarding

### Target Prices (Optional, User-Generated)

**What It Is**: Portfolio-specific target price forecasts (EOY, next year, downside scenarios)

**Analysis**: Target prices are **user-generated content**, NOT system setup data:

```python
# app/models/target_prices.py

class TargetPrice(Base):
    """Portfolio-specific target prices - user adds these later"""
    portfolio_id: Mapped[UUID] = ForeignKey("portfolios.id")  # Per-portfolio
    position_id: Mapped[Optional[UUID]] = ForeignKey("positions.id")  # Per-position
    target_price_eoy: Mapped[Optional[Decimal]]  # User-provided forecast
```

**Conclusion**: Target prices do NOT belong in onboarding pipeline because:
- ❌ NOT required for core analytics (batch processing works without them)
- ❌ User-generated forecasts, not system reference data
- ❌ Added incrementally through Target Price API endpoints
- ✅ Demo seeding includes them for testing purposes only
- ✅ Real users would add them post-onboarding as they develop investment theses

**User Workflow for Target Prices**:
1. User onboards → portfolio created without target prices ✅
2. User analyzes positions over time
3. User adds target prices via `POST /api/v1/portfolio/{id}/target-prices` ✅
4. Portfolio snapshots now include target price metrics (optional enhancement)

**Demo Seeding Includes Them Because**:
- Demonstrates Target Price API functionality
- Provides realistic test data for frontend development
- Shows example of complete portfolio with all features populated

**Recommendation**: Do NOT include target price seeding in user onboarding. Let users add them organically.
