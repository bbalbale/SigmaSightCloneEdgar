# Move Local Database to Railway

## Overview
This guide documents how to push your local PostgreSQL database to Railway when running on **Windows PowerShell** without PostgreSQL client tools installed.

## Prerequisites
- Docker Desktop running with PostgreSQL container
- Railway database credentials
- Local database running in Docker

## Problem Statement
On Windows systems without `psql` or `pg_dump` installed, we can't use standard PostgreSQL client commands directly. However, we can use the Docker PostgreSQL container to execute these commands.

## Solution: Using Docker Container

### Step 1: Identify Your Docker Container Name

```powershell
docker ps --filter "ancestor=postgres:15" --format "{{.Names}}"
```

Expected output: `backend-postgres-1`

### Step 2: Gather Database Credentials

**Local Database** (from `docker-compose.yml`):
- Host: `localhost`
- Port: `5432`
- User: `sigmasight`
- Password: `sigmasight_dev`
- Database: `sigmasight_db`

**Railway Database** (from Railway dashboard):
- Host: `hopper.proxy.rlwy.net`
- Port: `56725`
- User: `postgres`
- Password: `[your-railway-password]`
- Database: `railway`

### Step 3: Create Database Dump (Using INSERT Format)

```powershell
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --clean --if-exists --inserts --encoding=UTF8 > local_dump_inserts.sql
```

**What this does:**
- `docker exec`: Runs command inside the container
- `-e PGPASSWORD=...`: Sets password environment variable
- `pg_dump`: PostgreSQL backup utility
- `--clean --if-exists`: Drops existing objects before recreating
- `--inserts`: Use INSERT statements instead of COPY (better for character encoding)
- `--encoding=UTF8`: Explicitly set UTF-8 encoding
- `> local_dump_inserts.sql`: Saves output to file

**Why INSERT format?** The default COPY format can have issues with multi-byte UTF-8 characters at VARCHAR boundaries. INSERT format handles character encoding more reliably.

### Step 4: Restore to Railway

```powershell
powershell -Command "Get-Content local_dump_inserts.sql | docker exec -i -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway"
```

**What this does:**
- `Get-Content local_dump_inserts.sql`: Reads the dump file (PowerShell command)
- `|`: Pipes content to next command
- `docker exec -i`: Interactive mode to receive stdin
- `psql`: PostgreSQL client to restore data
- Railway connection parameters

**Note:** Using `Get-Content` (PowerShell) is more reliable than `cat` on Windows systems.

### Step 5: Verify Data Push

**Count portfolios:**
```powershell
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) as portfolios FROM portfolios;"
```

**Count positions:**
```powershell
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) as positions FROM positions;"
```

**List users:**
```powershell
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT email FROM users;"
```

**Count company profiles:**
```powershell
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) as company_profiles FROM company_profiles;"
```

## Expected Output

### During Restore
You'll see output like:
```
SET
SET
...
DROP TABLE
DROP TABLE
...
CREATE TABLE
CREATE TABLE
...
INSERT 0 1
INSERT 0 1
INSERT 0 1
...
CREATE INDEX
...
ERROR:  role "sigmasight" does not exist  # These errors are HARMLESS
ERROR:  role "sigmasight" does not exist  # Railway uses "postgres" user
...
```

**Note:** `INSERT 0 1` means each row was successfully inserted. You'll see hundreds of these messages.

### Verification Results (Example)
```
✅ Portfolios: 3
✅ Positions: 76
✅ Users: 3
✅ Company Profiles: 61
✅ Portfolio Snapshots: 4
```

## Common Issues & Solutions

### Issue 1: Role "sigmasight" Does Not Exist
**Error:**
```
ERROR:  role "sigmasight" does not exist
```

**Solution:** This is expected and harmless. The dump file includes ownership commands for the "sigmasight" user from your local database, but Railway uses the "postgres" user. The data is still copied successfully.

### Issue 2: Container Name Not Found
**Error:**
```
Error: No such container: backend-postgres-1
```

**Solution:** Find the actual container name:
```powershell
docker ps
```
Replace `backend-postgres-1` with your actual container name.

### Issue 3: Connection Timeout
**Error:**
```
could not connect to server: Connection timed out
```

**Solution:**
- Check Railway database is running
- Verify host/port are correct
- Check your network/firewall settings

### Issue 4: Company Profiles VARCHAR Character Encoding
**Error:**
```
ERROR:  value too long for type character varying(1000)
```

**Root Cause:** PostgreSQL `VARCHAR(N)` enforces byte limit, not character limit. Multi-byte UTF-8 characters (like é, ñ, etc.) can cause a 1000-character string to exceed 1000 bytes.

**Solution:** Use `--inserts` flag (recommended in Step 3). This handles most encoding issues automatically. If you still get this error for specific records (e.g., Home Depot):

