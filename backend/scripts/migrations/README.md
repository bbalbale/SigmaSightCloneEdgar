# Migration Scripts

One-time fixes and data migrations.

## Key Scripts

### DateTime Migrations
- **migrate_datetime_now.py** - Migrate datetime.now() usage
- **audit_datetime_usage.py** - Audit datetime usage patterns

### Data Fixes
- **fix_data_endpoints.py** - Fix data endpoint issues
- **fix_treasury_integration.py** - Fix treasury rate integration
- **fix_utf8_encoding.py** - Fix UTF-8 encoding issues
- **fix_zoom_ticker.py** - Fix Zoom ticker symbol issue
- **update_equity_values.py** - Update equity position values

## Usage

These scripts are typically run once to fix specific issues:

```bash
cd backend
# Fix UTF-8 encoding
uv run python scripts/migrations/fix_utf8_encoding.py

# Migrate datetime usage
uv run python scripts/migrations/migrate_datetime_now.py

# Fix treasury integration
uv run python scripts/migrations/fix_treasury_integration.py
```

## Important Notes

- Most migration scripts are idempotent (safe to run multiple times)
- Always backup database before running migrations
- Check script comments for specific prerequisites
- Some migrations may require stopping the application first