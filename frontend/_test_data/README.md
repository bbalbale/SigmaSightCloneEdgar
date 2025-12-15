# Sample Portfolios for Multi-Portfolio Onboarding Testing

This directory contains sample CSV portfolios designed to test the multi-portfolio onboarding features.

## Test Files

### 1. tech_growth_portfolio.csv
- **Account Name**: Tech IRA
- **Account Type**: IRA
- **Focus**: Growth-oriented technology stocks
- **Positions**: 8 (AAPL, MSFT, NVDA, GOOGL, META, AMZN, AMD, CRM)
- **Estimated Value**: ~$200,000+
- **Use Case**: Test IRA account type, technology sector concentration

### 2. dividend_income_portfolio.csv
- **Account Name**: Dividend Taxable
- **Account Type**: TAXABLE
- **Focus**: Income-focused dividend stocks
- **Positions**: 9 (JNJ, PG, KO, PEP, VZ, XOM, ABBV, O, MMM)
- **Estimated Value**: ~$150,000+
- **Use Case**: Test taxable account, defensive/income sectors

### 3. balanced_retirement_portfolio.csv
- **Account Name**: 401k Retirement
- **Account Type**: 401K
- **Focus**: Diversified mix of stocks and ETFs
- **Positions**: 10 (SPY, QQQ, VTI, BND, VNQ, SCHD, BRK.B, V, UNH, JPM)
- **Estimated Value**: ~$100,000+
- **Use Case**: Test 401k account type, ETF holdings, balanced allocation

### 4. small_test_portfolio.csv
- **Account Name**: Quick Test
- **Account Type**: TAXABLE
- **Focus**: Minimal portfolio for quick testing
- **Positions**: 3 (TSLA, DIS, COST)
- **Estimated Value**: ~$50,000+
- **Use Case**: Fast upload testing, minimal wait time

## Testing Scenarios

### Scenario 1: Full Multi-Portfolio Session
1. Upload `tech_growth_portfolio.csv` (IRA)
2. Click "Add Another Portfolio"
3. Upload `dividend_income_portfolio.csv` (Taxable)
4. Click "Add Another Portfolio"
5. Upload `balanced_retirement_portfolio.csv` (401k)
6. Verify session summary shows 3 portfolios
7. Click "Continue to Dashboard"

### Scenario 2: Mixed Success/Failure
1. Upload `tech_growth_portfolio.csv` (should succeed)
2. Click "Add Another"
3. Upload a malformed CSV (should fail)
4. Verify session shows 1 success, 1 failed
5. Click "Add Another"
6. Upload `small_test_portfolio.csv` (should succeed)
7. Verify session shows 2 success, 1 failed

### Scenario 3: Quick Single Upload
1. Upload `small_test_portfolio.csv`
2. Verify single-portfolio success view (not session list)
3. Continue to dashboard

### Scenario 4: Navigation Abandonment
1. Upload `tech_growth_portfolio.csv`
2. Click "Add Another"
3. Navigate away (e.g., back button)
4. Return to onboarding
5. Verify session is cleared, fresh start

## CSV Format

All files follow the 12-column format:
- **Required**: Symbol, Quantity, Entry Price Per Share, Entry Date
- **Optional**: Investment Class, Position Type, Account Name, Account Type, Notes, Target Price, Price Alert Low, Price Alert High

## Notes

- All entry dates are set to 2023-2024 for realistic holding periods
- Target prices and price alerts are included for testing those features
- Symbols are all valid, tradeable securities
- Quantities and prices are realistic for typical retail investors
