# ONBOARDING_NEW_ACCOUNT_PORTFOLIO.md

Complete guide for onboarding new client accounts with portfolio data into the SigmaSight platform.

> **Target Audience**: AI coding agents and human developers responsible for client onboarding
> **Prerequisites**: Complete [BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md) first
> **Estimated Time**: 45-60 minutes for complete onboarding and verification

## **⚠️ IMPORTANT: Complete Initial Setup First**

**Before using this guide**, you MUST complete the initial system setup:

1. **Read and follow**: [BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md)
2. **Verify**: System is running with demo accounts and API server active
3. **Then**: Return here to onboard new client accounts

This guide assumes you have a fully functioning SigmaSight environment.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Account Creation](#account-creation)
4. [CSV Portfolio Import](#csv-portfolio-import)
5. [Database Population](#database-population)
6. [Market Data Backfill](#market-data-backfill)
7. [Batch Calculation Workflow](#batch-calculation-workflow)
8. [End-to-End Verification](#end-to-end-verification)
9. [Troubleshooting](#troubleshooting)
10. [Production Considerations](#production-considerations)

---

## Overview

The SigmaSight onboarding process transforms a new client's portfolio data into a fully operational analytics platform with:
- **User Account**: Secure authentication with deterministic development IDs
- **Portfolio Structure**: Positions, tags, and metadata properly categorized
- **Market Data**: Historical pricing for all holdings
- **Analytics**: Risk metrics, factor exposures, correlations, and stress tests
- **Frontend Access**: Both portfolio dashboard and AI chat functionality

**Architecture Flow:**
```
CSV File → Account Creation → Database Population → Market Data → Batch Calculations → Frontend Verification
```

---

## Prerequisites

### Environment Requirements

> **⚠️ If you haven't completed initial setup, stop here and follow [BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md) first.**

**Quick verification** (should all pass if initial setup completed):

> **📁 Working Directory**: All commands in this guide assume you're in the `backend/` directory. Run `cd backend` first if needed.

```bash
# Verify you're in backend directory
cd /Users/elliottng/CascadeProjects/SigmaSight-BE/backend

# Verify database is running
docker ps | grep postgres

# Verify API server is running  
curl http://localhost:8000/health

# Verify demo accounts exist
uv run python scripts/list_portfolios.py
```

**Expected**: 3 demo portfolios listed with deterministic IDs

### Additional Requirements for Client Onboarding
- **Running API server** at `localhost:8000`
- **Demo accounts functioning** for testing patterns
- **Batch processing working** (tested in initial setup)

### Directory Structure
```bash
backend/
├── data/
│   └── imports/           # CSV files location
├── scripts/
│   ├── onboard_client.py  # Main onboarding script (to be created)
│   └── verify_client.py   # Verification script (to be created)
└── app/
    └── db/
        └── client_onboarding.py  # Onboarding utilities (to be created)
```

---

## Account Creation

### 1. Prepare Client Information

Create a client info JSON file for consistency:

```json
{
    "email": "john.smith@example.com", 
    "full_name": "John Smith",
    "password": "secure_client_password_123",
    "portfolio_name": "John Smith Investment Portfolio",
    "portfolio_description": "Growth-oriented portfolio with value opportunities and risk hedging",
    "currency": "USD"
}
```

**Required Fields (matching database schema):**
- `email`: Client email address (unique identifier)
- `full_name`: Client's full name
- `password`: Secure password for authentication
- `portfolio_name`: Display name for the portfolio
- `portfolio_description`: Optional strategy description
- `currency`: Portfolio currency (defaults to 'USD')

### 2. Generate Deterministic IDs (Development) vs Random (Production)

**Development Environment** (following existing demo pattern):
```python
def generate_deterministic_uuid(seed_string: str) -> UUID:
    """Generate consistent UUID from seed string - DEVELOPMENT ONLY"""
    import hashlib
    from uuid import UUID
    hash_hex = hashlib.md5(seed_string.encode()).hexdigest()
    return UUID(hash_hex)

# Usage - same IDs across all dev machines
user_id = generate_deterministic_uuid(f"{email}_user")
portfolio_id = generate_deterministic_uuid(f"{email}_portfolio")
```

**Production Environment**:
```python
from uuid import uuid4

# Usage - cryptographically secure random UUIDs
user_id = uuid4()
portfolio_id = uuid4()
```

> **Note**: The existing demo accounts use deterministic IDs for development consistency. New client accounts should use the same pattern in dev, but random UUIDs in production.

### 3. Account Creation Script Pattern

Based on existing `seed_demo_portfolios.py` pattern:

```python
async def create_client_account(db: AsyncSession, client_info: dict) -> tuple[UUID, UUID]:
    """Create new client account with user and portfolio"""
    
    # Create user
    hashed_password = get_password_hash(client_info["password"])
    user = User(
        id=generate_deterministic_uuid(f"{client_info['email']}_user"),
        email=client_info["email"],
        full_name=client_info["full_name"],
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(user)
    
    # Create portfolio
    portfolio = Portfolio(
        id=generate_deterministic_uuid(f"{client_info['email']}_portfolio"),
        user_id=user.id,
        name=client_info["portfolio_name"],
        description=client_info.get("portfolio_description"),
        currency=client_info.get("currency", "USD")
    )
    db.add(portfolio)
    
    await db.commit()
    return user.id, portfolio.id
```

---

## CSV Portfolio Import

### Expected CSV Format

Standard portfolio CSV with the following required columns:

```csv
symbol,quantity,entry_price,position_type,entry_date,tags,underlying_symbol,strike_price,expiration_date
AAPL,1000,150.25,LONG,2024-01-15,"Core Holdings,Tech Growth",,,
MSFT,800,320.50,LONG,2024-01-10,"Core Holdings,Tech Growth",,,
GOOGL,500,125.75,LONG,2024-01-20,"Core Holdings,Tech Growth",,,
SPY250919C00460000,200,7.00,LC,2024-01-10,"Options Overlay",SPY,460.00,2025-09-19
TSLA,-300,250.00,SHORT,2024-02-01,"Short Value Traps",,,
```

**Column Specifications (matching database schema):**
- `symbol`: Ticker symbol (for options: use OCC format)
- `quantity`: Position size (negative for shorts)
- `entry_price`: Average cost per share/contract (maps to `entry_price` field)
- `position_type`: LONG, SHORT, LC, LP, SC, SP (actual PositionType enum values)
- `entry_date`: YYYY-MM-DD format
- `tags`: Comma-separated tags for categorization
- `underlying_symbol`: (Options only) Underlying symbol - **MUST BE BLANK for equities**
- `strike_price`: (Options only) Strike price - **MUST BE BLANK for equities**  
- `expiration_date`: (Options only) Expiration date YYYY-MM-DD - **MUST BE BLANK for equities**

**Important**: For equity positions (LONG/SHORT), always leave the option fields (`underlying_symbol`, `strike_price`, `expiration_date`) completely empty to avoid parsing issues.

**Position Type Mapping:**
- `LONG`: Long Stock
- `SHORT`: Short Stock  
- `LC`: Long Call
- `LP`: Long Put
- `SC`: Short Call
- `SP`: Short Put

### CSV Import Directory

Place CSV files in: `backend/data/imports/{client_email}/portfolio.csv`

```bash
# Create import directory
mkdir -p data/imports/john.smith@example.com
# Place CSV file
cp ~/client_portfolio.csv data/imports/john.smith@example.com/portfolio.csv
```

---

## Database Population

### Position Import Script Pattern

Following the existing demo portfolio structure:

```python
async def import_positions_from_csv(
    db: AsyncSession, 
    portfolio_id: UUID, 
    csv_file_path: str
) -> List[Position]:
    """Import positions from CSV file"""
    
    # Get user_id from portfolio for tag association
    portfolio_result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = portfolio_result.scalar_one()
    user_id = portfolio.user_id
    
    positions = []
    
    with open(csv_file_path, 'r') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Parse position type
            position_type = parse_position_type(row['position_type'])
            
            # Create position
            position = Position(
                id=uuid4(),  # Use random UUID for positions
                portfolio_id=portfolio_id,
                symbol=row['symbol'],
                quantity=Decimal(row['quantity']),
                entry_price=Decimal(row['entry_price']),
                position_type=position_type,
                entry_date=datetime.strptime(row['entry_date'], '%Y-%m-%d').date()
            )
            
            # Handle options metadata (if present and not empty)
            if row.get('underlying_symbol'):
                position.underlying_symbol = row['underlying_symbol']
            if row.get('strike_price'):
                position.strike_price = Decimal(row['strike_price'])
            if row.get('expiration_date'):
                position.expiration_date = datetime.strptime(row['expiration_date'], '%Y-%m-%d').date()
            
            db.add(position)
            positions.append(position)
            
            # Process tags
            if row['tags']:
                tag_names = [tag.strip() for tag in row['tags'].split(',')]
                for tag_name in tag_names:
                    tag = await get_or_create_tag(db, tag_name, user_id)
                    position.tags.append(tag)  # Many-to-many relationship
    
    await db.commit()
    return positions

def parse_position_type(position_type_str: str) -> PositionType:
    """Convert string to PositionType enum"""
    mapping = {
        'LONG': PositionType.LONG,
        'SHORT': PositionType.SHORT, 
        'LC': PositionType.LC,
        'SC': PositionType.SC,
        'LP': PositionType.LP,
        'SP': PositionType.SP,
    }
    return mapping.get(position_type_str, PositionType.LONG)
```

### Complete Import Workflow

```bash
# Note: Custom onboarding script needs to be created based on this guide
# Use existing scripts as reference:
uv run python scripts/seed_database.py  # For database setup
uv run python scripts/check_database_content.py  # For verification
```

---

## Market Data Backfill

### Historical Data Requirements

Ensure all portfolio positions have adequate historical market data:

1. **Equities**: 2+ years of daily OHLCV data
2. **Options**: Current pricing data (Greeks calculation currently disabled in batch orchestrator)
3. **ETFs**: Daily prices plus underlying holdings data
4. **Economic Data**: Risk-free rates, benchmarks

### Market Data Backfill Process

Based on existing batch orchestration patterns:

```python
async def backfill_portfolio_market_data(
    portfolio_id: UUID,
    lookback_days: int = 730  # 2 years default
) -> Dict[str, Any]:
    """Backfill market data for all positions in portfolio"""
    
    results = {
        "symbols_processed": [],
        "symbols_failed": [],
        "data_points_added": 0
    }
    
    # Get all unique symbols from portfolio
    symbols = await get_portfolio_symbols(portfolio_id)
    
    # Process each symbol
    for symbol in symbols:
        try:
            # Check existing data coverage
            data_gap = await check_market_data_coverage(symbol, lookback_days)
            
            if data_gap:
                # Fetch missing data from FMP/Polygon
                await fetch_historical_data(symbol, data_gap)
                results["symbols_processed"].append(symbol)
                
        except Exception as e:
            logger.error(f"Failed to backfill {symbol}: {e}")
            results["symbols_failed"].append(symbol)
    
    return results

# Execute market data backfill
# Note: Custom market data backfill script needs to be created
# Use existing scripts as reference:
uv run python scripts/backfill_factor_etfs.py  # For factor ETF data
uv run python scripts/check_historical_data_coverage.py  # For coverage analysis
```

### Market Data Providers Priority

1. **FMP (Primary)**: Equities, ETFs, economic data
2. **Polygon**: Options data, alternatives
3. **Graceful Degradation**: Mock data when providers unavailable

---

## Batch Calculation Workflow

### Full Calculation Pipeline

Execute the complete 8-engine calculation workflow using existing batch orchestrator:

```bash
# Run complete batch processing for new portfolio
uv run python scripts/run_batch_with_reports.py --portfolio <portfolio_id>
```

### Calculation Engines Executed

1. **Market Data Cache**: Daily price updates
2. **Position Greeks**: ⚠️ **Currently disabled** in BatchOrchestratorV2  
3. **Factor Exposures**: Risk factor analysis
4. **Portfolio Snapshots**: Daily portfolio state
5. **Correlation Analysis**: Inter-position correlations
6. **Risk Metrics**: VaR, portfolio risk measures
7. **Stress Testing**: Scenario analysis
8. **Interest Rate Beta**: Fixed income sensitivity

### Monitoring Batch Execution

```python
# Check batch execution status
async def monitor_batch_progress(portfolio_id: UUID) -> Dict[str, Any]:
    """Monitor batch calculation progress"""
    from app.batch.batch_orchestrator_v2 import BatchOrchestratorV2
    
    orchestrator = BatchOrchestratorV2()
    status = await orchestrator.run_daily_batch_sequence(
        portfolio_id=str(portfolio_id),
        run_correlations=True  # Enable full correlation matrix
    )
    
    return {
        "engines_completed": len([r for r in status if r["status"] == "success"]),
        "engines_failed": len([r for r in status if r["status"] == "failed"]),
        "total_runtime": sum(r.get("runtime_seconds", 0) for r in status),
        "data_quality": await assess_data_quality(portfolio_id)
    }
```

### Expected Calculation Results

After successful batch execution, verify:
- ⚠️ Greeks calculations **currently disabled** in BatchOrchestratorV2 (line 177)
- ✅ Factor exposures for all equity positions  
- ✅ Correlation matrix with adequate data coverage
- ✅ Portfolio snapshots for last 30 days
- ✅ Stress test scenarios executed
- ✅ Risk metrics calculated

---

## End-to-End Verification

### 1. Backend API Verification

Test all critical API endpoints:

```bash
# Verify authentication works and capture JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"john.smith@example.com","password":"secure_client_password_123"}' \
    | jq -r '.access_token')

echo "JWT Token: $TOKEN"

# Test portfolio data endpoint
curl -X GET "http://localhost:8000/api/v1/data/portfolio/<portfolio_id>/complete" \
    -H "Authorization: Bearer $TOKEN"

# Test analytics endpoints
curl -X GET "http://localhost:8000/api/v1/analytics/portfolio/<portfolio_id>/overview" \
    -H "Authorization: Bearer $TOKEN"
```

### 2. Frontend Portfolio Page Verification

Navigate to frontend and verify:

```bash
# Start frontend (if not running)
cd frontend
# Build image first if not already built:
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Alternative: Use npm dev server
# npm run dev

# Test portfolio access
# Navigate to: http://localhost:3005/login
# Login with client credentials
# Verify redirect to portfolio page with data
```

**Frontend Verification Checklist:**
- ✅ Login successful with client credentials
- ✅ Portfolio page loads with positions data
- ✅ Position details show correct quantities and P&L
- ✅ Charts and visualizations display
- ✅ No console errors in browser DevTools

### 3. Chat Interface Verification  

Test AI chat functionality:

```bash
# Ensure chat authentication works
# From portfolio page, open chat interface
# Test sample queries:
```

**Chat Verification Queries:**
1. "What are my top 5 holdings by value?"
2. "Show me my portfolio's factor exposures"
3. "What's my portfolio's correlation with the S&P 500?"
4. "Run a stress test on my portfolio"

**Expected Chat Behaviors:**
- ✅ Chat opens without errors
- ✅ Authentication context preserved
- ✅ Portfolio-specific responses
- ✅ Accurate data in responses
- ✅ Streaming responses work correctly

### 4. Data Quality Verification

Run comprehensive data quality checks:

```bash
# Verify data completeness
uv run python scripts/verify_demo_portfolios.py  # Verify portfolio data
uv run python scripts/check_database_content.py  # Check database state
```

**Data Quality Metrics:**
- **Market Data Coverage**: >95% for last 90 days
- **Calculation Completeness**: All engines successful  
- **Position Accuracy**: CSV import matches DB positions
- **Risk Metrics**: All major metrics calculated
- **Performance**: API response times <500ms

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Portfolio not found" in frontend
**Cause**: Portfolio ID not properly resolved or authentication issue
**Solution**: 
```bash
# Verify portfolio exists and user has access
uv run python -c "
from app.database import get_async_session
from app.models.users import Portfolio, User
from sqlalchemy import select
import asyncio

async def check():
    async with get_async_session() as db:
        result = await db.execute(select(Portfolio).where(Portfolio.id == '<portfolio_id>'))
        portfolio = result.scalar_one_or_none()
        print(f'Portfolio found: {portfolio is not None}')

asyncio.run(check())
"
```

#### Issue: Missing market data for positions  
**Cause**: API rate limits, invalid symbols, or provider issues
**Solution**:
```bash
# Check specific symbol data
uv run python scripts/test_market_data.py  # Test market data integration

# Retry with graceful degradation
# Note: Custom market data backfill script needs to be created
# Use existing scripts as reference:
uv run python scripts/backfill_factor_etfs.py  # For factor ETF data
uv run python scripts/check_historical_data_coverage.py  # For coverage analysis --mock-fallback
```

#### Issue: Batch calculations failing
**Cause**: Missing dependencies, async/sync mixing, or data quality issues
**Solution**: 
```bash
# Run diagnostic checks
uv run python scripts/analyze_demo_calculation_engine_failures.py  # Diagnose batch issues

# Check for known issues
# Reference: backend/TODO1.md Section 1.6.14
```

#### Issue: Frontend shows 401 errors
**Cause**: JWT token issues or CORS configuration
**Solution**:
```bash
# Verify JWT token is properly stored
# Check browser DevTools → Application → localStorage for "access_token"

# Test authentication flow manually
curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"<client_email>","password":"<client_password>"}'
```

### Error Recovery Procedures

#### Rollback Failed Onboarding
```bash
# Remove client data if onboarding fails
# Note: Client removal script needs to be created
# Use database operations with proper cleanup

# Clean up market data cache
# Note: Market data cleanup script needs to be created
# Use existing database operations for cleanup
```

#### Retry Partial Failures
```bash
# Note: Resume functionality would need to be implemented in custom onboarding script
# Use existing scripts for specific recovery actions:
uv run python scripts/check_database_content.py  # Check current state
uv run python scripts/analyze_demo_calculation_engine_failures.py  # Diagnose issues
```

---

## Production Considerations

### Security Requirements

1. **Password Policies**: Enforce strong passwords in production
2. **JWT Secrets**: Use cryptographically secure secret keys
3. **API Rate Limiting**: Implement rate limits for client endpoints
4. **Input Validation**: Sanitize all CSV input data
5. **Audit Logging**: Log all onboarding activities

### Scalability Considerations

1. **Batch Processing**: Use background queues for large portfolios
2. **Market Data**: Implement caching and bulk data fetching
3. **Database**: Monitor query performance and optimize indexes
4. **File Storage**: Move CSV imports to cloud storage (S3/GCS)

### Monitoring and Alerting

```bash
# Set up monitoring for onboarding process
# Monitor batch job completion rates
# Alert on market data failures
# Track authentication success rates
```

### Production Deployment Checklist

- [ ] Use proper UUID generation (not deterministic)
- [ ] Configure production database with proper backup
- [ ] Set up SSL/TLS for all endpoints
- [ ] Implement proper logging and monitoring
- [ ] Configure rate limiting and security headers
- [ ] Test disaster recovery procedures
- [ ] Document client support procedures

---

## Script Templates

### Implementation Notes

**Custom Scripts Needed:**

The onboarding process requires creating custom scripts that combine existing functionality:

1. **`scripts/onboard_client.py`** - Main onboarding orchestration script
   - Use patterns from `scripts/seed_database.py` for database operations
   - Reference `scripts/check_database_content.py` for verification
   - Integrate with `app.batch.batch_orchestrator_v2.BatchOrchestratorV2`

2. **`scripts/verify_client.py`** - End-to-end verification script  
   - Use patterns from `scripts/verify_demo_portfolios.py`
   - Reference `scripts/test_api_endpoints.sh` for API testing
   - Check `scripts/analyze_demo_calculation_engine_failures.py` for diagnostics

**Implementation Approach:**
- Build on existing tested patterns from demo portfolio setup
- Use actual existing scripts as building blocks
- Follow async patterns from `app/batch/batch_orchestrator_v2.py`
- Reference `backend/AI_AGENT_REFERENCE.md` for established patterns

---

## Summary

This onboarding process provides a complete workflow for transforming a client's CSV portfolio data into a fully functional SigmaSight analytics platform. The process emphasizes:

- **Data Integrity**: Comprehensive validation at each step
- **Error Recovery**: Graceful handling of failures with retry capabilities  
- **Verification**: End-to-end testing of both backend and frontend functionality
- **Production Ready**: Security and scalability considerations built-in

**Total Process Time**: ~45-60 minutes for typical portfolio (20-100 positions)
**Success Criteria**: Client can login, view portfolio, and interact with AI chat
**Monitoring**: All steps logged with detailed metrics and error reporting

For production deployment, ensure all security measures are implemented and the process is thoroughly tested with various portfolio sizes and compositions.

---

## **Integration with Initial Setup Guide**

This onboarding process integrates seamlessly with the initial setup workflow:

### **Workflow Integration:**
1. **First**: Complete [BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md)
   - ✅ System setup with demo accounts
   - ✅ API server running
   - ✅ Batch processing validated

2. **Then**: Use this guide for client onboarding
   - ✅ New client account creation
   - ✅ CSV portfolio import  
   - ✅ Market data backfill
   - ✅ Frontend verification

### **Shared Components:**
- **Batch Processing**: Uses same `run_batch_with_reports.py` script
- **API Testing**: Uses same authentication and endpoint patterns
- **Verification**: Uses same health checks and validation scripts
- **Database**: Uses same PostgreSQL instance and models

### **Key Differences:**
- **Initial Setup**: Creates demo accounts with deterministic IDs
- **Client Onboarding**: Creates real client accounts (dev: deterministic, prod: random)
- **Initial Setup**: Tests with known demo portfolios
- **Client Onboarding**: Tests with new client portfolio data

This ensures a consistent development experience whether working with demo data or onboarding real clients.