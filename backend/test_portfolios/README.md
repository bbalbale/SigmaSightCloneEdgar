# Test Portfolios

This directory contains CSV files for testing portfolio uploads with variants of the original 3 demo portfolios using different tickers.

## Portfolio Variants

### 1. Conservative-Retiree-Portfolio.csv
**Profile**: ERROR TESTING PORTFOLIO (Intentionally Invalid)
**Purpose**: Test CSV validation error reporting and row number display
**Status**: ❌ Contains 11 validation errors across different error types

**Key Characteristics**:
- ⚠️ This CSV is designed to FAIL validation
- Tests 11 different error codes (ERR_POS_003, ERR_POS_005, ERR_POS_006, etc.)
- Includes 5 valid rows as baseline
- Each error row is documented with inline comments
- Use to verify error messages show correct row numbers and symbols

**Error Types Tested**:
- Invalid investment subtype (Row 3)
- Symbol with invalid characters (Row 4)
- Non-numeric quantity (Row 5)
- Zero quantity (Row 6)
- Non-numeric price (Row 7)
- Negative price (Row 8)
- Price with too many decimals (Row 9)
- Invalid date format (Row 10)
- Future date (Row 11)
- Duplicate position (Row 13)
- Invalid investment class (Row 15)
- Quantity with too many decimals (Row 17)

**Expected Result**: Upload will fail with ~11 validation errors displaying row numbers

---

### 2. Tech-Focused-Professional.csv
**Profile**: Professional with high risk tolerance and tech sector concentration
**Total Position Value**: ~$2,013,000
**Recommended Equity Balance**: $2,013,000 (no leverage)
**Strategy**: Growth-focused technology exposure with emerging software/cloud names

**Key Characteristics**:
- 40% Tech-focused ETFs (QQQ, XLK, SOXX, ARKK, VGT)
- 60% Individual tech stocks
- Cloud, cybersecurity, and fintech themes
- Higher volatility than "Sophisticated High Net Worth"

**Holdings**:
- ETFs: QQQ, XLK, SOXX, ARKK, VGT
- Stocks: CRWD, SNOW, NET, DDOG, PLTR, ADBE, CRM, NOW, PANW, FTNT, MELI, SQ

---

### 3. Contrarian-Value-Trader.csv
**Profile**: Sophisticated trader with long/short equity positions and options overlay
**Gross Position Value**: ~$3,028,000 (long + short + options)
**Recommended Equity Balance**: $2,019,000 (for 1.5x leverage ratio)
**Strategy**: Long undervalued sectors, short overvalued growth, options for leverage

**Key Characteristics**:
- Long Positions: $2,123,000 (105% of equity)
- Short Positions: $894,000 (44% of equity)
- Options Overlay: $11,000 (0.5% of equity)
- **Gross Exposure: $3,028,000 (150% of equity)** ← Use this divided by 1.5 for equity balance
- Net Exposure: $1,229,000 (61% of equity)

**Long Holdings**:
- Financials: BAC, WFC, USB, PNC
- Healthcare: MRK, PFE, GILD, BMY
- Energy: CVX, COP, SLB, HAL
- Defense: BA, LMT, RTX

**Short Holdings**:
- Growth Tech: SPOT, UBER, DASH, ABNB, CVNA, W, RH, BABA

**Options Positions**:
- Long Calls: IWM, DIA, XLE, XLF (sector rotation plays)
- Short Puts: TSLA, AMZN, NVDA, GOOGL (premium collection)

---

### 4. Diversified-Growth-Investor.csv
**Profile**: Growth investor with highly concentrated NVIDIA position plus diversified holdings
**Total Position Value**: ~$5,800,000
**Recommended Equity Balance**: $5,800,000 (no leverage)
**Strategy**: Concentrated tech bet (NVDA) with diversified multi-asset base across stocks, equity ETFs, and bond ETFs

**Key Characteristics**:
- **⚠️ 43.1% NVDA concentration** ($2.5M single position - highest concentration risk)
- 56.9% Diversified holdings across all major sectors
- 52 total positions
- Demonstrates concentrated conviction strategy with diversified tail risk management
- Second largest position is only 4.6% (SPY)

