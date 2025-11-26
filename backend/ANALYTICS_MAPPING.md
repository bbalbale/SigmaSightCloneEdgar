# Analytics Bundle - Correct Service/Function Mapping

## Overview Metrics
- **Service**: `PortfolioAnalyticsService()`
- **Method**: `get_portfolio_overview(db, portfolio_id)`
- **Returns**: Dict with portfolio overview data
- **Source**: `app/api/v1/analytics/portfolio.py` line 91-92

## Sector Exposure
- **Function**: `calculate_sector_exposure(db, portfolio_id)`
- **Import**: `from app.calculations.sector_analysis import calculate_sector_exposure`
- **Returns**: Dict with 'success', 'portfolio_weights', 'benchmark_weights', etc.
- **Source**: `app/api/v1/analytics/portfolio.py` line 431-432

## Concentration Metrics
- **Function**: `calculate_concentration_metrics(db, portfolio_id)`
- **Import**: `from app.calculations.sector_analysis import calculate_concentration_metrics`
- **Returns**: Dict with 'success', 'hhi', 'effective_num_positions', etc.
- **Source**: `app/api/v1/analytics/portfolio.py` line 520-521

## Volatility Metrics
- **Need to check volatility endpoint**

## Factor Exposures
- **Service**: `FactorExposureService(db)`
- **Method**: Need to check actual method name

## Correlation Matrix
- **Service**: `CorrelationService(db)`
- **Method**: `get_matrix(portfolio_id, lookback_days, min_overlap, max_symbols)`
- **Source**: `app/api/v1/analytics/portfolio.py` line 143-144

## Stress Test
- **Service**: `StressTestService()`
- **Method**: Need to check actual method name
