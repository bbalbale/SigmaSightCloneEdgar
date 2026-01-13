# Scripts Directory Documentation

This document describes all files in `backend/scripts/` and its subdirectories.

---

## Overview

The `scripts/` directory contains **80+ utility scripts** organized into 8 main directories. These scripts handle database management, data operations, verification, analysis, monitoring, and Railway deployment tasks.

---

## Directory: `database/` - Database Management & Seeding

| Filename | Purpose | Usage |
|----------|---------|-------|
| `seed_database.py` | Orchestrates demo data seeding with 3 portfolios, 63 positions | Standalone script; called from reset_and_seed.py |
| `reset_and_seed.py` | Main authoritative script for full reset and reseed | Primary seeding entry point |
| `clear_calculation_data.py` | Removes calculation results (snapshots, Greeks, factors) | Admin cleanup; pre-batch |
| `list_users.py` | Lists all users with portfolio details | Quick reference; diagnostic |
| `seed_stress_scenarios.py` | Creates stress test scenarios (15-18 per portfolio) | Called during seeding |
| `validate_seed_data_integrity.py` | Validates seeded demo data for consistency | Verification post-seed |
| `delete_users.py` | Deletes specific users and their portfolios | Admin account cleanup |
| `check_indexes_*.py` | Various scripts to check database indexes | Diagnostics |
| `create_indexes_*.py` | Creates missing indexes | Optimization |
| `compare_schemas*.py` | Compares database schemas | Schema validation |

---

## Directory: `verification/` - Setup Validation & Data Verification

| Filename | Purpose | Usage |
|----------|---------|-------|
| `validate_setup.py` | Comprehensive setup validation (8 checks) | Run after initial setup |
| `verify_setup.py` | Alternative setup verification script | Setup validation |
| `verify_demo_portfolios.py` | Verifies 3 demo portfolios with 63 positions exist | Daily health check |
| `verify_batch_results.py` | Checks if batch calculations completed successfully | Post-batch verification |
| `verify_database_state.py` | Comprehensive database state check | Database health |
| `verify_migrations.py` | Verifies Alembic migrations applied correctly | Migration status |
| `check_equity_values.py` | Checks portfolio equity balance values | Financial accuracy |
| `check_portfolio.py` | Detailed portfolio inspection | Diagnostic tool |
| `verify_target_prices.py` | Verifies target price data | Target price validation |

---

## Directory: `analysis/` - Deep Analysis & Debugging Tools

| Filename | Purpose | Usage |
|----------|---------|-------|
| `analyze_beta_distributions.py` | Analyzes beta calculation distribution | Beta analysis |
| `analyze_interest_rate_impact.py` | Analyzes interest rate effects on portfolio | Rate sensitivity |
| `check_factor_exposures.py` | Detailed check of factor exposure calculations | Factor analysis |
| `check_historical_data_coverage.py` | Analyzes historical price data coverage per symbol | Data coverage |
| `check_stress_test.py` | Detailed stress test results analysis | Stress testing |

---

## Directory: `data_operations/` - Market Data & ETF Management

| Filename | Purpose | Usage |
|----------|---------|-------|
| `fetch_factor_etf_data.py` | Fetches factor ETF historical prices | Daily/periodic task |
| `backfill_factor_etfs.py` | Backfills missing factor ETF historical data | Data backfill |
| `list_symbols.py` | Lists all position symbols in database | Quick reference |
| `sync_position_prices.py` | Updates position prices from MarketDataCache | Phase 2.5 operation |
| `populate_company_profiles.py` | Populates company profile data (53 fields) | Data enrichment |
| `populate_historical_prices.py` | Populates historical OHLC price data | Historical data |

---

## Directory: `monitoring/` - Real-Time System Monitoring

| Filename | Purpose | Usage |
|----------|---------|-------|
| `monitor_chat_interface.py` | Automated browser testing of chat interface with Playwright | Monitoring |
| `simple_monitor.py` | Basic system health monitoring | Quick health check |
| `monitor_provider_usage.py` | Monitors API provider usage and rate limits | Usage tracking |

---

