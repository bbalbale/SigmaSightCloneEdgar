# Migration Scripts

Active one-time fixes and data migrations.

> **Note**: Completed migration scripts have been archived to `../../_archive/scripts/migrations/`

## Active Scripts

### Data Fixes
- **fix_data_endpoints.py** - Fix data endpoint issues
- **fix_treasury_integration.py** - Fix treasury rate integration
- **fix_zoom_ticker.py** - Fix Zoom ticker symbol issue
- **audit_datetime_usage.py** - Audit datetime usage patterns
- **migrate_position_tags_to_strategy_tags.py** - Migrate tagging system

## Archived Scripts (Completed)

The following scripts have been completed and archived to `../../_archive/scripts/migrations/`:
- **fix_utf8_encoding.py** ✅ COMPLETED (UTF-8 now handled automatically)
- **migrate_datetime_now.py** ✅ COMPLETED (datetime migration done)
- **update_equity_values.py** ✅ COMPLETED (equity values set)

See `../../_archive/scripts/README.md` for complete archive listing.

## Usage

These scripts are typically run once to fix specific issues:

```bash
cd backend
# Fix treasury integration
uv run python scripts/migrations/fix_treasury_integration.py

# Audit datetime usage
uv run python scripts/migrations/audit_datetime_usage.py
```

## Important Notes

- Most migration scripts are idempotent (safe to run multiple times)
- Always backup database before running migrations
- Check script comments for specific prerequisites
- Some migrations may require stopping the application first
- **17 one-time migration scripts** archived on 2025-10-04