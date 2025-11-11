"""
Test Trading Calendar Logic

Verifies that the trading calendar correctly identifies:
- Weekends (Saturday, Sunday)
- US market holidays (2024-2026)
- Most recent trading day
"""
from datetime import date, timedelta
from app.core.trading_calendar import (
    is_trading_day,
    get_most_recent_trading_day,
    get_next_trading_day,
    get_trading_days_between
)

def test_weekends():
    """Test weekend detection"""
    print("=" * 80)
    print("TEST 1: Weekend Detection")
    print("=" * 80)

    # Nov 2, 2025 is Saturday
    saturday = date(2025, 11, 2)
    sunday = date(2025, 11, 3)
    friday = date(2025, 10, 31)
    monday = date(2025, 11, 3)  # Actually Sunday, let's use Nov 4
    monday = date(2025, 11, 4)

    print(f"Saturday (Nov 2, 2025): {is_trading_day(saturday)} (should be False)")
    print(f"Sunday (Nov 3, 2025): {is_trading_day(sunday)} (should be False)")
    print(f"Friday (Oct 31, 2025): {is_trading_day(friday)} (should be True)")
    print(f"Monday (Nov 4, 2025): {is_trading_day(monday)} (should be True)")
    print()

def test_holidays():
    """Test holiday detection"""
    print("=" * 80)
    print("TEST 2: Holiday Detection")
    print("=" * 80)

    # Test major holidays
    new_years_2025 = date(2025, 1, 1)
    christmas_2025 = date(2025, 12, 25)
    july_4_2025 = date(2025, 7, 4)
    thanksgiving_2025 = date(2025, 11, 27)

    print(f"New Year's Day 2025: {is_trading_day(new_years_2025)} (should be False)")
    print(f"Christmas 2025: {is_trading_day(christmas_2025)} (should be False)")
    print(f"July 4th 2025: {is_trading_day(july_4_2025)} (should be False)")
    print(f"Thanksgiving 2025: {is_trading_day(thanksgiving_2025)} (should be False)")
    print()

def test_most_recent_trading_day():
    """Test getting most recent trading day"""
    print("=" * 80)
    print("TEST 3: Most Recent Trading Day")
    print("=" * 80)

    # Sunday Nov 3, 2025 → should return Friday Oct 31, 2025
    sunday = date(2025, 11, 3)
    most_recent = get_most_recent_trading_day(sunday)
    print(f"From Sunday (Nov 3, 2025): {most_recent} (should be Oct 31, 2025 - Friday)")

    # Friday Oct 31, 2025 → should return itself
    friday = date(2025, 10, 31)
    most_recent = get_most_recent_trading_day(friday)
    print(f"From Friday (Oct 31, 2025): {most_recent} (should be Oct 31, 2025)")

    # Christmas 2025 (Friday) → should return previous trading day
    christmas = date(2025, 12, 25)
    most_recent = get_most_recent_trading_day(christmas)
    print(f"From Christmas 2025 (Dec 25): {most_recent} (should be Dec 24, 2025)")
    print()

def test_next_trading_day():
    """Test getting next trading day"""
    print("=" * 80)
    print("TEST 4: Next Trading Day")
    print("=" * 80)

    # Friday Oct 31, 2025 → should return Monday Nov 4, 2025
    friday = date(2025, 10, 31)
    next_day = get_next_trading_day(friday)
    print(f"After Friday (Oct 31, 2025): {next_day} (should be Nov 4, 2025 - Monday)")

    # Thursday Dec 24, 2025 → should skip Christmas and return Dec 26
    thursday = date(2025, 12, 24)
    next_day = get_next_trading_day(thursday)
    print(f"After Thursday (Dec 24, 2025): {next_day} (should be Dec 26, 2025)")
    print()

def test_trading_days_between():
    """Test getting list of trading days in a range"""
    print("=" * 80)
    print("TEST 5: Trading Days Between Dates")
    print("=" * 80)

    # Oct 30 (Thu) to Nov 4 (Mon) = 3 trading days (Thu, Fri, Mon - skip Sat/Sun)
    start = date(2025, 10, 30)
    end = date(2025, 11, 4)
    trading_days = get_trading_days_between(start, end)
    print(f"Oct 30 to Nov 4, 2025: {len(trading_days)} trading days")
    print(f"Trading days: {[str(d) for d in trading_days]}")
    print(f"Should be: ['2025-10-30', '2025-10-31', '2025-11-04'] (Thu, Fri, Mon)")
    print()

def test_batch_scenario():
    """Test realistic batch processing scenario"""
    print("=" * 80)
    print("TEST 6: Batch Processing Scenario (The Main Use Case)")
    print("=" * 80)

    # Scenario: Batch runs on Sunday Nov 3, 2025
    calculation_date = date(2025, 11, 3)
    print(f"Calculation date: {calculation_date} ({calculation_date.strftime('%A')})")
    print(f"Is trading day: {is_trading_day(calculation_date)}")

    if not is_trading_day(calculation_date):
        adjusted_date = get_most_recent_trading_day(calculation_date)
        print(f"✅ ADJUSTED: Using most recent trading day {adjusted_date} ({adjusted_date.strftime('%A')})")
        print(f"This prevents wasting API calls on weekend data that doesn't exist!")
    else:
        print(f"No adjustment needed - {calculation_date} is a trading day")
    print()

if __name__ == "__main__":
    print("\n" + "🗓️" * 40)
    print("TRADING CALENDAR TESTING")
    print("🗓️" * 40 + "\n")

    test_weekends()
    test_holidays()
    test_most_recent_trading_day()
    test_next_trading_day()
    test_trading_days_between()
    test_batch_scenario()

    print("=" * 80)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 80)
    print()
