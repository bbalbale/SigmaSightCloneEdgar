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
**Total Value**: ~$2,850,000
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
**Total Value**: ~$3,200,000 starting equity
**Strategy**: Long undervalued sectors, short overvalued growth, options for leverage

**Key Characteristics**:
- Long Positions (100% of equity): Banks, healthcare, energy, defense
- Short Positions (50% of equity): High-valuation tech and consumer
- Options Overlay (15% of portfolio): Sector ETF calls, individual stock puts
- Gross Exposure: ~150% (leveraged)

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

## Entry Date & Pricing

All positions are set with:
- **Entry Date**: June 30, 2025
- **Entry Prices**: Approximate June 30, 2025 market close prices
- **Purpose**: Clean P&L tracking starting July 1, 2025

## How to Use

1. Navigate to SigmaSight frontend at http://localhost:3005
2. Register a new user account
3. Upload one of these CSV files during onboarding
4. Wait for batch processing to complete (~1-2 minutes)
5. View analytics and compare with other demo portfolios

## Comparison with Original Demo Portfolios

| Metric | Original | Conservative | Tech-Focused | Contrarian |
|--------|----------|--------------|--------------|------------|
| **Size** | $485K/$2.85M/$3.2M | N/A | $2.85M | $3.2M |
| **Style** | Mixed/Balanced | ❌ Error Test | Growth/Tech | Value/Contrarian |
| **Tickers** | AAPL, MSFT, etc. | Various (invalid) | CRWD, SNOW, PLTR | BAC, CVX, MRK |
| **Risk** | Low/Med/High | N/A | Medium-High | High |
| **Leverage** | No/No/Yes | N/A | No | Yes (150%) |
| **Options** | No/No/Yes | N/A | No | Yes |
| **Purpose** | Live portfolios | Validation testing | Live portfolio | Live portfolio |

**Note**: Conservative-Retiree-Portfolio.csv is specifically designed to test error validation and should produce ~11 validation errors. Use Tech-Focused or Contrarian portfolios for successful upload testing.

---

**Created**: November 16, 2025
**Purpose**: Test portfolio upload functionality with diverse ticker sets
**Source**: Based on Ben's Mock Portfolios requirements with variant tickers
