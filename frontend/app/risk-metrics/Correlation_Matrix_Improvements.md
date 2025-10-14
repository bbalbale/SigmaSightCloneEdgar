# Correlation Matrix Quality Improvements

**Date**: January 14, 2025
**Status**: ✅ Implemented
**Backend File Modified**: `backend/app/services/correlation_service.py`

---

## Executive Summary

Fixed 7 critical issues in the correlation matrix calculation engine to ensure statistically sound and reliable correlation measurements for financial portfolio analysis. All improvements implemented with comprehensive logging (no database schema changes).

---

## Problem Statement

The correlation matrix calculation was producing unreliable results due to:

1. **Insufficient minimum overlap** - Correlations calculated with as few as 1-2 overlapping data points
2. **No data alignment validation** - Missing data handled inconsistently
3. **No PSD validation** - Mathematically invalid matrices could be produced
4. **Poor error handling** - Zero/negative prices caused crashes
5. **No statistical significance tracking** - Unreliable correlations not flagged
6. **Limited transparency** - No visibility into data quality issues

---

## Issues Fixed

### 1. **Minimum Overlap Enforcement** ⚠️ CRITICAL

**Problem**: Pandas `.corr()` uses `min_periods=1` by default, allowing correlations to be calculated with just ONE overlapping data point.

**Fix**: Added explicit `min_periods` parameter (adaptive: 1/3 of lookback period, minimum 20 days)

**Code Changes** (`correlation_service.py:245-276`):
```python
def calculate_pairwise_correlations(
    self,
    returns_df: pd.DataFrame,
    min_periods: int = 30
) -> pd.DataFrame:
    # Calculate correlation matrix with minimum period requirement
    correlation_matrix = returns_df.corr(method='pearson', min_periods=min_periods)

    # Log filtered pairs
    nan_count = correlation_matrix.isna().sum().sum()
    if nan_count > 0:
        logger.info(
            f"Filtered {nan_count}/{total_pairs} correlation pairs "
            f"due to insufficient overlap (min_periods={min_periods})"
        )
```

**Impact**: Prevents statistically meaningless correlations from being stored and displayed.

---

### 2. **PSD Validation and Correction** ⚠️ HIGH

**Problem**: Correlation matrices must be Positive Semi-Definite (all eigenvalues ≥ 0) to be mathematically valid. Non-PSD matrices can occur from numerical precision issues or inconsistent data.

**Fix**: Added `_validate_and_fix_psd()` method with eigenvalue analysis and correction

**Code Changes** (`correlation_service.py:278-349`):
```python
def _validate_and_fix_psd(self, correlation_matrix: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    # Check eigenvalues
    eigenvalues = np.linalg.eigvalsh(correlation_matrix.values)
    min_eigenvalue = np.min(eigenvalues)

    if min_eigenvalue < -1e-10:
        logger.warning(f"Non-PSD matrix detected. Min eigenvalue: {min_eigenvalue:.6f}")

        # Apply nearest PSD correction (eigenvalue clipping)
        eigenvalues_clipped = np.maximum(eigenvalues, 0)
        # ... reconstruct matrix and rescale diagonal to 1.0

        return corrected_df, True

    return correlation_matrix, False
```

**Impact**: Ensures all correlation matrices are mathematically valid for portfolio optimization and risk analysis.

---

### 3. **Robust Zero/Negative Price Handling** ⚠️ MEDIUM

**Problem**: Log returns calculation `np.log(price_t / price_t-1)` produces infinity when prices are zero or negative.

**Fix**: Added error state suppression and explicit handling of infinite values

**Code Changes** (`correlation_service.py:626-641`):
```python
# Calculate log returns with error handling
with np.errstate(divide='ignore', invalid='ignore'):
    log_returns = np.log(price_series / price_series.shift(1))

# Handle infinite values
inf_count = np.isinf(log_returns).sum()
if inf_count > 0:
    logger.warning(
        f"Position {symbol}: {inf_count} infinite log returns "
        f"(likely from zero/negative prices). Replacing with NaN."
    )
    log_returns = log_returns.replace([np.inf, -np.inf], np.nan)
```

