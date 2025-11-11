# Railway Production Database Migration Script
# Migrates local database to Railway production environment

# Production Configuration
$RAILWAY_HOST = "maglev.proxy.rlwy.net"
$RAILWAY_PORT = "27062"
$RAILWAY_USER = "postgres"
$RAILWAY_PASSWORD = "xvymYweUKKCmCpHoFptrmBFOiqFjzLhz"
$RAILWAY_DB = "railway"
$CONTAINER = "backend-postgres-1"

Write-Host "=== DATABASE MIGRATION TO RAILWAY PRODUCTION ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This will REPLACE all data in PRODUCTION database!" -ForegroundColor Red
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
Write-Host "  Schema exported to schema_only.sql" -ForegroundColor Green

# Step 2: Export data (custom format)
Write-Host "Step 2: Exporting data..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER pg_dump -h localhost -U sigmasight -d sigmasight_db --data-only --no-owner --no-privileges --disable-triggers --format=custom --file=/tmp/data_only.dump
docker cp ${CONTAINER}:/tmp/data_only.dump ./data_only.dump
Write-Host "  Data exported to data_only.dump" -ForegroundColor Green

# Step 3: Restore schema
Write-Host "Step 3: Restoring schema to Railway Production..." -ForegroundColor Yellow
powershell -Command "Get-Content schema_only.sql | docker exec -i -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB 2>&1" | Out-Null
Write-Host "  Schema restored" -ForegroundColor Green

# Step 4: Copy data to container
Write-Host "Step 4: Preparing data for restore..." -ForegroundColor Yellow
docker cp ./data_only.dump ${CONTAINER}:/tmp/railway_data.dump
Write-Host "  Data copied to container" -ForegroundColor Green

# Step 5: Restore data
Write-Host "Step 5: Restoring data to Railway Production..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER pg_restore -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB --data-only --no-owner --no-privileges /tmp/railway_data.dump 2>&1 | Out-Null
Write-Host "  Data restored" -ForegroundColor Green

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

    if ($local -eq $railway) {
        $status = "OK"
        $color = "Green"
    } else {
        $status = "MISMATCH"
        $color = "Red"
    }

    Write-Host ("{0,-30} {1,10} {2,10} {3,10}" -f $table, $local, $railway, $status) -ForegroundColor $color
}

Write-Host ""
Write-Host "=== MIGRATION COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Test the production application" -ForegroundColor White
Write-Host "2. Verify all portfolios and positions are accessible" -ForegroundColor White
Write-Host "3. Check factor exposures and calculations" -ForegroundColor White
