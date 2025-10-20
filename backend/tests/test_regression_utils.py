"""
Test suite for regression_utils.py
Tests OLS regression wrapper, R² classification, and significance classification

Created: 2025-10-20 (Calculation Consolidation Refactor)
Follows: TDD approach - tests written before implementation
"""
import pytest
import numpy as np
import pandas as pd
from decimal import Decimal

from app.calculations.regression_utils import (
    run_single_factor_regression,
    classify_r_squared,
    classify_significance,
)


# ============================================================================
# SECTION 1: Test run_single_factor_regression()
# ============================================================================

class TestRunSingleFactorRegression:
    """Test the OLS regression wrapper with various scenarios"""

    def test_perfect_linear_relationship(self):
        """Test regression with perfect linear relationship (R² = 1.0)"""
        # y = 2x + 1 (perfect linear relationship)
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 2.0 * x + 1.0

        result = run_single_factor_regression(y, x)

        assert result['success'] is True
        assert abs(result['beta'] - 2.0) < 0.0001
        assert abs(result['alpha'] - 1.0) < 0.0001
        assert abs(result['r_squared'] - 1.0) < 0.0001
        assert result['is_significant'] is True

    def test_no_relationship(self):
        """Test regression with no relationship (R² ≈ 0)"""
        # Random uncorrelated data
        np.random.seed(42)
        x = np.random.randn(100)
        y = np.random.randn(100)  # Independent of x

        result = run_single_factor_regression(y, x)

        assert result['success'] is True
        assert abs(result['beta']) < 0.3  # Should be near zero
        assert result['r_squared'] < 0.1  # Very low R²
        assert result['is_significant'] is False  # p-value should be high

    def test_negative_beta(self):
        """Test regression with negative relationship"""
        # y = -1.5x + 10
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        y = -1.5 * x + 10.0

        result = run_single_factor_regression(y, x)

        assert result['success'] is True
        assert abs(result['beta'] - (-1.5)) < 0.0001
        assert result['beta'] < 0  # Negative relationship

    def test_beta_capping_positive(self):
        """Test beta capping for extreme positive values"""
        # Simulate extreme positive beta scenario
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 15.0 * x + 1.0  # Beta would be 15.0 without capping

        result = run_single_factor_regression(y, x, cap=5.0)

        assert result['success'] is True
        assert result['beta'] == 5.0  # Should be capped at 5.0
        assert result['capped'] is True
        assert result['original_beta'] == pytest.approx(15.0, abs=0.01)

    def test_beta_capping_negative(self):
        """Test beta capping for extreme negative values"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = -15.0 * x + 1.0  # Beta would be -15.0 without capping

        result = run_single_factor_regression(y, x, cap=5.0)

        assert result['success'] is True
        assert result['beta'] == -5.0  # Should be capped at -5.0
        assert result['capped'] is True
        assert result['original_beta'] == pytest.approx(-15.0, abs=0.01)

    def test_no_capping_when_within_limit(self):
        """Test that beta is not capped when within limits"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 2.0 * x + 1.0  # Beta = 2.0, well within cap

        result = run_single_factor_regression(y, x, cap=5.0)

        assert result['success'] is True
        assert abs(result['beta'] - 2.0) < 0.0001
        assert result['capped'] is False

    def test_disable_capping(self):
        """Test that capping can be disabled"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 15.0 * x + 1.0  # Extreme beta

        result = run_single_factor_regression(y, x, cap=None)

        assert result['success'] is True
        assert abs(result['beta'] - 15.0) < 0.01  # Not capped
        assert result['capped'] is False

    def test_confidence_level_strict(self):
        """Test significance with strict confidence (5%)"""
        # Generate data with weak relationship
        np.random.seed(42)
        x = np.linspace(0, 10, 50)
        y = 0.3 * x + np.random.randn(50) * 2  # Noisy relationship

        result = run_single_factor_regression(y, x, confidence=0.05)

        assert result['success'] is True
        assert 'is_significant' in result
        # With strict threshold, weak relationships may not be significant

    def test_confidence_level_relaxed(self):
        """Test significance with relaxed confidence (10%)"""
        np.random.seed(42)
        x = np.linspace(0, 10, 50)
        y = 0.3 * x + np.random.randn(50) * 2

        result = run_single_factor_regression(y, x, confidence=0.10)

        assert result['success'] is True
        assert 'is_significant' in result

    def test_return_minimal_output(self):
        """Test return_diagnostics=False for minimal output"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 2.0 * x + 1.0

        result = run_single_factor_regression(y, x, return_diagnostics=False)

        # Should have essential fields
        assert 'beta' in result
        assert 'alpha' in result
        assert 'r_squared' in result
        # Should not have extended diagnostics
        assert 'std_error' not in result or result.get('std_error') is None

    def test_return_full_diagnostics(self):
        """Test return_diagnostics=True for complete output"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 2.0 * x + 1.0

        result = run_single_factor_regression(y, x, return_diagnostics=True)

        # Should have all diagnostic fields
        assert 'beta' in result
        assert 'alpha' in result
        assert 'r_squared' in result
        assert 'std_error' in result
        assert 'p_value' in result
        assert 'is_significant' in result
        assert 'observations' in result

    def test_insufficient_data(self):
        """Test regression with too few data points"""
        x = np.array([1.0, 2.0])  # Only 2 points
        y = np.array([2.0, 4.0])

        # Should still work but with warnings
        result = run_single_factor_regression(y, x)

        assert result['success'] is True  # Can technically run, but not reliable
        assert result['observations'] == 2

    def test_mismatched_array_lengths(self):
        """Test error handling for mismatched array lengths"""
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([2.0, 4.0])  # Different length

        with pytest.raises(ValueError):
            run_single_factor_regression(y, x)

    def test_nan_values_in_data(self):
        """Test error handling for NaN values"""
        x = np.array([1.0, 2.0, np.nan, 4.0])
        y = np.array([2.0, 4.0, 6.0, 8.0])

        with pytest.raises(ValueError):
            run_single_factor_regression(y, x)

    def test_real_market_data_scenario(self):
        """Test with realistic market returns data"""
        # Simulate stock returns (y) vs market returns (x)
        np.random.seed(123)
        days = 90
        market_returns = np.random.randn(days) * 0.01  # 1% daily volatility
        stock_beta = 1.2
        alpha = 0.0002  # Small positive alpha
        idiosyncratic_vol = 0.005

        stock_returns = alpha + stock_beta * market_returns + np.random.randn(days) * idiosyncratic_vol

        result = run_single_factor_regression(stock_returns, market_returns, cap=5.0)

        assert result['success'] is True
        assert 1.0 < result['beta'] < 1.5  # Should be close to 1.2
        assert result['r_squared'] > 0.5  # Should have decent fit
        assert result['is_significant'] is True


# ============================================================================
# SECTION 2: Test classify_r_squared()
# ============================================================================

class TestClassifyRSquared:
    """Test R² classification logic"""

    def test_excellent_r_squared(self):
        """Test classification of excellent R² (≥ 0.70)"""
        result = classify_r_squared(0.85)

        assert result['quality'] == 'excellent'
        assert result['variance_explained_pct'] == 85.0
        assert result['idiosyncratic_risk_pct'] == 15.0
        assert result['r_squared'] == 0.85
        assert 'interpretation' in result

    def test_good_r_squared(self):
        """Test classification of good R² (0.50 - 0.70)"""
        result = classify_r_squared(0.60)

        assert result['quality'] == 'good'
        assert result['variance_explained_pct'] == 60.0
        assert result['idiosyncratic_risk_pct'] == 40.0

    def test_fair_r_squared(self):
        """Test classification of fair R² (0.30 - 0.50)"""
        result = classify_r_squared(0.42)

        assert result['quality'] == 'fair'
        assert result['variance_explained_pct'] == 42.0
        assert result['idiosyncratic_risk_pct'] == 58.0

    def test_poor_r_squared(self):
        """Test classification of poor R² (0.10 - 0.30)"""
        result = classify_r_squared(0.18)

        assert result['quality'] == 'poor'
        assert result['variance_explained_pct'] == 18.0
        assert result['idiosyncratic_risk_pct'] == 82.0

    def test_very_poor_r_squared(self):
        """Test classification of very poor R² (< 0.10)"""
        result = classify_r_squared(0.05)

        assert result['quality'] == 'very_poor'
        assert result['variance_explained_pct'] == 5.0
        assert result['idiosyncratic_risk_pct'] == 95.0

    def test_perfect_r_squared(self):
        """Test classification of perfect R² (1.0)"""
        result = classify_r_squared(1.0)

        assert result['quality'] == 'excellent'
        assert result['variance_explained_pct'] == 100.0
        assert result['idiosyncratic_risk_pct'] == 0.0

    def test_zero_r_squared(self):
        """Test classification of zero R² (0.0)"""
        result = classify_r_squared(0.0)

        assert result['quality'] == 'very_poor'
        assert result['variance_explained_pct'] == 0.0
        assert result['idiosyncratic_risk_pct'] == 100.0

    def test_boundary_values(self):
        """Test exact threshold boundaries"""
        # Test at exact threshold values
        assert classify_r_squared(0.70)['quality'] == 'excellent'
        assert classify_r_squared(0.69)['quality'] == 'good'
        assert classify_r_squared(0.50)['quality'] == 'good'
        assert classify_r_squared(0.49)['quality'] == 'fair'
        assert classify_r_squared(0.30)['quality'] == 'fair'
        assert classify_r_squared(0.29)['quality'] == 'poor'
        assert classify_r_squared(0.10)['quality'] == 'poor'
        assert classify_r_squared(0.09)['quality'] == 'very_poor'


# ============================================================================
# SECTION 3: Test classify_significance()
# ============================================================================

class TestClassifySignificance:
    """Test statistical significance classification"""

    def test_highly_significant(self):
        """Test p-value < 0.01 (highly significant)"""
        result = classify_significance(0.005, strict=True)

        assert result['is_significant'] is True
        assert result['confidence_level'] == '***'
        assert result['p_value'] == 0.005
        assert result['threshold'] == 0.05
        assert 'highly significant' in result['interpretation']

    def test_significant(self):
        """Test 0.01 < p-value < 0.05 (significant)"""
        result = classify_significance(0.03, strict=True)

        assert result['is_significant'] is True
        assert result['confidence_level'] == '**'
        assert 'significant' in result['interpretation']

    def test_marginally_significant(self):
        """Test 0.05 < p-value < 0.10 (marginally significant)"""
        result = classify_significance(0.08, strict=False)

        # With relaxed threshold (0.10), this should be significant
        assert result['is_significant'] is True
        assert result['confidence_level'] == '*'
        assert 'marginally significant' in result['interpretation']

    def test_not_significant(self):
        """Test p-value ≥ 0.10 (not significant)"""
        result = classify_significance(0.15, strict=False)

        assert result['is_significant'] is False
        assert result['confidence_level'] == 'ns'
        assert 'not significant' in result['interpretation']

    def test_strict_threshold(self):
        """Test strict threshold (0.05) classification"""
        # p-value = 0.08 should be NOT significant with strict threshold
        result = classify_significance(0.08, strict=True)

        assert result['is_significant'] is False
        assert result['threshold'] == 0.05

    def test_relaxed_threshold(self):
        """Test relaxed threshold (0.10) classification"""
        # p-value = 0.08 should be significant with relaxed threshold
        result = classify_significance(0.08, strict=False)

        assert result['is_significant'] is True
        assert result['threshold'] == 0.10

    def test_threshold_boundary_strict(self):
        """Test exact threshold boundaries for strict mode"""
        # At boundary (0.05)
        result_at = classify_significance(0.05, strict=True)
        result_below = classify_significance(0.049, strict=True)
        result_above = classify_significance(0.051, strict=True)

        assert result_below['is_significant'] is True
        assert result_above['is_significant'] is False

    def test_threshold_boundary_relaxed(self):
        """Test exact threshold boundaries for relaxed mode"""
        # At boundary (0.10)
        result_below = classify_significance(0.09, strict=False)
        result_above = classify_significance(0.11, strict=False)

        assert result_below['is_significant'] is True
        assert result_above['is_significant'] is False

    def test_perfect_significance(self):
        """Test p-value very close to 0"""
        result = classify_significance(0.0001, strict=True)

        assert result['is_significant'] is True
        assert result['confidence_level'] == '***'

    def test_no_significance(self):
        """Test p-value very high"""
        result = classify_significance(0.95, strict=False)

        assert result['is_significant'] is False
        assert result['confidence_level'] == 'ns'


# ============================================================================
# SECTION 4: Integration Tests
# ============================================================================

class TestRegressionUtilsIntegration:
    """Integration tests combining multiple functions"""

    def test_full_regression_with_classification(self):
        """Test complete regression workflow with classification"""
        # Generate data with good fit
        np.random.seed(42)
        x = np.linspace(0, 10, 100)
        y = 2.5 * x + 1.0 + np.random.randn(100) * 0.5

        # Run regression
        reg_result = run_single_factor_regression(y, x, cap=5.0, confidence=0.10)

        # Classify results
        r2_class = classify_r_squared(reg_result['r_squared'])
        sig_class = classify_significance(reg_result['p_value'], strict=False)

        # Validate complete workflow
        assert reg_result['success'] is True
        assert r2_class['quality'] in ['excellent', 'good']  # Should have good fit
        assert sig_class['is_significant'] is True  # Should be significant
        assert reg_result['beta'] > 0  # Positive relationship

    def test_regression_with_poor_fit(self):
        """Test workflow with data that has poor fit"""
        np.random.seed(123)
        x = np.random.randn(50)
        y = np.random.randn(50)  # No relationship

        reg_result = run_single_factor_regression(y, x)
        r2_class = classify_r_squared(reg_result['r_squared'])
        sig_class = classify_significance(reg_result['p_value'])

        # Poor fit should be detected
        assert r2_class['quality'] in ['poor', 'very_poor']
        assert sig_class['is_significant'] is False
