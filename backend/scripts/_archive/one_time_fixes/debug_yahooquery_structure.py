"""
Debug script to see actual YahooQuery DataFrame structure
"""
from yahooquery import Ticker

# Test AAPL
ticker = Ticker("AAPL")

print("=" * 60)
print("Income Statement Structure")
print("=" * 60)
income = ticker.income_statement(frequency='q')
print(f"\nType: {type(income)}")
print(f"\nShape: {income.shape if hasattr(income, 'shape') else 'N/A'}")
print(f"\nIndex: {income.index if hasattr(income, 'index') else 'N/A'}")
print(f"\nIndex names: {income.index.names if hasattr(income.index, 'names') else 'N/A'}")
print(f"\nColumns (first 10): {list(income.columns[:10]) if hasattr(income, 'columns') else 'N/A'}")
print(f"\nFirst few rows:")
print(income.head())

print("\n" + "=" * 60)
print("Balance Sheet Structure")
print("=" * 60)
balance = ticker.balance_sheet(frequency='q')
print(f"\nType: {type(balance)}")
print(f"\nShape: {balance.shape if hasattr(balance, 'shape') else 'N/A'}")
print(f"\nIndex: {balance.index if hasattr(balance, 'index') else 'N/A'}")
print(f"\nIndex names: {balance.index.names if hasattr(balance.index, 'names') else 'N/A'}")
print(f"\nColumns (first 10): {list(balance.columns[:10]) if hasattr(balance, 'columns') else 'N/A'}")
print(f"\nFirst few rows:")
print(balance.head())
