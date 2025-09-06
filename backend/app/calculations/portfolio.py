"""Portfolio aggregation calculations for SigmaSight.

This module provides functions for aggregating portfolio-level metrics from
individual positions. All functions accept pre-calculated values from Section 1.4.1
and 1.4.2, and do NOT recalculate market values or exposures.

Key Design Decisions:
- Use pre-calculated values (no recalculation)
- Return Decimal types (convert to float at API layer)
- Handle edge cases gracefully (empty portfolios, missing data)
- Use pandas for performance with large portfolios
- Cache results with 60-second TTL
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from functools import lru_cache, wraps
from datetime import datetime, timedelta
import logging
from app.core.datetime_utils import utc_now, to_utc_iso8601

from app.constants.portfolio import (
    OPTIONS_POSITION_TYPES,
    STOCK_POSITION_TYPES,
    TAG_MODE_ANY,
    TAG_MODE_ALL,
    AGGREGATION_CACHE_TTL,
    MONETARY_DECIMAL_PLACES,
    GREEKS_DECIMAL_PLACES
)

# Configure logging
logger = logging.getLogger(__name__)


def timed_lru_cache(seconds: int = AGGREGATION_CACHE_TTL, maxsize: int = 128):
    """LRU cache decorator with time-based expiration.
    
    Args:
        seconds: Cache TTL in seconds
        maxsize: Maximum number of cached results
    
    Returns:
        Decorated function with time-based LRU cache
    """
    def wrapper_cache(func):
        # Store the original function with LRU cache
        func = lru_cache(maxsize=maxsize)(func)
        # Track when cache was last cleared
        func._last_clear = utc_now()
        
        @wraps(func)
        def wrapper_func(*args, **kwargs):
            # Check if cache needs to be cleared
            if utc_now() - func._last_clear > timedelta(seconds=seconds):
                func.cache_clear()
                func._last_clear = utc_now()
            return func(*args, **kwargs)
        
        # Expose cache_info and cache_clear methods
        wrapper_func.cache_info = func.cache_info
        wrapper_func.cache_clear = func.cache_clear
        
        return wrapper_func
    return wrapper_cache


def calculate_portfolio_exposures(positions: List[Dict]) -> Dict[str, Any]:
    """Calculate portfolio exposure metrics from pre-calculated position values.
    
    This function aggregates exposure metrics across all positions. It does NOT
    recalculate market values or exposures - these must be pre-calculated by
    Section 1.4.1 functions.
    
    Args:
        positions: List of position dictionaries with pre-calculated fields:
            - market_value: Decimal (already calculated)
            - exposure: Decimal (already calculated, signed by position)
            - position_type: str ("LONG", "SHORT", "LC", "LP", "SC", "SP")
            - quantity: Decimal (for notional calculation)
            
    Returns:
        Dict containing:
            - gross_exposure: Sum of absolute exposures
            - net_exposure: Sum of signed exposures
            - long_exposure: Sum of positive exposures
            - short_exposure: Sum of negative exposures (stored as negative)
            - long_count: Number of long positions
            - short_count: Number of short positions
            - options_exposure: Exposure from options only
            - stock_exposure: Exposure from stocks only
            - notional: Sum of abs(quantity × price × multiplier)
            
    Example:
        >>> positions = [
        ...     {"exposure": Decimal("10000"), "position_type": "LONG", ...},
        ...     {"exposure": Decimal("-5000"), "position_type": "SHORT", ...}
        ... ]
        >>> calculate_portfolio_exposures(positions)
        {
            "gross_exposure": Decimal("15000.00"),
            "net_exposure": Decimal("5000.00"),
            "long_exposure": Decimal("10000.00"),
            "short_exposure": Decimal("-5000.00"),
            ...
        }
    """
    # Handle empty portfolio
    if not positions:
        logger.info("Calculating exposures for empty portfolio")
        return {
            "gross_exposure": Decimal("0.00"),
            "net_exposure": Decimal("0.00"),
            "long_exposure": Decimal("0.00"),
            "short_exposure": Decimal("0.00"),
            "long_count": 0,
            "short_count": 0,
            "options_exposure": Decimal("0.00"),
            "stock_exposure": Decimal("0.00"),
            "notional": Decimal("0.00"),
            "metadata": {
                "calculated_at": to_utc_iso8601(utc_now()),
                "position_count": 0,
                "warnings": ["Empty portfolio - all values are zero"]
            }
        }
    
    # If passed a dict (e.g., {"positions": [...], "warnings": [...]}) use the list under 'positions'
    if isinstance(positions, dict):
        logger.error(
            "calculate_portfolio_exposures received a dict instead of a list; "
            "falling back to positions=list under 'positions' key"
        )
        positions = positions.get("positions", [])
    
    # Convert to DataFrame for efficient calculations
    df = pd.DataFrame(positions)
    logger.debug(f"Exposure DF constructed with columns={list(df.columns)} and rows={len(df)}")
    
    # Normalize position_type to string code (handles Enum values like PositionType.LC)
    if 'position_type' in df.columns:
        df['position_type'] = df['position_type'].apply(lambda x: getattr(x, 'value', x))
    
    # Ensure numeric types and handle missing columns
    df['exposure'] = df['exposure'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal("0"))
    
    # Handle missing market_value column
    if 'market_value' not in df.columns:
        df['market_value'] = df['exposure'].apply(abs)
    else:
        df['market_value'] = df['market_value'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal("0"))
    
    # Calculate exposures
    gross_exposure = df['exposure'].apply(abs).sum()
    net_exposure = df['exposure'].sum()
    
    # Long/short exposures
    long_mask = df['exposure'] > 0
    short_mask = df['exposure'] < 0
    
    long_exposure = df.loc[long_mask, 'exposure'].sum() if long_mask.any() else Decimal("0")
    short_exposure = df.loc[short_mask, 'exposure'].sum() if short_mask.any() else Decimal("0")
    
    # Position counts
    long_count = int(long_mask.sum())
    short_count = int(short_mask.sum())
    
    # Options vs stocks exposure
    options_mask = df['position_type'].isin(OPTIONS_POSITION_TYPES)
    stocks_mask = df['position_type'].isin(STOCK_POSITION_TYPES)
    
    options_exposure = df.loc[options_mask, 'exposure'].apply(abs).sum() if options_mask.any() else Decimal("0")
    stock_exposure = df.loc[stocks_mask, 'exposure'].apply(abs).sum() if stocks_mask.any() else Decimal("0")
    
    # Notional exposure (sum of absolute market values)
    notional = df['market_value'].apply(abs).sum()
    
    # Build response with proper decimal precision
    result = {
        "gross_exposure": gross_exposure.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "net_exposure": net_exposure.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "long_exposure": long_exposure.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "short_exposure": short_exposure.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "long_count": long_count,
        "short_count": short_count,
        "options_exposure": options_exposure.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "stock_exposure": stock_exposure.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "notional": notional.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "metadata": {
            "calculated_at": to_utc_iso8601(utc_now()),
            "position_count": len(positions),
            "warnings": []
        }
    }
    
    logger.info(f"Calculated portfolio exposures for {len(positions)} positions")
    return result


def aggregate_portfolio_greeks(positions: List[Dict]) -> Dict[str, Decimal]:
    """Aggregate portfolio-level Greeks from individual positions.
    
    This function sums Greeks across all positions that have Greeks data.
    Positions without Greeks (stocks or missing data) are skipped.
    
    Args:
        positions: List of position dictionaries with optional 'greeks' field:
            - greeks: Dict with delta, gamma, theta, vega, rho (or None)
            
    Returns:
        Dict with portfolio-level Greeks:
            - delta: Portfolio delta
            - gamma: Portfolio gamma  
            - theta: Portfolio theta
            - vega: Portfolio vega
            - rho: Portfolio rho
            
    Example:
        >>> positions = [
        ...     {"greeks": {"delta": Decimal("0.5"), "gamma": Decimal("0.1"), ...}},
        ...     {"greeks": None}  # Stock position, skipped
        ... ]
        >>> aggregate_portfolio_greeks(positions)
        {"delta": Decimal("0.5000"), "gamma": Decimal("0.1000"), ...}
    """
    # If passed a dict (e.g., {"positions": [...], "warnings": [...]}) use the list under 'positions'
    if isinstance(positions, dict):
        logger.error(
            "aggregate_portfolio_greeks received a dict instead of a list; "
            "falling back to positions=list under 'positions' key"
        )
        positions = positions.get("positions", [])

    # Initialize totals
    total_greeks = {
        "delta": Decimal("0"),
        "gamma": Decimal("0"),
        "theta": Decimal("0"),
        "vega": Decimal("0"),
        "rho": Decimal("0")
    }
    
    positions_with_greeks = 0
    positions_without_greeks = 0
    
    # Sum Greeks from positions that have them
    for position in positions:
        greeks = position.get("greeks")
        
        if greeks is None:
            positions_without_greeks += 1
            continue
            
        positions_with_greeks += 1
        
        # Add each Greek value
        for greek_name in total_greeks:
            if greek_name in greeks and greeks[greek_name] is not None:
                value = Decimal(str(greeks[greek_name]))
                total_greeks[greek_name] += value
    
    # Apply precision
    for greek_name in total_greeks:
        total_greeks[greek_name] = total_greeks[greek_name].quantize(
            Decimal(f"0.{'0' * GREEKS_DECIMAL_PLACES}")
        )
    
    # Add metadata
    total_greeks["metadata"] = {
        "calculated_at": to_utc_iso8601(utc_now()),
        "positions_with_greeks": positions_with_greeks,
        "positions_without_greeks": positions_without_greeks,
        "warnings": []
    }
    
    if positions_without_greeks > 0:
        total_greeks["metadata"]["warnings"].append(
            f"{positions_without_greeks} positions excluded from Greeks aggregation (no Greeks data)"
        )
    
    logger.info(f"Aggregated Greeks for {positions_with_greeks} positions "
                f"({positions_without_greeks} skipped)")
    
    return total_greeks


def calculate_delta_adjusted_exposure(positions: List[Dict]) -> Dict[str, Decimal]:
    """Calculate delta-adjusted exposure for the portfolio.
    
    For options: exposure × delta
    For stocks: exposure × 1.0 (long) or -1.0 (short)
    Positions without Greeks are skipped.
    
    Args:
        positions: List of position dictionaries with:
            - exposure: Decimal (pre-calculated)
            - greeks: Dict with delta (or None for stocks)
            - position_type: str
            
    Returns:
        Dict with:
            - raw_exposure: Sum of all exposures
            - delta_adjusted_exposure: Sum of delta-weighted exposures
            
    Example:
        >>> positions = [
        ...     {"exposure": Decimal("10000"), "greeks": {"delta": Decimal("0.5")}, ...},
        ...     {"exposure": Decimal("5000"), "greeks": None, "position_type": "LONG"}
        ... ]
        >>> calculate_delta_adjusted_exposure(positions)
        {"raw_exposure": Decimal("15000.00"), "delta_adjusted_exposure": Decimal("10000.00")}
    """
    if not positions:
        return {
            "raw_exposure": Decimal("0.00"),
            "delta_adjusted_exposure": Decimal("0.00"),
            "metadata": {
                "calculated_at": to_utc_iso8601(utc_now()),
                "positions_included": 0,
                "positions_excluded": 0,
                "warnings": ["Empty portfolio"]
            }
        }
    
    raw_exposure = Decimal("0")
    delta_adjusted = Decimal("0")
    positions_included = 0
    positions_excluded = 0
    
    for position in positions:
        exposure = Decimal(str(position.get("exposure", 0)))
        raw_exposure += abs(exposure)
        
        # Get delta
        greeks = position.get("greeks")
        if greeks and "delta" in greeks and greeks["delta"] is not None:
            # Options with Greeks
            delta = Decimal(str(greeks["delta"]))
            delta_adjusted += exposure * delta
            positions_included += 1
        elif position.get("position_type") in STOCK_POSITION_TYPES:
            # Stocks: use 1.0 or -1.0 based on position direction
            if position["position_type"] == "LONG":
                delta_adjusted += exposure  # exposure is already positive
            else:  # SHORT
                delta_adjusted += exposure  # exposure is already negative
            positions_included += 1
        else:
            # Skip positions without delta info
            positions_excluded += 1
    
    result = {
        "raw_exposure": raw_exposure.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "delta_adjusted_exposure": delta_adjusted.quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}")),
        "metadata": {
            "calculated_at": to_utc_iso8601(utc_now()),
            "positions_included": positions_included,
            "positions_excluded": positions_excluded,
            "warnings": []
        }
    }
    
    if positions_excluded > 0:
        result["metadata"]["warnings"].append(
            f"{positions_excluded} positions excluded from delta adjustment (no delta data)"
        )
    
    logger.info(f"Calculated delta-adjusted exposure: included={positions_included}, excluded={positions_excluded}")
    
    return result


def aggregate_by_tags(
    positions: List[Dict],
    tag_filter: Optional[Union[str, List[str]]] = None,
    tag_mode: str = TAG_MODE_ANY
) -> Dict[str, Dict]:
    """Aggregate positions by tags with flexible filtering.
    
    This function groups positions by their tags and calculates aggregate metrics
    for each tag. Positions with multiple tags are counted in each tag's aggregation.
    
    Args:
        positions: List of position dictionaries with 'tags' field
        tag_filter: Optional tag(s) to filter by. If provided, only these tags are aggregated
        tag_mode: "any" (OR logic) or "all" (AND logic) when multiple tags provided
        
    Returns:
        Dict mapping tags to aggregated metrics for positions with that tag
        
    Example:
        >>> positions = [
        ...     {"exposure": Decimal("10000"), "tags": ["tech", "momentum"], ...},
        ...     {"exposure": Decimal("5000"), "tags": ["tech", "value"], ...}
        ... ]
        >>> aggregate_by_tags(positions, tag_filter="tech")
        {
            "tech": {
                "gross_exposure": Decimal("15000.00"),
                "net_exposure": Decimal("15000.00"),
                "position_count": 2,
                ...
            }
        }
    """
    # Normalize tag_filter to list
    if tag_filter is not None:
        if isinstance(tag_filter, str):
            tag_filter = [tag_filter]
        tag_filter_set = set(tag_filter)
    else:
        tag_filter_set = None
    
    # Build tag aggregations
    tag_aggregations = {}
    
    for position in positions:
        position_tags = set(position.get("tags", []))
        
        # Skip if position has no tags
        if not position_tags:
            continue
        
        # Apply tag filter if specified
        if tag_filter_set is not None:
            if tag_mode == TAG_MODE_ALL:
                # Position must have ALL specified tags
                if not tag_filter_set.issubset(position_tags):
                    continue
            else:  # TAG_MODE_ANY
                # Position must have at least ONE specified tag
                if not tag_filter_set.intersection(position_tags):
                    continue
        
        # Determine which tags to aggregate for this position
        tags_to_aggregate = position_tags
        if tag_filter_set is not None:
            # Only aggregate the filtered tags
            tags_to_aggregate = position_tags.intersection(tag_filter_set)
        
        # Add position to each tag's aggregation
        exposure = Decimal(str(position.get("exposure", 0)))
        
        for tag in tags_to_aggregate:
            if tag not in tag_aggregations:
                tag_aggregations[tag] = {
                    "positions": [],
                    "gross_exposure": Decimal("0"),
                    "net_exposure": Decimal("0"),
                    "long_exposure": Decimal("0"),
                    "short_exposure": Decimal("0"),
                    "position_count": 0,
                    "long_count": 0,
                    "short_count": 0
                }
            
            agg = tag_aggregations[tag]
            agg["positions"].append(position)
            agg["gross_exposure"] += abs(exposure)
            agg["net_exposure"] += exposure
            agg["position_count"] += 1
            
            if exposure > 0:
                agg["long_exposure"] += exposure
                agg["long_count"] += 1
            elif exposure < 0:
                agg["short_exposure"] += exposure
                agg["short_count"] += 1
    
    # Format results and remove position lists
    result = {}
    for tag, agg in tag_aggregations.items():
        # Remove the temporary positions list
        agg.pop("positions", None)
        
        # Apply decimal precision
        agg["gross_exposure"] = agg["gross_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        agg["net_exposure"] = agg["net_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        agg["long_exposure"] = agg["long_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        agg["short_exposure"] = agg["short_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        
        result[tag] = agg
    
    # Add metadata
    metadata = {
        "calculated_at": to_utc_iso8601(utc_now()),
        "tag_filter": tag_filter,
        "tag_mode": tag_mode,
        "total_positions": len(positions),
        "tags_found": len(tag_aggregations),
        "warnings": []
    }
    
    if not tag_aggregations:
        metadata["warnings"].append("No positions matched the tag filter criteria")
    
    result["metadata"] = metadata
    
    logger.info(f"Aggregated by tags: {len(tag_aggregations)} tags, "
                f"filter={tag_filter}, mode={tag_mode}")
    
    return result


def aggregate_by_underlying(positions: List[Dict]) -> Dict[str, Dict]:
    """Aggregate positions by underlying symbol.
    
    This function groups all positions (stocks and options) by their underlying symbol.
    Critical for options risk analysis to see total exposure per underlying.
    
    Args:
        positions: List of position dictionaries with:
            - symbol: str (for stocks)
            - underlying_symbol: str (for options)
            - exposure, market_value, etc.
            
    Returns:
        Dict mapping underlying symbols to aggregated metrics
        
    Example:
        >>> positions = [
        ...     {"symbol": "AAPL", "exposure": Decimal("10000"), "position_type": "LONG"},
        ...     {"symbol": "AAPL_240119C150", "underlying_symbol": "AAPL", 
        ...      "exposure": Decimal("5000"), "position_type": "LC"}
        ... ]
        >>> aggregate_by_underlying(positions)
        {
            "AAPL": {
                "gross_exposure": Decimal("15000.00"),
                "position_count": 2,
                "stock_count": 1,
                "option_count": 1,
                ...
            }
        }
    """
    underlying_aggregations = {}
    
    for position in positions:
        # Determine underlying symbol
        position_type = position.get("position_type", "")
        if position_type in OPTIONS_POSITION_TYPES:
            underlying = position.get("underlying_symbol")
        elif position_type in STOCK_POSITION_TYPES:
            underlying = position.get("symbol")
        else:
            # Unknown position type, try to get symbol anyway
            underlying = position.get("symbol")
        
        
        if not underlying:
            logger.warning(f"Position missing underlying symbol: {position}")
            continue
        
        # Initialize aggregation for this underlying
        if underlying not in underlying_aggregations:
            underlying_aggregations[underlying] = {
                "gross_exposure": Decimal("0"),
                "net_exposure": Decimal("0"),
                "long_exposure": Decimal("0"),
                "short_exposure": Decimal("0"),
                "position_count": 0,
                "stock_count": 0,
                "option_count": 0,
                "call_count": 0,
                "put_count": 0,
                "greeks": {
                    "delta": Decimal("0"),
                    "gamma": Decimal("0"),
                    "theta": Decimal("0"),
                    "vega": Decimal("0"),
                    "rho": Decimal("0")
                }
            }
        
        agg = underlying_aggregations[underlying]
        exposure = Decimal(str(position.get("exposure", 0)))
        
        # Update exposures
        agg["gross_exposure"] += abs(exposure)
        agg["net_exposure"] += exposure
        agg["position_count"] += 1
        
        if exposure > 0:
            agg["long_exposure"] += exposure
        else:
            agg["short_exposure"] += exposure
        
        # Count position types
        position_type = position.get("position_type", "")
        if position_type in STOCK_POSITION_TYPES:
            agg["stock_count"] += 1
        elif position_type in OPTIONS_POSITION_TYPES:
            agg["option_count"] += 1
            if position_type in ["LC", "SC"]:
                agg["call_count"] += 1
            else:
                agg["put_count"] += 1
        
        # Aggregate Greeks if available
        greeks = position.get("greeks")
        if greeks:
            for greek_name in agg["greeks"]:
                if greek_name in greeks and greeks[greek_name] is not None:
                    agg["greeks"][greek_name] += Decimal(str(greeks[greek_name]))
    
    # Format results
    result = {}
    for underlying, agg in underlying_aggregations.items():
        # Apply decimal precision
        agg["gross_exposure"] = agg["gross_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        agg["net_exposure"] = agg["net_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        agg["long_exposure"] = agg["long_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        agg["short_exposure"] = agg["short_exposure"].quantize(Decimal(f"0.{'0' * MONETARY_DECIMAL_PLACES}"))
        
        # Format Greeks
        for greek_name in agg["greeks"]:
            agg["greeks"][greek_name] = agg["greeks"][greek_name].quantize(
                Decimal(f"0.{'0' * GREEKS_DECIMAL_PLACES}")
            )
        
        result[underlying] = agg
    
    # Add metadata
    result["metadata"] = {
        "calculated_at": to_utc_iso8601(utc_now()),
        "total_positions": len(positions),
        "underlyings_found": len(underlying_aggregations),
        "warnings": []
    }
    
    logger.info(f"Aggregated by underlying: {len(underlying_aggregations)} symbols")
    
    return result


# Cache clearing utility
def clear_portfolio_cache():
    """Clear all cached portfolio aggregation results."""
    # Clear cache for all cached functions
    if hasattr(calculate_portfolio_exposures, 'cache_clear'):
        calculate_portfolio_exposures.cache_clear()
    if hasattr(aggregate_portfolio_greeks, 'cache_clear'):
        aggregate_portfolio_greeks.cache_clear()
    if hasattr(calculate_delta_adjusted_exposure, 'cache_clear'):
        calculate_delta_adjusted_exposure.cache_clear()
    if hasattr(aggregate_by_tags, 'cache_clear'):
        aggregate_by_tags.cache_clear()
    if hasattr(aggregate_by_underlying, 'cache_clear'):
        aggregate_by_underlying.cache_clear()
    
    logger.info("Cleared all portfolio aggregation caches")


# TODO: Future enhancement for historical analysis
# def aggregate_portfolio_historical(positions: List[Dict], as_of_date: datetime) -> Dict[str, Any]:
#     """Calculate aggregations for a specific historical date.
#     
#     This function would filter positions to those active on the given date
#     and use historical market data for calculations.
#     """
#     pass