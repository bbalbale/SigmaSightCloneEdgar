# Complete Workflow Guide - From Setup to Reports & API Server

> **Last Updated**: 2025-08-26
> **Phase**: 3.0 - API Development (30% complete)
> **API Status**: Raw Data APIs 100% operational

This guide walks through the **complete workflow** from initial setup to generating portfolio reports and running the FastAPI server for API access.

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

```bash
# Use the bulletproof demo setup (avoids async/sync issues)
uv run python scripts/setup_minimal_demo.py
```

This creates:
- **3 Demo Accounts**:
  - `demo_individual@sigmasight.com` (password: demo12345)
  - `demo_hnw@sigmasight.com` (password: demo12345)
  - `demo_hedgefundstyle@sigmasight.com` (password: demo12345)
- **3 Demo Portfolios** ready for calculations and reports

## Step 3.1: Validate Setup (Recommended)

```bash
# Run comprehensive validation
uv run python scripts/validate_setup.py
```

Expected output: `📊 Validation Summary: 8/8 checks passed`

---

## Step 4: Find Your Portfolio IDs

```bash
# List all portfolios with their IDs
uv run python scripts/list_portfolios.py

# Or use the verbose mode for more details
uv run python scripts/list_portfolios.py --verbose
```

**Save these IDs!** You'll need them for batch processing and reports.

Example output:
```
Portfolio: Individual Investor Portfolio
  ID: 123e4567-e89b-12d3-a456-426614174000
  Owner: demo_individual@sigmasight.com

Portfolio: High Net Worth Portfolio
  ID: 223e4567-e89b-12d3-a456-426614174001
  Owner: demo_hnw@sigmasight.com

Portfolio: Hedge Fund Style Portfolio
  ID: 323e4567-e89b-12d3-a456-426614174002
  Owner: demo_hedgefundstyle@sigmasight.com
```

---

## Step 5: Run Batch Processing to Populate All Calculation Data

### Option A: Process All Portfolios (Recommended for First Run)

```bash
# Run batch processing for ALL portfolios and generate reports
uv run python scripts/run_batch_with_reports.py

# Or run with correlations (slower but more complete)
uv run python scripts/run_batch_with_reports.py --correlations
```

This will:
1. Fetch latest market data
2. Calculate portfolio aggregations and exposures
3. Calculate Greeks for options positions
4. Run factor analysis (7 factors)
5. Generate market risk scenarios
6. Run 15 stress test scenarios
7. Create portfolio snapshots
8. Calculate correlations (if --correlations flag used)
9. Generate reports in all formats

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

## Step 6: View Generated Reports

The script generates reports in the `backend/reports/` directory. The folder is named using a slugified version of the **portfolio's name** and the report date.

For example, a report for the "Demo Hedge Fund-Style Investor" portfolio on August 8, 2025, will be in: `reports/demo-hedge-fund-style-investor-portfolio_2025-08-08/`

Inside this date-stamped directory, you'll find the report in three standard formats:

```bash
# Windows - Open reports folder
explorer reports

# Mac - Open reports folder  
open reports

# Or list reports from command line
dir reports     # Windows
ls -la reports  # Mac/Linux
```

**Report Structure**:
```
reports/
├── portfolio_<ID>_<DATE>.md     # Markdown format (human-readable)
├── portfolio_<ID>_<DATE>.json   # JSON format (machine-readable)
└── portfolio_<ID>_<DATE>.csv    # CSV format (Excel-compatible)
```

### View Markdown Report

The `.md` files are best viewed in:
- **VS Code** - Has built-in Markdown preview (Ctrl+Shift+V)
- **GitHub** - Upload to a gist for formatted viewing
- **Markdown Viewer** - Any online Markdown viewer
- **Notepad++** - With Markdown plugin

### Open CSV in Excel

1. Double-click the `.csv` file
2. Excel should open automatically
3. Contains all positions with calculations

### Parse JSON Programmatically

The `.json` files contain complete structured data for integration.

---

## Step 7: Generate Reports for Different Dates

```bash
# Generate report for specific date
uv run python -m app.cli.report_generator_cli generate \
    --portfolio-id <PORTFOLIO_ID> \
    --as-of 2025-08-15 \
    --format md,json,csv

# Generate only Markdown
uv run python -m app.cli.report_generator_cli generate \
    --portfolio-id <PORTFOLIO_ID> \
    --format md

# Save to custom directory
uv run python -m app.cli.report_generator_cli generate \
    --portfolio-id <PORTFOLIO_ID> \
    --output-dir C:\Users\Ben\Documents\Reports
```

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

### Test Raw Data APIs (100% Complete)

