"""
Trading Calendar Utilities

Provides NYSE trading day detection using pandas_market_calendars.
Handles weekends and US market holidays automatically.
"""

import datetime
from typing import Optional
import pandas_market_calendars as mcal
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache the NYSE calendar for performance
_nyse_calendar: Optional[mcal.MarketCalendar] = None


def get_nyse_calendar() -> mcal.MarketCalendar:
    """
    Get the NYSE market calendar (cached).

    Returns:
        NYSE market calendar instance
    """
    global _nyse_calendar
    if _nyse_calendar is None:
        _nyse_calendar = mcal.get_calendar('NYSE')
        logger.debug("NYSE calendar loaded and cached")
    return _nyse_calendar


def is_trading_day(date: Optional[datetime.date] = None) -> bool:
    """
    Check if the given date is a US market trading day.

    Rules:
    - Must be Monday-Friday (weekday)
    - Not a US market holiday (NYSE calendar)
    - Returns False for weekends

    Args:
        date: Date to check (defaults to today)

    Returns:
        True if trading day, False otherwise

    Examples:
        >>> is_trading_day(datetime.date(2025, 1, 1))  # New Year's Day
        False
        >>> is_trading_day(datetime.date(2025, 1, 6))  # Monday (trading day)
        True
        >>> is_trading_day(datetime.date(2025, 1, 11))  # Saturday
        False
    """
    if date is None:
        date = datetime.date.today()

    # Quick check: weekend?
    if date.weekday() >= 5:  # Saturday=5, Sunday=6
        logger.debug(f"{date} is a weekend (day {date.weekday()})")
        return False

    # Check NYSE calendar for holidays
    nyse = get_nyse_calendar()
    try:
        schedule = nyse.schedule(start_date=date, end_date=date)
        is_trading = len(schedule) > 0

        if is_trading:
            logger.debug(f"{date} is a trading day")
        else:
            logger.debug(f"{date} is a market holiday")

        return is_trading
    except Exception as e:
        logger.error(f"Error checking trading day for {date}: {e}")
        # Conservative fallback: assume it's not a trading day if we can't check
        return False


def get_last_trading_day(reference_date: Optional[datetime.date] = None) -> datetime.date:
    """
    Get the most recent trading day on or before the reference date.

    Args:
        reference_date: Date to search backwards from (defaults to today)

    Returns:
        Most recent trading day

    Examples:
        >>> # If today is Saturday Jan 11, 2025
        >>> get_last_trading_day()
        datetime.date(2025, 1, 10)  # Friday Jan 10
    """
    if reference_date is None:
        reference_date = datetime.date.today()

    # Search backwards up to 10 days (handles long weekends)
    for i in range(10):
        check_date = reference_date - datetime.timedelta(days=i)
        if is_trading_day(check_date):
            logger.debug(f"Last trading day before {reference_date}: {check_date}")
            return check_date

    # Fallback: just return 1 day ago (shouldn't happen)
    logger.warning(f"Could not find trading day within 10 days of {reference_date}")
    return reference_date - datetime.timedelta(days=1)


def get_next_trading_day(reference_date: Optional[datetime.date] = None) -> datetime.date:
    """
    Get the next trading day after the reference date.

    Args:
        reference_date: Date to search forwards from (defaults to today)

    Returns:
        Next trading day

    Examples:
        >>> # If today is Friday Jan 10, 2025
        >>> get_next_trading_day()
        datetime.date(2025, 1, 13)  # Monday Jan 13
    """
    if reference_date is None:
        reference_date = datetime.date.today()

    # Search forwards up to 10 days
    for i in range(1, 11):
        check_date = reference_date + datetime.timedelta(days=i)
        if is_trading_day(check_date):
            logger.debug(f"Next trading day after {reference_date}: {check_date}")
            return check_date

    # Fallback: just return 1 day ahead (shouldn't happen)
    logger.warning(f"Could not find trading day within 10 days of {reference_date}")
    return reference_date + datetime.timedelta(days=1)


def get_trading_days_in_range(
    start_date: datetime.date,
    end_date: datetime.date
) -> list[datetime.date]:
    """
    Get all trading days within a date range (inclusive).

    Args:
        start_date: Start of range
        end_date: End of range

    Returns:
        List of trading days in chronological order

    Examples:
        >>> # Week of Jan 6-10, 2025 (all trading days)
        >>> get_trading_days_in_range(
        ...     datetime.date(2025, 1, 6),
        ...     datetime.date(2025, 1, 10)
        ... )
        [datetime.date(2025, 1, 6), ..., datetime.date(2025, 1, 10)]  # 5 days
    """
    nyse = get_nyse_calendar()
    schedule = nyse.schedule(start_date=start_date, end_date=end_date)

    # Convert schedule index to list of dates
    trading_days = [date.date() for date in schedule.index]

    logger.debug(
        f"Found {len(trading_days)} trading days between {start_date} and {end_date}"
    )

    return trading_days
