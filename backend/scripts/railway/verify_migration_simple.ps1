# Database Migration Verification Script
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
    'tags_v2',
    'factor_definitions',
    'agent_conversations',
    'agent_messages'
)

Write-Host ""
Write-Host "=== DATABASE MIGRATION VERIFICATION ===" -ForegroundColor Cyan
Write-Host ("{0,-35} {1,10} {2,10} {3,15}" -f "Table", "Local", "Railway", "Status") -ForegroundColor Yellow
Write-Host ("-" * 75) -ForegroundColor Gray

$totalLocal = 0
$totalRailway = 0
$mismatches = 0

foreach ($table in $tables) {
    $local = (docker exec -e PGPASSWORD=sigmasight_dev backend-postgres-1 psql -h localhost -U sigmasight -d sigmasight_db -t -c "SELECT COUNT(*) FROM $table" 2>$null).Trim()
    $railway = (docker exec -e PGPASSWORD=cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb backend-postgres-1 psql -h hopper.proxy.rlwy.net -p 56725 -U postgres -d railway -t -c "SELECT COUNT(*) FROM $table" 2>$null).Trim()

    if ($local -match '^\d+$' -and $railway -match '^\d+$') {
        $totalLocal += [int]$local
        $totalRailway += [int]$railway

        $status = if ($local -eq $railway) { "OK" } else { "MISMATCH"; $mismatches++ }
        $color = if ($local -eq $railway) { "Green" } else { "Red" }

        Write-Host ("{0,-35} {1,10} {2,10} {3,15}" -f $table, $local, $railway, $status) -ForegroundColor $color
    }
}

Write-Host ("-" * 75) -ForegroundColor Gray
Write-Host ("{0,-35} {1,10} {2,10}" -f "TOTAL ROWS", $totalLocal, $totalRailway) -ForegroundColor Cyan
Write-Host ""

if ($mismatches -eq 0) {
    Write-Host "SUCCESS - All tables match!" -ForegroundColor Green
} else {
    Write-Host "WARNING - $mismatches table(s) have mismatches" -ForegroundColor Yellow
}
Write-Host ""
