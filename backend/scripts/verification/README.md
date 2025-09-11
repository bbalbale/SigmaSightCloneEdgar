# Verification Scripts

System validation and verification tools.

## Key Scripts

- **verify_setup.py** - Comprehensive setup verification
- **verify_demo_portfolios.py** - Verify demo portfolio data integrity
- **verify_exposure_fix.py** - Verify factor exposure fixes
- **verify_factor_data.py** - Verify factor data quality
- **verify_mock_vs_real_data.py** - Compare mock vs real data
- **validate_option_b_implementation.py** - Validate specific implementation
- **validate_setup.py** - Environment setup validation

## Usage

### Verify complete setup:
```bash
cd backend
uv run python scripts/verification/verify_setup.py
```

### Verify demo portfolios:
```bash
uv run python scripts/verification/verify_demo_portfolios.py
```

### Compare mock vs real data:
```bash
uv run python scripts/verification/verify_mock_vs_real_data.py
```

## What Gets Verified

- Database connectivity
- API key validity
- Demo data integrity
- Calculation results
- Factor data availability
- Market data coverage