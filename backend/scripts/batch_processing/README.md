# Batch Processing Scripts

Core script for running batch calculations for portfolio analytics.

## Key Script

- **run_batch.py** ⭐ **MAIN** - Batch processor for all portfolio calculations

> **Note**: Report generation has been removed. All data is now accessed via REST API endpoints.

## Usage

### Run calculations for all portfolios:
```bash
cd backend
uv run python scripts/batch_processing/run_batch.py
```

### Run for specific portfolio:
```bash
uv run python scripts/batch_processing/run_batch.py --portfolio <UUID>
```

### Include correlation calculations (normally Tuesday only):
```bash
uv run python scripts/batch_processing/run_batch.py --correlations
```

## Calculation Engines

Runs 7 sequential calculation engines:
1. Portfolio Aggregation - Delta, notional, exposure calculations
2. Greeks - Options pricing (delta, gamma, theta, vega)
3. Factor Analysis - Multi-factor exposure (7 factors)
4. Market Risk Scenarios - Monte Carlo simulations
5. Portfolio Snapshots - Daily portfolio state
6. Position Correlations - Cross-position correlations
7. Factor Correlations - Factor-to-position relationships

## Output

All calculation results are stored in PostgreSQL and accessible via:
- `/api/v1/data/portfolio/{id}/complete` - Full portfolio snapshot
- `/api/v1/analytics/position-greeks` - Greeks calculations
- `/api/v1/analytics/factor-exposure` - Factor analysis
- Other analytics endpoints (see API_REFERENCE_V1.4.6.md)

## Archived

- `run_batch_with_reports.py` - Replaced by run_batch.py (October 2025)
- `generate_all_reports.py` - Report generation removed (October 2025)
- `run_batch_calculations.py` - Deprecated (September 2025)
