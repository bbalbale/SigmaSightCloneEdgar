# Portfolio CSV Upload Format

## 1. Overview
This document defines the CSV format for uploading portfolio positions to SigmaSight. The format uses a **12-column structure** with 4 required columns and 8 optional columns for detailed position classification.

**Last Updated**: November 14, 2025

## 2. CSV Format (12 Columns)

### 2.1 Column Structure

| # | Column Name | Required | Type | Description |
|---|-------------|----------|------|-------------|
| 1 | Symbol | ✅ | String | Stock/ETF/Option symbol |
| 2 | Quantity | ✅ | Decimal | Number of shares/contracts (negative = short) |
| 3 | Entry Price Per Share | ✅ | Decimal | Purchase price per share |
| 4 | Entry Date | ✅ | Date | Entry date (YYYY-MM-DD) |
| 5 | Investment Class | ❌ | String | PUBLIC, OPTIONS, or PRIVATE |
| 6 | Investment Subtype | ❌ | String | STOCK, ETF, CALL, PUT, etc. |
| 7 | Underlying Symbol | ❌ | String | For options only |
| 8 | Strike Price | ❌ | Decimal | For options only |
| 9 | Expiration Date | ❌ | Date | For options (YYYY-MM-DD) |
| 10 | Option Type | ❌ | String | CALL or PUT |
| 11 | Exit Date | ❌ | Date | For closed positions (YYYY-MM-DD) |
| 12 | Exit Price Per Share | ❌ | Decimal | For closed positions |

### 2.2 Header Row (Exact Column Names)

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
```

**Important**: Column names are **case-sensitive** and must match exactly.

## 3. Required Columns

### 3.1 Symbol (Required)
- Stock/ETF ticker symbol (e.g., "AAPL", "SPY")
- For options: Use a descriptive symbol (e.g., "SPY_C450_20240315")
- **Cannot be blank** - all positions must have a symbol
- **Validation**:
  - Max 100 characters
  - Alphanumeric, dash, dot, underscore only
  - Pattern: `^[A-Za-z0-9._-]+$`

### 3.2 Quantity (Required)
- Number of shares or contracts
- **Positive** for long positions
- **Negative** for short positions
- For options: number of contracts (1 contract = 100 shares)
- **Validation**:
  - Cannot be zero
  - Max 6 decimal places
  - Must be valid decimal number

### 3.3 Entry Price Per Share (Required)
- Purchase/entry price per share
- **Always positive**, even for short positions
- For options: price per contract
- **Validation**:
  - Must be positive (> 0)
  - Max 2 decimal places
  - Must be valid decimal number

### 3.4 Entry Date (Required)
- Date position was entered
- **Format**: `YYYY-MM-DD` (ISO 8601)
- Used for cost basis and P&L calculations
- **Validation**:
  - Cannot be in future
  - Cannot be >100 years old
  - Must be valid date in YYYY-MM-DD format

## 4. Optional Columns

### 4.1 Investment Class
- Valid values: `PUBLIC`, `OPTIONS`, or `PRIVATE`
- Leave blank for auto-detection
- **Auto-detection logic**:
  - Has options fields (Underlying/Strike/Expiration) → `OPTIONS`
  - Default → `PUBLIC`

### 4.2 Investment Subtype
- Valid values depend on Investment Class:
  - **PUBLIC**: `STOCK`, `ETF`, `MUTUAL_FUND`, `BOND`, `CASH`
  - **OPTIONS**: `CALL`, `PUT`
  - **PRIVATE**: `PRIVATE_EQUITY`, `VENTURE_CAPITAL`, `HEDGE_FUND`, `PRIVATE_REIT`, `REAL_ESTATE`, `CRYPTOCURRENCY`, `CRYPTO`, `ART`, `MONEY_MARKET`, `TREASURY_BILLS`, `CASH`, `COMMODITY`, `OTHER`

### 4.3 Options-Specific Columns

**Important**: All four options columns are **required** when Investment Class = `OPTIONS`.

**Underlying Symbol**:
- **Required** if Investment Class = `OPTIONS`
- Underlying stock/ETF symbol (e.g., "SPY")

**Strike Price**:
- **Required** if Investment Class = `OPTIONS`
- Strike price as decimal (e.g., 450.00)

**Expiration Date**:
- **Required** if Investment Class = `OPTIONS`
- Format: `YYYY-MM-DD`

**Option Type**:
- **Required** if Investment Class = `OPTIONS`
- Valid values: `CALL` or `PUT`

### 4.4 Closed Position Columns

**Exit Date**:
- Optional, for closed positions
- Format: `YYYY-MM-DD`
- Must be after Entry Date

**Exit Price Per Share**:
- Optional, for closed positions
- Exit price as decimal

## 5. File Format Rules

### 5.1 General Requirements
- **Encoding**: UTF-8
- **File extension**: `.csv`
- **Max file size**: 10 MB
- **First row**: Must contain column headers (exact names)
- **Comment lines**: Lines starting with `#` are automatically ignored by parser
- **Empty rows**: Automatically skipped during processing

