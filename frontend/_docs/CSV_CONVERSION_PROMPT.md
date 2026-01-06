# CSV Conversion Prompt for Test Customers

Copy and paste the prompt below into ChatGPT (or Claude) along with your existing portfolio data to convert it to SigmaSight's format.

---

## PROMPT TO COPY:

```
I need you to convert my portfolio data into a specific CSV format for SigmaSight. Please follow these instructions exactly.

## TARGET FORMAT (12 columns)

The output CSV must have this exact header row:
```
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
```

## COLUMN DEFINITIONS

**Required columns (must have values):**
1. **Symbol** - Stock/ETF ticker (e.g., AAPL, SPY) or descriptive option name (e.g., SPY_C450_20240315)
2. **Quantity** - Number of shares/contracts. Use NEGATIVE numbers for short positions (e.g., -100)
3. **Entry Price Per Share** - Purchase price per share. Always POSITIVE, even for shorts
4. **Entry Date** - Date acquired in YYYY-MM-DD format (e.g., 2024-01-15)

**Optional columns (leave empty if not applicable):**
5. **Investment Class** - One of: PUBLIC, OPTIONS, or PRIVATE (auto-detected if blank)
6. **Investment Subtype** - STOCK, ETF, MUTUAL_FUND, BOND, CASH, CALL, PUT, etc.
7. **Underlying Symbol** - For options only: the underlying stock (e.g., SPY)
8. **Strike Price** - For options only: the strike price (e.g., 450.00)
9. **Expiration Date** - For options only: expiration in YYYY-MM-DD format
10. **Option Type** - For options only: CALL or PUT
11. **Exit Date** - For closed positions: exit date in YYYY-MM-DD format
12. **Exit Price Per Share** - For closed positions: exit price

## CONVERSION RULES

1. **Dates**: Convert ALL dates to YYYY-MM-DD format
   - "1/15/2024" → "2024-01-15"
   - "Jan 15, 2024" → "2024-01-15"
   - "15-Jan-24" → "2024-01-15"

2. **Numbers**: Remove currency symbols and thousand separators
   - "$1,500.00" → "1500.00"
   - "1,000" → "1000"

3. **Short positions**: Use NEGATIVE quantity, POSITIVE price
   - Short 100 shares at $50 → Quantity: -100, Entry Price: 50.00

4. **Options**: Create a descriptive symbol and fill ALL option columns
   - SPY $450 Call expiring Mar 15, 2024 → Symbol: SPY_C450_20240315
   - Fill: Underlying Symbol=SPY, Strike Price=450.00, Expiration Date=2024-03-15, Option Type=CALL

5. **Empty optional columns**: Leave blank (no "N/A" or "-")

## EXAMPLES

**Stock (long):**
```
AAPL,100,175.50,2024-01-15,PUBLIC,STOCK,,,,,,
```

**Stock (short - note negative quantity):**
```
TSLA,-50,250.00,2024-02-01,PUBLIC,STOCK,,,,,,
```

**ETF:**
```
SPY,25,450.00,2024-01-20,PUBLIC,ETF,,,,,,
```

**Call Option:**
```
SPY_C450_20240315,10,5.50,2024-02-01,OPTIONS,,SPY,450.00,2024-03-15,CALL,,
```

**Put Option:**
```
AAPL_P170_20240419,5,3.25,2024-03-01,OPTIONS,,AAPL,170.00,2024-04-19,PUT,,
```

**Closed position (sold):**
```
NVDA,30,450.00,2023-06-15,PUBLIC,STOCK,,,,2024-01-10,550.00
```

**Cash/Money Market:**
```
SPAXX,50000,1.00,2024-01-01,PUBLIC,CASH,,,,,,
```

## YOUR TASK

Convert the following portfolio data to the SigmaSight CSV format. Output ONLY the CSV with:
1. The header row (exactly as shown above)
2. One row per position
3. No extra text, explanations, or formatting

Here is my portfolio data to convert:

[PASTE YOUR DATA HERE]
```

---

## TIPS FOR TESTERS

1. **Paste your data** after the prompt where it says "[PASTE YOUR DATA HERE]"
2. Your data can be in any format - spreadsheet columns, broker statements, even plain text lists
3. If the AI isn't sure about something, it will make reasonable assumptions
4. **Verify the output** before uploading - check dates and prices look correct
5. The AI will leave optional columns empty if your data doesn't include that information

## EXAMPLE INPUT/OUTPUT

**Example input you might paste:**
```
My Fidelity positions:
- 100 shares AAPL bought Jan 2024 at $175
- 50 shares MSFT bought Feb 2024 at $380
- Short 25 SHOP at $62.50 from Feb 10
- SPY March 450 calls (10 contracts) at $5.50
```

**AI will output:**
```
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,175.00,2024-01-15,PUBLIC,STOCK,,,,,,
MSFT,50,380.00,2024-02-15,PUBLIC,STOCK,,,,,,
SHOP,-25,62.50,2024-02-10,PUBLIC,STOCK,,,,,,
SPY_C450_20240315,10,5.50,2024-03-01,OPTIONS,,SPY,450.00,2024-03-15,CALL,,
```

---

## QUESTIONS?

Contact support if you have issues with the conversion or upload process.
