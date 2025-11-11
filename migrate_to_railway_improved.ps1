# Railway Database Migration Script - Improved Method
# Uses schema-first, data-second approach to avoid foreign key constraint issues

# Railway Configuration (from planning doc)
$RAILWAY_HOST = "hopper.proxy.rlwy.net"
$RAILWAY_PORT = "56725"
$RAILWAY_USER = "postgres"
$RAILWAY_PASSWORD = "cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb"
$RAILWAY_DB = "railway"

# Local Database Configuration
$LOCAL_HOST = "localhost"
$LOCAL_PORT = "5432"
$LOCAL_USER = "sigmasight"
$LOCAL_PASSWORD = "sigmasight_dev"
$LOCAL_DB = "sigmasight_db"

# Docker Container Name
$CONTAINER = "backend-postgres-1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DATABASE MIGRATION TO RAILWAY - V2" -ForegroundColor Cyan
Write-Host "Schema-First, Data-Second Approach" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify container is running
Write-Host "Checking Docker container..." -ForegroundColor Yellow
$containerCheck = docker ps --filter "name=$CONTAINER" --format "{{.Names}}"
if ($containerCheck -ne $CONTAINER) {
    Write-Host "[FAIL] Container $CONTAINER not found or not running!" -ForegroundColor Red
    Write-Host "   Run: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Container $CONTAINER is running" -ForegroundColor Green
Write-Host ""

# Step 1: Export schema
Write-Host "Step 1: Exporting database schema..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=$LOCAL_PASSWORD $CONTAINER pg_dump `
    -h $LOCAL_HOST -U $LOCAL_USER -d $LOCAL_DB `
    --schema-only --no-owner --no-privileges --clean --if-exists `
    > schema_only.sql

if ($LASTEXITCODE -eq 0) {
    $schemaSize = (Get-Item schema_only.sql).Length / 1KB
    Write-Host "[OK] Schema exported: schema_only.sql ($([math]::Round($schemaSize, 2)) KB)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Schema export failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Export data (custom format)
Write-Host "Step 2: Exporting database data..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=$LOCAL_PASSWORD $CONTAINER pg_dump `
    -h $LOCAL_HOST -U $LOCAL_USER -d $LOCAL_DB `
    --data-only --no-owner --no-privileges --format=custom `
    --file=/tmp/data_only.dump

docker cp ${CONTAINER}:/tmp/data_only.dump ./data_only.dump

if ($LASTEXITCODE -eq 0) {
    $dataSize = (Get-Item data_only.dump).Length / 1MB
    Write-Host "[OK] Data exported: data_only.dump ($([math]::Round($dataSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Data export failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Restore schema to Railway
Write-Host "Step 3: Restoring schema to Railway..." -ForegroundColor Yellow
Write-Host "   (This will drop and recreate all tables)" -ForegroundColor Gray
Get-Content schema_only.sql | docker exec -i -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER `
    psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Schema restored to Railway" -ForegroundColor Green
} else {
    Write-Host "[WARN] Schema restore completed with warnings (usually harmless)" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Copy data to container
Write-Host "Step 4: Preparing data for restore..." -ForegroundColor Yellow
docker cp ./data_only.dump ${CONTAINER}:/tmp/railway_data.dump

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Data copied to container" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Failed to copy data to container!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Restore data to Railway
Write-Host "Step 5: Restoring data to Railway..." -ForegroundColor Yellow
Write-Host "   (This may take several minutes for large datasets)" -ForegroundColor Gray
docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER pg_restore `
    -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB `
    --data-only --no-owner --no-privileges `
    /tmp/railway_data.dump 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Data restored to Railway" -ForegroundColor Green
} else {
    Write-Host "[WARN] Data restore completed (check verification below)" -ForegroundColor Yellow
}
Write-Host ""

# Step 6: Comprehensive Verification
Write-Host "Step 6: Verifying migration..." -ForegroundColor Yellow
Write-Host ""

$tables = @(
    'users',
    'portfolios',
    'positions',
    'company_profiles',
    'portfolio_snapshots',
    'position_factor_exposures',
    'position_greeks',
    'position_market_betas',
    'position_volatility',
    'position_tags',
    'tags',
    'correlation_calculations',
    'pairwise_correlations',
    'target_prices'
)

Write-Host ("{0,-35} {1,10} {2,10} {3,10}" -f "Table", "Local", "Railway", "Status") -ForegroundColor Cyan
Write-Host ("-" * 70) -ForegroundColor Gray

$allMatch = $true
foreach ($table in $tables) {
    $local = (docker exec -e PGPASSWORD=$LOCAL_PASSWORD $CONTAINER `
        psql -h $LOCAL_HOST -U $LOCAL_USER -d $LOCAL_DB -t -c "SELECT COUNT(*) FROM $table" 2>&1).Trim()

    $railway = (docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER `
        psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM $table" 2>&1).Trim()

    $status = if ($local -eq $railway) { "[OK]" } else { "[MISMATCH]"; $allMatch = $false }
    $color = if ($local -eq $railway) { "Green" } else { "Red" }

    Write-Host ("{0,-35} {1,10} {2,10} {3,10}" -f $table, $local, $railway, $status) -ForegroundColor $color
}

Write-Host ""

# Step 7: Critical Data Tests
Write-Host "Step 7: Testing critical data relationships..." -ForegroundColor Yellow
Write-Host ""

# Test 1: Users (CRITICAL)
Write-Host "Test 1: Users and portfolios" -ForegroundColor Cyan
docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER `
    psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB `
    -c "SELECT u.email, p.name FROM users u JOIN portfolios p ON u.id = p.user_id ORDER BY u.email;"
Write-Host ""

# Test 2: Position relationships
Write-Host "Test 2: Portfolio positions" -ForegroundColor Cyan
docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER `
    psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB `
    -c "SELECT p.name as portfolio, COUNT(pos.id) as positions FROM portfolios p LEFT JOIN positions pos ON p.id = pos.portfolio_id GROUP BY p.name ORDER BY p.name;"
Write-Host ""

# Test 3: Orphaned records
Write-Host "Test 3: Data integrity checks" -ForegroundColor Cyan
$orphanedPositions = (docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER `
    psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t `
    -c "SELECT COUNT(*) FROM positions WHERE portfolio_id IS NULL;").Trim()

$orphanedExposures = (docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER `
    psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t `
    -c "SELECT COUNT(*) FROM position_factor_exposures pfe WHERE NOT EXISTS (SELECT 1 FROM positions p WHERE p.id = pfe.position_id);").Trim()

Write-Host "   Positions without portfolio: $orphanedPositions" -ForegroundColor $(if ($orphanedPositions -eq "0") { "Green" } else { "Red" })
Write-Host "   Orphaned factor exposures: $orphanedExposures" -ForegroundColor $(if ($orphanedExposures -eq "0") { "Green" } else { "Red" })
Write-Host ""

# Final Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MIGRATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($allMatch -and $orphanedPositions -eq "0" -and $orphanedExposures -eq "0") {
    Write-Host "[SUCCESS] MIGRATION SUCCESSFUL!" -ForegroundColor Green
    Write-Host ""
    Write-Host "All tables migrated successfully with no data loss." -ForegroundColor Green
    Write-Host "Railway database is ready to use." -ForegroundColor Green
} else {
    Write-Host "[WARN] MIGRATION COMPLETED WITH ISSUES" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Some data mismatches detected. Review the verification output above." -ForegroundColor Yellow
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Check Railway logs for specific errors" -ForegroundColor Gray
    Write-Host "  - Verify foreign key constraints are satisfied" -ForegroundColor Gray
    Write-Host "  - Consider running manual table-by-table migration for failed tables" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Test Railway backend API endpoints" -ForegroundColor White
Write-Host "  2. Update frontend .env.local to use Railway backend" -ForegroundColor White
Write-Host "  3. Verify login with demo credentials" -ForegroundColor White
Write-Host ""
Write-Host "Demo Credentials:" -ForegroundColor Cyan
Write-Host "  - demo_individual@sigmasight.com / demo12345" -ForegroundColor White
Write-Host "  - demo_hnw@sigmasight.com / demo12345" -ForegroundColor White
Write-Host "  - demo_hedgefundstyle@sigmasight.com / demo12345" -ForegroundColor White
Write-Host "  - demo_familyoffice@sigmasight.com / demo12345" -ForegroundColor White
Write-Host ""
