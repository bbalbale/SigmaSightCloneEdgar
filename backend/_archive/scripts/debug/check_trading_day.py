"""
Check if Oct 17, 2025 is a trading day
"""
from datetime import date
from app.utils.trading_calendar import trading_calendar

oct17 = date(2025, 10, 17)
is_trading = trading_calendar.is_trading_day(oct17)

print(f"October 17, 2025 ({oct17.strftime('%A')}) is a trading day: {is_trading}")

# Also check Oct 14
oct14 = date(2025, 10, 14)
is_trading_14 = trading_calendar.is_trading_day(oct14)
print(f"October 14, 2025 ({oct14.strftime('%A')}) is a trading day: {is_trading_14}")

# Check upcoming days
from datetime import timedelta
for i in range(1, 8):
    check_date = date.today() - timedelta(days=i)
    is_trading_day = trading_calendar.is_trading_day(check_date)
    print(f"{check_date} ({check_date.strftime('%A')}): {is_trading_day}")
