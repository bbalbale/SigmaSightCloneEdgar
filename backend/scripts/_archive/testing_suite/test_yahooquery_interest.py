"""
Deep dive into YahooQuery to find Interest Expense fields
"""
from yahooquery import Ticker
import pandas as pd

TEST_SYMBOL = 'AAPL'

def find_interest_fields():
    """Check all available fields for interest-related data"""
    print("="*80)
    print("SEARCHING FOR INTEREST EXPENSE IN YAHOOQUERY")
    print("="*80)

    ticker = Ticker(TEST_SYMBOL)

    # Get income statement
    print(f"\n--- Checking Income Statement for {TEST_SYMBOL} ---")
    income_q = ticker.income_statement(frequency='q')

    if isinstance(income_q, pd.DataFrame) and not income_q.empty:
        # Look for any field containing 'interest' (case insensitive)
        interest_fields = [col for col in income_q.columns if 'interest' in col.lower()]

        if interest_fields:
            print(f"\nFound {len(interest_fields)} interest-related fields:")
            for field in interest_fields:
                print(f"  - {field}")
                # Show recent values
                values = income_q[field].head(3)
                print(f"    Recent values: {values.tolist()}")
        else:
            print("\nNo fields containing 'interest' found!")

        # Also check for fields that might contain interest indirectly
        print("\n--- Checking Related Fields ---")
        related_fields = ['OtherIncomeExpense', 'OtherNonOperatingIncomeExpenses',
                         'NetNonOperatingInterestIncomeExpense', 'InterestIncome',
                         'InterestExpense', 'InterestExpenseNonOperating',
                         'NonOperatingIncomeExpense']

        for field in related_fields:
            if field in income_q.columns:
                print(f"\n[FOUND] {field}:")
                values = income_q[field].head(3)
                print(f"  Recent values: {values.tolist()}")
            else:
                print(f"[MISSING] {field}")

    # Get cash flow statement to check interest payments
    print(f"\n--- Checking Cash Flow Statement for {TEST_SYMBOL} ---")
    cashflow_q = ticker.cash_flow(frequency='q')

    if isinstance(cashflow_q, pd.DataFrame) and not cashflow_q.empty:
        interest_fields = [col for col in cashflow_q.columns if 'interest' in col.lower()]

        if interest_fields:
            print(f"\nFound {len(interest_fields)} interest-related fields in cash flow:")
            for field in interest_fields:
                print(f"  - {field}")
                values = cashflow_q[field].head(3)
                print(f"    Recent values: {values.tolist()}")
        else:
            print("\nNo interest fields in cash flow statement")

    # Get balance sheet to check debt (interest is based on debt)
    print(f"\n--- Checking Balance Sheet for {TEST_SYMBOL} ---")
    balance_q = ticker.balance_sheet(frequency='q')

    if isinstance(balance_q, pd.DataFrame) and not balance_q.empty:
        debt_fields = [col for col in balance_q.columns if 'debt' in col.lower()]

        if debt_fields:
            print(f"\nFound {len(debt_fields)} debt-related fields:")
            for field in debt_fields:
                print(f"  - {field}")

    # Print ALL available fields for reference
    print(f"\n--- ALL Income Statement Fields ({len(income_q.columns)} total) ---")
    for col in sorted(income_q.columns):
        print(f"  {col}")

def test_with_debt_heavy_company():
    """Test with a company that has significant debt (AT&T)"""
    print("\n" + "="*80)
    print("TESTING WITH DEBT-HEAVY COMPANY (AT&T)")
    print("="*80)

    ticker = Ticker('T')  # AT&T has significant debt

    income_q = ticker.income_statement(frequency='q')

    if isinstance(income_q, pd.DataFrame) and not income_q.empty:
        # Look for interest fields
        interest_candidates = ['InterestExpense', 'InterestExpenseNonOperating',
                              'NetNonOperatingInterestIncomeExpense',
                              'OtherNonOperatingIncomeExpenses']

        print("\nChecking AT&T income statement:")
        for field in interest_candidates:
            if field in income_q.columns:
                print(f"\n[FOUND] {field}:")
                values = income_q[field].head(4)
                for idx, val in values.items():
                    date = income_q.loc[idx, 'asOfDate'] if 'asOfDate' in income_q.columns else 'N/A'
                    print(f"  {date}: ${val:,.0f}" if pd.notna(val) else f"  {date}: N/A")

if __name__ == "__main__":
    find_interest_fields()
    test_with_debt_heavy_company()
