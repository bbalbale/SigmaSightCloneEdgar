# Railway Database Migration V2 - Improved Process
# Handles foreign keys and complex data relationships properly

# Railway Configuration
$RAILWAY_HOST = "hopper.proxy.rlwy.net"
$RAILWAY_PORT = "56725"
$RAILWAY_USER = "postgres"
$RAILWAY_PASSWORD = "cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb"
$RAILWAY_DB = "railway"
$CONTAINER = "backend-postgres-1"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "       DATABASE MIGRATION TO RAILWAY V2 (Improved Process)      " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Export schema
Write-Host "[1/6] Exporting database schema..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER pg_dump `
    -h localhost -U sigmasight -d sigmasight_db `
    --schema-only --no-owner --no-privileges --clean --if-exists `
    > schema_only.sql

if ($LASTEXITCODE -eq 0) {
    $schemaSize = (Get-Item schema_only.sql).Length / 1KB
    $schemaSizeRounded = [math]::Round($schemaSize, 2)
    Write-Host "  Success - Schema exported successfully ($schemaSizeRounded KB)" -ForegroundColor Green
} else {
    Write-Host "  Error - Schema export failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Export data (custom format for better reliability)
Write-Host ""
Write-Host "[2/6] Exporting database data (custom format)..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER pg_dump `
    -h localhost -U sigmasight -d sigmasight_db `
    --data-only --no-owner --no-privileges `
    --format=custom --file=/tmp/data_only.dump

if ($LASTEXITCODE -eq 0) {
    docker cp ${CONTAINER}:/tmp/data_only.dump ./data_only.dump
    $dataSize = (Get-Item data_only.dump).Length / 1MB
    $dataSizeRounded = [math]::Round($dataSize, 2)
    Write-Host "  Success - Data exported successfully ($dataSizeRounded MB)" -ForegroundColor Green
} else {
    Write-Host "  Error - Data export failed!" -ForegroundColor Red
    exit 1
}

# Step 3: Restore schema to Railway
Write-Host ""
Write-Host "[3/6] Restoring schema to Railway..." -ForegroundColor Yellow
$schemaErrors = powershell -Command "Get-Content schema_only.sql | docker exec -i -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB 2>&1" | Where-Object { $_ -match "ERROR" -and $_ -notmatch "role .* does not exist" }

if ($schemaErrors) {
    Write-Host "  Warning - Schema restored with warnings (check for critical errors)" -ForegroundColor Yellow
    $schemaErrors | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
} else {
    Write-Host "  Success - Schema restored successfully" -ForegroundColor Green
}

# Step 4: Copy data dump to container
Write-Host ""
Write-Host "[4/6] Preparing data for Railway restore..." -ForegroundColor Yellow
docker cp ./data_only.dump ${CONTAINER}:/tmp/railway_data.dump

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Success - Data file ready in container" -ForegroundColor Green
} else {
    Write-Host "  Error - Failed to copy data to container!" -ForegroundColor Red
    exit 1
}

# Step 5: Restore data to Railway
Write-Host ""
Write-Host "[5/6] Restoring data to Railway (this may take a minute)..." -ForegroundColor Yellow
$restoreErrors = docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER pg_restore `
    -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB `
    --data-only --no-owner --no-privileges `
    /tmp/railway_data.dump 2>&1 | Where-Object { $_ -match "ERROR" -and $_ -notmatch "role .* does not exist" }

if ($restoreErrors) {
    Write-Host "  Warning - Data restored with some errors:" -ForegroundColor Yellow
    $restoreErrors | Select-Object -First 10 | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
    if ($restoreErrors.Count -gt 10) {
        $remainingErrors = $restoreErrors.Count - 10
        Write-Host "    ... and $remainingErrors more errors" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Success - Data restored successfully" -ForegroundColor Green
}

# Step 6: Comprehensive verification
Write-Host ""
Write-Host "[6/6] Verifying migration..." -ForegroundColor Yellow
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
    'correlation_calculations',
    'pairwise_correlations',
    'tags'
)

Write-Host ("{0,-35} {1,12} {2,12} {3,12}" -f "Table Name", "Local", "Railway", "Status") -ForegroundColor Cyan
Write-Host ("-" * 75) -ForegroundColor Gray

$totalMismatches = 0
$criticalMismatches = @()

foreach ($table in $tables) {
    try {
        $local = (docker exec -e PGPASSWORD=sigmasight_dev $CONTAINER psql -h localhost -U sigmasight -d sigmasight_db -t -c "SELECT COUNT(*) FROM $table" 2>$null).Trim()
        $railway = (docker exec -e PGPASSWORD=$RAILWAY_PASSWORD $CONTAINER psql -h $RAILWAY_HOST -p $RAILWAY_PORT -U $RAILWAY_USER -d $RAILWAY_DB -t -c "SELECT COUNT(*) FROM $table" 2>$null).Trim()

        $match = ($local -eq $railway)
        $status = if ($match) { "OK" } else { "MISMATCH" }
        $color = if ($match) { "Green" } else { "Red" }

        Write-Host ("{0,-35} {1,12} {2,12} {3,12}" -f $table, $local, $railway, $status) -ForegroundColor $color

        if (-not $match) {
            $totalMismatches++
            if ($table -in @('users', 'portfolios', 'positions', 'position_factor_exposures')) {
                $criticalMismatches += $table
            }
        }
    } catch {
        Write-Host ("{0,-35} {1,12} {2,12} {3,12}" -f $table, "ERROR", "ERROR", "ERROR - Failed") -ForegroundColor Red
        $totalMismatches++
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan

if ($totalMismatches -eq 0) {
    Write-Host "  SUCCESS - MIGRATION SUCCESSFUL - ALL DATA VERIFIED" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test login with demo credentials" -ForegroundColor White
    Write-Host "  2. Verify portfolios load correctly" -ForegroundColor White
    Write-Host "  3. Check risk metrics calculations" -ForegroundColor White
} elseif ($criticalMismatches.Count -gt 0) {
    Write-Host "  ERROR - CRITICAL DATA MISSING" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Critical tables with mismatches:" -ForegroundColor Red
    $criticalMismatches | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Action required:" -ForegroundColor Yellow
    Write-Host "  1. Check error messages above for clues" -ForegroundColor White
    Write-Host "  2. Review ImprovedMigration.md for troubleshooting" -ForegroundColor White
    Write-Host "  3. Consider table-by-table migration for failed tables" -ForegroundColor White
} else {
    Write-Host "  WARNING - MIGRATION COMPLETED WITH WARNINGS" -ForegroundColor Yellow
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Non-critical mismatches detected: $totalMismatches tables" -ForegroundColor Yellow
    Write-Host "Review the comparison above and verify affected functionality" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Log files created:" -ForegroundColor White
Write-Host "  - schema_only.sql (database structure)" -ForegroundColor Gray
Write-Host "  - data_only.dump (database data)" -ForegroundColor Gray
Write-Host ""
