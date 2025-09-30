# Setup Guide: Deterministic Portfolio IDs

**CRITICAL: Windows Machine Portfolio ID Sync**

Your development partner's Windows machine needs to be synced with the new deterministic portfolio IDs to eliminate "404 portfolio not found" errors.

## 🚨 Problem Summary

- Portfolio IDs were previously random UUIDs (different on every machine)
- Frontend hardcodes specific portfolio IDs that only worked on one developer's machine
- Windows machine has different portfolio IDs → 404 errors when accessing portfolios

## ✅ Solution: Deterministic UUIDs

The backend now generates **identical portfolio IDs on every machine** using deterministic UUID generation.

## 📋 Setup Instructions for Windows Machine

### Step 1: Verify Prerequisites

```bash
# Ensure backend directory exists and dependencies installed
cd backend
uv --version  # Should show uv version
docker-compose ps  # PostgreSQL should be running
```

### Step 2: Reset Database with Deterministic IDs

```bash
# Navigate to backend directory
cd backend

# Reset database and seed with deterministic UUIDs
uv run python scripts/reset_and_seed.py reset --confirm

# Verify successful seeding (should show 3 portfolios, 63 positions)
```

Expected output should show:
```
✅ Created 3 demo portfolios with 63 total positions
🎯 Demo portfolios ready for batch processing framework!
```

### Step 3: Verify Portfolio IDs Match

Run this verification command:

```bash
uv run python -c "
import asyncio
from app.database import get_async_session
from sqlalchemy import select
from app.models.users import User, Portfolio

async def verify_ids():
    async with get_async_session() as db:
        result = await db.execute(select(User.email, Portfolio.id).join(Portfolio))
        rows = result.all()
        print('Portfolio IDs in your database:')
        for email, portfolio_id in rows:
            if 'demo_' in email:
                print(f'  {email}: {portfolio_id}')

asyncio.run(verify_ids())
"
```

**Expected Output (must match exactly):**
```
Portfolio IDs in your database:
  demo_individual@sigmasight.com: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
  demo_hnw@sigmasight.com: e23ab931-a033-edfe-ed4f-9d02474780b4
  demo_hedgefundstyle@sigmasight.com: fcd71196-e93e-f000-5a74-31a9eead3118
```

### Step 4: Test Portfolio Access

Test that all demo accounts work:

```bash
# Start the backend server
uv run python run.py
```

In another terminal, test login and portfolio access:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_hnw@sigmasight.com", "password": "demo12345"}'

# Should return JWT token - copy the access_token value
# Then test portfolio access (replace TOKEN with actual token):

curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/data/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/complete

# Should return portfolio data, not 404
```

### Step 5: Test Frontend

```bash
# In frontend directory
cd ../frontend
npm run dev

# Open http://localhost:3005
# Login with: demo_hnw@sigmasight.com / demo12345
# Portfolio page should load without 404 errors
```

## 🎯 What Changed

### Backend Changes
- `backend/app/db/seed_demo_portfolios.py` now uses MD5-based deterministic UUID generation
- All Users, Portfolios, Positions, and Tags get consistent IDs across machines
- Database seeding is now reproducible and deterministic

### Frontend Changes  
- `frontend/src/services/portfolioResolver.ts` updated with new deterministic portfolio IDs
- Test scripts updated with consistent IDs

## 🔍 Troubleshooting

### Portfolio IDs Don't Match
If your portfolio IDs don't match the expected ones:

1. **Clear all data completely:**
   ```bash
   # Stop backend server first
   docker-compose down
   docker-compose up -d  # Fresh PostgreSQL container
   uv run alembic upgrade head  # Recreate schema
   uv run python scripts/reset_and_seed.py reset --confirm
   ```

2. **Verify git sync:**
   ```bash
   git status  # Should show you're on the correct branch
   git pull origin frontendtest  # Get latest deterministic UUID code
   ```

### Frontend Still Shows 404
If frontend still shows portfolio 404 errors:

1. **Clear browser cache/localStorage**
2. **Verify frontend is updated:**
   ```bash
   cd frontend
   git status  # Should show portfolioResolver.ts is updated
   npm run dev  # Fresh frontend build
   ```

### Backend Seed Fails
If database seeding fails:

1. **Check PostgreSQL is running:**
   ```bash
   docker-compose ps  # PostgreSQL should be "Up"
   ```

2. **Reset completely:**
   ```bash
   docker-compose down
   docker volume prune -f  # Remove all Docker volumes
   docker-compose up -d
   uv run alembic upgrade head
   uv run python scripts/reset_and_seed.py reset --confirm
   ```

## ✅ Success Criteria

After completing these steps, your Windows machine should have:

- ✅ Identical portfolio IDs to all other developer machines
- ✅ All 3 demo accounts can login and access portfolios  
- ✅ Frontend loads portfolio pages without 404 errors
- ✅ No more "works on my machine" portfolio ID issues

## 🔄 Team Coordination

**All developers** should run the same reset command to ensure consistency:

```bash
cd backend
uv run python scripts/reset_and_seed.py reset --confirm
```

This ensures everyone has identical demo data with the same deterministic portfolio IDs.

## 📞 Support

If you encounter issues:

1. **Verify the exact portfolio IDs match** the expected values above
2. **Check that both backend and frontend have been updated** with the latest deterministic UUID code  
3. **Ensure PostgreSQL container is fresh** (not carrying old random UUID data)

The key is that **every developer machine must generate the exact same portfolio IDs**. If they don't match, the deterministic seeding didn't work correctly.