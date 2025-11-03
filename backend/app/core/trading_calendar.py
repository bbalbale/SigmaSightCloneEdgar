"""
Trading Calendar Utility

Determines whether a date is a valid US stock market trading day.
Excludes weekends and major US stock market holidays.
"""
from datetime import date, timedelta
from typing import List

# Major US stock market holidays (approximate - does not account for observed dates shifting)
# For production, consider using pandas_market_calendars library
US_MARKET_HOLIDAYS_2024 = [
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # MLK Day
    date(2024, 2, 19),  # Presidents Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),   # Independence Day
    date(2024, 9, 2),   # Labor Day
    date(2024, 11, 28), # Thanksgiving
    date(2024, 12, 25), # Christmas
]

US_MARKET_HOLIDAYS_2025 = [
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
]

US_MARKET_HOLIDAYS_2026 = [
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas
]

# Combine all holidays
US_MARKET_HOLIDAYS = set(
    US_MARKET_HOLIDAYS_2024 +
    US_MARKET_HOLIDAYS_2025 +
    US_MARKET_HOLIDAYS_2026
)


def is_trading_day(check_date: date) -> bool:
    """
    Check if a given date is a US stock market trading day.

    Args:
        check_date: Date to check

    Returns:
        True if the date is a trading day (not weekend or holiday)
    """
    # Check if weekend (Saturday = 5, Sunday = 6)
    if check_date.weekday() >= 5:
        return False

    # Check if market holiday
    if check_date in US_MARKET_HOLIDAYS:
        return False

    return True


def get_trading_days_between(start_date: date, end_date: date) -> List[date]:
    """
    Get list of trading days between start and end dates (inclusive).

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        List of trading days
    """
    trading_days = []
    current = start_date

    while current <= end_date:
        if is_trading_day(current):
            trading_days.append(current)
        current += timedelta(days=1)

    return trading_days


def get_most_recent_trading_day(from_date: date = None) -> date:
    """
    Get the most recent trading day on or before the given date.

    Args:
        from_date: Date to check from (defaults to today)

    Returns:
        Most recent trading day
    """
    if from_date is None:
        from_date = date.today()

    current = from_date
    # Maximum lookback of 7 days (to handle long weekends)
    for _ in range(7):
        if is_trading_day(current):
            return current
        current -= timedelta(days=1)

    # Fallback: return the original date
    return from_date


def get_next_trading_day(from_date: date = None) -> date:
    """
    Get the next trading day after the given date.

    Args:
        from_date: Date to check from (defaults to today)

    Returns:
        Next trading day
    """
    if from_date is None:
        from_date = date.today()

    current = from_date + timedelta(days=1)
    # Maximum lookahead of 7 days (to handle long weekends)
    for _ in range(7):
        if is_trading_day(current):
            return current
        current += timedelta(days=1)

    # Fallback: return the original date + 1
    return from_date + timedelta(days=1)


def add_holidays_for_year(year: int, holidays: List[date]) -> None:
    """
    Add holidays for a specific year (for future expansion).

    Args:
        year: Year to add holidays for
        holidays: List of holiday dates
    """
    US_MARKET_HOLIDAYS.update(holidays)
