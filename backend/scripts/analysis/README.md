# Analysis & Debugging Scripts

Deep analysis and debugging tools for troubleshooting calculation issues.

## Key Scripts

### Beta & Factor Analysis
- **analyze_beta_distributions.py** - Analyze beta calculation distributions
- **investigate_beta_calculation.py** - Deep dive into beta calculations
- **analyze_exposure_dependencies.py** - Factor exposure dependencies
- **debug_factor_calculation.py** - Debug factor calculation issues

### Portfolio Analysis
- **check_equity.py** - Check equity calculations
- **check_short_exposure.py** - Verify short exposure calculations
- **check_monitoring_status.py** - Check monitoring system status

### Market Analysis
- **analyze_interest_rate_impact.py** - Interest rate impact analysis
- **analyze_return_scaling.py** - Return scaling analysis
- **debug_multivariate_regression.py** - Regression debugging

### Data Quality
- **check_historical_data_coverage.py** - Historical data coverage
- **check_exposure_storage.py** - Exposure data storage
- **check_factor_exposures.py** - Factor exposure verification
- **check_stress_test.py** - Stress test results
- **inspect_stress_results.py** - Detailed stress result inspection

## Usage

Most analysis scripts are run when troubleshooting specific issues:

```bash
cd backend
# Analyze beta calculations
uv run python scripts/analysis/investigate_beta_calculation.py

# Check factor exposures
uv run python scripts/analysis/check_factor_exposures.py

# Debug calculation failures
uv run python scripts/analysis/analyze_demo_calculation_engine_failures.py
```