# Scripts Directory Organization

This directory contains all utility scripts for the SigmaSight backend, organized by functionality.

## Directory Structure

```
scripts/
├── batch_processing/     # Main calculation and report generation
├── data_operations/      # Data fetching, backfilling, exports
├── database/            # Database setup, seeding, migrations
├── testing/             # All test scripts
├── analysis/            # Analysis and debugging tools
├── verification/        # Validation and verification scripts
├── monitoring/          # System monitoring scripts
├── migrations/          # One-time fixes and migrations
├── utilities/           # General utility scripts
├── legacy/              # Deprecated/historical scripts
└── test_api_providers/  # API provider testing
```

## Quick Reference

### Most Common Tasks

**Run batch calculations:**
```bash
cd backend
uv run python scripts/batch_processing/run_batch_with_reports.py
```

**Reset and seed database:**
```bash
cd backend
uv run python scripts/database/reset_and_seed.py
```

**Verify setup:**
```bash
cd backend
uv run python scripts/verification/verify_setup.py
```

**Test authentication:**
```bash
cd backend
uv run python scripts/testing/test_auth.py
```

## Directory Purposes

- **batch_processing**: Core operations for running calculations and generating reports
- **data_operations**: Market data fetching, ETF data management, backfilling
- **database**: Database initialization, seeding, and management
- **testing**: Comprehensive test scripts for all components
- **analysis**: Deep dive analysis and debugging tools
- **verification**: System validation and verification
- **monitoring**: Real-time monitoring and health checks
- **migrations**: One-time data migrations and fixes
- **utilities**: General purpose utility scripts
- **legacy**: Deprecated scripts kept for reference

## Usage Notes

1. Always run scripts from the `backend` directory
2. Most scripts require the database to be running (`docker-compose up -d`)
3. Ensure environment variables are set in `.env` file
4. Use `uv run python` to execute scripts with proper dependencies