"""
Quick test script to verify fundamentals endpoints are working
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.fundamentals_service import FundamentalsService


async def test_income_statement():
    """Test income statement retrieval"""
    print("\n" + "="*60)
    print("Testing Income Statement Endpoint")
    print("="*60)

    service = FundamentalsService()

    # Test with AAPL (Apple)
    print("\nFetching AAPL income statement (quarterly)...")
    result = await service.get_income_statement("AAPL", frequency="q", periods=4)

    print(f"\nSymbol: {result.symbol}")
    print(f"Frequency: {result.frequency}")
    print(f"Currency: {result.currency}")
    print(f"Periods returned: {result.metadata.periods_returned}")

    if result.periods:
        latest = result.periods[0]
        print(f"\nLatest Period: {latest.period_date}")
        print(f"Fiscal Year: {latest.fiscal_year}")
        print(f"Fiscal Quarter: {latest.fiscal_quarter}")

        metrics = latest.metrics
        print(f"\nRevenue: ${metrics.revenue:,.2f}" if metrics.revenue else "Revenue: N/A")
        print(f"Gross Profit: ${metrics.gross_profit:,.2f}" if metrics.gross_profit else "Gross Profit: N/A")
        print(f"Gross Margin: {float(metrics.gross_margin)*100:.2f}%" if metrics.gross_margin else "Gross Margin: N/A")
        print(f"Net Income: ${metrics.net_income:,.2f}" if metrics.net_income else "Net Income: N/A")
        print(f"Net Margin: {float(metrics.net_margin)*100:.2f}%" if metrics.net_margin else "Net Margin: N/A")
        print(f"EPS (Diluted): ${metrics.diluted_eps}" if metrics.diluted_eps else "EPS: N/A")

        print("\n[PASS] Income statement test PASSED")
    else:
        print("\n[FAIL] No income statement periods returned")
        return False

    await service.close()
    return True


async def test_balance_sheet():
    """Test balance sheet retrieval"""
    print("\n" + "="*60)
    print("Testing Balance Sheet Endpoint")
    print("="*60)

    service = FundamentalsService()

    # Test with AAPL (Apple)
    print("\nFetching AAPL balance sheet (quarterly)...")
    result = await service.get_balance_sheet("AAPL", frequency="q", periods=4)

    print(f"\nSymbol: {result.symbol}")
    print(f"Frequency: {result.frequency}")
    print(f"Currency: {result.currency}")
    print(f"Periods returned: {result.metadata.periods_returned}")

    if result.periods:
        latest = result.periods[0]
        print(f"\nLatest Period: {latest.period_date}")

        metrics = latest.metrics
        assets = metrics.assets
        liabilities = metrics.liabilities
        equity = metrics.equity
        ratios = metrics.ratios

        print(f"\nTotal Assets: ${assets.total_assets:,.2f}" if assets.total_assets else "Total Assets: N/A")
        print(f"Total Liabilities: ${liabilities.total_liabilities:,.2f}" if liabilities.total_liabilities else "Total Liabilities: N/A")
        print(f"Total Equity: ${equity.total_stockholders_equity:,.2f}" if equity.total_stockholders_equity else "Total Equity: N/A")

        print(f"\nCurrent Ratio: {float(ratios.current_ratio):.2f}" if ratios.current_ratio else "Current Ratio: N/A")
        print(f"Debt-to-Equity: {float(ratios.debt_to_equity):.2f}" if ratios.debt_to_equity else "Debt-to-Equity: N/A")

        print("\n[PASS] Balance sheet test PASSED")
    else:
        print("\n[FAIL] No balance sheet periods returned")
        return False

    await service.close()
    return True


async def test_cash_flow():
    """Test cash flow retrieval"""
    print("\n" + "="*60)
    print("Testing Cash Flow Endpoint")
    print("="*60)

    service = FundamentalsService()

    # Test with AAPL (Apple)
    print("\nFetching AAPL cash flow (quarterly)...")
    result = await service.get_cash_flow("AAPL", frequency="q", periods=4)

    print(f"\nSymbol: {result.symbol}")
    print(f"Frequency: {result.frequency}")
    print(f"Currency: {result.currency}")
    print(f"Periods returned: {result.metadata.periods_returned}")

    if result.periods:
        latest = result.periods[0]
        print(f"\nLatest Period: {latest.period_date}")
        print(f"Fiscal Year: {latest.fiscal_year}")
        print(f"Fiscal Quarter: {latest.fiscal_quarter}")

        metrics = latest.metrics
        operating = metrics.operating_activities
        investing = metrics.investing_activities
        financing = metrics.financing_activities
        calculated = metrics.calculated_metrics

        print(f"\nOperating Cash Flow: ${operating.operating_cash_flow:,.2f}" if operating.operating_cash_flow else "Operating Cash Flow: N/A")
        print(f"CapEx: ${investing.capital_expenditures:,.2f}" if investing.capital_expenditures else "CapEx: N/A")
        print(f"Free Cash Flow: ${calculated.free_cash_flow:,.2f}" if calculated.free_cash_flow else "Free Cash Flow: N/A")
        print(f"Dividends Paid: ${financing.dividends_paid:,.2f}" if financing.dividends_paid else "Dividends: N/A")
        print(f"Stock Repurchases: ${financing.stock_repurchases:,.2f}" if financing.stock_repurchases else "Repurchases: N/A")

        print("\n[PASS] Cash flow test PASSED")
    else:
        print("\n[FAIL] No cash flow periods returned")
        return False

    await service.close()
    return True


async def test_all_statements():
    """Test all statements combined retrieval"""
    print("\n" + "="*60)
    print("Testing All Statements Combined Endpoint")
    print("="*60)

    service = FundamentalsService()

    # Test with AAPL (Apple)
    print("\nFetching AAPL all statements (quarterly)...")
    result = await service.get_all_statements("AAPL", frequency="q", periods=4)

    print(f"\nSymbol: {result.symbol}")
    print(f"Frequency: {result.frequency}")
    print(f"Currency: {result.currency}")

    # Check all three statements
    has_income = len(result.income_statement.periods) > 0
    has_balance = len(result.balance_sheet.periods) > 0
    has_cash = len(result.cash_flow.periods) > 0

    print(f"\nIncome Statement Periods: {len(result.income_statement.periods)}")
    print(f"Balance Sheet Periods: {len(result.balance_sheet.periods)}")
    print(f"Cash Flow Periods: {len(result.cash_flow.periods)}")

    if has_income and has_balance and has_cash:
        print("\n[PASS] All statements test PASSED - Got all three financial statements")
    else:
        print(f"\n[FAIL] Missing statements - Income: {has_income}, Balance: {has_balance}, Cash: {has_cash}")
        return False

    await service.close()
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("FUNDAMENTALS SERVICE TEST SUITE")
    print("="*60)

    results = []

    # Test income statement
    try:
        result = await test_income_statement()
        results.append(("Income Statement", result))
    except Exception as e:
        print(f"\n[FAIL] Income statement test FAILED: {str(e)}")
        results.append(("Income Statement", False))

    # Test balance sheet
    try:
        result = await test_balance_sheet()
        results.append(("Balance Sheet", result))
    except Exception as e:
        print(f"\n[FAIL] Balance sheet test FAILED: {str(e)}")
        results.append(("Balance Sheet", False))

    # Test cash flow
    try:
        result = await test_cash_flow()
        results.append(("Cash Flow", result))
    except Exception as e:
        print(f"\n[FAIL] Cash flow test FAILED: {str(e)}")
        results.append(("Cash Flow", False))

    # Test all statements
    try:
        result = await test_all_statements()
        results.append(("All Statements", result))
    except Exception as e:
        print(f"\n[FAIL] All statements test FAILED: {str(e)}")
        results.append(("All Statements", False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name}: {status}")

    all_passed = all(passed for _, passed in results)
    print(f"\nOverall: {'[PASS] ALL TESTS PASSED' if all_passed else '[FAIL] SOME TESTS FAILED'}")


if __name__ == "__main__":
    asyncio.run(main())
