# Backend Daily Complete Workflow Guide

> **Last Updated**: 2025-09-11  
> **Purpose**: Daily operational guide for backend development after initial setup  
> **Platforms**: Windows & Mac  
> **Covers**: Database, API Server, Batch Processing, Agent System, Market Data
> 
> ⚠️ **CRITICAL CHANGES (2025-09-11)**:
> - **Scripts Reorganized**: All scripts now organized into subdirectories by function (see note below)
> - **Unicode Encoding**: ✅ FIXED - Scripts now handle UTF-8 automatically on all platforms
> - **Database Migrations**: ALWAYS run migrations after pulling code changes
> - **Equity System**: Portfolio model now includes equity_balance field

## Table of Contents
1. [Critical Developer Notes](#critical-developer-notes) ⚠️ **READ FIRST**
2. [Pre-Flight Checklist](#pre-flight-checklist)
3. [Starting Core Services](#starting-core-services)
4. [Verify System Health](#verify-system-health)
5. [Daily Data Updates](#daily-data-updates)
6. [API Server Operations](#api-server-operations)
7. [Agent System Operations](#agent-system-operations)
8. [Batch Processing](#batch-processing)
9. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
10. [End of Day Shutdown](#end-of-day-shutdown)

---

## Critical Developer Notes

### ⚠️ MUST READ - Recent Breaking Changes

#### 1. Unicode Encoding (✅ RESOLVED)
**Previous Issue**: Scripts with emoji characters failed with `UnicodeEncodeError` on Windows  
**Status**: Fixed as of 2025-09-11 - UTF-8 handling now built into all scripts

```bash
# ✅ Now works on ALL platforms (Windows, Mac, Linux)
uv run python scripts/verification/verify_demo_portfolios.py
uv run python scripts/batch_processing/run_batch_with_reports.py --skip-reports

# No PYTHONIOENCODING prefix needed anymore!
```

**What Changed**:
- All scripts now include UTF-8 handling internally
- Works identically on Windows, Mac, and Linux
- No platform-specific commands needed

#### 2. Database Migrations (CRITICAL)
**Issue**: New fields added to database models require migrations  
**Solution**: ALWAYS run migrations after pulling code

```bash
# After every git pull or code update:
uv run alembic upgrade head

# Verify current status:
uv run alembic current
```

**Recent Critical Migrations**:
- `add_equity_balance_to_portfolio` - Adds equity field for risk calculations
- Without this, API endpoints will return 500 errors!

#### 3. Equity-Based System Changes
**What Changed**: Portfolio model now includes `equity_balance` field  
**Impact**: All portfolio calculations now use equity-based formulas

**Current Equity Values**:
- Demo Individual: $600,000
- Demo HNW: $2,000,000  
- Demo Hedge Fund: $4,000,000

**Key Formulas**:
```
Cash = Equity - Long MV + |Short MV|
Leverage = Gross Exposure / Equity
```

#### 4. Factor Exposure Changes
**What Changed**: Short Interest factor disabled (no ETF proxy)  
**Impact**: Factor API now accepts partial factor sets (7 factors instead of 8)

#### 5. Scripts Directory Reorganization (NEW)
**What Changed**: All 108 scripts reorganized into logical subdirectories  
**Impact**: Script paths have changed - update your commands accordingly

**New Directory Structure**:
```
scripts/
├── batch_processing/     # run_batch_with_reports.py, generate_all_reports.py
├── database/            # seed_database.py, reset_and_seed.py, check_database_content.py
├── testing/             # All test_*.py scripts
├── verification/        # verify_demo_portfolios.py, verify_setup.py
├── analysis/           # Debugging and analysis tools
├── data_operations/    # fetch_factor_etf_data.py, backfill scripts
├── monitoring/         # monitor_chat_interface.py
├── migrations/         # One-time fixes (fix_utf8_encoding.py, etc.)
└── utilities/          # General utilities
```

**Quick Reference - Common Scripts**:
- Batch processing: `scripts/batch_processing/run_batch_with_reports.py`
- Database seeding: `scripts/database/seed_database.py`
- Verify portfolios: `scripts/verification/verify_demo_portfolios.py`
- Check database: `scripts/database/check_database_content.py`
- List portfolios: `scripts/database/list_portfolios.py`

---

## Pre-Flight Checklist

### 1. Environment Check
```bash
# Navigate to backend directory
cd ~/CascadeProjects/SigmaSight-BE/backend    # Mac
cd C:\Projects\SigmaSight-BE\backend          # Windows

# Verify you're in the right directory
ls -la .env     # Mac/Linux
dir .env        # Windows

# Check environment variables are set
grep "FMP_API_KEY" .env       # Mac/Linux
findstr "FMP_API_KEY" .env    # Windows
```

### 2. Check What's Already Running
```bash
# Check if Docker is running
docker ps

# Check if PostgreSQL container exists
docker ps -a | grep postgres

# Check if API server is running
lsof -i :8000                  # Mac/Linux  
netstat -an | findstr :8000    # Windows

# Check if any Python processes are running
ps aux | grep python           # Mac/Linux
tasklist | findstr python      # Windows
```

### 3. Clean Up Stale Processes (if needed)
```bash
# Kill stale API server
kill $(lsof -t -i:8000)        # Mac/Linux
# Windows: Use Task Manager to end python.exe processes

# Remove stale Docker containers
docker stop backend_postgres_1
docker rm backend_postgres_1
```

---

## Starting Core Services

### Step 1: Start Docker Desktop
**Mac:**
```bash
# Check if Docker Desktop is running
docker version

# If not running, start it
open -a Docker  # Opens Docker Desktop app
# Wait for Docker to fully start (whale icon in menu bar)
```

**Windows:**
```bash
# Check if Docker Desktop is running
docker version

# If not running, start it from Start Menu or:
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# Wait for Docker to fully start (whale icon in system tray)
```

### Step 2: Start PostgreSQL Database
```bash
# Start PostgreSQL container
docker-compose up -d

# Verify it's running (should see backend_postgres_1)
docker ps

# Check database logs if needed
docker logs backend_postgres_1

# Test database connection
uv run python -c "from app.database import test_connection; import asyncio; asyncio.run(test_connection())"
```

### Step 3: Apply Database Migrations ⚠️ CRITICAL
```bash
# Check current migration status
uv run alembic current

# Apply any pending migrations - ALWAYS DO THIS AFTER PULLING CODE
uv run alembic upgrade head

# Verify migrations applied
uv run alembic history --verbose | head -10

# Recent critical migrations:
# - add_equity_balance_to_portfolio.py (adds equity_balance field)
# If missing, your API calls will fail!
```

---

## Verify System Health

### 1. Check Demo Data
```bash
# Verify demo users and portfolios exist
uv run python scripts/database/check_database_content.py

# Expected output:
# Users: 3
# Portfolios: 3  
# Total Positions: 63
```

### 2. List Portfolio IDs
```bash
# Get portfolio IDs for today's work
uv run python scripts/database/list_portfolios.py --verbose

# These should be the deterministic IDs (same on all machines):
# demo_individual@sigmasight.com: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
# demo_hnw@sigmasight.com: e23ab931-a033-edfe-ed4f-9d02474780b4
# demo_hedgefundstyle@sigmasight.com: fcd71196-e93e-f000-5a74-31a9eead3118

# If IDs don't match, see SETUP_DETERMINISTIC_IDS.md for fix
```

### 3. Check Market Data Cache
```bash
# Check how much historical data we have
uv run python -c "
import asyncio
from app.database import get_async_session
from sqlalchemy import select, func
from app.models.market_data import MarketDataCache

async def check():
    async with get_async_session() as db:
        count = await db.scalar(select(func.count(MarketDataCache.id)))
        symbols = await db.scalar(select(func.count(func.distinct(MarketDataCache.symbol))))
        print(f'Market data records: {count}')
        print(f'Unique symbols: {symbols}')

asyncio.run(check())
"
```

---

## Daily Data Updates

### 1. Update Market Data (Required Daily)
```bash
# Sync latest market prices (last 5 trading days)
# NOTE: Preserves existing historical data (won't overwrite)
uv run python -c "
import asyncio
from app.batch.market_data_sync import sync_market_data
asyncio.run(sync_market_data())
"

# Backfill missing historical data if needed (90 days)
# NOTE: Now checks per-symbol coverage with 80% threshold
uv run python -c "
import asyncio
from app.batch.market_data_sync import fetch_missing_historical_data
asyncio.run(fetch_missing_historical_data(days_back=90))
"

# Ensure factor analysis data (252 days) - ONLY if doing factor analysis
# NOTE: Automatically backfills any symbols with insufficient data
uv run python -c "
import asyncio
from app.batch.market_data_sync import validate_and_ensure_factor_analysis_data
from app.database import AsyncSessionLocal

async def validate():
    async with AsyncSessionLocal() as db:
        result = await validate_and_ensure_factor_analysis_data(db)
        print(f'Status: {result.get(\"status\")}')
        print(f'Sufficient data: {len(result.get(\"symbols_with_sufficient_data\", []))} symbols')

asyncio.run(validate())
"
```

**Important Changes (Section 6.1.10 Fixes):**
- ✅ Historical data is now **preserved**, not overwritten
- ✅ Coverage checked **per-symbol** (80% threshold for trading days)
- ✅ GICS fetching now **optional** (defaults to False for performance)
- ✅ Metadata rows filtered (only counts actual price data)

### 2. Seed Target Prices (If Needed)

If target prices haven't been seeded or need updating:

```bash
# Check if target prices exist
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.target_prices import TargetPrice
from sqlalchemy import select, func

async def check():
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(TargetPrice.id)))
        print(f'Target price records: {count}')

asyncio.run(check())
"

# If count is 0, seed target prices
uv run python scripts/data_operations/populate_target_prices_via_service.py \
  --csv-file data/target_prices_import.csv --execute
```

Expected: 105 target price records (35 symbols × 3 portfolios)

### 3. Run Batch Calculations

**⚠️ IMPORTANT NOTES**:
1. Pre-API reports (.md summary, .json, .csv) are planned for deletion.
2. **UTF-8 FIXED**: All scripts now handle Unicode automatically (no prefix needed)
3. **DO NOT RUN REPORTS** - Use `--skip-reports` flag for all batch operations.

```bash
# Run batch processing WITHOUT reports (Mac/Linux)
uv run python scripts/batch_processing/run_batch_with_reports.py --skip-reports

# Run batch processing WITHOUT reports (Windows - MUST USE UTF-8)
uv run python scripts/batch_processing/run_batch_with_reports.py --skip-reports

# Run batch for specific portfolio WITHOUT reports
# UTF-8 handling is now built into all scripts (as of 2025-09-11)

# Examples with actual portfolio IDs (ALL PLATFORMS):
# Individual portfolio only
uv run python scripts/batch_processing/run_batch_with_reports.py --portfolio 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe --skip-reports

# High Net Worth portfolio only  
uv run python scripts/batch_processing/run_batch_with_reports.py --portfolio e23ab931-a033-edfe-ed4f-9d02474780b4 --skip-reports

# Hedge Fund portfolio only
uv run python scripts/batch_processing/run_batch_with_reports.py --portfolio fcd71196-e93e-f000-5a74-31a9eead3118 --skip-reports

# The commands work identically on all platforms now!
# Individual portfolio only
uv run python scripts/batch_processing/run_batch_with_reports.py --portfolio 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe --skip-reports

# High Net Worth portfolio only  
uv run python scripts/batch_processing/run_batch_with_reports.py --portfolio e23ab931-a033-edfe-ed4f-9d02474780b4 --skip-reports

# Hedge Fund portfolio only
uv run python scripts/batch_processing/run_batch_with_reports.py --portfolio fcd71196-e93e-f000-5a74-31a9eead3118 --skip-reports
```

**What Batch Processing Does:**
1. Market data sync (fetches latest prices)
2. Portfolio aggregation (calculates totals)
3. Greeks calculation (options sensitivities)
4. Factor analysis (7-factor regression)
5. Market risk scenarios (±5%, ±10%, ±20%)
6. Stress testing (15 extreme scenarios)
7. Portfolio snapshots (daily state capture)
8. Position correlations (relationship analysis)
9. ~~Report generation~~ (DEPRECATED - use API instead)

---

## API Server Operations

### Start the API Server
```bash
# Option A: Production-like mode
uv run python run.py

# Option B: Development mode with auto-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option C: Run in background (Mac/Linux)
nohup uv run python run.py > api.log 2>&1 &
echo $! > api.pid  # Save PID for later

# Option C: Run in background (Windows)
start /B uv run python run.py > api.log 2>&1
```

### Verify API Server
```bash
# Check health endpoint
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# Check API docs
open http://localhost:8000/docs      # Mac
start http://localhost:8000/docs     # Windows

# Test authentication
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_individual@sigmasight.com", "password": "demo12345"}'
```

### Common API Endpoints (13 Verified Working)
**Reference**: See `backend/_docs/requirements/API_SPECIFICATIONS_V1.4.5.md` for complete documentation

```bash
# Set your auth token (from login response)
TOKEN="your_jwt_token_here"

# DATA ENDPOINTS
# Get all portfolios for user
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolios

# Get complete portfolio data with all sections
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/complete

# Get data quality metrics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/data-quality

# Get position details with P&L calculations
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/positions/details?portfolio_id=e23ab931-a033-edfe-ed4f-9d02474780b4

# Get historical prices for a symbol
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/prices/historical/AAPL?days=30

# Get market quotes for multiple symbols
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/prices/quotes?symbols=AAPL,MSFT,GOOGL

# Get factor ETF prices
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/factors/etf-prices

# ANALYTICS ENDPOINTS
# Get portfolio overview with exposures and P&L
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/overview
```

---

## Agent System Operations

### ⚠️ IMPORTANT: Chat/Agent Testing Requires Frontend Authentication

The agent/chat system uses a **dual authentication flow** that requires proper frontend login for full functionality:
- JWT tokens must be set via frontend login page
- Cookie-based authentication for SSE streaming  
- Portfolio context required for chat data access

**For proper end-to-end testing of the chat/agent system:**

### 📖 See Frontend Chat Testing Guide
```bash
# The complete testing guide with authentication flow
cat ../frontend/CHAT_TESTING_GUIDE.md

# Quick reference - MANDATORY sequence:
# 1. Navigate to http://localhost:3005/login
# 2. Login with demo_hnw@sigmasight.com / demo12345
# 3. Wait for redirect to portfolio page (sets JWT)
# 4. ONLY THEN test chat functionality
```

### Why Frontend Testing is Required
- **Authentication Context**: Chat requires JWT tokens set by frontend login
- **Cookie Management**: SSE streaming uses HttpOnly cookies
- **Portfolio Data Access**: Chat tools need authenticated portfolio context
- **Console Monitoring**: Frontend guide includes browser console capture

### Backend-Only Verification (Limited)
If you only need to verify the backend agent endpoints exist:

```bash
# Check if agent endpoints are registered (won't work without auth)
curl http://localhost:8000/api/v1/agent/health

# Test direct backend auth (limited functionality)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' \
  | jq -r '.access_token')

# This may return 401 due to missing cookie auth
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agent/tools
```

### Agent System Components (Backend)
The agent system (`/backend/app/agent/`) provides:
- **OpenAI Integration**: Uses Responses API (not Chat Completions)
- **Tool Registry**: Portfolio analysis tools
- **SSE Streaming**: Real-time response streaming
- **Authentication**: Dual JWT + cookie system

### Monitoring (During Frontend Testing)
```bash
# Start monitoring with browser console capture
cd backend
uv run python simple_monitor.py --mode manual &

# View live monitoring data
tail -f chat_monitoring_report.json | jq '.console_logs[-10:]'

# Check for errors
jq '.console_logs[] | select(.category=="error")' chat_monitoring_report.json
```

**Bottom Line**: For actual chat/agent testing, use the frontend guide at `../frontend/CHAT_TESTING_GUIDE.md`

---

## Batch Processing

### Manual Batch Runs
```bash
# Run specific calculation engine
uv run python -c "
import asyncio
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

async def run():
    # Run factor analysis for all portfolios
    await batch_orchestrator_v2._run_factor_analysis()
    
    # Or run stress tests
    await batch_orchestrator_v2._run_stress_tests()

asyncio.run(run())
"

# Check batch job history
uv run python -c "
import asyncio
from app.database import get_async_session
from sqlalchemy import select
from app.models.batch_jobs import BatchJob
from sqlalchemy.orm import selectinload

async def check():
    async with get_async_session() as db:
        stmt = select(BatchJob).order_by(BatchJob.created_at.desc()).limit(10)
        jobs = await db.scalars(stmt)
        for job in jobs:
            print(f'{job.job_type}: {job.status} - {job.created_at}')

asyncio.run(check())
"
```

### Verify Calculation Results
```bash
# Check if calculations exist for portfolio
# Windows users: Use UTF-8 encoding for scripts with emoji output
uv run python scripts/verification/verify_demo_portfolios.py  # Windows
uv run python scripts/verification/verify_demo_portfolios.py                          # Mac/Linux

# Check specific calculation data
uv run python -c "
import asyncio
from app.database import get_async_session
from sqlalchemy import select, func
from app.models.market_data import PositionFactorExposure

async def check():
    async with get_async_session() as db:
        count = await db.scalar(select(func.count(PositionFactorExposure.id)))
        print(f'Factor exposure records: {count}')

asyncio.run(check())
"
```

---

## Monitoring & Troubleshooting

### Common Issues and Solutions

#### 1. "Database connection refused"
```bash
# Check Docker is running
docker ps

# Restart PostgreSQL
docker-compose restart

# Check connection string
grep DATABASE_URL .env
```

#### 2. "Port 8000 already in use"
```bash
# Find and kill process
lsof -i :8000                    # Mac/Linux
netstat -ano | findstr :8000     # Windows

kill -9 <PID>                    # Mac/Linux
taskkill /PID <PID> /F           # Windows
```

#### 3. "Market data fetch failed"
```bash
# Check API keys
grep "FMP_API_KEY\|POLYGON_API_KEY" .env

# Test market data service
uv run python scripts/testing/test_market_data_service.py

# Check rate limits
tail -f logs/market_data.log | grep "429"
```

#### 4. "Agent not responding"
```bash
# Check OpenAI API key
grep OPENAI_API_KEY .env

# Test OpenAI connection
uv run python -c "
import openai
from app.config import settings
openai.api_key = settings.OPENAI_API_KEY
print('OpenAI configured:', bool(openai.api_key))
"

# Check agent logs
tail -f logs/agent.log
```

### Performance Monitoring
```bash
# Monitor API response times
tail -f logs/access.log | grep -E "POST|GET"

# Check database query performance
docker exec -it backend_postgres_1 psql -U sigmasight -d sigmasight -c "
SELECT query, calls, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;"

# Monitor memory usage
ps aux | grep python | awk '{sum+=$6} END {print "Python Memory: " sum/1024 " MB"}'
```

---

## End of Day Shutdown

### 1. Generate End of Day Reports
```bash
# Generate final reports for the day
uv run python scripts/batch_processing/run_batch_with_reports.py --skip-batch

# Backup reports
cp -r reports/ reports_backup_$(date +%Y%m%d)/    # Mac/Linux
xcopy reports reports_backup_%date:~10,4%%date:~4,2%%date:~7,2% /I    # Windows
```

### 2. Stop Services Gracefully
```bash
# Stop API server
# If running in foreground: Ctrl+C
# If running in background:
kill $(cat api.pid)              # Mac/Linux (if you saved PID)
taskkill /IM python.exe /F       # Windows (kills all Python)

# Stop PostgreSQL (keeps data)
docker-compose stop

# Or completely remove containers (data persists in volumes)
docker-compose down
```

### 3. Clean Up Logs (Optional)
```bash
# Archive old logs
tar -czf logs_$(date +%Y%m%d).tar.gz logs/    # Mac/Linux
# Windows: Use 7-Zip or similar

# Clear log files but keep structure
> logs/app.log
> logs/agent.log
> logs/market_data.log
```

### 4. Verify Clean Shutdown
```bash
# No Python processes should be running
ps aux | grep python             # Mac/Linux
tasklist | findstr python        # Windows

# No ports should be occupied
lsof -i :8000                    # Mac/Linux
netstat -an | findstr :8000      # Windows

# Docker should show no running containers (or only unrelated ones)
docker ps
```

---

## Quick Reference Card

### Essential Commands
```bash
# Start everything
docker-compose up -d && uv run python run.py

# Check status
docker ps && curl http://localhost:8000/health

# Run batch processing
uv run python scripts/batch_processing/run_batch_with_reports.py

# Stop everything
docker-compose stop && pkill -f "python run.py"

# View logs
tail -f logs/app.log

# Database shell
docker exec -it backend_postgres_1 psql -U sigmasight -d sigmasight
```

### Portfolio IDs (Deterministic - Same on All Machines)
```
Individual: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe (Equity: $600,000)
High Net Worth: e23ab931-a033-edfe-ed4f-9d02474780b4 (Equity: $2,000,000)
Hedge Fund: fcd71196-e93e-f000-5a74-31a9eead3118 (Equity: $4,000,000)
```
**Note**: These are deterministic UUIDs generated from email hashes.
**Equity Values**: Set via database migration (add_equity_balance_to_portfolio)
If your IDs differ, run: `uv run python scripts/database/reset_and_seed.py reset --confirm`
See [SETUP_DETERMINISTIC_IDS.md](../SETUP_DETERMINISTIC_IDS.md) for details.

### API Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_individual@sigmasight.com", "password": "demo12345"}'

# Use token
export TOKEN="<token_from_login>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/data/portfolios
```

---

## Daily Checklist

- [ ] Docker Desktop running
- [ ] PostgreSQL container started
- [ ] ⚠️ Database migrations applied (CRITICAL - check after every pull)
- [ ] Market data synced
- [ ] Target prices populated (if using Target Price APIs)
- [ ] Batch calculations run (Windows: use PYTHONIOENCODING=utf-8)
- [ ] API server started
- [ ] Agent system verified
- [ ] ~~Reports generated~~ (SKIP - use API instead)
- [ ] Monitoring active
- [ ] Clean shutdown at end of day

---

## Notes

- **Market Data**: FMP/Polygon API rate limits reset daily
- **Options Data**: Limited availability, expect some failures
- **Factor Analysis**: Requires 252 days of historical data (7 factors now, Short Interest disabled)
- **Agent System**: Uses OpenAI API (check usage/costs)
- **Batch Processing**: Takes ~60 seconds per portfolio
- **Database Backups**: Volumes persist between container restarts
- **⚠️ Unicode on Windows**: ALWAYS use `PYTHONIOENCODING=utf-8` prefix for scripts
- **⚠️ Database Changes**: ALWAYS run `uv run alembic upgrade head` after pulling code
- **Equity System**: Portfolios now have equity_balance field for risk calculations

For initial setup, see [BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md)