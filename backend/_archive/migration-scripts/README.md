# Position Tagging Migration Scripts (ARCHIVED)

**Archive Date:** October 4, 2025
**Reason:** Demo data only - migration unnecessary for fresh builds

## Purpose

These scripts were created during the October 2025 migration from **strategy tagging** (deprecated) to **position tagging** (preferred architecture). They handle data migration for existing portfolios.

## When to Use These Scripts

**Use these scripts ONLY if:**
- You need to preserve existing development or production data
- You have portfolios with strategy tags that need conversion to position tags
- Your partner wants to migrate his dev build data

**DO NOT use these scripts if:**
- Building fresh demo portfolios (use seed scripts instead)
- Starting a new deployment
- No existing user data to preserve

## Migration Scripts

### Position Tagging Migration
- `migrate_strategy_tags_to_positions.py` - Migrate old strategy tags to position tags
- `verify_position_tags_only.py` - Validate migration completion
- `check_position_tags.py` - Verify tagging system after migration

### Strategy Cleanup
- `separate_combined_strategies.py` - Split combined strategies
- `check_combined_strategies.py` - Identify combinations
- `delete_empty_strategies.py` - Remove empty records
- `update_strategy_names.py` - Standardize naming
- `check_empty_strategy_positions.py` - Find orphaned strategies
- `show_combined_strategy_positions.py` - Debug combinations

### Portfolio Verification
- `check_portfolios_tags.py` - Verify portfolio tags (migration specific)

## New Position Tagging Architecture

The current preferred architecture uses **direct position-to-tag relationships**:

### Database
- `position_tags` junction table with `unique(position_id, tag_id)`
- `company_profiles` table for enriched stock data (yfinance/yahooquery)

### Backend APIs
- **Position tagging**: `/api/v1/positions/{id}/tags` (position_tags.py)
- **Tag management**: `/api/v1/tags/` (tags.py)

### Frontend
- **Hooks**: `usePositionTags.ts` (replaces deprecated `useStrategies.ts`)
- **Services**: `tagsApi.ts` with position tagging methods

## Alternative for Fresh Builds

For demo data and fresh deployments, use the seed script instead:
```bash
cd backend
uv run python scripts/seed_database.py
```

This creates portfolios with the new position tagging architecture directly, avoiding migration complexity.

## Documentation References

- **Architecture**: `frontend/_docs/TAGGING_ARCHITECTURE.md`
- **Implementation**: `frontend/_docs/redotagging.md`
- **Company Profiles**: `frontend/_docs/CompanyProfilesTableRec.md`
- **Cleanup Plan**: `backend/TODO_REPO_CLEANUP.md` (Section 16)

---

**Note**: These scripts are preserved for reference and potential partner data migration. For new deployments, always prefer fresh seeding with the current architecture.