**Sector Breakdown**:
- Technology: MSFT, NVDA, AMD, ORCL, ADBE, CRM, TSLA, AMZN
- Healthcare: JNJ, UNH, PFE, ABBV
- Financials: JPM, BAC, GS, BLK, V, MA
- Consumer: COST, HD, NKE, SBUX, WMT, PG, KO, MCD
- Industrials: CAT, BA, GE, HON
- Energy: XOM, CVX
- Communications: DIS, T, VZ
- Utilities: NEE, DUK

**ETF Holdings**:
- Equity: SPY, QQQ, VTI, IWM, EEM, VNQ, XLRE, SCHD
- Fixed Income: AGG, BND, TLT, HYG, LQD, MUB, VCIT

---

## Entry Date & Pricing

All positions are set with:
- **Entry Date**: June 30, 2025
- **Entry Prices**: Approximate June 30, 2025 market close prices
- **Purpose**: Clean P&L tracking starting July 1, 2025

## 🔑 How to Calculate Equity Balance

**CRITICAL**: Equity balance represents your **starting capital**, NOT your position values!

### For Non-Leveraged Portfolios (Tech-Focused)
```
Equity Balance = Sum of all position entry values
Example: $2,013,000 in positions → Equity Balance = $2,013,000
```

### For Leveraged Portfolios (Contrarian)
```
Equity Balance = Gross Exposure ÷ Target Leverage Ratio

Example (Contrarian):
- Long positions: $2,123,000
- Short positions: $894,000
- Options: $11,000
- Gross Exposure: $3,028,000
- Target Leverage: 1.5x
- Equity Balance: $3,028,000 ÷ 1.5 = $2,019,000

Why? Because you're using $2,019,000 of capital to control $3,028,000 worth of positions (1.5x leverage)
```

### Quick Formula
- **No leverage**: Equity Balance = Position Values
- **With leverage**: Equity Balance = Gross Exposure ÷ Leverage Ratio

## How to Use

1. Navigate to SigmaSight frontend at http://localhost:3005
2. Register a new user account
3. Upload one of these CSV files during onboarding
4. **IMPORTANT**: Enter the **Recommended Equity Balance** shown above, NOT the gross position value
5. Wait for batch processing to complete (~1-2 minutes)
6. View analytics and compare with other demo portfolios

## Comparison with Original Demo Portfolios

| Metric | Original | Conservative | Tech-Focused | Contrarian | Diversified |
|--------|----------|--------------|--------------|------------|-------------|
| **Equity Balance** | $485K/$2.85M/$3.2M | N/A | **$2.01M** | **$2.02M** | **$5.80M** |
| **Gross Exposure** | $485K/$2.85M/$4.8M | N/A | $2.01M | $3.03M | $5.80M |
| **Leverage** | No/No/Yes (1.5x) | N/A | No | Yes (1.5x) | No |
| **Style** | Mixed/Balanced | ❌ Error Test | Growth/Tech | Value/Contrarian | **Concentrated/Growth** |
| **Top Holding** | AAPL (varies) | N/A | CRWD | BAC | **NVDA (43%)** |
| **Tickers** | AAPL, MSFT, etc. | Various (invalid) | CRWD, SNOW, PLTR | BAC, CVX, MRK | NVDA, MSFT, SPY, AGG |
| **Positions** | 16/17/30 | Variable | 12 | 24 | 52 |
| **Risk** | Low/Med/High | N/A | Medium-High | High | **High (concentration)** |
| **Options** | No/No/Yes | N/A | No | Yes | No |
| **Purpose** | Live portfolios | Validation testing | Live portfolio | Live portfolio | Live portfolio |

**Important Notes**:
- **Conservative-Retiree-Portfolio.csv**: Error testing file - will fail with ~11 validation errors
- **Tech-Focused-Professional.csv**: Enter equity balance of **$2,013,000** (no leverage)
- **Contrarian-Value-Trader.csv**: Enter equity balance of **$2,019,000** (NOT $3,028,000 - that's the gross exposure with 1.5x leverage)
- **Diversified-Growth-Investor.csv**: Enter equity balance of **$5,800,000** (no leverage) - ⚠️ Contains 43% NVDA concentration

---

**Created**: November 16, 2025
**Purpose**: Test portfolio upload functionality with diverse ticker sets
**Source**: Based on Ben's Mock Portfolios requirements with variant tickers
