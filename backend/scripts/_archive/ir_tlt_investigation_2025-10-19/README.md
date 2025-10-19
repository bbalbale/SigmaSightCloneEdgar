# Interest Rate Beta Methodology Investigation (2025-10-19)

## Purpose
This archive contains the investigation scripts used to compare DGS10 (Fed 10-Year Treasury yields) vs TLT (20+ Year Treasury Bond ETF) methodologies for calculating interest rate beta.

## Decision Outcome
**SWITCHED TO TLT** - TLT-based methodology selected for production use.

## Rationale
- **DGS10 betas**: ~0.0001 (realistic but too small, rounded to $0 in stress tests)
- **TLT betas**: -0.001 to -0.006 (7-44x larger, measurable P&L impacts)
- **Statistical Quality**: Similar R^2 values between both methods
- **Industry Best Practice**: Bloomberg PORT, BlackRock Aladdin, MSCI Barra all use tradeable instruments (TLT-type)
- **Practical Use**: TLT can be traded for hedging, DGS10 cannot

## Comparison Results
Demo Individual Portfolio:
- DGS10: 50bp shock = $0.29 (rounds to $0)
- TLT: 50bp shock = $12.81 (measurable)
- Magnitude: 44x larger with TLT

Demo HNW Portfolio:
- DGS10: 50bp shock = $1.46
- TLT: 50bp shock = $53.79
- Magnitude: 37x larger with TLT

Demo Hedge Fund Portfolio:
- DGS10: 50bp shock = $14.53
- TLT: 50bp shock = $511.66
- Magnitude: 35x larger with TLT

## Files in This Archive

### Investigation Scripts
- `save_dgs10_ir_results.py` - Captured DGS10 baseline analysis
- `save_tlt_ir_results.py` - Ran TLT-based analysis
- `compare_dgs10_vs_tlt.py` - Generated comprehensive comparison report
- `fetch_tlt_data.py` - Fetched TLT historical price data (127 records)

### Comparison Calculator
- `interest_rate_beta_tlt.py` - Standalone TLT calculator for comparison (now integrated into main `interest_rate_beta.py`)

## Analysis Results
Detailed comparison results saved in `backend/analysis/`:
- `dgs10_ir_results.json` - DGS10 baseline results
- `tlt_ir_results.json` - TLT analysis results
- `ir_method_comparison.txt` - Comprehensive comparison report with recommendation

## Production Implementation
The TLT methodology has been integrated into:
- `backend/app/calculations/interest_rate_beta.py` (updated 2025-10-19)
  - Changed `fetch_treasury_yield_changes()` -> `fetch_tlt_returns()`
  - Default `treasury_symbol` parameter changed from 'DGS10' to 'TLT'
  - Updated regression to use TLT price returns (%) instead of yield changes (bp)

## Key Technical Changes
**OLD (DGS10):**
```python
# Fetch yield changes in basis points
treasury_changes = df['value'].diff().dropna()

# Regression: stock_return = α + β × yield_change_bp + ε
```

**NEW (TLT):**
```python
# Fetch TLT price percentage returns
tlt_returns = df['price'].pct_change().dropna() * 100

# Regression: stock_return = α + β_TLT × tlt_return + ε
```

## Stress Test Approximation
- 50bp rate increase ≈ 2.5% TLT price decline (duration ~17)
- 100bp rate increase ≈ 5% TLT price decline

## See Also
- Backend CLAUDE.md for context on the investigation
- `TODO3.md` for related API development work
- `backend/analysis/ir_method_comparison.txt` for full technical comparison