**Manual Fix:**
```powershell
# Insert the missing record with truncated description
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "INSERT INTO company_profiles (symbol, company_name, sector, industry, exchange, country, market_cap, description, is_etf, is_fund, employees, website, pe_ratio, forward_pe, dividend_yield, beta, week_52_high, week_52_low, target_mean_price, target_high_price, target_low_price, number_of_analyst_opinions, recommendation_mean, recommendation_key, forward_eps, earnings_growth, revenue_growth, earnings_quarterly_growth, profit_margins, operating_margins, gross_margins, return_on_assets, return_on_equity, total_revenue, current_year_revenue_avg, current_year_revenue_low, current_year_revenue_high, current_year_revenue_growth, current_year_earnings_avg, current_year_earnings_low, current_year_earnings_high, current_year_end_date, next_year_revenue_avg, next_year_revenue_low, next_year_revenue_high, next_year_revenue_growth, next_year_earnings_avg, next_year_earnings_low, next_year_earnings_high, next_year_end_date, data_source, last_updated, created_at, updated_at) SELECT symbol, company_name, sector, industry, exchange, country, market_cap, LEFT(description, 995), is_etf, is_fund, employees, website, pe_ratio, forward_pe, dividend_yield, beta, week_52_high, week_52_low, target_mean_price, target_high_price, target_low_price, number_of_analyst_opinions, recommendation_mean, recommendation_key, forward_eps, earnings_growth, revenue_growth, earnings_quarterly_growth, profit_margins, operating_margins, gross_margins, return_on_assets, return_on_equity, total_revenue, current_year_revenue_avg, current_year_revenue_low, current_year_revenue_high, current_year_revenue_growth, current_year_earnings_avg, current_year_earnings_low, current_year_earnings_high, current_year_end_date, next_year_revenue_avg, next_year_revenue_low, next_year_revenue_high, next_year_revenue_growth, next_year_earnings_avg, next_year_earnings_low, next_year_earnings_high, next_year_end_date, data_source, last_updated, created_at, updated_at FROM company_profiles_local WHERE symbol = 'HD';"
```

Or simply accept that 60/61 profiles loaded and the backend will re-fetch the missing one from market data APIs on next update.

## Complete Verification Script

Save this as `verify_railway_db.ps1`:

```powershell
# Railway credentials
$RAILWAY_HOST = "hopper.proxy.rlwy.net"
$RAILWAY_PORT = "56725"
$RAILWAY_USER = "postgres"
$RAILWAY_PASSWORD = "[your-password]"
$RAILWAY_DB = "railway"
$CONTAINER = "backend-postgres-1"

Write-Host "🔍 Verifying Railway Database..." -ForegroundColor Cyan
Write-Host ""

# Portfolios
$result = docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM portfolios;"
Write-Host "📊 Portfolios: $($result.Trim())" -ForegroundColor Green

# Positions
$result = docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM positions;"
Write-Host "📈 Positions: $($result.Trim())" -ForegroundColor Green

# Users
$result = docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM users;"
Write-Host "👥 Users: $($result.Trim())" -ForegroundColor Green

# Company Profiles
$result = docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM company_profiles;"
Write-Host "🏢 Company Profiles: $($result.Trim())" -ForegroundColor Green

Write-Host ""
Write-Host "✅ Verification complete!" -ForegroundColor Green
```

## Key Learnings

1. **Docker as PostgreSQL Client**: When PostgreSQL client tools aren't installed on Windows, use the Docker container that's already running PostgreSQL.

2. **Password Handling**: Use `-e PGPASSWORD=...` to pass passwords securely to Docker container commands.

3. **Pipeline with Docker**: Use `Get-Content file | docker exec -i ...` (PowerShell) to pipe SQL files into the container for restoration.

4. **Railway User Differences**: Railway uses `postgres` user, local uses `sigmasight`. Ownership errors are harmless.

5. **Windows PowerShell**: Commands work in PowerShell but may need adjustment for CMD (use `type` instead of `Get-Content`).

6. **INSERT vs COPY Format**: Use `--inserts` flag for better character encoding handling. COPY format can fail on multi-byte UTF-8 characters at VARCHAR boundaries.

7. **Character vs Byte Limits**: PostgreSQL `VARCHAR(N)` enforces byte limit, not character limit. Multi-byte characters count as multiple bytes.

## Backup Strategy

Always keep a local dump before pushing:
```powershell
# Create timestamped backup (INSERT format recommended)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --clean --if-exists --inserts --encoding=UTF8 > "backup_$timestamp.sql"
```

## Related Documentation

- Railway Database Setup: `scripts/railway/README.md`
- Railway Audit Scripts: `scripts/railway/audit_railway_*.py`
- Database Seeding: `scripts/reset_and_seed.py`

## Quick Reference Commands

```powershell
# Full push process (INSERT format - recommended, update passwords)
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --clean --if-exists --inserts --encoding=UTF8 > local_dump_inserts.sql

powershell -Command "Get-Content local_dump_inserts.sql | docker exec -i -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway"

docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) FROM portfolios;"

# Verify company profiles loaded
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) FROM company_profiles;"
```

---

**Last Updated:** 2025-10-23
**Tested On:** Windows 11, PowerShell 7, Docker Desktop, PostgreSQL 15
**Known Issues Fixed:** Company profiles VARCHAR encoding (use --inserts flag)