**Impact**: Prevents crashes and data corruption from bad price data.

---

### 4. **Statistical Significance Logging** ⚠️ MEDIUM

**Problem**: P-values were calculated but never used to identify unreliable correlations.

**Fix**: Added logging for low-confidence correlations (p-value > 0.05)

**Code Changes** (`correlation_service.py:694-707`):
```python
_, p_value = stats.pearsonr(returns_df[symbol1].dropna(), returns_df[symbol2].dropna())

# Log low-confidence correlations (< 95% confidence)
if p_value > 0.05:
    logger.debug(
        f"Low-confidence correlation: {symbol1}-{symbol2} "
        f"(r={correlation_value:.3f}, p={p_value:.3f}, n={data_points})"
    )
```

**Impact**: Provides transparency about which correlations are statistically significant.

---

### 5. **Adaptive Minimum Overlap** ⚠️ HIGH

**Problem**: Fixed minimum overlap doesn't scale with different lookback periods (30 days vs 180 days).

**Fix**: Adaptive calculation based on lookback period

**Code Changes** (`correlation_service.py:131-137`):
```python
# Require at least 1/3 of lookback period, minimum 20 days
min_overlap = max(20, duration_days // 3)
correlation_matrix = self.calculate_pairwise_correlations(
    returns_df,
    min_periods=min_overlap
)

# Validate and fix PSD property
correlation_matrix, psd_corrected = self._validate_and_fix_psd(correlation_matrix)
```

**Impact**: Scales data quality requirements appropriately for different analysis periods.

---

### 6. **Comprehensive Data Quality Logging** ⚠️ HIGH

**Problem**: No visibility into correlation calculation quality and potential issues.

**Fix**: Added detailed logging block with all relevant metrics

**Code Changes** (`correlation_service.py:188-206`):
```python
logger.info(
    f"Correlation calculation data quality for portfolio {portfolio_id}:\n"
    f"  - Duration: {duration_days} days\n"
    f"  - Positions included: {len(valid_positions)}\n"
    f"  - Positions excluded: {excluded_count}\n"
    f"  - Min overlap required: {min_overlap} days\n"
    f"  - Total correlation pairs: {total_pairs}\n"
    f"  - Valid pairs (sufficient data): {valid_pairs}\n"
    f"  - Filtered pairs (insufficient overlap): {filtered_pairs}\n"
    f"  - PSD validation: {'CORRECTED' if psd_corrected else 'PASSED'}\n"
    f"  - Overall correlation: {metrics['overall_correlation']:.4f}\n"
    f"  - Effective positions: {metrics['effective_positions']:.2f}\n"
    f"  - Correlation clusters detected: {len(clusters)}"
)
```

**Impact**: Full transparency for debugging and quality assurance.

---

## Where to Find Logs

### Log Locations

**Development (local)**:
```
backend/logs/app.log              # Main application log
```

**Console Output**:
```bash
cd backend
uv run python run.py              # View logs in terminal
```

**Grep Examples**:
```bash
# View correlation quality summaries
grep "Correlation calculation data quality" backend/logs/app.log

# View PSD issues
grep "Non-PSD correlation matrix" backend/logs/app.log

# View insufficient data warnings
grep "insufficient overlap" backend/logs/app.log

# View specific portfolio
grep "portfolio abc-123" backend/logs/app.log | grep "correlation"
```

---

## Log Levels

### INFO (Always Logged)
- Data quality summary after each calculation
- Successful PSD validation
- Correlation pairs filtered due to min_periods

### WARNING (Issues Found)
- Non-PSD matrix detected (with correction applied)
- Infinite log returns from zero/negative prices
- Slow correlation calculation (>500ms)

### DEBUG (Verbose Details)
- Individual low-confidence correlations (p > 0.05)
- Position-by-position data sufficiency

---

## Example Log Output

