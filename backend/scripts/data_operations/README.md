# Data Operations Scripts

Scripts for fetching, managing, and exporting market data.

## Key Scripts

### ETF Data Management
- **fetch_factor_etf_data.py** - Fetch factor ETF historical data from providers
- **backfill_factor_etfs.py** - Backfill missing ETF data
- **check_etf_data.py** - Verify ETF data quality
- **check_etf_mapping.py** - Check ETF factor mappings
- **export_factor_etf_data.py** - Export ETF data to files

### Position Data
- **backfill_position_symbols.py** - Fix missing position symbols
- **sample_data_generator.py** - Generate sample market data

### Target Prices
- **populate_target_prices_via_service.py** ⭐ **MAIN** - Populate target prices from CSV
- **populate_target_prices.py** - Legacy target price population

### Data Fetching
- **fetch_with_round_robin.py** - Round-robin fetch across multiple providers

## Common Commands

### Fetch factor ETF data:
```bash
cd backend
uv run python scripts/data_operations/fetch_factor_etf_data.py
```

### Backfill missing data:
```bash
uv run python scripts/data_operations/backfill_factor_etfs.py
```

### Check data quality:
```bash
uv run python scripts/data_operations/check_etf_data.py
```

### Export data:
```bash
uv run python scripts/data_operations/export_factor_etf_data.py
```

## Data Sources

- **Primary**: Financial Modeling Prep (FMP)
- **Options**: Polygon.io
- **Economic**: FRED API

## Factor ETFs Tracked

- SPY (Market Beta)
- IWM (Size Factor - Small Cap) - Changed from SLY
- VTV (Value Factor)
- VUG (Growth Factor)
- MTUM (Momentum Factor)
- QUAL (Quality Factor)
- USMV (Low Volatility)

See **FACTOR_ETF_REFERENCE.md** in this directory for complete details and change history.