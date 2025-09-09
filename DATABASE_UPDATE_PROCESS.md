# Database Update Process - September 8, 2025

## Overview
This document details the complete database update process performed to bring the SigmaSight database to its current state with demo data and proper migrations.

## Steps Performed

### 1. Database Container Verification
**Command:** `docker ps`
- Verified PostgreSQL container `backend-postgres-1` was running
- Status: Up 2 hours (healthy)
- Port: 5432

### 2. Alembic Migration Management

#### 2.1 Check Current Migration Status
**Command:** `cd backend && uv run python -m alembic current`
- Initial status: `129ae82e72ca (head)`

#### 2.2 Generate New Migration
**Command:** `cd backend && uv run python -m alembic revision --autogenerate -m "Add analytics and storage updates"`
- Created migration: `4e4d181af13d_add_analytics_and_storage_updates.py`
- No schema changes detected (empty migration)
- Purpose: Update migration history after frontendtest branch merge

#### 2.3 Apply Migration
**Command:** `cd backend && uv run python -m alembic upgrade head`
- Successfully upgraded from `129ae82e72ca` to `4e4d181af13d`
- New head: `4e4d181af13d`

### 3. Demo Data Seedinghhave

#### 3.1 Seed Database with Demo Data
**Command:** `cd backend && PYTHONIOENCODING=utf-8 uv run python scripts/seed_database.py`

Created the following demo structure:
- **3 Demo Users** (all passwords: `demo12345`):
  - `demo_individual@sigmasight.com`
  - `demo_hnw@sigmasight.com`
  - `demo_hedgefundstyle@sigmasight.com`

- **3 Demo Portfolios** with deterministic IDs:
  - Individual Investor: `1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe` (16 positions)
  - High Net Worth: `e23ab931-a033-edfe-ed4f-9d02474780b4` (17 positions)
  - Hedge Fund Style: `fcd71196-e93e-f000-5a74-31a9eead3118` (30 positions)

- **63 Total Positions** across all portfolios
- **8 Factor Definitions** (Market Beta, Momentum, Value, Growth, Quality, Size, Low Volatility, Short Interest)

### 4. Setup Validation
**Command:** `cd backend && PYTHONIOENCODING=utf-8 uv run python scripts/validate_setup.py`

Validation Results (8/8 checks passed):
- ✅ Python 3.11.13
- ✅ uv 0.8.9
- ✅ Docker running
- ✅ PostgreSQL container healthy
- ✅ .env file configured
- ✅ Virtual environment with dependencies
- ✅ API server responding (http://localhost:8000)
- ✅ 3 demo users found

### 5. Batch Calculations (Partial)
**Command:** `cd backend && PYTHONIOENCODING=utf-8 uv run python scripts/run_batch_with_reports.py --portfolio 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe`

Started batch processing for market data:
- Fetched 5 days of market data for most symbols
- Hit API rate limits (429 errors) from Polygon API
- Data partially populated but calculations continuing in background

## Key Features Implemented

### Deterministic Portfolio IDs
The seeding process uses deterministic UUID generation to ensure consistent portfolio IDs across all developer machines:

```python
def generate_deterministic_uuid(seed_string: str) -> UUID:
    hash_hex = hashlib.md5(seed_string.encode()).hexdigest()
    return UUID(hash_hex)

# Portfolio IDs are generated from email addresses
portfolio_id = generate_deterministic_uuid(f"{user.email}_portfolio")
```

This ensures all developers get the same portfolio IDs:
- Individual: `1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe`
- HNW: `e23ab931-a033-edfe-ed4f-9d02474780b4`
- Hedge Fund: `fcd71196-e93e-f000-5a74-31a9eead3118`

### Database Schema State
Current migration head: `4e4d181af13d`

Tables created and populated:
- users
- portfolios
- positions
- position_tags
- tags
- factor_definitions
- market_data_cache
- alembic_version

## Common Commands for Future Use

### Check Portfolio IDs
```bash
cd backend && uv run python scripts/list_portfolios.py
```

### Run Batch Calculations for All Portfolios
```bash
cd backend && uv run python scripts/run_batch_calculations.py
```

### Run Batch for Specific Portfolio
```bash
cd backend && uv run python scripts/run_batch_with_reports.py --portfolio <PORTFOLIO_ID>
```

### Reset and Reseed (DESTRUCTIVE)
```bash
cd backend && uv run python scripts/reset_and_seed.py reset --confirm
```

### Validate Setup
```bash
cd backend && uv run python scripts/validate_setup.py
```

## Services Running
- **PostgreSQL Database**: Port 5432 (Docker container)
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3006

## Git Status
- Branch: APIIntegration
- Latest commit: `4abd8e76` - "Add database migration for analytics updates"
- Merged from: origin/frontendtest

## Notes
- Windows environment requires `PYTHONIOENCODING=utf-8` for proper Unicode handling
- API rate limits may affect batch calculation completion time
- All demo accounts use password: `demo12345`
- Portfolio IDs are deterministic for development consistency

## Next Steps
1. Allow batch calculations to complete (may take time due to rate limits)
2. Access API documentation at http://localhost:8000/docs
3. Login with demo credentials to test functionality
4. Frontend is ready for portfolio data display at http://localhost:3006