#!/usr/bin/env python3
"""
Check Valuation Data for Today

Queries company_profiles to see what valuation data was updated today.

Usage:
    # Local
    uv run python scripts/maintenance/check_valuation_data.py

    # Railway
    railway run python scripts/maintenance/check_valuation_data.py
"""

import asyncio
import sys
import os
from datetime import date, datetime, timedelta

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select, func, text
from app.database import get_async_session


async def check_valuation_data():
    """Check what valuation data exists for today."""

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    print("=" * 60)
    print("  VALUATION DATA CHECK")
    print("=" * 60)
    print(f"Today's Date: {today}")
    print()

    async with get_async_session() as db:
        # 1. Total company profiles
        total_result = await db.execute(
            text("SELECT COUNT(*) FROM company_profiles")
        )
        total_profiles = total_result.scalar()
        print(f"Total company_profiles records: {total_profiles}")

        # 2. Profiles updated today
        updated_today_result = await db.execute(
            text("""
                SELECT COUNT(*) FROM company_profiles
                WHERE updated_at >= :today_start AND updated_at <= :today_end
            """),
            {"today_start": today_start, "today_end": today_end}
        )
        updated_today = updated_today_result.scalar()
        print(f"Profiles updated today: {updated_today}")

        # 3. Sample of profiles updated today with valuation data
        print("\n" + "-" * 60)
        print("Sample profiles updated today (first 20):")
        print("-" * 60)

        sample_result = await db.execute(
            text("""
                SELECT symbol, pe_ratio, forward_pe, beta,
                       week_52_high, week_52_low, market_cap, dividend_yield,
                       updated_at
                FROM company_profiles
                WHERE updated_at >= :today_start AND updated_at <= :today_end
                ORDER BY symbol
                LIMIT 20
            """),
            {"today_start": today_start, "today_end": today_end}
        )
        samples = sample_result.fetchall()

        if samples:
            print(f"{'Symbol':<8} {'PE':>8} {'Fwd PE':>8} {'Beta':>6} {'52w Hi':>10} {'52w Lo':>10} {'Mkt Cap':>14}")
            print("-" * 70)
            for row in samples:
                symbol, pe, fwd_pe, beta, w52_hi, w52_lo, mkt_cap, div_yield, updated = row
                pe_str = f"{pe:.2f}" if pe else "N/A"
                fwd_pe_str = f"{fwd_pe:.2f}" if fwd_pe else "N/A"
                beta_str = f"{beta:.2f}" if beta else "N/A"
                w52_hi_str = f"{w52_hi:.2f}" if w52_hi else "N/A"
                w52_lo_str = f"{w52_lo:.2f}" if w52_lo else "N/A"
                mkt_cap_str = f"{mkt_cap/1e9:.1f}B" if mkt_cap else "N/A"
                print(f"{symbol:<8} {pe_str:>8} {fwd_pe_str:>8} {beta_str:>6} {w52_hi_str:>10} {w52_lo_str:>10} {mkt_cap_str:>14}")
        else:
            print("No profiles updated today.")

        # 4. Check valuation field coverage (all profiles)
        print("\n" + "-" * 60)
        print("Valuation field coverage (all profiles):")
        print("-" * 60)

        coverage_result = await db.execute(
            text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(pe_ratio) as has_pe,
                    COUNT(forward_pe) as has_fwd_pe,
                    COUNT(beta) as has_beta,
                    COUNT(week_52_high) as has_52w_hi,
                    COUNT(week_52_low) as has_52w_lo,
                    COUNT(market_cap) as has_mkt_cap,
                    COUNT(dividend_yield) as has_div_yield
                FROM company_profiles
            """)
        )
        coverage = coverage_result.fetchone()
        total, has_pe, has_fwd_pe, has_beta, has_52w_hi, has_52w_lo, has_mkt_cap, has_div_yield = coverage

        print(f"PE Ratio:       {has_pe:>5} / {total} ({100*has_pe/total:.1f}%)")
        print(f"Forward PE:     {has_fwd_pe:>5} / {total} ({100*has_fwd_pe/total:.1f}%)")
        print(f"Beta:           {has_beta:>5} / {total} ({100*has_beta/total:.1f}%)")
        print(f"52-Week High:   {has_52w_hi:>5} / {total} ({100*has_52w_hi/total:.1f}%)")
        print(f"52-Week Low:    {has_52w_lo:>5} / {total} ({100*has_52w_lo/total:.1f}%)")
        print(f"Market Cap:     {has_mkt_cap:>5} / {total} ({100*has_mkt_cap/total:.1f}%)")
        print(f"Dividend Yield: {has_div_yield:>5} / {total} ({100*has_div_yield/total:.1f}%)")

        # 5. Check market_data_cache for today's prices
        print("\n" + "-" * 60)
        print("Market Data Cache (recent prices):")
        print("-" * 60)

        cache_result = await db.execute(
            text("""
                SELECT COUNT(DISTINCT symbol)
                FROM market_data_cache
                WHERE date = :today
            """),
            {"today": today}
        )
        symbols_with_prices = cache_result.scalar()
        print(f"Symbols with price data for {today}: {symbols_with_prices}")

        # Check yesterday too (in case market was closed)
        yesterday = today - timedelta(days=1)
        yesterday_result = await db.execute(
            text("""
                SELECT COUNT(DISTINCT symbol)
                FROM market_data_cache
                WHERE date = :yesterday
            """),
            {"yesterday": yesterday}
        )
        symbols_yesterday = yesterday_result.scalar()
        print(f"Symbols with price data for {yesterday}: {symbols_yesterday}")

        # Last Friday (if today is weekend)
        friday = today - timedelta(days=(today.weekday() - 4) % 7 if today.weekday() >= 5 else 0)
        if friday != today:
            friday_result = await db.execute(
                text("""
                    SELECT COUNT(DISTINCT symbol)
                    FROM market_data_cache
                    WHERE date = :friday
                """),
                {"friday": friday}
            )
            symbols_friday = friday_result.scalar()
            print(f"Symbols with price data for {friday} (last Friday): {symbols_friday}")

        # 6. Detailed price data analysis
        print("\n" + "-" * 60)
        print("Price Data Details:")
        print("-" * 60)

        # Total rows and date range
        stats_result = await db.execute(
            text("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM market_data_cache
            """)
        )
        stats = stats_result.fetchone()
        total_rows, unique_symbols, earliest, latest = stats
        print(f"Total price rows: {total_rows:,}")
        print(f"Unique symbols: {unique_symbols}")
        print(f"Date range: {earliest} to {latest}")

        # Most recent 5 trading dates with counts
        print("\nMost recent trading dates:")
        recent_dates_result = await db.execute(
            text("""
                SELECT date, COUNT(DISTINCT symbol) as symbol_count
                FROM market_data_cache
                GROUP BY date
                ORDER BY date DESC
                LIMIT 5
            """)
        )
        recent_dates = recent_dates_result.fetchall()
        for d, count in recent_dates:
            print(f"  {d}: {count} symbols")

        # Sample prices for major symbols (latest date)
        print("\nSample prices (latest available):")
        sample_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'SPY', 'QQQ', 'IWM']
        sample_result = await db.execute(
            text("""
                SELECT DISTINCT ON (symbol) symbol, date, close, volume
                FROM market_data_cache
                WHERE symbol = ANY(:symbols)
                ORDER BY symbol, date DESC
            """),
            {"symbols": sample_symbols}
        )
        samples = sample_result.fetchall()
        if samples:
            print(f"  {'Symbol':<8} {'Date':<12} {'Close':>10} {'Volume':>15}")
            print("  " + "-" * 50)
            for symbol, dt, close, volume in sorted(samples, key=lambda x: x[0]):
                vol_str = f"{volume:,}" if volume else "N/A"
                print(f"  {symbol:<8} {str(dt):<12} {float(close):>10.2f} {vol_str:>15}")
        else:
            print("  No sample prices found for major symbols")

    print("\n" + "=" * 60)
    print("  CHECK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_valuation_data())
