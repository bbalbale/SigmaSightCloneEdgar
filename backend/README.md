# SigmaSight Backend

FastAPI-based portfolio risk analytics platform with 8 calculation engines, automated batch processing, and AI-powered chat interface.

## Quick Start

### Development (Local)
```bash
# Start PostgreSQL
docker-compose up -d

# Run migrations
uv run alembic upgrade head

# Seed demo data
uv run python scripts/database/seed_database.py

# Start development server
uv run python run.py
```

Backend runs at: http://localhost:8000
API Docs: http://localhost:8000/docs

## Updating Your Local Environment

### Database Migrations

When pulling updates that include database migrations:

```bash
# 1. Pull latest code
git pull origin main

# 2. Apply migrations
uv run alembic upgrade head

# 3. If migration requires reset (check migration notes or errors):
uv run python scripts/database/reset_and_seed.py reset --confirm
```

### ⚠️ Breaking Change: Strategy System Removal (October 2025)

Migration `a766488d98ea` removes the legacy strategy system. **Requires full database reset.**

```bash
# After pulling this change:
git pull origin main
uv run alembic upgrade head  # Apply migration
uv run python scripts/database/reset_and_seed.py reset --confirm  # Reset required
```

**What this does:**
- Drops all tables and recreates schema with position tagging system
- Seeds 3 demo portfolios with 75 positions and 130 position-tag relationships
- Removes: strategies, strategy_legs, strategy_metrics, strategy_tags tables
- Adds: Direct position-to-tag relationships via `position_tags` junction table

**What you'll lose:**
- Any custom data (demo data will be recreated)
- Strategy configurations (deprecated system, now uses position tagging)

### Production (Docker)

**Build:**
```bash
docker build -t sigmasight-backend:prod .
```

**Run:**
```bash
docker run -d -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:port/db" \
  -e SECRET_KEY="your-secret-key" \
  -e POLYGON_API_KEY="your-key" \
  -e FMP_API_KEY="your-key" \
  -e OPENAI_API_KEY="your-key" \
  sigmasight-backend:prod
```

**Deploy to Railway:**
```bash
railway link
railway up --detach
```

### Railway Operations

**Database Setup (in Railway SSH):**
```bash
railway shell

# Run migrations
uv run python scripts/railway/railway_run_migration.py

# Verify migration
uv run python scripts/railway/verify_railway_migration.py

# Reset and reseed (DESTRUCTIVE)
uv run python scripts/railway/railway_reset_database.py
```

**Daily Batch Processing:**
```bash
# In Railway SSH
uv run python scripts/automation/railway_daily_batch.py --force

# Verify results
uv run python scripts/verification/verify_batch_results.py
uv run python scripts/verification/verify_database_state.py
```

**Audit from Local Machine (no SSH needed):**
```bash
# Audit portfolio/position data via API
python scripts/railway/audit_railway_data.py

# Audit market data with detailed per-position coverage
python scripts/railway/audit_railway_market_data.py
```

**Note:** All Railway scripts (`scripts/railway/`) automatically convert Railway's `postgresql://` URLs to `postgresql+asyncpg://` for async compatibility.

## User Onboarding System

The backend includes a comprehensive onboarding system for beta users to self-register and import portfolios via CSV.

### Onboarding Flow

**1. User Registration** (POST `/api/v1/onboarding/register`)
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe",
    "invite_code": "PRESCOTT-LINNAEAN-COWPERTHWAITE"
  }'
```

**2. Login** (POST `/api/v1/auth/login`)
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

**3. Download CSV Template** (GET `/api/v1/onboarding/csv-template`)
```bash
curl http://localhost:8000/api/v1/onboarding/csv-template \
  -o portfolio_template.csv
```

**4. Create Portfolio with CSV** (POST `/api/v1/onboarding/create-portfolio`)
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/create-portfolio \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "portfolio_name=My Portfolio" \
  -F "equity_balance=100000" \
  -F "description=My investment portfolio" \
  -F "csv_file=@positions.csv"
```

