"""
Constants for factor analysis calculations
"""

# Factor calculation parameters
REGRESSION_WINDOW_DAYS = 150  # Adjusted for FMP API data availability (was 252 - ~12 months, ~6 months trading days)
MIN_REGRESSION_DAYS = 60      # 3-month minimum data requirement
BETA_CAP_LIMIT = 3.0         # Cap factor betas at ±3 to prevent outliers

# Batch processing parameters
POSITION_CHUNK_SIZE = 1000   # Process positions in chunks for large portfolios

# Data quality flags
QUALITY_FLAG_FULL_HISTORY = "full_history"
QUALITY_FLAG_LIMITED_HISTORY = "limited_history"

# Factor ETF symbols (7-factor model for V1.4)
FACTOR_ETFS = {
    "Market": "SPY",       # Market factor
    "Value": "VTV",        # Value factor
    "Growth": "VUG",       # Growth factor
    "Momentum": "MTUM",    # Momentum factor
    "Quality": "QUAL",     # Quality factor
    "Size": "IWM",         # Size factor (Russell 2000 small-cap index)
    "Low Volatility": "USMV"  # Low Volatility factor
}

# Factor types
FACTOR_TYPE_STYLE = "style"
FACTOR_TYPE_SECTOR = "sector"
FACTOR_TYPE_MACRO = "macro"

# APScheduler job configuration
FACTOR_JOB_SCHEDULE = "0 17 15 * * *"  # 5:15 PM daily (cron format)
FACTOR_JOB_ID = "calculate_factor_exposures"
FACTOR_JOB_NAME = "Factor Exposure Calculation"

# Cache configuration
DEFAULT_FACTOR_CACHE_TTL = 86400  # 24 hours in seconds

# Calculation timeouts
DEFAULT_FACTOR_CALCULATION_TIMEOUT = 60  # seconds per portfolio
BATCH_FACTOR_CALCULATION_TIMEOUT = 900   # 15 minutes for batch processing

# Options multiplier
OPTIONS_MULTIPLIER = 100  # Standard options contract multiplier

# Error messages
ERROR_INSUFFICIENT_DATA = "Insufficient historical data for factor calculation"
ERROR_NO_POSITIONS = "No positions found for portfolio"
ERROR_CALCULATION_FAILED = "Factor calculation failed"
ERROR_INVALID_DATE_RANGE = "Invalid date range for factor calculation"