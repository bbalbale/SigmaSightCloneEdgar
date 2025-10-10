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

### Step 3: Create Database Dump

```powershell
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --clean --if-exists > local_dump.sql
```

**What this does:**
- `docker exec`: Runs command inside the container
- `-e PGPASSWORD=...`: Sets password environment variable
- `pg_dump`: PostgreSQL backup utility
- `--clean --if-exists`: Drops existing objects before recreating
- `> local_dump.sql`: Saves output to file

### Step 4: Restore to Railway

```powershell
cat local_dump.sql | docker exec -i -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway
```

**What this does:**
- `cat local_dump.sql`: Reads the dump file
- `|`: Pipes content to next command
- `docker exec -i`: Interactive mode to receive stdin
- `psql`: PostgreSQL client to restore data
- Railway connection parameters

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
COPY 335
COPY 140
...
CREATE INDEX
...
ERROR:  role "sigmasight" does not exist  # These errors are HARMLESS
ERROR:  role "sigmasight" does not exist  # Railway uses "postgres" user
...
```

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

3. **Pipeline with Docker**: Use `cat file | docker exec -i ...` to pipe SQL files into the container for restoration.

4. **Railway User Differences**: Railway uses `postgres` user, local uses `sigmasight`. Ownership errors are harmless.

5. **Windows PowerShell**: Commands work in PowerShell but may need adjustment for CMD (use `type` instead of `cat`).

## Backup Strategy

Always keep a local dump before pushing:
```powershell
# Create timestamped backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --clean --if-exists > "backup_$timestamp.sql"
```

## Related Documentation

- Railway Database Setup: `scripts/railway/README.md`
- Railway Audit Scripts: `scripts/railway/audit_railway_*.py`
- Database Seeding: `scripts/reset_and_seed.py`

## Quick Reference Commands

```powershell
# Full push process (update passwords)
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --clean --if-exists > local_dump.sql

cat local_dump.sql | docker exec -i -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway

docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) FROM portfolios;"
```

---

**Last Updated:** 2025-10-09
**Tested On:** Windows 11, PowerShell 7, Docker Desktop, PostgreSQL 15