**5. Trigger Calculations** (POST `/api/v1/portfolio/{id}/calculate`)
```bash
curl -X POST http://localhost:8000/api/v1/portfolio/{portfolio_id}/calculate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### CSV Template Format

The system supports a 12-column CSV format:
1. **Symbol** (required) - Stock/ETF/Option symbol
2. **Quantity** (required) - Number of shares (negative for shorts)
3. **Entry Price Per Share** (required) - Purchase price
4. **Entry Date** (required) - YYYY-MM-DD format
5. **Investment Class** (optional) - PUBLIC, OPTIONS, or PRIVATE
6. **Investment Subtype** (optional) - STOCK, ETF, MUTUAL_FUND, etc.
7. **Underlying Symbol** (for options)
8. **Strike Price** (for options)
9. **Expiration Date** (for options, YYYY-MM-DD)
10. **Option Type** (for options: CALL or PUT)
11. **Exit Date** (optional, for closed positions)
12. **Exit Price Per Share** (optional, for closed positions)

### Configuration

Set environment variables in `.env`:
```bash
# Beta invite code (can be rotated without code changes)
BETA_INVITE_CODE=PRESCOTT-LINNAEAN-COWPERTHWAITE

# UUID generation (deterministic for Phase 1 testing)
DETERMINISTIC_UUIDS=true

# Skip startup validation for local dev/CI
SKIP_STARTUP_VALIDATION=false
```

### Invite Code Management

**Development/Testing:**
- Default invite code works out of the box
- Defined in `app/config.py` with environment variable override

**Production:**
- Override via `BETA_INVITE_CODE` environment variable
- Rotate without code changes for security
- Emergency override capability

**Rotation Procedure:**
1. Update environment variable in deployment
2. Restart application
3. No code changes or redeployment needed

### CSV Import Features

- **Comprehensive Validation**: 35+ error codes with actionable messages
- **Investment Class Auto-Detection**: Automatically classifies stocks, options, ETFs
- **Position Type Detection**: LONG/SHORT for stocks, LC/LP/SC/SP for options
- **Cash Positions**: Supports both tickered (SPAXX) and non-tickered (CASH_USD)
- **Closed Positions**: Track exit dates and realized P&L
- **Duplicate Detection**: Prevents duplicate positions by symbol + entry date

### Preprocessing Pipeline

The system automatically prepares portfolios for batch processing:
1. **Security Master Enrichment**: Adds sector/industry data for each symbol
2. **Price Cache Bootstrap**: Fetches 30 days of historical prices
3. **Readiness Check**: Validates 80% data coverage before calculations

### Batch Processing

After CSV import, trigger the calculation endpoint to:
- Run all 8 calculation engines (Greeks, factors, correlations, etc.)
- Populate risk metrics for the portfolio
- Complete in 30-60 seconds (after 10-30s preprocessing)

### Error Handling

Structured error codes for all validation failures:
- **ERR_INVITE_001**: Invalid invite code
- **ERR_USER_001-004**: User registration errors
- **ERR_CSV_001-006**: CSV file validation errors
- **ERR_POS_001-023**: Position validation errors
- **ERR_PORT_001-008**: Portfolio creation errors

See API docs at `/docs` for complete error reference.

## Features

- **8 Calculation Engines**: Greeks, Factor Analysis, Correlations, Market Risk, Stress Testing, etc.
- **Batch Processing**: Automated daily calculations with APScheduler
- **AI Chat**: OpenAI Responses API integration with SSE streaming
- **Demo Data**: 3 portfolios, 75 positions, ready for testing
- **Async-First**: SQLAlchemy 2.0 async with asyncpg driver
- **Auto Migrations**: Alembic runs on container startup

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection (auto-transformed to asyncpg)
- `SECRET_KEY` - JWT secret key
- `POLYGON_API_KEY` - Market data API
- `FMP_API_KEY` - Financial Modeling Prep API

Optional:
- `OPENAI_API_KEY` - AI chat functionality
- `FRED_API_KEY` - Treasury rates
- `PORT` - Server port (default: 8000)

## Documentation

- **Complete README**: See `/README.md` at repository root
- **API Reference**: `/docs` endpoint when server is running
- **Codebase Guide**: `CLAUDE.md` for AI agents and developers
- **Script Reference**: `scripts/README.md` for detailed script documentation
