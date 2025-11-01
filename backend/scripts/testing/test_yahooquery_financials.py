"""
Test script to verify YahooQuery can pull all requested financial metrics
Tests both historical financials and forward-looking analyst estimates
"""
import asyncio
from yahooquery import Ticker
import pandas as pd
from pprint import pprint

# Test with Apple (well-covered stock)
TEST_SYMBOL = 'AAPL'


def test_historical_financials():
    """Test pulling historical financial statement items"""
    print("\n" + "="*80)
    print("TESTING HISTORICAL FINANCIALS")
    print("="*80)

    ticker = Ticker(TEST_SYMBOL)

    # Get quarterly and annual income statements
    print(f"\n--- Income Statement (Quarterly) for {TEST_SYMBOL} ---")
    income_q = ticker.income_statement(frequency='q')

    if isinstance(income_q, pd.DataFrame) and not income_q.empty:
        # Print available fields
        print(f"\nAvailable fields ({len(income_q.columns)} total):")
        for col in sorted(income_q.columns):
            print(f"  - {col}")

        # Check for our requested fields
        print("\n--- Requested Fields Status ---")
        requested_fields = {
            'Revenue': ['TotalRevenue', 'OperatingRevenue'],
            'Cost of Goods Sold': ['CostOfRevenue', 'ReconciledCostOfRevenue'],
            'Gross Profit': ['GrossProfit'],
            'S&M Expense': ['SellingAndMarketingExpense', 'SellingGeneralAndAdministration'],
            'R&D Expense': ['ResearchAndDevelopment'],
            'G&A Expense': ['GeneralAndAdministrativeExpense', 'SellingGeneralAndAdministration'],
            'SG&A': ['SellingGeneralAndAdministration'],
            'EBIT': ['EBIT', 'OperatingIncome'],
            'Interest Expense': ['InterestExpense', 'InterestExpenseNonOperating'],
            'Taxes': ['TaxProvision'],
            'Depreciation': ['DepreciationAndAmortization', 'ReconciledDepreciation'],
            'EBITDA': ['EBITDA', 'NormalizedEBITDA'],
            'Share Count': ['BasicAverageShares', 'DilutedAverageShares'],
        }

        for metric, possible_fields in requested_fields.items():
            found = [f for f in possible_fields if f in income_q.columns]
            if found:
                print(f"[OK] {metric}: {found[0]}")
                # Show most recent value
                latest_value = income_q[found[0]].iloc[0]
                print(f"   Latest value: {latest_value:,.0f}" if pd.notna(latest_value) else "   Latest value: N/A")
            else:
                print(f"[MISSING] {metric}: NOT FOUND (tried: {', '.join(possible_fields)})")

    # Get cash flow statement
    print(f"\n--- Cash Flow Statement (Quarterly) for {TEST_SYMBOL} ---")
    cashflow_q = ticker.cash_flow(frequency='q')

    if isinstance(cashflow_q, pd.DataFrame) and not cashflow_q.empty:
        cashflow_fields = {
            'Operating Cash Flow': ['OperatingCashFlow'],
            'CAPEX': ['CapitalExpenditure'],
            'Free Cash Flow': ['FreeCashFlow'],
        }

        for metric, possible_fields in cashflow_fields.items():
            found = [f for f in possible_fields if f in cashflow_q.columns]
            if found:
                print(f"[OK] {metric}: {found[0]}")
                latest_value = cashflow_q[found[0]].iloc[0]
                print(f"   Latest value: {latest_value:,.0f}" if pd.notna(latest_value) else "   Latest value: N/A")
            else:
                print(f"[MISSING] {metric}: NOT FOUND")

    # Show sample of most recent quarter data
    print(f"\n--- Sample Data (Most Recent Quarter) ---")
    if isinstance(income_q, pd.DataFrame) and not income_q.empty:
        sample_fields = ['TotalRevenue', 'GrossProfit', 'OperatingIncome', 'EBITDA', 'NetIncome']
        available_sample = [f for f in sample_fields if f in income_q.columns]
        if available_sample:
            print(income_q[available_sample].iloc[0])


