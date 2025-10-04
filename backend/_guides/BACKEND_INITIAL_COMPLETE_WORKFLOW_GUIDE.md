# Initial Setup Guide - First-Time Installation

> **Last Updated**: 2025-09-06
> **Purpose**: Initial setup and configuration only
> **Next Steps**: See [BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md) for daily operations

This guide covers the **initial setup only**. After completing this guide, refer to the [Daily Workflow Guide](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md) for ongoing operations.

## Prerequisites

✅ Completed the [Windows Setup Guide](setup-guides/WINDOWS_SETUP_GUIDE.md) or [Mac Install Guide](setup-guides/MAC_INSTALL_GUIDE.md)  
✅ Docker Desktop is running  
✅ You're in the project directory: `backend`  
✅ API keys configured in `.env` file (especially FMP_API_KEY which is REQUIRED)  
✅ JWT_SECRET_KEY configured in `.env` file for API authentication

---

## Step 1: Start the Database

```bash
# Make sure you're in the sigmasight-backend directory
cd C:\Projects\SigmaSight-BE\backend  # Windows
# or
cd ~/Projects/SigmaSight-BE/backend    # Mac

# Start PostgreSQL
docker-compose up -d

# Verify it's running
docker ps
```

You should see a container named `backend_postgres_1` running.

---

## Step 2: Set Up Database Schema

```bash
# Apply all database migrations (recommended)
uv run alembic upgrade head

# Or use the automated setup script (alternative)
uv run python scripts/setup_dev_database_alembic.py
```

This creates all necessary tables for calculations, snapshots, correlations, etc.

---

## Step 3: Create Demo Accounts and Portfolios

### ⚠️ CRITICAL WARNING: Check for Existing Data First!

**BEFORE running any reset commands, check if you already have data:**

```bash
# CHECK FIRST - See if you already have portfolios
uv run python scripts/database/check_database_content.py

# If portfolios exist, SKIP THIS STEP entirely!
# The reset command DELETES ALL DATA permanently
```

### Only for FIRST-TIME Setup (No Existing Data)

```bash
# ⚠️ WARNING: This command DELETES ALL EXISTING DATA!
# Only run if you have NO existing portfolios/data
uv run python scripts/reset_and_seed.py reset --confirm

# Alternative: Safer approach - seed without reset
uv run python scripts/database/seed_database.py
```

This creates:
- **3 Demo Accounts** with deterministic portfolio IDs:
  - `demo_individual@sigmasight.com` → Portfolio: `1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe`
  - `demo_hnw@sigmasight.com` → Portfolio: `e23ab931-a033-edfe-ed4f-9d02474780b4`
  - `demo_hedgefundstyle@sigmasight.com` → Portfolio: `fcd71196-e93e-f000-5a74-31a9eead3118`
- **All passwords**: `demo12345`
- **63 positions** across 3 portfolios

> **Note**: Portfolio IDs are now deterministic and will be identical across all machines. See [SETUP_DETERMINISTIC_IDS.md](../SETUP_DETERMINISTIC_IDS.md) for details.

## Step 3.1: Validate Setup (Recommended)

```bash
# Run comprehensive validation
uv run python scripts/validate_setup.py
```

Expected output: `📊 Validation Summary: 8/8 checks passed`

---

## Step 4: Verify Portfolio IDs

```bash
# List portfolios (IDs will be deterministic)
uv run python scripts/list_portfolios.py
```

**Expected Output** (IDs must match exactly):
```
Portfolio: Individual Investor Portfolio
  ID: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
  Owner: demo_individual@sigmasight.com

Portfolio: High Net Worth Portfolio
  ID: e23ab931-a033-edfe-ed4f-9d02474780b4
  Owner: demo_hnw@sigmasight.com

Portfolio: Hedge Fund Style Portfolio
  ID: fcd71196-e93e-f000-5a74-31a9eead3118
  Owner: demo_hedgefundstyle@sigmasight.com
```

> **Important**: These IDs are deterministic and identical across all developer machines.

---

## Step 5: Seed Target Prices (Optional but Recommended)

Populate target prices for all portfolios to enable Target Price API testing:

```bash
# Preview what will be created (dry run)
uv run python scripts/data_operations/populate_target_prices_via_service.py \
  --csv-file data/target_prices_import.csv --dry-run

# Execute the import (creates 105 target price records)
uv run python scripts/data_operations/populate_target_prices_via_service.py \
  --csv-file data/target_prices_import.csv --execute
```

This creates:
- **105 target price records** (35 symbols × 3 portfolios)
- Target prices for EOY, next year, and downside scenarios
- Automatic calculation of expected returns
- Links to existing positions in portfolios

> **Note**: Target prices are required for testing Target Price APIs but optional for other functionality.

---

## Step 6: Run Batch Processing to Populate All Calculation Data

### Option A: Process All Portfolios (Recommended for First Run)

```bash
# Run batch processing for ALL portfolios
uv run python scripts/run_batch_calculations.py
```

> **⚠️ IMPORTANT**: Pre-API reports (.md, .json, .csv) are deprecated and planned for deletion.
> Use the API endpoints for accessing portfolio data instead.

This will:
1. Fetch latest market data (with improved historical coverage)
2. Calculate portfolio aggregations and exposures
3. ~~Calculate Greeks~~ (Disabled - no reliable options data)
4. Run factor analysis (7 factors)
5. Generate market risk scenarios
6. Run 15 stress test scenarios
7. Create portfolio snapshots
8. Calculate correlations (runs daily)

**Expected time**: ~30-60 seconds per portfolio

### Option B: Process Specific Portfolio

```bash
# Replace <PORTFOLIO_ID> with actual UUID from Step 4
uv run python scripts/run_batch_with_reports.py --portfolio <PORTFOLIO_ID>
```

### Option C: Skip Batch, Only Generate Reports (if batch already ran)

```bash
# Generate reports using existing calculation data
uv run python scripts/run_batch_with_reports.py --skip-batch
```

---

## Step 7: Access Data via API (Reports Deprecated)

> **Note**: File-based reports are deprecated. Use the API endpoints to access portfolio data.

Data is now accessed through the API. After batch processing completes, use the API endpoints documented in the [Daily Workflow Guide](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md).

---

## Step 8: Launch FastAPI Server for API Access

### Start the Development Server

```bash
# Option A: Using the run.py script (recommended)
uv run python run.py

# Option B: Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option C: Using uv run with uvicorn
uv run uvicorn app.main:app --reload
```

The server will start at: `http://localhost:8000`

**Expected output when server starts successfully**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Verify Server is Running

1. **Quick Health Check**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy"}
   ```

2. **Check API Version**:
   ```bash
   curl http://localhost:8000/api/v1/
   # Should return API version info
   ```

3. **Browser Check**:
   - Open http://localhost:8000/docs in your browser
   - You should see the Swagger UI interface

### Access Interactive API Documentation

1. **Swagger UI**: http://localhost:8000/docs
   - Interactive API testing interface
   - Try out endpoints directly in the browser
   - View request/response schemas

2. **ReDoc**: http://localhost:8000/redoc
   - Alternative API documentation format
   - Better for reading, less interactive

### Test API Authentication

```bash
# Login to get JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_individual@sigmasight.com", "password": "demo12345"}'

# Save the token from the response
# Example response: {"access_token": "eyJ...", "token_type": "bearer"}
```

### Test API Endpoints

For complete API endpoint documentation, see:
- [Daily Workflow Guide - API Endpoints](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md#common-api-endpoints)
- [API Specifications V1.4.5](_docs/requirements/API_SPECIFICATIONS_V1.4.5.md)

**Quick test with demo portfolio**:
```bash
# Get High Net Worth portfolio data
curl -X GET "http://localhost:8000/api/v1/data/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/complete" \
  -H "Authorization: Bearer <TOKEN>"
```

### Using Python to Test APIs

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "demo_individual@sigmasight.com", "password": "demo12345"}
)
token = response.json()["access_token"]

# Set headers
headers = {"Authorization": f"Bearer {token}"}

# Get portfolios
portfolios = requests.get(
    "http://localhost:8000/api/v1/data/portfolios",
    headers=headers
).json()

print(f"Found {len(portfolios['data'])} portfolios")
```

### Keep Server Running in Background

```bash
# Windows - Run in background
start /B uv run python run.py

# Mac/Linux - Run in background with nohup
nohup uv run python run.py &

# Or use screen/tmux for persistent sessions
screen -S sigmasight
uv run python run.py
# Press Ctrl+A then D to detach
# Reattach with: screen -r sigmasight
```

