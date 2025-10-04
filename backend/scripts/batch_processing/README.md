# Batch Processing Scripts

Core scripts for running batch calculations and generating portfolio reports.

## Key Scripts

- **run_batch_with_reports.py** ⭐ **MAIN** - Batch processor with integrated report generation (use with --skip-reports flag)
- **generate_all_reports.py** - Standalone report generation for all portfolios (deprecated - use API instead)

> **Note**: `run_batch_calculations.py` has been deprecated and archived. Use `run_batch_with_reports.py --skip-reports` instead.

## Usage

### Run calculations and reports for all portfolios:
```bash
cd backend
uv run python scripts/batch_processing/run_batch_with_reports.py
```

### Run for specific portfolio:
```bash
uv run python scripts/batch_processing/run_batch_with_reports.py --portfolio <UUID>
```

### Skip report generation:
```bash
uv run python scripts/batch_processing/run_batch_with_reports.py --skip-reports
```

### Generate reports only:
```bash
uv run python scripts/batch_processing/generate_all_reports.py
```

## Calculation Engines

Runs 8 sequential calculation engines:
1. Greeks (options pricing)
2. Factor Analysis
3. Correlations
4. Market Risk
5. Portfolio Snapshots
6. Stress Testing
7. Performance Attribution
8. Data Quality Monitoring