def test_forward_metrics():
    """Test pulling forward-looking analyst estimates"""
    print("\n" + "="*80)
    print("TESTING FORWARD-LOOKING METRICS")
    print("="*80)

    ticker = Ticker(TEST_SYMBOL)

    # 1. Earnings Trend (analyst estimates for future quarters/years)
    print(f"\n--- Earnings Trend (Future Estimates) for {TEST_SYMBOL} ---")
    earnings_trend = ticker.earnings_trend

    if isinstance(earnings_trend, dict) and TEST_SYMBOL in earnings_trend:
        trend_data = earnings_trend[TEST_SYMBOL].get('trend', [])

        if trend_data:
            print(f"\nFound estimates for {len(trend_data)} periods")
            for period in trend_data:
                period_name = period.get('period', 'Unknown')

                # Revenue estimates
                rev_est = period.get('revenueEstimate', {})
                if rev_est:
                    print(f"\n{period_name} - Revenue Estimates:")
                    print(f"  Average: ${rev_est.get('avg', 'N/A'):,.0f}" if rev_est.get('avg') else "  Average: N/A")
                    print(f"  Low: ${rev_est.get('low', 'N/A'):,.0f}" if rev_est.get('low') else "  Low: N/A")
                    print(f"  High: ${rev_est.get('high', 'N/A'):,.0f}" if rev_est.get('high') else "  High: N/A")
                    print(f"  # Analysts: {rev_est.get('numberOfAnalysts', 'N/A')}")
                    print(f"  Growth: {rev_est.get('growth', 'N/A'):.2%}" if rev_est.get('growth') else "  Growth: N/A")

                # Earnings estimates
                earn_est = period.get('earningsEstimate', {})
                if earn_est:
                    print(f"\n{period_name} - Earnings Estimates:")
                    print(f"  Average EPS: ${earn_est.get('avg', 'N/A')}" if earn_est.get('avg') else "  Average EPS: N/A")
                    print(f"  Low EPS: ${earn_est.get('low', 'N/A')}" if earn_est.get('low') else "  Low EPS: N/A")
                    print(f"  High EPS: ${earn_est.get('high', 'N/A')}" if earn_est.get('high') else "  High EPS: N/A")
                    print(f"  # Analysts: {earn_est.get('numberOfAnalysts', 'N/A')}")

    # 2. Financial Data (includes analyst price targets)
    print(f"\n--- Financial Data (Price Targets) for {TEST_SYMBOL} ---")
    financial_data = ticker.financial_data

    if isinstance(financial_data, dict) and TEST_SYMBOL in financial_data:
        fin_data = financial_data[TEST_SYMBOL]
        print(f"Target Price - Low: ${fin_data.get('targetLowPrice', 'N/A')}")
        print(f"Target Price - Mean: ${fin_data.get('targetMeanPrice', 'N/A')}")
        print(f"Target Price - High: ${fin_data.get('targetHighPrice', 'N/A')}")
        print(f"Recommendation: {fin_data.get('recommendationMean', 'N/A')} (1=Strong Buy, 5=Sell)")
        print(f"# Analyst Opinions: {fin_data.get('numberOfAnalystOpinions', 'N/A')}")

        # Forward metrics from financial_data
        print(f"\nForward Metrics:")
        print(f"  Forward Revenue: ${fin_data.get('revenuePerShare', 'N/A')}")
        print(f"  Forward EPS: ${fin_data.get('forwardEps', 'N/A')}" if fin_data.get('forwardEps') else "  Forward EPS: N/A")
        print(f"  Revenue Growth: {fin_data.get('revenueGrowth', 'N/A'):.2%}" if fin_data.get('revenueGrowth') else "  Revenue Growth: N/A")
        print(f"  Earnings Growth: {fin_data.get('earningsGrowth', 'N/A'):.2%}" if fin_data.get('earningsGrowth') else "  Earnings Growth: N/A")

    # 3. Calendar Events (next earnings date estimates)
    print(f"\n--- Calendar Events (Next Earnings) for {TEST_SYMBOL} ---")
    calendar = ticker.calendar_events

    if isinstance(calendar, dict) and TEST_SYMBOL in calendar:
        cal_data = calendar[TEST_SYMBOL]
        earnings = cal_data.get('earnings', {})
        if earnings:
            print(f"Next Earnings Date: {earnings.get('earningsDate', ['N/A'])[0]}")
            print(f"Average Earnings Estimate: ${earnings.get('earningsAverage', 'N/A')}" if earnings.get('earningsAverage') else "Average Earnings Estimate: N/A")
            print(f"Low Earnings Estimate: ${earnings.get('earningsLow', 'N/A')}" if earnings.get('earningsLow') else "Low Earnings Estimate: N/A")
            print(f"High Earnings Estimate: ${earnings.get('earningsHigh', 'N/A')}" if earnings.get('earningsHigh') else "High Earnings Estimate: N/A")
            print(f"Average Revenue Estimate: ${earnings.get('revenueAverage', 'N/A'):,.0f}" if earnings.get('revenueAverage') else "Average Revenue Estimate: N/A")
            print(f"Low Revenue Estimate: ${earnings.get('revenueLow', 'N/A'):,.0f}" if earnings.get('revenueLow') else "Low Revenue Estimate: N/A")
            print(f"High Revenue Estimate: ${earnings.get('revenueHigh', 'N/A'):,.0f}" if earnings.get('revenueHigh') else "High Revenue Estimate: N/A")


def test_data_structure():
    """Show the actual data structure we'll work with"""
    print("\n" + "="*80)
    print("DATA STRUCTURE ANALYSIS")
    print("="*80)

    ticker = Ticker(TEST_SYMBOL)

    # Show income statement structure
    print("\n--- Income Statement DataFrame Structure ---")
    income_q = ticker.income_statement(frequency='q')

    if isinstance(income_q, pd.DataFrame) and not income_q.empty:
        print(f"Shape: {income_q.shape} (rows x columns)")
        print(f"Index levels: {income_q.index.names}")
        print(f"Number of quarters: {len(income_q)}")
        print(f"\nFirst row (most recent quarter):")
        print(income_q.iloc[0].head(10))

    # Show earnings trend structure
    print("\n--- Earnings Trend Data Structure ---")
    earnings_trend = ticker.earnings_trend

    if isinstance(earnings_trend, dict) and TEST_SYMBOL in earnings_trend:
        print("Keys in earnings_trend:")
        pprint(list(earnings_trend[TEST_SYMBOL].keys()))

        trend_data = earnings_trend[TEST_SYMBOL].get('trend', [])
        if trend_data:
            print(f"\nFirst trend period structure:")
            pprint(trend_data[0])


if __name__ == "__main__":
    print("\n" + "="*80)
    print("YAHOOQUERY FINANCIAL DATA CAPABILITY TEST")
    print("="*80)
    print(f"Testing symbol: {TEST_SYMBOL}")

    try:
        # Run all tests
        test_historical_financials()
        test_forward_metrics()
        test_data_structure()

        print("\n" + "="*80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR]: {str(e)}")
        import traceback
        traceback.print_exc()
