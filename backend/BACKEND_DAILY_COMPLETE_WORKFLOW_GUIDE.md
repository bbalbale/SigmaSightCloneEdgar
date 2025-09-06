# Backend Daily Complete Workflow Guide

> **Last Updated**: 2025-09-06  
> **Purpose**: Daily operational guide for backend development after initial setup  
> **Platforms**: Windows & Mac  
> **Covers**: Database, API Server, Batch Processing, Agent System, Market Data

## Table of Contents
1. [Pre-Flight Checklist](#pre-flight-checklist)
2. [Starting Core Services](#starting-core-services)
3. [Verify System Health](#verify-system-health)
4. [Daily Data Updates](#daily-data-updates)
5. [API Server Operations](#api-server-operations)
6. [Agent System Operations](#agent-system-operations)
7. [Batch Processing](#batch-processing)
8. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
9. [End of Day Shutdown](#end-of-day-shutdown)

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

### Step 3: Apply Database Migrations
```bash
# Check current migration status
uv run alembic current

# Apply any pending migrations
uv run alembic upgrade head

# Verify migrations applied
uv run alembic history --verbose | head -10
```

---

## Verify System Health

### 1. Check Demo Data
```bash
# Verify demo users and portfolios exist
uv run python scripts/check_database_content.py

# Expected output:
# Users: 3
# Portfolios: 3  
# Total Positions: 63
```

### 2. List Portfolio IDs
```bash
# Get portfolio IDs for today's work
uv run python scripts/list_portfolios.py --verbose

# Save these IDs - you'll need them for:
# - Batch processing specific portfolios
# - API testing
# - Report generation
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
uv run python -c "
import asyncio
from app.batch.market_data_sync import sync_market_data
asyncio.run(sync_market_data())
"

# Backfill missing historical data if needed (90 days)
uv run python -c "
import asyncio
from app.batch.market_data_sync import fetch_missing_historical_data
asyncio.run(fetch_missing_historical_data(days_back=90))
"

# Ensure factor analysis data (252 days) - ONLY if doing factor analysis
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

### 2. Run Batch Calculations
```bash
# Run batch processing for all portfolios
uv run python scripts/run_batch_with_reports.py

# Run for specific portfolio only
uv run python scripts/run_batch_with_reports.py --portfolio <PORTFOLIO_ID>

# Skip batch, only generate reports  
uv run python scripts/run_batch_with_reports.py --skip-batch

# Run batch without reports
uv run python scripts/run_batch_with_reports.py --skip-reports
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

### Common API Endpoints
```bash
# Set your auth token (from login response)
TOKEN="your_jwt_token_here"

# Get portfolios
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolios

# Get portfolio overview
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/portfolios/<PORTFOLIO_ID>/overview

# Get positions
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolios/<PORTFOLIO_ID>/positions

# Get factor exposures
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolios/<PORTFOLIO_ID>/factor_exposures
```

---

## Agent System Operations

### 1. Start Agent Server (Chat Interface)
The agent system provides an AI-powered chat interface for portfolio analysis.

```bash
# The agent endpoints are part of the main API server
# Ensure API server is running first (see above)

# Verify agent endpoints are available
curl http://localhost:8000/api/v1/agent/health

# Check available tools
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agent/tools
```

### 2. Test Agent Chat
```bash
# Start a chat session
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my portfolio performance?",
    "portfolio_id": "<PORTFOLIO_ID>"
  }'

# Stream responses (SSE)
curl -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/agent/chat/stream?message=Analyze+my+risk&portfolio_id=<PORTFOLIO_ID>"
```

### 3. Agent System Components
The agent system (`/backend/app/agent/`) includes:
- **Chat Handler**: Processes natural language queries
- **Tool Registry**: Available analysis tools
- **Market Data Tools**: Fetch prices, quotes
- **Portfolio Tools**: Analyze positions, risk
- **Calculation Tools**: Run factor analysis, stress tests
- **Report Tools**: Generate custom reports

### 4. Monitor Agent Activity
```bash
# Check agent logs
tail -f logs/agent.log

# Monitor OpenAI API usage
grep "OpenAI" logs/app.log | tail -20

# Check active sessions
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agent/sessions
```

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
uv run python scripts/verify_demo_portfolios.py

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
uv run python scripts/test_market_data_service.py

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
uv run python scripts/run_batch_with_reports.py --skip-batch

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
uv run python scripts/run_batch_with_reports.py

# Stop everything
docker-compose stop && pkill -f "python run.py"

# View logs
tail -f logs/app.log

# Database shell
docker exec -it backend_postgres_1 psql -U sigmasight -d sigmasight
```

### Portfolio IDs (Update with your actual IDs)
```
Individual: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
High Net Worth: e23ab931-a033-edfe-ed4f-9d02474780b4
Hedge Fund: fcd71196-e93e-f000-5a74-31a9eead3118
```

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
- [ ] Database migrations applied
- [ ] Market data synced
- [ ] Batch calculations run
- [ ] API server started
- [ ] Agent system verified
- [ ] Reports generated
- [ ] Monitoring active
- [ ] Clean shutdown at end of day

---

## Notes

- **Market Data**: FMP/Polygon API rate limits reset daily
- **Options Data**: Limited availability, expect some failures
- **Factor Analysis**: Requires 252 days of historical data
- **Agent System**: Uses OpenAI API (check usage/costs)
- **Batch Processing**: Takes ~60 seconds per portfolio
- **Database Backups**: Volumes persist between container restarts

For initial setup, see [BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md)