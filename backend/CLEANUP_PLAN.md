# Backend Cleanup Plan

**Created**: 2025-11-28
**Status**: ✅ ALL PHASES COMPLETE
**Last Updated**: 2025-11-28
**Total Files Analyzed**: 573 Python files + 140+ documentation files

---

## Executive Summary

The backend cleanup has been completed. All one-time scripts, investigation files, and deprecated code have been archived while preserving core functionality.

**Cleanup Results:**
- **Files Archived**: 75+ files moved to `_archive/` directories
- **Directories Removed**: 6 empty directories cleaned up
- **Unused Code Identified**: 2 deprecated service files archived
- **Core Preserved**: All essential `app/`, `scripts/database/`, `scripts/railway/` files intact

**Final Structure:**
- Core application: ~178 essential files in `app/`
- Active scripts: ~40 files in production-use directories
- Archive: 200+ historical files for reference

---

## Table of Contents

1. [Core Files (DO NOT REMOVE)](#1-core-files-do-not-remove)
2. [Top-Level Files to Archive](#2-top-level-files-to-archive)
3. [Scripts Directory Analysis](#3-scripts-directory-analysis)
4. [Archive Directory Review](#4-archive-directory-review)
5. [App Directory Review](#5-app-directory-review)
6. [Documentation Files](#6-documentation-files)
7. [Implementation Phases](#7-implementation-phases)

---

## 1. Core Files (DO NOT REMOVE)

These directories and files are **essential** for production operation:

### Essential Directories
| Directory | Files | Purpose | Status |
|-----------|-------|---------|--------|
| `app/api/v1/` | 28 files | REST API endpoints (59 endpoints) | ESSENTIAL |
| `app/models/` | 16 files | SQLAlchemy ORM models | ESSENTIAL |
| `app/services/` | 37 files | Business logic layer | ESSENTIAL |
| `app/batch/` | 7 files | Batch processing framework | ESSENTIAL |
| `app/calculations/` | 14 files | Risk calculation engines | ESSENTIAL |
| `app/agent/` | 15+ files | AI chat system (OpenAI Responses API) | ESSENTIAL |
| `app/clients/` | 6 files | Data provider integrations | ESSENTIAL |
| `app/core/` | 10 files | Core utilities (auth, logging) | ESSENTIAL |
| `app/schemas/` | 18 files | Pydantic request/response schemas | ESSENTIAL |
| `alembic/` | 40+ files | Database migrations | ESSENTIAL |

### Essential Root Files
| File | Purpose | Status |
|------|---------|--------|
| `run.py` | Development server entry point | ESSENTIAL |
| `app/main.py` | FastAPI application initialization | ESSENTIAL |
| `app/config.py` | Settings and environment config | ESSENTIAL |
| `app/database.py` | Database connection utilities | ESSENTIAL |
| `CLAUDE.md` | AI agent instructions | ESSENTIAL |
| `README.md` | Project documentation | ESSENTIAL |
| `requirements.txt` | Python dependencies | ESSENTIAL |
| `pyproject.toml` | Project configuration | ESSENTIAL |
| `docker-compose.yml` | Database container config | ESSENTIAL |

---

## 2. Top-Level Files to Archive

These files in the backend root have been moved to `_archive/`:

### ✅ COMPLETED - Debug Scripts (Moved 2025-11-28)
| File | Size | New Location |
|------|------|--------------|
| `check_factors.py` | ~1KB | `_archive/debug/check_factors.py` |
| `check_login.py` | ~1KB | `_archive/debug/check_login.py` |
| `test_option_c.py` | ~2KB | `_archive/debug/test_option_c.py` |
| `test_option_c_simple.py` | ~1KB | `_archive/debug/test_option_c_simple.py` |
| `show_option_c_difference.py` | ~1KB | `_archive/debug/show_option_c_difference.py` |

### ✅ COMPLETED - Documentation (Moved 2025-11-28)
| File | Size | New Location |
|------|------|--------------|
| `TODO5.md` | 187KB | `_archive/todos/TODO5.md` |
| `PHASE_2.10_CODE_REVIEW.md` | 15KB | `_archive/code-reviews/PHASE_2.10_CODE_REVIEW.md` |
| `ONBOARDING_TESTS.md` | 17KB | `_archive/guides/ONBOARDING_TESTS.md` |
| `OPTION_C_VERIFICATION_GUIDE.md` | 7.5KB | `_archive/guides/OPTION_C_VERIFICATION_GUIDE.md` |
| `DATABASE_FIXES.md` | ~5KB | `_archive/incidents/DATABASE_FIXES.md` |
| `FIRST_DAY_PNL_FIX.md` | ~3KB | `_archive/incidents/FIRST_DAY_PNL_FIX.md` |
| `ANALYTICS_MAPPING.md` | ~3KB | `_archive/planning/ANALYTICS_MAPPING.md` |

### Keep at Root
| File | Reason |
|------|--------|
| `CLAUDE.md` | Active AI agent instructions |
| `README.md` | Project documentation |
| `requirements.txt` | Dependencies |
| `pyproject.toml` | Project config |
| `docker-compose.yml` | Database setup |

---

## 3. Scripts Directory Analysis

### 3.1 KEEP - Production/Active Scripts

#### `scripts/database/` (13 files) - KEEP ALL
| File | Purpose | Used By |
|------|---------|---------|
| `reset_and_seed.py` | Authoritative seeding script | Manual/CI |
| `seed_demo_portfolios.py` | Demo data creation | Seeding |
| `user_management.py` | User CRUD operations | Admin |
| `corrected_seed_data.txt` | Seed data definitions | Seeding |
| Other utility files | Database operations | Various |

#### `scripts/railway/` (15 files) - KEEP ALL
| File | Purpose | Status |
|------|---------|--------|
| `audit_railway_data.py` | Production data audit | Active |
| `audit_railway_market_data.py` | Market data audit | Active |
| `audit_railway_analytics.py` | Analytics audit | Active |
| `audit_railway_calculations_verbose.py` | Calculation audit | Active |
| `railway_batch_job.py` | Railway cron job | Production |
| Migration and deployment scripts | Production ops | Active |

#### `scripts/automation/` (4 files) - KEEP ALL
| File | Purpose | Status |
|------|---------|--------|
| `railway_batch_cron.py` | Railway cron entry point | Production |
| Other automation scripts | Scheduled tasks | Active |

#### `scripts/verification/` (15 files) - KEEP ALL
| File | Purpose | Status |
|------|---------|--------|
| `check_database_content.py` | Database verification | Active |
| `verify_demo_portfolios.py` | Demo data validation | Active |
| `verify_batch_orchestrator.py` | Batch system check | Active |
| Other verification scripts | System diagnostics | Active |

#### `scripts/monitoring/` (4 files) - KEEP ALL
| File | Purpose | Status |
|------|---------|--------|
| Production monitoring scripts | Health checks | Active |

---

### 3.2 ARCHIVE - One-Time Use Scripts

#### `scripts/analysis/` (40+ files) - REVIEW & ARCHIVE MOST

**Files to KEEP** (general-purpose tools):
| File | Purpose |
|------|---------|
| `analyze_portfolio.py` | Generic portfolio analysis |
| `debug_market_data.py` | Market data debugging |
| `check_position_values.py` | Position validation |

**Files to ARCHIVE** (investigation-specific):
| File | Reason |
|------|--------|
| `analyze_etf_spy_issue.py` | One-time investigation |
| `debug_aggregation_source_nov20.py` | Dated investigation |
| `investigate_correlation_discrepancy.py` | One-time debug |
| `test_factor_exposure_endpoint.py` | One-time test |
| `check_sarah_positions.py` | User-specific debug |
| `check_wednesday_issue.py` | Dated investigation |
| Most files with dates in name | One-time investigations |
| Most files starting with `debug_` | One-time debugging |
| Most files starting with `investigate_` | One-time investigations |
| Most files starting with `test_` | One-time tests |

#### `scripts/data_operations/` (15 files) - REVIEW & ARCHIVE MOST

**Files to KEEP**:
| File | Purpose |
|------|---------|
| `backfill_market_data.py` | Data backfill utility |
| `populate_etf_prices.py` | ETF data population |

**Files to ARCHIVE**:
| File | Reason |
|------|--------|
| `export_portfolio_*.py` | One-time exports |
| `fix_*.py` | One-time fixes |
| Dated backup scripts | Historical backups |

#### `scripts/migrations/` (10 files) - ARCHIVE ALL

All migration scripts are one-time use and should be archived after successful migration:
| File | Status |
|------|--------|
| All files | Completed migrations, ARCHIVE |

#### `scripts/testing/` - ARCHIVE OR MOVE TO tests/
One-time test scripts should be archived or formalized into the test suite.

---

### 3.3 Already Archived

#### `scripts/_archive/` - NO ACTION NEEDED
Already contains old scripts that were previously archived. Keep as historical reference.

#### `scripts/DANGEROUS_DESTRUCTIVE_SCRIPTS/` - KEEP WITH CAUTION
| File | Purpose | Status |
|------|---------|--------|
| `DANGEROUS_railway_reset_database.py` | Full DB reset | Emergency only |
| `DANGEROUS_reseed_july_2025_complete.py` | Historical reseed | Reference |
| Other destructive scripts | Emergency operations | Keep isolated |

---

## 4. Archive Directory Review

### `_archive/` Current Contents

| Subdirectory | Size | Purpose | Recommendation |
|--------------|------|---------|----------------|
| `todos/` | 692KB | TODO1-4.md historical tracking | KEEP (reference) |
| `scripts/` | 661KB | Old diagnostic scripts | KEEP (reference) |
| `planning/` | 552KB | PRDs, specs, design docs | KEEP (reference) |
| `migration_2025_10_29/` | 112KB | PostgreSQL migration | KEEP (recent) |
| `legacy_scripts_for_reference_only/` | 212KB | Old implementations | KEEP (reference) |
| `incidents/` | 177KB | Incident reports | KEEP (debugging) |
| `migration-scripts/` | 68KB | Position/strategy migration | KEEP (rollback) |
| `tagging-project/` | 156KB | Position tagging docs | KEEP (reference) |
| `guides/` | 52KB | Historical guides | KEEP (reference) |
| `config/` | 12KB | Old config docs | KEEP (reference) |
| `data-providers/` | 20KB | Provider research | KEEP (reference) |

**Recommendation**: Keep entire `_archive/` directory as historical reference. It's already properly organized.

---

## 5. App Directory Review

### 5.1 Potential Duplicates/Redundant Files

| File | Size | Potential Issue | Action Required |
|------|------|-----------------|-----------------|
| `app/services/market_data_service.py` | 61KB | Primary implementation | KEEP |
| `app/services/market_data_service_async.py` | 12KB | May be redundant | VERIFY USAGE |

**Verification Command:**
```bash
cd backend
grep -r "market_data_service_async" app/ --include="*.py"
```

If no imports found → ARCHIVE

### 5.2 Large Files to Consider Refactoring (NOT REMOVING)

These files are essential but could benefit from refactoring:

| File | Size | Issue | Recommendation |
|------|------|-------|----------------|
| `app/api/v1/data.py` | 57KB | Multiple endpoints in one file | Consider splitting |
| `app/services/market_data_service.py` | 61KB | Very large service | Consider splitting |
| `app/api/v1/insights.py` | 31KB | Large insights file | Review for splitting |

**Note**: These are NOT candidates for removal, only for future refactoring.

### 5.3 Database Seed Files in app/db/

| File | Purpose | Recommendation |
|------|---------|----------------|
| `seed_demo_portfolios.py` | Demo data | KEEP - used by seeding |
| `seed_demo_familyoffice.py` | Family office demo | VERIFY USAGE |
| `seed_factors.py` | Factor definitions | KEEP |
| `seed_initial_prices.py` | Initial prices | KEEP |
| `seed_security_master.py` | Security master | KEEP |
| `fetch_historical_data.py` | Historical data | KEEP |
| `snapshot_helpers.py` | Snapshot utilities | KEEP |
| `verify_schema.py` | Schema verification | KEEP |

---

## 6. Documentation Files

### `_docs/` Directory

| Subdirectory | Contents | Recommendation |
|--------------|----------|----------------|
| `reference/` | API reference docs | KEEP |
| `requirements/` | Product requirements | KEEP |
| `architecture/` | Architecture docs | KEEP |
| Other docs | Various documentation | REVIEW |

### Recommendation
Keep all `_docs/` content - documentation is valuable for onboarding and reference.

---

## 7. Implementation Phases

### Phase 1: Immediate Cleanup (No Risk) ✅ COMPLETED 2025-11-28
**Estimated Time**: 30 minutes
**Risk Level**: None
**Status**: ✅ COMPLETE

**Completed Actions:**
1. ✅ Created archive subdirectories: `_archive/debug/`, `_archive/code-reviews/`, `_archive/guides/`, `_archive/incidents/`, `_archive/planning/`

2. ✅ Moved 5 debug scripts to `_archive/debug/`:
   - `check_factors.py`
   - `check_login.py`
   - `test_option_c.py`
   - `test_option_c_simple.py`
   - `show_option_c_difference.py`

3. ✅ Moved 7 documentation files to `_archive/`:
   - `TODO5.md` → `_archive/todos/TODO5.md`
   - `PHASE_2.10_CODE_REVIEW.md` → `_archive/code-reviews/`
   - `ONBOARDING_TESTS.md` → `_archive/guides/`
   - `OPTION_C_VERIFICATION_GUIDE.md` → `_archive/guides/`
   - `DATABASE_FIXES.md` → `_archive/incidents/`
   - `FIRST_DAY_PNL_FIX.md` → `_archive/incidents/`
   - `ANALYTICS_MAPPING.md` → `_archive/planning/`

**Files Archived**: 12 total (~250KB)

### Phase 2: Scripts Cleanup (Low Risk)
**Estimated Time**: 1-2 hours
**Risk Level**: Low

1. Archive investigation-specific scripts from `scripts/analysis/`:
   - All files with dates in name
   - All files starting with `debug_`, `investigate_`, `test_`
   - Create `scripts/_archive/analysis_investigations/`

2. Archive one-time data operation scripts:
   - Move completed migration scripts
   - Move one-time export scripts

3. Archive migration scripts:
   - Move all `scripts/migrations/` to `_archive/migrations/`

### Phase 3: Verification & Consolidation (Medium Risk)
**Estimated Time**: 2-3 hours
**Risk Level**: Medium

1. Verify `market_data_service_async.py` usage:
   ```bash
   grep -r "market_data_service_async" app/ --include="*.py"
   ```
   If unused → Archive

2. Consolidate remaining analysis scripts:
   - Keep only general-purpose tools
   - Create README documenting purpose of each

3. Verify `seed_demo_familyoffice.py` usage:
   - If unused by seeding → Archive

### Phase 4: Documentation Update (No Risk)
**Estimated Time**: 1 hour
**Risk Level**: None

1. Update `CLAUDE.md` with new structure
2. Create `scripts/README.md` documenting each script's purpose
3. Update `_archive/README.md` with archive contents

---

## Files Summary

### Files to Archive (Move to _archive/)

#### From Root (~250KB)
```
check_factors.py
check_login.py
test_option_c.py
test_option_c_simple.py
show_option_c_difference.py
TODO5.md
PHASE_2.10_CODE_REVIEW.md
ONBOARDING_TESTS.md
OPTION_C_VERIFICATION_GUIDE.md
DATABASE_FIXES.md
FIRST_DAY_PNL_FIX.md
ANALYTICS_MAPPING.md
```

#### From scripts/analysis/ (~500KB estimated)
All investigation-specific scripts (files with dates, debug_, investigate_, test_ prefixes)

#### From scripts/data_operations/ (~100KB estimated)
One-time export and fix scripts

#### From scripts/migrations/ (~100KB estimated)
All completed migration scripts

### Files to Verify Before Action

| File | Verification Needed |
|------|---------------------|
| `app/services/market_data_service_async.py` | Check if imported anywhere |
| `app/db/seed_demo_familyoffice.py` | Check if used by seeding |

### Files to Keep (No Changes)

- All files in `app/` (except verification targets above)
- `scripts/database/`
- `scripts/railway/`
- `scripts/automation/`
- `scripts/verification/`
- `scripts/monitoring/`
- `scripts/batch_processing/`
- `alembic/`
- `_docs/`
- `_archive/` (already archived content)

---

## Execution Checklist

- [x] Phase 1: Archive top-level debug scripts ✅ (2025-11-28)
- [x] Phase 1: Archive top-level documentation ✅ (2025-11-28)
- [x] Phase 2: Archive analysis investigation scripts ✅ (2025-11-28) - 25 files
- [x] Phase 2: Archive data operation one-time scripts ✅ (2025-11-28) - 7 files
- [x] Phase 2: Archive migration scripts ✅ (2025-11-28) - 7 files
- [x] Phase 2: Archive root-level one-time scripts ✅ (2025-11-28) - 30+ files
- [x] Phase 3: Verify market_data_service_async.py usage ✅ - UNUSED, archived
- [x] Phase 3: Verify seed_demo_familyoffice.py usage ✅ - UNUSED, archived
- [x] Phase 4: Update CLAUDE.md ✅ (2025-11-28)
- [x] Phase 4: Update CLEANUP_PLAN.md ✅ (2025-11-28)

---

## Cleanup Summary

### Phase 1: Root-Level Cleanup (12 files)
- 5 debug scripts → `_archive/debug/`
- 7 documentation files → `_archive/{todos,code-reviews,guides,incidents,planning}/`

### Phase 2: Scripts Directory Cleanup (69+ files)
- 25 analysis investigation scripts → `scripts/_archive/analysis_investigations/`
- 7 data operations one-time scripts → `scripts/_archive/data_ops_one_time/`
- 7 migration scripts → `scripts/_archive/completed_migrations/`
- 20+ one-time fixes/tests → `scripts/_archive/one_time_fixes/`
- 10+ root production scripts → `scripts/_archive/root_scripts/`

### Phase 3: App Directory Cleanup (2 files)
- `market_data_service_async.py` → `_archive/deprecated_services/` (unused)
- `seed_demo_familyoffice.py` → `_archive/deprecated_services/` (unused)

### Directories Removed (Empty)
- `scripts/migrations/`
- `scripts/utilities/`
- `scripts/diagnostics/`
- `scripts/testing/`
- `scripts/repair/`
- `scripts/test/`

---

## Final Scripts Structure

```
scripts/
├── _archive/                    # Archived one-time scripts
│   ├── analysis_investigations/ # Investigation-specific analysis
│   ├── completed_migrations/    # Completed migration scripts
│   ├── data_ops_one_time/      # One-time data operations
│   ├── one_time_fixes/         # One-time fixes and tests
│   ├── root_scripts/           # Archived root-level scripts
│   ├── manual_tests/           # Manual test scripts
│   └── testing_suite/          # Old testing suite
│
├── analysis/                    # Active analysis tools (15 files)
├── automation/                  # Railway cron automation
├── batch_processing/            # Batch job helpers
├── DANGEROUS_DESTRUCTIVE_SCRIPTS/ # Emergency reset scripts
├── data_operations/             # Active data tools (11 files)
├── database/                    # Database management (KEEP ALL)
├── debug/                       # Quick debug utilities
├── monitoring/                  # Production monitoring
├── railway/                     # Railway deployment (KEEP ALL)
├── verification/                # System verification (KEEP ALL)
└── README.md                    # Scripts documentation
```

---

## Notes

- All archived files remain accessible in `_archive/` directories for reference
- No production functionality was affected
- Git history preserves all file changes for recovery if needed
- Core functionality verified: batch processing, API endpoints, database operations
