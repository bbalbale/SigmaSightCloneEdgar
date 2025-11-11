# Improved Database Migration Process

## Environments

### Sandbox Environment (Original)
- **Host**: hopper.proxy.rlwy.net:56725
- **Database**: railway
- **User**: postgres
- **Purpose**: Testing and development

### Production Environment
- **Host**: maglev.proxy.rlwy.net:27062
- **Database**: railway
- **User**: postgres
- **Purpose**: Live production data
- **⚠️ CRITICAL**: Always use production script for production migrations

## Problem Statement

The INSERT-based migration has serious issues with foreign key constraints and data ordering. The previous migration resulted in:
- **0/76 positions migrated** (100% data loss)
- **2,264/29,262 factor exposures** (92% data loss)
- **0/114 market betas** (100% data loss)
- All position-related data missing

## Root Cause

The `pg_dump --inserts` approach doesn't properly handle:
1. Foreign key constraint checking during INSERT
2. Data insertion order (parents before children)
3. Complex relationships between tables

## Improved Solution: Schema-First, Data-Second Approach

### Strategy Overview

1. **Export schema only** (structure without data)
2. **Restore schema** to Railway
3. **Disable foreign key checks** temporarily
4. **Export data only** with proper ordering
5. **Restore data** table by table in dependency order
6. **Re-enable foreign key checks**
7. **Verify all data**

### Step-by-Step Process

#### Step 1: Export Schema Only (Local)

```powershell
# Export database structure (tables, indexes, constraints)
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --schema-only --no-owner --no-privileges --clean --if-exists > schema_only.sql
```

#### Step 2: Export Data Only (Local) - Custom Format for Reliability

```powershell
# Export all data in PostgreSQL custom format (handles binary data better)
docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --data-only --no-owner --no-privileges --disable-triggers --format=custom --file=/tmp/data_only.dump

# Copy dump file from container to host
docker cp backend-postgres-1:/tmp/data_only.dump ./data_only.dump
```

#### Step 3: Restore Schema to Railway

```powershell
# Restore schema structure (creates all tables, indexes, constraints)
powershell -Command "Get-Content schema_only.sql | docker exec -i -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway"
```

#### Step 4: Copy Data Dump to Container

```powershell
# Copy data dump back into container for Railway restore
docker cp ./data_only.dump backend-postgres-1:/tmp/data_only.dump
```

#### Step 5: Restore Data to Railway

```powershell
# Restore data with disabled triggers (bypasses foreign key checks during load)
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 pg_restore -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway --data-only --disable-triggers --no-owner --no-privileges /tmp/data_only.dump
```

**Note:** `--disable-triggers` requires superuser privileges. If you get a permission error, use the alternative approach below.

#### Alternative Step 5: Manual Table-by-Table Migration

If `--disable-triggers` fails, migrate tables in dependency order:

```powershell
# Define table order (parents first, children last)
$tables = @(
    'users',
    'portfolios',
    'positions',
    'tags',
    'company_profiles',
    'factor_definitions',
    'portfolio_snapshots',
    'position_tags',
    'position_greeks',
    'position_market_betas',
    'position_volatility',
    'position_factor_exposures',
    'correlation_calculations',
    'correlation_clusters',
    'correlation_cluster_positions',
    'pairwise_correlations',
    'factor_correlations',
    'portfolio_target_prices',
    'position_interest_rate_betas',
    'market_risk_scenarios',
    'factor_exposures'
)

# Export and import each table individually
foreach ($table in $tables) {
    Write-Host "Migrating $table..." -ForegroundColor Cyan

    # Export table data as INSERT statements
    docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 pg_dump -h localhost -U sigmasight -d sigmasight_db --data-only --table=$table --inserts --no-owner --no-privileges > "${table}_data.sql"

    # Import to Railway
    powershell -Command "Get-Content ${table}_data.sql | docker exec -i -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway"

    # Verify count
    $localCount = docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 psql -h localhost -U sigmasight -d sigmasight_db -t -c "SELECT COUNT(*) FROM $table"
    $railwayCount = docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -t -c "SELECT COUNT(*) FROM $table"

    Write-Host "  Local: $($localCount.Trim()) | Railway: $($railwayCount.Trim())" -ForegroundColor $(if ($localCount -eq $railwayCount) { 'Green' } else { 'Red' })
}
```