### 5.2 Data Formatting
- **Decimals**: Use period (`.`) as decimal separator
- **Dates**: YYYY-MM-DD format only
- **No currency symbols**: Remove `$`, `,` from numbers
- **No thousand separators**: Use `1000.00` not `1,000.00`
- **Blank cells**: Leave optional columns empty (do not use "N/A" or "-")

## 6. Position Type Determination

### 6.1 Stocks and ETFs
- **LONG**: `quantity > 0`
- **SHORT**: `quantity < 0`

### 6.2 Options

**Options positions require**:
- Symbol column filled (e.g., "SPY_C450_20240315")
- Investment Class = `OPTIONS`
- All four options columns: Underlying Symbol, Strike Price, Expiration Date, Option Type

**Position Types** (determined by quantity and option type):
- **Long Call**: Option Type = CALL, `quantity > 0`
- **Short Call**: Option Type = CALL, `quantity < 0`
- **Long Put**: Option Type = PUT, `quantity > 0`
- **Short Put**: Option Type = PUT, `quantity < 0`

## 7. Example CSV Files

### 7.1 Minimal Example (4 Required Columns Only)

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,,,,,,,,
MSFT,50,380.00,2024-01-20,,,,,,,,
SPY,25,445.20,2024-02-01,,,,,,,,
```

### 7.2 Mixed Portfolio (Stocks + Options)

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,
MSFT,50,380.00,2024-01-20,PUBLIC,STOCK,,,,,,
SPY,25,445.20,2024-02-01,PUBLIC,ETF,,,,,,
SPY_C450_20240315,10,5.50,2024-02-01,OPTIONS,,SPY,450.00,2024-03-15,CALL,,
AAPL_P160_20240315,5,3.25,2024-02-05,OPTIONS,,AAPL,160.00,2024-03-15,PUT,,
```

### 7.3 Long/Short Equity Portfolio

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,1000,150.00,2024-01-15,PUBLIC,STOCK,,,,,,
MSFT,-500,380.00,2024-01-20,PUBLIC,STOCK,,,,,,
JPM,800,140.50,2024-02-01,PUBLIC,STOCK,,,,,,
TSLA,-200,195.00,2024-02-10,PUBLIC,STOCK,,,,,,
```

### 7.4 With Closed Positions

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
TSLA,50,185.00,2023-12-01,PUBLIC,STOCK,,,,2024-01-15,215.00
NVDA,25,450.00,2024-01-05,PUBLIC,STOCK,,,,,,
META,30,325.00,2024-01-08,PUBLIC,STOCK,,,,2024-02-01,355.00
```

## 8. Download Template

### 8.1 Via API

```bash
curl https://api.sigmasight.io/api/v1/onboarding/csv-template \
  -o portfolio_template.csv
```

### 8.2 Template Location

See `backend/Sample_Template.csv` for a downloadable template with examples.

## 9. Common Errors and Solutions

### 9.1 CSV Validation Errors

| Error Code | Error Message | Solution |
|------------|---------------|----------|
| ERR_CSV_001 | File too large (>10MB) | Split into multiple files |
| ERR_CSV_002 | Invalid file type (must be .csv) | Save as CSV format |
| ERR_CSV_003 | Empty file | Add position data |
| ERR_CSV_004 | Missing required column | Check header matches exactly |
| ERR_CSV_006 | Malformed CSV | Check for proper CSV formatting |

### 9.2 Position Validation Errors

| Error Code | Error Message | Solution |
|------------|---------------|----------|
| ERR_POS_001 | Symbol is required | Add symbol to row |
| ERR_POS_004 | Quantity is required | Add quantity to row |
| ERR_POS_006 | Quantity cannot be zero | Use non-zero quantity |
| ERR_POS_008 | Entry price is required | Add entry price to row |
| ERR_POS_010 | Entry price must be positive | Use positive price (even for shorts) |
| ERR_POS_012 | Entry date is required | Add entry date in YYYY-MM-DD format |
| ERR_POS_013 | Invalid date format | Use YYYY-MM-DD format |
| ERR_POS_014 | Entry date cannot be in future | Use past or current date |
| ERR_POS_023 | Duplicate position | Same symbol+date appears twice |

### 9.3 Options Validation Errors

| Error Code | Error Message | Solution |
|------------|---------------|----------|
| ERR_POS_019 | Underlying symbol required | Add underlying symbol for options |
| ERR_POS_020 | Strike price required | Add strike price for options |
| ERR_POS_021 | Expiration date required | Add expiration date for options |
| ERR_POS_022 | Invalid option type | Use CALL or PUT |

