# Quick Start Guide - Windows

## One-Time Setup (Already Done if Following Windows Guide)

```powershell
# 1. Clone repository
git clone https://github.com/elliottng/SigmaSight-BE.git
cd SigmaSight-BE\backend

# 2. Install dependencies
uv sync

# 3. Copy environment config
copy .env.example .env

# 4. Start database
docker-compose up -d

# 5. Setup database schema
uv run alembic upgrade head

# 6. Seed demo data
uv run python scripts/seed_database.py
```

## Daily Workflow - The Essential Commands

```powershell
# Navigate to project
cd C:\Projects\SigmaSight-BE\backend

# Start database (if not running)
docker-compose up -d

# Run everything (batch + reports)
uv run python scripts/run_batch_with_reports.py

# Open reports folder
explorer reports
```

## Find Portfolio IDs (You'll Need These!)

```powershell
# Quick way to list all portfolio IDs
uv run python -c "import asyncio; from app.database import get_async_session; from sqlalchemy import select; from app.models.users import Portfolio; asyncio.run(lambda: asyncio.create_task(list_portfolios()))()" 

# Or use this cleaner script
uv run python scripts/list_portfolios.py
```

## Common Tasks

### Generate Report for Specific Portfolio
```powershell
# Replace PORTFOLIO_ID with actual UUID
uv run python -m app.cli.report_generator_cli generate --portfolio-id PORTFOLIO_ID
```

### Run Batch for Specific Portfolio
```powershell
uv run python scripts/run_batch_with_reports.py --portfolio PORTFOLIO_ID
```

### Generate Reports Only (Skip Batch)
```powershell
uv run python scripts/run_batch_with_reports.py --skip-batch
```

### Run Batch Only (Skip Reports)
```powershell
uv run python scripts/run_batch_with_reports.py --skip-reports
```

### Update Code from GitHub
```powershell
git pull
uv sync  # Update dependencies if needed
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "docker not recognized" | Start Docker Desktop |
| "No portfolios found" | Run: `uv run python scripts/seed_database.py` |
| "Module not found" | Use `uv run` before python commands |
| "Port 5432 in use" | Another PostgreSQL is running, stop it |
| "Greeks all zero" | Expected - no options data available |

## File Locations

- **Reports**: `reports/` folder
- **Logs**: `logs/` folder  
- **Config**: `.env` file
- **Database**: Docker container (persistent)

## API Keys (in .env file)

- `FMP_API_KEY` - Primary market data (required)
- `POLYGON_API_KEY` - Backup market data (optional)
- `FRED_API_KEY` - Interest rates (optional)

## Demo Accounts

| Email | Password | Description |
|-------|----------|-------------|
| demo_individual@sigmasight.com | demo12345 | Retail investor |
| demo_hnw@sigmasight.com | demo12345 | High net worth |
| demo_hedgefundstyle@sigmasight.com | demo12345 | Hedge fund style |

## Report Formats

- `.md` - Markdown (human-readable, view in VS Code)
- `.json` - JSON (for programming/integration)
- `.csv` - CSV (open in Excel)

## Need Help?

1. Check `COMPLETE_WORKFLOW_GUIDE.md` for detailed instructions
2. Review `logs/sigmasight.log` for error details
3. See `TODO2.md` for known issues

---
*Last Updated: 2025-08-10*