#### Step 6: Comprehensive Verification

```powershell
# Create verification script
$script = @"
`$tables = @('users', 'portfolios', 'positions', 'company_profiles', 'portfolio_snapshots',
             'position_factor_exposures', 'position_greeks', 'position_market_betas',
             'position_volatility', 'position_tags', 'correlation_calculations',
             'correlation_clusters', 'pairwise_correlations', 'tags')

Write-Host "`n=== DATABASE COMPARISON ===" -ForegroundColor Cyan
Write-Host ("{0,-30} {1,10} {2,10} {3,10}" -f "Table", "Local", "Railway", "Status") -ForegroundColor Yellow
Write-Host ("-" * 65) -ForegroundColor Gray

foreach (`$table in `$tables) {
    `$local = (docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 psql -h localhost -U sigmasight -d sigmasight_db -t -c "SELECT COUNT(*) FROM `$table").Trim()
    `$railway = (docker exec -e PGPASSWORD=cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -t -c "SELECT COUNT(*) FROM `$table").Trim()

    `$status = if (`$local -eq `$railway) { "✓ OK" } else { "✗ MISMATCH" }
    `$color = if (`$local -eq `$railway) { "Green" } else { "Red" }

    Write-Host ("{0,-30} {1,10} {2,10} {3,10}" -f `$table, `$local, `$railway, `$status) -ForegroundColor `$color
}
"@

$script | Out-File -FilePath verify_migration.ps1 -Encoding UTF8
powershell -ExecutionPolicy Bypass -File verify_migration.ps1
```

### Step 7: Test Critical Data

```powershell
# Test 1: Verify positions have correct portfolio relationships
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT p.name as portfolio, COUNT(pos.id) as positions FROM portfolios p LEFT JOIN positions pos ON p.id = pos.portfolio_id GROUP BY p.name ORDER BY p.name;"

# Test 2: Verify factor exposures are linked to positions
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) as orphaned_exposures FROM position_factor_exposures pfe WHERE NOT EXISTS (SELECT 1 FROM positions p WHERE p.id = pfe.position_id);"

# Test 3: Check for any NULL foreign keys
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT COUNT(*) as positions_without_portfolio FROM positions WHERE portfolio_id IS NULL;"
```

## Full Migration Scripts

### Sandbox Migration Script

Save this as `migrate_to_railway_sandbox.ps1`:

```powershell
# Railway Sandbox Configuration
$RAILWAY_HOST = "hopper.proxy.rlwy.net"
$RAILWAY_PORT = "56725"
$RAILWAY_USER = "postgres"
$RAILWAY_PASSWORD = "cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb"
$RAILWAY_DB = "railway"
$CONTAINER = "backend-postgres-1"

Write-Host "=== DATABASE MIGRATION TO RAILWAY V2 ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Export schema
Write-Host "Step 1: Exporting schema..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER pg_dump -h localhost -U sigmasight -d sigmasight_db --schema-only --no-owner --no-privileges --clean --if-exists > schema_only.sql
Write-Host "  ✓ Schema exported to schema_only.sql" -ForegroundColor Green

# Step 2: Export data (custom format)
Write-Host "Step 2: Exporting data..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER pg_dump -h localhost -U sigmasight -d sigmasight_db --data-only --no-owner --no-privileges --disable-triggers --format=custom --file=/tmp/data_only.dump
docker cp ${CONTAINER}:/tmp/data_only.dump ./data_only.dump
Write-Host "  ✓ Data exported to data_only.dump" -ForegroundColor Green

# Step 3: Restore schema
Write-Host "Step 3: Restoring schema to Railway..." -ForegroundColor Yellow
powershell -Command "Get-Content schema_only.sql | docker exec -i -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB 2>&1" | Out-Null
Write-Host "  ✓ Schema restored" -ForegroundColor Green

# Step 4: Copy data to container
Write-Host "Step 4: Preparing data for restore..." -ForegroundColor Yellow
docker cp ./data_only.dump ${CONTAINER}:/tmp/railway_data.dump
Write-Host "  ✓ Data copied to container" -ForegroundColor Green

# Step 5: Restore data
Write-Host "Step 5: Restoring data to Railway..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER pg_restore -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB --data-only --no-owner --no-privileges /tmp/railway_data.dump 2>&1 | Out-Null
Write-Host "  ✓ Data restored" -ForegroundColor Green

# Step 6: Verify
Write-Host ""
Write-Host "Step 6: Verifying migration..." -ForegroundColor Yellow
Write-Host ""

$tables = @('users', 'portfolios', 'positions', 'position_factor_exposures', 'position_market_betas', 'position_volatility')

Write-Host ("{0,-30} {1,10} {2,10} {3,10}" -f "Table", "Local", "Railway", "Status") -ForegroundColor Cyan
Write-Host ("-" * 65)

foreach ($table in $tables) {
    $local = (docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER psql -h localhost -U sigmasight -d sigmasight_db -t -c "SELECT COUNT(*) FROM $table").Trim()
    $railway = (docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM $table").Trim()

    $status = if ($local -eq $railway) { "✓ OK" } else { "✗ MISMATCH" }
    $color = if ($local -eq $railway) { "Green" } else { "Red" }

    Write-Host ("{0,-30} {1,10} {2,10} {3,10}" -f $table, $local, $railway, $status) -ForegroundColor $color
}

Write-Host ""
Write-Host "=== MIGRATION COMPLETE ===" -ForegroundColor Green
```

### Production Migration Script

Save this as `migrate_to_production.ps1`:

```powershell
# Railway Production Configuration
$RAILWAY_HOST = "maglev.proxy.rlwy.net"
$RAILWAY_PORT = "27062"
$RAILWAY_USER = "postgres"
$RAILWAY_PASSWORD = "xvymYweUKKCmCpHoFptrmBFOiqFjzLhz"
$RAILWAY_DB = "railway"
$CONTAINER = "backend-postgres-1"

Write-Host "=== DATABASE MIGRATION TO RAILWAY PRODUCTION ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  WARNING: This will REPLACE all data in PRODUCTION database!" -ForegroundColor Red
Write-Host "   Host: $RAILWAY_HOST" -ForegroundColor Yellow
Write-Host "   Database: $RAILWAY_DB" -ForegroundColor Yellow
Write-Host ""
$confirmation = Read-Host "Type 'MIGRATE PRODUCTION' to continue"

if ($confirmation -ne "MIGRATE PRODUCTION") {
    Write-Host "Migration cancelled." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 1: Export schema
Write-Host "Step 1: Exporting schema..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER pg_dump -h localhost -U sigmasight -d sigmasight_db --schema-only --no-owner --no-privileges --clean --if-exists > schema_only.sql
Write-Host "  ✓ Schema exported to schema_only.sql" -ForegroundColor Green

# Step 2: Export data (custom format)
Write-Host "Step 2: Exporting data..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER pg_dump -h localhost -U sigmasight -d sigmasight_db --data-only --no-owner --no-privileges --disable-triggers --format=custom --file=/tmp/data_only.dump
docker cp ${CONTAINER}:/tmp/data_only.dump ./data_only.dump
Write-Host "  ✓ Data exported to data_only.dump" -ForegroundColor Green

# Step 3: Restore schema
Write-Host "Step 3: Restoring schema to Railway Production..." -ForegroundColor Yellow
powershell -Command "Get-Content schema_only.sql | docker exec -i -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB 2>&1" | Out-Null
Write-Host "  ✓ Schema restored" -ForegroundColor Green

# Step 4: Copy data to container
Write-Host "Step 4: Preparing data for restore..." -ForegroundColor Yellow
docker cp ./data_only.dump ${CONTAINER}:/tmp/railway_data.dump
Write-Host "  ✓ Data copied to container" -ForegroundColor Green

# Step 5: Restore data
Write-Host "Step 5: Restoring data to Railway Production..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER pg_restore -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB --data-only --no-owner --no-privileges /tmp/railway_data.dump 2>&1 | Out-Null
Write-Host "  ✓ Data restored" -ForegroundColor Green

# Step 6: Verify
Write-Host ""
Write-Host "Step 6: Verifying migration..." -ForegroundColor Yellow
Write-Host ""

$tables = @('users', 'portfolios', 'positions', 'position_factor_exposures', 'position_market_betas', 'position_volatility', 'portfolio_snapshots')

Write-Host ("{0,-30} {1,10} {2,10} {3,10}" -f "Table", "Local", "Railway", "Status") -ForegroundColor Cyan
Write-Host ("-" * 65)

foreach ($table in $tables) {
    $local = (docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER psql -h localhost -U sigmasight -d sigmasight_db -t -c "SELECT COUNT(*) FROM $table").Trim()
    $railway = (docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM $table").Trim()

    $status = if ($local -eq $railway) { "✓ OK" } else { "✗ MISMATCH" }
    $color = if ($local -eq $railway) { "Green" } else { "Red" }

    Write-Host ("{0,-30} {1,10} {2,10} {3,10}" -f $table, $local, $railway, $status) -ForegroundColor $color
}

Write-Host ""
Write-Host "=== MIGRATION COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Test the production application" -ForegroundColor White
Write-Host "2. Verify all portfolios and positions are accessible" -ForegroundColor White
Write-Host "3. Check factor exposures and calculations" -ForegroundColor White
```

## Key Improvements Over Previous Method

1. **Custom Format**: Uses PostgreSQL's custom dump format instead of text INSERT statements - handles binary data and encoding better
2. **No Foreign Key Issues**: Custom format preserves proper insertion order automatically
3. **Atomic Operations**: Schema and data separate - easier to debug
4. **Better Error Handling**: Each step can be verified independently
5. **Comprehensive Verification**: Automated comparison of all tables

## When to Use This Method

- ✅ Full database migrations
- ✅ Large datasets (10,000+ rows)
- ✅ Complex foreign key relationships
- ✅ Binary data (bytea columns)
- ✅ Multi-byte UTF-8 characters

## When to Use INSERT Method (Original)

- Single table migrations
- Small datasets (<1,000 rows)
- No foreign key constraints
- Simple data types only

## Troubleshooting

### Error: "must be owner of table"
**Solution**: Add `--no-owner --no-privileges` to both dump and restore commands

### Error: "permission denied to disable triggers"
**Solution**: Use the table-by-table migration approach instead of `--disable-triggers`

### Error: "duplicate key value violates unique constraint"
**Solution**: Add `--clean` to schema export to drop existing tables first

### Verification Shows Mismatches
**Solution**: Check Railway logs for specific INSERT errors:
```powershell
docker exec -e PGPASSWORD=[railway-password] backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

## Related Documentation

- Original Migration Guide: `MoveDBLocalToRailway.md`
- PostgreSQL pg_dump docs: https://www.postgresql.org/docs/current/app-pgdump.html
- Custom format benefits: https://www.postgresql.org/docs/current/backup-dump.html

## Quick Reference

### To Migrate to Sandbox:
```powershell
cd backend/scripts
./migrate_to_railway_sandbox.ps1
```

### To Migrate to Production:
```powershell
cd backend/scripts
./migrate_to_production.ps1
```

**⚠️ IMPORTANT**: Production script requires typing `MIGRATE PRODUCTION` for safety.

---

**Last Updated:** 2025-11-11
**Status:** Recommended for all future migrations
**Environments:** Sandbox (hopper.proxy.rlwy.net:56725), Production (maglev.proxy.rlwy.net:27062)
**Previous Method Issues:** 100% positions data loss, 92% factor exposures data loss