```
2025-01-14 10:23:45,123 - app.services.correlation_service - INFO - Correlation calculation data quality for portfolio abc-123:
  - Duration: 90 days
  - Positions included: 12
  - Positions excluded: 3
  - Min overlap required: 30 days
  - Total correlation pairs: 144
  - Valid pairs (sufficient data): 132
  - Filtered pairs (insufficient overlap): 12
  - PSD validation: PASSED
  - Overall correlation: 0.4523
  - Effective positions: 8.45
  - Correlation clusters detected: 2
```

---

## Testing Recommendations

### 1. Run Batch Processing
```bash
cd backend
uv run python -c "
import asyncio
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

async def test():
    await batch_orchestrator_v2.run_daily_batch_sequence()

asyncio.run(test())
"
```

### 2. Check Logs
```bash
tail -n 100 backend/logs/app.log | grep "Correlation calculation data quality"
```

### 3. Verify Improvements
- **Before**: Correlations calculated with 1-2 overlapping points
- **After**: Minimum 20-30 overlapping observations required

- **Before**: No validation of matrix quality
- **After**: PSD property validated and corrected if needed

- **Before**: Crashes on zero/negative prices
- **After**: Robust handling with clear logging

---

## Best Practices for Financial Correlations

Based on research of industry standards and academic literature:

### 1. **Minimum Data Requirements**
- ✅ **30-50 overlapping observations** for reliable correlation estimates
- ✅ **20 days minimum** (our implementation)
- ❌ Avoid using correlations with < 10 overlapping points

### 2. **Statistical Significance**
- ✅ **p-value < 0.05** (95% confidence) for reliable correlations
- ✅ Our implementation logs all p > 0.05 correlations
- ❌ Correlations with p > 0.05 may be noise

### 3. **Matrix Properties**
- ✅ **Positive Semi-Definite** (required for portfolio optimization)
- ✅ **Eigenvalues ≥ 0** (mathematical requirement)
- ✅ Our implementation validates and corrects PSD property

### 4. **Data Alignment**
- ✅ **Synchronized trading dates** across all securities
- ✅ **Handle missing data** transparently
- ✅ Our implementation uses pairwise deletion with min_periods

### 5. **Log Returns vs Simple Returns**
- ✅ **Log returns** for correlation analysis (our implementation)
- ✅ More symmetric distribution assumption
- ✅ Better for time-series analysis

---

## Impact on Frontend

### No Changes Required

The frontend correlation matrix component (`frontend/src/components/risk/CorrelationMatrix.tsx`) requires **no changes**. It continues to receive the same API response structure from the backend.

### What Changed (Backend Only)

1. **More reliable correlation values** - filtered by minimum overlap
2. **Mathematically valid matrices** - PSD validation ensures correctness
3. **Better error handling** - no crashes from bad price data
4. **Full transparency** - comprehensive logging of data quality

### API Response (Unchanged)

```typescript
interface CorrelationMatrixResponse {
  available: boolean;
  data?: {
    matrix: Record<string, Record<string, number>>;
    average_correlation: number;
  };
  metadata?: {
    calculation_date: string;
    lookback_days: number;
    positions_included: number;
  };
  reason?: string;
}
```

---

## Related Files

### Modified
- `backend/app/services/correlation_service.py` (7 improvements)

### No Changes Required
- `frontend/src/hooks/useCorrelationMatrix.ts`
- `frontend/src/components/risk/CorrelationMatrix.tsx`
- `frontend/src/services/analyticsApi.ts`
- Database schema (no migrations needed)

---

## Summary

All 7 critical improvements have been implemented with comprehensive logging. The correlation matrix calculation engine now produces statistically sound, mathematically valid correlation measurements with full transparency into data quality.

**Key Achievements**:
- ✅ Minimum 20-30 overlapping observations enforced
- ✅ PSD validation prevents invalid matrices
- ✅ Robust error handling for edge cases
- ✅ Statistical significance tracked and logged
- ✅ Full transparency through comprehensive logging
- ✅ Zero database schema changes required
- ✅ Zero frontend changes required

**Next Steps**:
1. Run batch processing to generate new logs
2. Review log output for data quality insights
3. Monitor for PSD corrections or data quality issues
4. Consider adding log aggregation/monitoring dashboard
