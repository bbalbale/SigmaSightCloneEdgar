# Backend Archive

**Last Updated**: 2025-11-28

This directory contains archived files from the backend that are no longer actively used but are preserved for historical reference.

## Directory Structure

| Directory | Contents | Purpose |
|-----------|----------|---------|
| `todos/` | TODO1-5.md | Historical task tracking from development phases |
| `debug/` | check_*.py, test_*.py | One-time debug scripts from root directory |
| `code-reviews/` | PHASE_2.10_CODE_REVIEW.md | Code review documentation |
| `guides/` | ONBOARDING_TESTS.md, etc. | Historical guides and verification docs |
| `incidents/` | DATABASE_FIXES.md, etc. | Incident reports and fix documentation |
| `planning/` | ANALYTICS_MAPPING.md, etc. | Historical planning documents |
| `deprecated_services/` | Unused service files | Code that was superseded or never used |
| `scripts/` | Old diagnostic scripts | Superseded by current scripts/ directory |
| `legacy_scripts_for_reference_only/` | Reference implementations | Old implementations for context |
| `migration_2025_10_29/` | PostgreSQL migration docs | October 2025 migration reference |
| `migration-scripts/` | Position/strategy migration | Scripts from strategy→tagging migration |
| `tagging-project/` | Tagging implementation docs | October 2025 tagging project planning |
| `config/` | Old config docs | Historical configuration documentation |
| `data-providers/` | Provider research | Historical data provider analysis |

## Cleanup Summary (2025-11-28)

### Files Archived
- **12 root-level files**: Debug scripts and documentation moved from backend root
- **2 deprecated services**: `market_data_service_async.py`, `seed_demo_familyoffice.py`

### When to Check This Archive

1. **Before recreating documentation**: Check if it already exists here
2. **Debugging historical issues**: Reference past incident reports
3. **Understanding design decisions**: Review planning documents
4. **Recovery**: If archived code/docs are needed, copy back to active location

## Related Documentation

- `backend/CLEANUP_PLAN.md` - Full cleanup plan and execution details
- `backend/scripts/_archive/README.md` - Archived scripts documentation
- `backend/CLAUDE.md` - Current AI agent instructions

## Notes

- All files remain accessible via git history
- No production functionality was affected by archiving
- Files are organized by type/purpose for easy discovery