### Available API Endpoints

See the [Daily Workflow Guide](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md#common-api-endpoints) for the current list of working endpoints.

## Next Steps: Daily Operations

✅ **Initial setup is complete!**

For daily operations including:
- Starting services
- Running batch calculations
- Updating market data
- Testing the chat/agent system
- API endpoint reference

**See**: [BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md)

---

## API Server Management

### Check if Server is Running

```bash
# Windows
netstat -an | findstr :8000

# Mac/Linux  
lsof -i :8000
# or
netstat -an | grep 8000
```

### Stop the Server

- If running in foreground: Press `Ctrl+C`
- If running in background:
  ```bash
  # Find the process
  ps aux | grep "run.py\|uvicorn"
  # Kill it
  kill <PID>
  ```

### Common API Issues

**"Connection refused" error**:
- Make sure the server is running: `uv run python run.py`
- Check the port isn't blocked by firewall
- Try accessing via `127.0.0.1:8000` instead of `localhost:8000`

**"401 Unauthorized" error**:
- Token may have expired (default: 30 days)
- Re-login to get a new token
- Make sure you're including the Bearer prefix: `Authorization: Bearer <token>`

**"Database connection error"**:
- Ensure PostgreSQL is running: `docker ps`
- Check DATABASE_URL in `.env` file
- Restart Docker if needed: `docker-compose restart`

## Troubleshooting

### "No portfolios found"
- Run the seeding script: `uv run python scripts/seed_database.py`
- List portfolios to verify: `uv run python scripts/list_portfolios.py`

### "Market data fetch failed"
- Check your `.env` file has valid API keys:
  - `FMP_API_KEY` for market data
  - `POLYGON_API_KEY` as backup
  - `FRED_API_KEY` for interest rates

### "Greeks are all zero"
- This is expected - we don't have options chain data
- Greeks are approximated using simplified Black-Scholes

### "Stress test shows 99% loss"
- Known issue with correlation cascade
- See White Paper "Issues Observed With Our Stress Testing Approach"

### "ImportError" or module errors
- Make sure you're using `uv run` before python commands
- This ensures the virtual environment is active

---

## Understanding the Batch Process

The batch orchestrator runs calculation engines in sequence:

1. **Market Data Update** - Fetches latest prices with improved historical coverage
2. **Portfolio Aggregation** - Calculates exposures
3. ~~**Greeks Calculation**~~ - Disabled (no reliable options data)
4. **Factor Analysis** - 7-factor model betas
5. **Market Risk Scenarios** - ±5%, ±10%, ±20% scenarios
6. **Stress Testing** - 15 extreme scenarios
7. **Portfolio Snapshot** - Daily state capture
8. **Correlations** - Now runs daily (not optional)

Each engine saves results to the database for API access.

---

## Advanced Options

### Run Batch Processing Only
```bash
uv run python scripts/run_batch_calculations.py
```

### Run Specific Calculation Engine Tests
```bash
# Test Greeks calculation
uv run python tests/test_greeks_calculations.py

# Test factor analysis
uv run python tests/batch/test_factor_analysis.py

# Test market data integration
uv run python scripts/test_fmp_batch_integration.py
```

---

## Additional Resources

1. **Daily Operations** - [BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md)
2. **API Documentation** - http://localhost:8000/docs (when server is running)
3. **Deterministic IDs** - [SETUP_DETERMINISTIC_IDS.md](../SETUP_DETERMINISTIC_IDS.md)
4. **Chat Testing** - [Frontend Chat Testing Guide](../frontend/CHAT_TESTING_GUIDE.md)

---

## Questions?

- **Daily Operations**: [BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md](BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md)
- **Calculation Details**: [White Paper](_docs/generated/Calculation_Engine_White_Paper.md)
- **API Status**: [TODO3.md](TODO3.md)
- **Code Structure**: [AI_AGENT_REFERENCE.md](AI_AGENT_REFERENCE.md)
- **API Specs**: [API_SPECIFICATIONS_V1.4.5.md](_docs/requirements/API_SPECIFICATIONS_V1.4.5.md)

Remember: The first run takes longer as it fetches historical data. Subsequent runs are faster!