## Directory: `automation/` - Automated Batch Jobs & Scheduling

| Filename | Purpose | Usage |
|----------|---------|-------|
| `railway_daily_batch.py` | Daily batch job runner for Railway | Railway cron job |
| `trading_calendar.py` | NYSE trading calendar utilities | Imported by automation scripts |

---

## Directory: `railway/` - Railway Deployment & Auditing

### Core Operations (SSH Required)

| Filename | Purpose | Usage |
|----------|---------|-------|
| `railway_run_migration.py` | Runs Alembic migrations on Railway | Run in Railway SSH |
| `verify_railway_migration.py` | Verifies migration status | Run in Railway SSH |
| `seed_portfolios_railway.py` | Seeds demo portfolios on Railway | Railway seeding |

### Audit Scripts (No SSH - API-Based)

| Filename | Purpose | Usage |
|----------|---------|-------|
| `audit_railway_data.py` | API-based audit of portfolio, position, tag data | Run locally |
| `audit_railway_market_data.py` | API-based audit of market data, company profiles | Run locally |
| `audit_railway_analytics.py` | API-based audit of all 7 analytics endpoints | Run locally |
| `audit_railway_calculations_verbose.py` | Detailed calculation audit | Via `railway run` |

### Diagnostic & Health Check

| Filename | Purpose | Usage |
|----------|---------|-------|
| `test_railway_batch.py` | Tests batch processing trigger | Batch testing |
| `check_railway_positions.py` | Checks position data on Railway | Quick check |
| `test_railway_health.py` | Health check of Railway deployment | Health check |
| `diagnose_batch_corruption.py` | Diagnoses batch data corruption | Corruption detection |

---

## Directory: `DANGEROUS_DESTRUCTIVE_SCRIPTS/`

**⚠️ WARNING: These scripts PERMANENTLY DELETE all data**

| Filename | Purpose | Usage |
|----------|---------|-------|
| `DANGEROUS_reseed_july_2025_complete.py` | Deletes all data, reseeds to July 1 2025 | NEVER on production |
| `DANGEROUS_reseed_with_v3_backfill.py` | Truncates all data, reseeds July 2025 | Test environments only |
| `DANGEROUS_railway_reset_database.py` | Auto-confirms database reset on Railway | Railway reset only |

All require DOUBLE CONFIRMATION (interactive prompt + "DELETE ALL MY DATA").

---

## Directory: `_archive/` - Deprecated & Legacy Scripts

Organized archived files:
- `completed_migrations/` - 20 one-time data migrations
- `analysis_investigations/` - Legacy debug analysis
- `data_ops_one_time/` - One-time data operations
- `one_time_fixes/` - Completed one-time fixes
- `manual_tests/` - Puppeteer browser automation
- `testing_suite/` - Old automated test scripts
- `test_api_providers/` - API provider testing

---

## Usage Workflow

### Initial Setup
```bash
uv run alembic -c alembic.ini upgrade head
uv run alembic -c alembic_ai.ini upgrade head
python scripts/database/seed_database.py
python scripts/verification/validate_setup.py
```

### Daily Operations
```bash
python scripts/data_operations/populate_company_profiles.py
python scripts/verification/verify_batch_results.py
python scripts/monitoring/monitor_provider_usage.py
```

### Railway Production
```bash
# SSH-based
railway shell
uv run python scripts/railway/railway_run_migration.py

# Local auditing
python scripts/railway/audit_railway_data.py
python scripts/railway/audit_railway_analytics.py
```

---

## Key Features by Directory

| Directory | Scripts | Primary Use |
|-----------|---------|-------------|
| `database/` | 23 | Setup, seeding, data corrections |
| `verification/` | 24 | Validation, integrity checks |
| `analysis/` | 13 | Debugging, investigation |
| `data_operations/` | 8 | Market data, company profiles |
| `monitoring/` | 4 | Health checks, API usage |
| `automation/` | 2 | Scheduled batch jobs |
| `railway/` | 33 | Deployment, audit, diagnostics |
| `DANGEROUS/` | 3 | Full database reset (ISOLATED) |