## 10. Common Issues

### 10.1 Date Format Errors
**Problem**: Excel changes dates to MM/DD/YYYY
**Solution**: Format cells as Text before entering dates, or use YYYY-MM-DD

### 10.2 Number Formatting
**Problem**: Excel adds thousand separators (1,000.00)
**Solution**: Format cells as Number with no thousand separator

### 10.3 Negative Prices for Shorts
**Problem**: Using negative entry price for short positions
**Solution**: Entry price is always positive, use negative quantity instead

### 10.4 Missing Required Columns
**Problem**: Column headers don't match exactly
**Solution**: Copy header row from template exactly (case-sensitive)

### 10.5 Blank Symbol Column
**Problem**: Leaving Symbol column empty for options or other positions
**Solution**: All positions require a symbol - use descriptive names like "SPY_C450_20240315"

## 11. Migration from Legacy Systems

### 11.1 From Paragon Excel

**Column Mapping**:
- `symbol` → `Symbol`
- `qty` or `quantity` → `Quantity`
- `price` → `Entry Price Per Share`
- `trade date` → `Entry Date`
- Leave optional columns blank

**Data Cleanup**:
1. Remove thousand separators: `1,000.00` → `1000.00`
2. Remove currency symbols: `$150.00` → `150.00`
3. Convert dates: `01/15/2024` → `2024-01-15`
4. Don't include calculated fields (market value, P&L, etc.)

### 11.2 From Broker Exports

**Schwab**:
- Map: Symbol → Symbol, Qty → Quantity
- Add Entry Date from transaction history
- Entry Price = Cost Basis ÷ Quantity

**Fidelity**:
- Similar to Schwab
- Watch for date format differences

**Interactive Brokers**:
- Export positions report
- Map columns accordingly
- Handle options in OCC format

## 12. Validation Process

### 12.1 File-Level Validation
1. File size < 10 MB
2. File extension is `.csv`
3. UTF-8 encoding
4. Valid CSV structure

### 12.2 Row-Level Validation
1. All 4 required columns present
2. Quantity is non-zero decimal
3. Entry price is positive decimal
4. Entry date is valid YYYY-MM-DD
5. If Investment Class = OPTIONS, all options fields required
6. Exit date > Entry date (if provided)
7. No duplicate positions (same symbol + entry date)

### 12.3 Processing
- **All-or-nothing import**: If any row fails validation, the entire import is rejected
- No partial imports - all positions must be valid
- Error response includes all validation failures with row numbers
- Duplicate detection prevents same position twice (same symbol + entry date)

## 13. Important Notes

- **Tags are NOT supported in CSV import** (use UI or API after import)
- **All-or-nothing import**: Any validation error aborts the entire import
- **Symbol required for all rows**: Cannot be blank, even for options
- **Options require all 4 columns**: Underlying Symbol, Strike Price, Expiration Date, Option Type
- **Investment Class auto-detection** works well for most cases
- **Short positions**: Use negative quantity, positive price
- **Closed positions**: Optional Exit Date/Exit Price columns
- **Maximum precision**: 6 decimals for quantity, 2 for prices
- **Comment lines (#) are automatically stripped** by the parser - no need to remove them manually

## 14. API Integration

### 14.1 Upload Endpoint

```bash
POST /api/v1/onboarding/create-portfolio
```

**Parameters**:
- `portfolio_name`: Display name (required)
- `account_name`: Unique account identifier (required)
- `account_type`: Account type (required - taxable, ira, roth_ira, 401k, 403b, 529, hsa, trust, other)
- `equity_balance`: Total account value (required)
- `description`: Optional description
- `csv_file`: CSV file upload (required)

### 14.2 Response

**Success**:
```json
{
  "portfolio_id": "uuid",
  "portfolio_name": "My Portfolio",
  "account_name": "main",
  "account_type": "taxable",
  "equity_balance": 250000.0,
  "positions_imported": 45,
  "positions_failed": 0,
  "total_positions": 45,
  "message": "Portfolio created successfully",
  "next_step": {
    "action": "calculate",
    "endpoint": "/api/v1/portfolio/{id}/calculate"
  }
}
```

**Validation Errors**:
```json
{
  "error": {
    "code": "ERR_PORT_008",
    "message": "CSV validation failed with 2 error(s)",
    "details": {
      "errors": [
        {
          "code": "ERR_POS_012",
          "message": "Entry date is required",
          "row": 5,
          "field": "Entry Date"
        }
      ]
    }
  }
}
```

---

**For complete API documentation, see**: `backend/_docs/reference/API_REFERENCE_V1.4.6.md`