```bash
# Replace <TOKEN> with the access_token from login

# Get portfolios
curl -X GET "http://localhost:8000/api/v1/data/portfolios" \
  -H "Authorization: Bearer <TOKEN>"

# Get positions for a portfolio
curl -X GET "http://localhost:8000/api/v1/data/portfolios/<PORTFOLIO_ID>/positions" \
  -H "Authorization: Bearer <TOKEN>"

# Get risk metrics
curl -X GET "http://localhost:8000/api/v1/data/portfolios/<PORTFOLIO_ID>/risk_metrics" \
  -H "Authorization: Bearer <TOKEN>"

# Get factor exposures
curl -X GET "http://localhost:8000/api/v1/data/portfolios/<PORTFOLIO_ID>/factor_exposures" \
  -H "Authorization: Bearer <TOKEN>"

# Get market quotes
curl -X GET "http://localhost:8000/api/v1/data/prices/quotes?symbols=AAPL,MSFT,GOOGL" \
  -H "Authorization: Bearer <TOKEN>"

# Get portfolio exposures
curl -X GET "http://localhost:8000/api/v1/data/portfolios/<PORTFOLIO_ID>/exposures" \
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

### Available API Endpoints Overview

**🟢 Raw Data APIs (100% Complete)**:
- `/api/v1/data/portfolios` - Get all portfolios
- `/api/v1/data/portfolios/{id}/positions` - Get portfolio positions
- `/api/v1/data/portfolios/{id}/risk_metrics` - Get risk metrics
- `/api/v1/data/portfolios/{id}/factor_exposures` - Get factor exposures
- `/api/v1/data/portfolios/{id}/exposures` - Get portfolio exposures
- `/api/v1/data/prices/quotes` - Get market quotes

**🟡 Authentication APIs**:
- `/api/v1/auth/login` - Login and get JWT token
- `/api/v1/auth/register` - Register new user
- `/api/v1/auth/me` - Get current user info

**🔴 Other APIs (In Development)**:
- Analytics APIs - Calculations and derived metrics
- Management APIs - Portfolio CRUD operations
- Export APIs - Report generation and downloads

See [API Specifications V1.4.4](_docs/requirements/API_SPECIFICATIONS_V1.4.4.md) for complete endpoint documentation.

## Step 9: Daily Workflow

Once everything is set up, your daily workflow is:

```bash
# 1. Start Docker (if not running)
# 2. Navigate to project
cd C:\Projects\SigmaSight-BE\backend

# 3. Start database
docker-compose up -d

# 4. Start API server
uv run python run.py

# 5. Run batch and generate reports (in another terminal)
uv run python scripts/run_batch_with_reports.py

# 6. View reports
explorer reports  # Windows

# 7. Access API at http://localhost:8000/docs
```

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

The batch orchestrator runs 8 calculation engines in sequence:

1. **Market Data Update** - Fetches latest prices
2. **Portfolio Aggregation** - Calculates exposures
3. **Greeks Calculation** - Options sensitivities
4. **Factor Analysis** - 7-factor model betas
5. **Market Risk Scenarios** - ±5%, ±10%, ±20% scenarios
6. **Stress Testing** - 15 extreme scenarios
7. **Portfolio Snapshot** - Daily state capture
8. **Correlations** (optional) - Position relationships
9. **Report Generation** - Creates MD/JSON/CSV files

Each engine saves results to the database, making data available for reports.

---

## Advanced Options

### Run Batch Without Reports
```bash
uv run python scripts/run_batch_with_reports.py --skip-reports
```

### Generate Reports Without Batch
```bash
uv run python scripts/run_batch_with_reports.py --skip-batch
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

## Next Steps

1. **Explore API Endpoints** - Use http://localhost:8000/docs to test all endpoints
2. **Review Generated Reports** - Check all sections are populated
3. **Verify Calculations** - Ensure numbers make sense via API responses
4. **Test Different Portfolios** - Run for all 3 demo portfolios
5. **Integrate with Frontend** - Use Raw Data APIs for UI development
6. **Customize Reports** - Modify templates in `app/reports/templates/`
7. **Schedule Daily Runs** - Set up Windows Task Scheduler or cron
8. **Monitor API Performance** - Check response times in `/docs`

---

## Questions?

- Check the [White Paper](_docs/generated/Calculation_Engine_White_Paper.md) for calculation details
- Review [TODO3.md](TODO3.md) for current API development status
- See [AI_AGENT_REFERENCE.md](AI_AGENT_REFERENCE.md) for code structure
- View [API Specifications](/_docs/requirements/API_SPECIFICATIONS_V1.4.4.md) for endpoint details

Remember: The first run takes longer as it fetches historical data. Subsequent runs are faster!