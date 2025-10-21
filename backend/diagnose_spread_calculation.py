"""
Comprehensive Diagnostic for Spread Factor Calculation Failures
Traces through the entire calculation flow to identify where and why regressions fail
"""
import asyncio
from uuid import UUID
from datetime import date, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import select, and_

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.constants.factors import (
    SPREAD_FACTORS, SPREAD_REGRESSION_WINDOW_DAYS,
    SPREAD_MIN_REGRESSION_DAYS
)
from app.calculations.factor_utils import load_portfolio_context
from app.calculations.market_data import get_returns


async def diagnose_spread_calculation():
    """
    Step-by-step diagnostic of spread factor calculation for HNW portfolio
    """
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    calculation_date = date(2025, 10, 20)

    print('=' * 80)
    print('SPREAD FACTOR CALCULATION DIAGNOSTIC')
    print('=' * 80)
    print(f'Portfolio ID: {portfolio_id}')
    print(f'Calculation Date: {calculation_date}')
    print(f'Regression Window: {SPREAD_REGRESSION_WINDOW_DAYS} days')
    print(f'Minimum Required: {SPREAD_MIN_REGRESSION_DAYS} days')
    print('=' * 80)
    print()

    async with AsyncSessionLocal() as db:
        # STEP 1: Load Portfolio Context
        print('STEP 1: LOAD PORTFOLIO CONTEXT')
        print('-' * 80)
        context = await load_portfolio_context(db, portfolio_id, calculation_date)

        counts = context.get_position_count_summary()
        print(f'  Total positions: {counts["total"]}')
        print(f'  PUBLIC positions: {counts["public"]}')
        print(f'  PRIVATE positions: {counts["private"]}')
        print(f'  Active (non-exited): {counts["active"]}')
        print()

        public_positions = context.public_positions
        print(f'  PUBLIC positions for factor analysis: {len(public_positions)}')
        for pos in public_positions[:5]:
            print(f'    - {pos.symbol:10s} (entry: {pos.entry_date})')
        if len(public_positions) > 5:
            print(f'    ... and {len(public_positions) - 5} more')
        print()

        # STEP 2: Define Date Range
        print('STEP 2: DEFINE DATE RANGE')
        print('-' * 80)
        end_date = calculation_date
        start_date = end_date - timedelta(days=SPREAD_REGRESSION_WINDOW_DAYS + 30)
        print(f'  Start date: {start_date}')
        print(f'  End date: {end_date}')
        print(f'  Target days: {SPREAD_REGRESSION_WINDOW_DAYS} (trading days)')
        print(f'  Calendar window: {(end_date - start_date).days} days')
        print()

        # STEP 3: Fetch Spread Returns
        print('STEP 3: FETCH SPREAD RETURNS (QUAL-SPY, etc.)')
        print('-' * 80)

        # Collect all unique ETF symbols
        etf_symbols = set()
        for long_etf, short_etf in SPREAD_FACTORS.values():
            etf_symbols.add(long_etf)
            etf_symbols.add(short_etf)

        print(f'  Required ETFs: {sorted(etf_symbols)}')
        print()

        # Check data availability for each ETF
        print('  ETF Data Availability:')
        etf_data_status = {}
        for symbol in sorted(etf_symbols):
            stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)

            result = await db.execute(stmt)
            prices = result.scalars().all()

            if prices:
                dates = [p.date for p in prices]
                etf_data_status[symbol] = {
                    'days': len(prices),
                    'first_date': min(dates),
                    'last_date': max(dates),
                    'has_data': True
                }
                status = 'OK' if len(prices) >= SPREAD_MIN_REGRESSION_DAYS else 'INSUFFICIENT'
                print(f'    {symbol:6s}: {len(prices):3d} days ({min(dates)} to {max(dates)}) [{status}]')
            else:
                etf_data_status[symbol] = {'days': 0, 'has_data': False}
                print(f'    {symbol:6s}:   0 days [NO DATA]')
        print()

        # Fetch returns using canonical function
        print('  Fetching ETF returns...')
        try:
            returns = await get_returns(
                db=db,
                symbols=list(etf_symbols),
                start_date=start_date,
                end_date=end_date,
                align_dates=True
            )

            print(f'  [OK] ETF returns fetched: {len(returns)} days, {len(returns.columns)} ETFs')
            print(f'  Date range: {returns.index[0]} to {returns.index[-1]}')
            print()
        except Exception as e:
            print(f'  [ERROR] ERROR fetching ETF returns: {e}')
            return

        # Calculate spread returns
        print('  Calculating spread returns...')
        spread_returns = pd.DataFrame(index=returns.index)

        for spread_name, (long_etf, short_etf) in SPREAD_FACTORS.items():
            if long_etf in returns.columns and short_etf in returns.columns:
                spread_returns[spread_name] = returns[long_etf] - returns[short_etf]
                mean_ret = spread_returns[spread_name].mean()
                std_ret = spread_returns[spread_name].std()
                print(f'    {spread_name:25s}: mean={mean_ret:>7.4f}, std={std_ret:>7.4f}')
            else:
                print(f'    {spread_name:25s}: MISSING DATA')

        spread_returns = spread_returns.dropna()
        print(f'\n  [OK] Spread returns: {len(spread_returns)} days after alignment')
        print()

        # STEP 4: Fetch Position Returns
        print('STEP 4: FETCH POSITION RETURNS')
        print('-' * 80)

        # Get unique symbols from public positions
        symbols = list(set(pos.symbol for pos in public_positions))
        print(f'  Public position symbols ({len(symbols)}): {symbols[:10]}')
        if len(symbols) > 10:
            print(f'    ... and {len(symbols) - 10} more')
        print()

        # Check price data availability for each position symbol
        print('  Position Price Data Availability:')
        position_data_status = {}
        for symbol in sorted(symbols):
            stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)

            result = await db.execute(stmt)
            prices = result.scalars().all()

            if prices:
                dates = [p.date for p in prices]
                position_data_status[symbol] = {
                    'days': len(prices),
                    'first_date': min(dates),
                    'last_date': max(dates),
                    'has_data': True
                }
                status = 'OK' if len(prices) >= SPREAD_MIN_REGRESSION_DAYS else 'INSUFFICIENT'
                print(f'    {symbol:10s}: {len(prices):3d} days [{status}]')
            else:
                position_data_status[symbol] = {'days': 0, 'has_data': False}
                print(f'    {symbol:10s}:   0 days [NO DATA]')
        print()

        # Fetch position returns
        print('  Fetching position returns...')
        try:
            # Import here to use actual calculation function
            from app.calculations.factors import calculate_position_returns

            position_returns = await calculate_position_returns(
                db=db,
                portfolio_id=portfolio_id,
                start_date=start_date,
                end_date=end_date,
                use_delta_adjusted=False,
                context=context
            )

            if position_returns.empty:
                print(f'  [ERROR] NO POSITION RETURNS AVAILABLE')
                return

            print(f'  [OK] Position returns fetched: {len(position_returns)} days, {len(position_returns.columns)} positions')
            print(f'  Date range: {position_returns.index[0]} to {position_returns.index[-1]}')
            print()
        except Exception as e:
            print(f'  [ERROR] ERROR fetching position returns: {e}')
            return

        # STEP 5: Align Data
        print('STEP 5: ALIGN POSITION RETURNS WITH SPREAD RETURNS')
        print('-' * 80)

        common_dates = spread_returns.index.intersection(position_returns.index)
        print(f'  Spread returns dates: {len(spread_returns)} days')
        print(f'  Position returns dates: {len(position_returns)} days')
        print(f'  Common dates: {len(common_dates)} days')
        print()

        if len(common_dates) < SPREAD_MIN_REGRESSION_DAYS:
            print(f'  [ERROR] INSUFFICIENT ALIGNED DATA!')
            print(f'    Required: {SPREAD_MIN_REGRESSION_DAYS} days')
            print(f'    Available: {len(common_dates)} days')
            print(f'    Gap: {SPREAD_MIN_REGRESSION_DAYS - len(common_dates)} days')
            print()

            # Analyze the gap
            print('  GAP ANALYSIS:')
            spread_dates = set(spread_returns.index)
            position_dates = set(position_returns.index)

            only_in_spread = spread_dates - position_dates
            only_in_position = position_dates - spread_dates

            print(f'    Dates only in spread returns: {len(only_in_spread)}')
            if only_in_spread and len(only_in_spread) <= 10:
                print(f'      {sorted(only_in_spread)}')

            print(f'    Dates only in position returns: {len(only_in_position)}')
            if only_in_position and len(only_in_position) <= 10:
                print(f'      {sorted(only_in_position)}')

            return

        spread_returns_aligned = spread_returns.loc[common_dates]
        position_returns_aligned = position_returns.loc[common_dates]

        print(f'  [OK] Data aligned successfully: {len(common_dates)} common days')
        print(f'  Date range: {common_dates[0]} to {common_dates[-1]}')
        print()

        # STEP 6: Test Regressions
        print('STEP 6: TEST POSITION-LEVEL REGRESSIONS')
        print('-' * 80)
        print(f'  Testing Quality Spread regressions for all {len(position_returns_aligned.columns)} positions...')
        print()

        successful_regressions = 0
        failed_regressions = 0
        failure_reasons = {}

        for position_id in position_returns_aligned.columns:
            pos_returns = position_returns_aligned[position_id]
            spread_ret = spread_returns_aligned['Quality Spread']

            # Align on common dates
            data = pd.concat([pos_returns, spread_ret], axis=1).dropna()

            if len(data) < SPREAD_MIN_REGRESSION_DAYS:
                failed_regressions += 1
                reason = f'Insufficient data: {len(data)} days'
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
                continue

            # Try regression
            try:
                from app.calculations.regression_utils import run_single_factor_regression

                y = data.iloc[:, 0].values
                x = data.iloc[:, 1].values

                result = run_single_factor_regression(
                    y=y,
                    x=x,
                    cap=5.0,
                    confidence=0.10,
                    return_diagnostics=True
                )

                if result.get('success', False):
                    successful_regressions += 1
                else:
                    failed_regressions += 1
                    reason = result.get('error', 'Unknown error')
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

            except Exception as e:
                failed_regressions += 1
                reason = f'Exception: {type(e).__name__}'
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        print(f'  RESULTS:')
        print(f'    Successful: {successful_regressions} positions')
        print(f'    Failed: {failed_regressions} positions')
        print()

        if failure_reasons:
            print(f'  FAILURE BREAKDOWN:')
            for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1]):
                print(f'    {reason}: {count} positions')
            print()

        # STEP 7: Summary
        print('STEP 7: DIAGNOSIS SUMMARY')
        print('=' * 80)

        if successful_regressions == 0:
            print('  STATUS: ALL REGRESSIONS FAILED')
            print()
            print('  ROOT CAUSE:')
            if len(common_dates) < SPREAD_MIN_REGRESSION_DAYS:
                print('    Insufficient aligned data between position returns and spread returns')
                print(f'    Required: {SPREAD_MIN_REGRESSION_DAYS} days')
                print(f'    Available: {len(common_dates)} days')
            else:
                print('    Other regression failures (see breakdown above)')
            print()
            print('  IMPACT:')
            print('    - No position-level spread factor exposures stored')
            print('    - Portfolio-level spread beta calculated on total portfolio returns')
            print('    - Results may be unstable due to:')
            print('      * Inclusion of illiquid assets in portfolio returns')
            print('      * No position-level diversification')
            print('      * Single regression on noisy aggregate returns')
        else:
            print(f'  STATUS: PARTIAL SUCCESS ({successful_regressions}/{successful_regressions + failed_regressions} positions)')
            print()
            print(f'  Note: {failed_regressions} positions failed but should have some exposures')

        print('=' * 80)


if __name__ == '__main__':
    asyncio.run(diagnose_spread_calculation())
