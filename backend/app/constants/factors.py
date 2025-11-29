"""
Constants for factor analysis calculations

See factor_utils.py for complete architecture documentation.
"""

# Factor calculation parameters
REGRESSION_WINDOW_DAYS = 90   # ~3 months of data for factor regression (reduced from 150 for faster calculations)
MIN_REGRESSION_DAYS = 30      # Minimum 30 days for market beta regression
BETA_CAP_LIMIT = 5.0         # Cap market betas at ±5 to prevent extreme outliers

# Batch processing parameters
POSITION_CHUNK_SIZE = 1000   # Process positions in chunks for large portfolios

# Data quality flags
QUALITY_FLAG_FULL_HISTORY = "full_history"
QUALITY_FLAG_LIMITED_HISTORY = "limited_history"
QUALITY_FLAG_NO_PUBLIC_POSITIONS = "no_public_positions"  # Phase 8.1 Task 4: All PUBLIC positions filtered out

# ================================================================================
# FACTOR ETF SYMBOLS - Master list of all factor proxies
# ================================================================================
# This is the MASTER LIST of all factor ETF proxies used across the system.
# Different calculation modules filter this list for their specific needs:
#
#   factors_ridge.py:       Uses 6 style factors (excludes Market, Interest Rate)
#   market_beta.py:         Uses Market (SPY) only
#   interest_rate_beta.py:  Uses Interest Rate (TLT) only
#   factors_spread.py:      Uses pairs from SPREAD_FACTORS below
#
FACTOR_ETFS = {
    # Market factor - calculated separately by market_beta.py
    "Market": "SPY",

    # 6 Style factors - calculated by factors_ridge.py (Ridge regression)
    "Value": "VTV",
    "Growth": "VUG",
    "Momentum": "MTUM",
    "Quality": "QUAL",
    "Size": "IWM",
    "Low Volatility": "USMV",

    # Macro factor - calculated separately by interest_rate_beta.py
    "Interest Rate": "TLT"
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

# Spread factor definitions (180-day regression window)
SPREAD_REGRESSION_WINDOW_DAYS = 180  # 6 months for better statistical power
SPREAD_MIN_REGRESSION_DAYS = 60      # Minimum 60 days required for spread factor regression

# Spread factors - long-short factor spreads to eliminate multicollinearity
SPREAD_FACTORS = {
    "Growth-Value Spread": ("VUG", "VTV"),  # Long Growth, Short Value
    "Momentum Spread": ("MTUM", "SPY"),     # Long Momentum, Short Market
    "Size Spread": ("IWM", "SPY"),          # Long Small Cap, Short Large Cap
    "Quality Spread": ("QUAL", "SPY")       # Long Quality, Short Market
}

# Interpretation thresholds for spread betas
SPREAD_BETA_THRESHOLDS = {
    'strong': 0.5,      # |beta| > 0.5 = strong tilt
    'moderate': 0.2,    # 0.2 < |beta| <= 0.5 = moderate tilt
    'neutral': 0.2      # |beta| <= 0.2 = neutral/balanced
}

# Error messages
ERROR_INSUFFICIENT_DATA = "Insufficient historical data for factor calculation"
ERROR_NO_POSITIONS = "No positions found for portfolio"
ERROR_CALCULATION_FAILED = "Factor calculation failed"
ERROR_INVALID_DATE_RANGE = "Invalid date range for factor calculation"