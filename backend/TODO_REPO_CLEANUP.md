# TODO: Repository Cleanup Tasks

**Created:** 2025-09-23
**Last Updated:** 2025-10-04
**Purpose:** Clean up the backend repository by removing outdated files and updating documentation to reflect current state

> ℹ️ Follow CLAUDE/AGENTS guardrails. Where a section calls out `AGENTS.md` or other instruction files, avoid edits unless the owning document explicitly allows them.

---

## RECENT CHANGES (October 2025)

### Position Tagging System Migration
The project has migrated from **strategy tagging** (deprecated) to **position tagging** (preferred). This impacts cleanup priorities:

**New Architecture Components:**
- ✅ Backend: `/api/v1/position_tags.py`, `position_tag_service.py`
- ✅ Frontend: Deleted `useStrategies.ts`, added `usePositionTags.ts`
- ✅ Database: `position_tags` junction table, `company_profiles` table
- ✅ Documentation: `TAGGING_ARCHITECTURE.md`, `redotagging.md`

**New Migration Scripts (scripts/):**
- `migrate_strategy_tags_to_positions.py` - Migrate old strategy tags to position tags
- `check_position_tags.py` - Verify position tagging system
- `verify_position_tags_only.py` - Validate migration completion
- `separate_combined_strategies.py` - Split combined strategies
- `check_combined_strategies.py` - Identify combined strategies
- `delete_empty_strategies.py` - Clean up empty strategy records
- `update_strategy_names.py` - Standardize strategy naming

**New Data Integration:**
- `populate_company_profiles.py` - Fetch company data via yfinance/yahooquery
- `test_yfinance_integration.py` - Test new data provider
- `monitor_provider_usage.py` - Track API usage and costs

**Action Required:** These migration scripts should be **documented** in a new section (see Section 16 below) rather than cleaned up, as they represent the current state of the system.

---

## 1. Rationalize Root-Level Manual Test Scripts

### Files to Relocate or Merge:
- [x] ~~`test_target_prices_api.py`~~ - **ALREADY MOVED** to `scripts/` ✅
- [x] ~~`test_target_prices_comprehensive.py`~~ - **ALREADY MOVED** to `scripts/` ✅
- [x] ~~`test_target_prices_detailed.py`~~ - **ALREADY MOVED** to `scripts/` ✅
- [ ] `test_auth_dependency.py` (manually pokes auth dependency)
- [ ] `test_auth.py` (HTTP smoketest using `requests`)
- [ ] `test_minimal_api.py`
- [ ] `test_service_direct.py` - **NOT FOUND** (may have been removed) ✅
- [ ] `test_model_imports.py` - **NEW** - verify model imports work
- [ ] `test_orm_relationships.py` - **NEW** - verify ORM relationships

**Action:** Migrate remaining auth test scripts to `scripts/manual_tests/`.

---

## 2. Rehome Legacy Verification Scripts

### Files to Relocate/Update:
- [ ] `check_equity_values.py` - Still exists
- [ ] `get_demo_portfolio.py` - Still exists
- [ ] `manual_test_ids.py` - Still exists
- [ ] `seed_positions_only.py` - Still exists
- [x] ~~`verify_portfolio_ids.py`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`verify_target_prices.py`~~ - **NOT FOUND** (removed) ✅
- [ ] `check_portfolio.py` - Still exists (simple script)
- [ ] `check_users.py` - **NEW** - verify user accounts
- [ ] `run_model_test.py` - **NEW** - test model loading
- [ ] `run_orm_test.py` - **NEW** - test ORM functionality

**Action:** Move still-relevant helpers into `scripts/verification/` and document workflows in `scripts/README.md`. Consider whether the new `check_users.py` and ORM test scripts belong in `tests/` instead.

---

## 3. Remove Historical Git History Files

### Files to Remove:
- [ ] `detailed_git_history_ending_0720.txt`
- [ ] `detailed_git_history_ending_0808.txt`
- [ ] `detailed_git_history_ending_0810.txt`
- [x] ~~`detailed_git_history_ending_0905.txt`~~ - **NOT FOUND** (removed) ✅

**Action:** Remove these files.

---

## 4. Clean Up Chat/Monitoring Harnesses

### JavaScript Harnesses (depend on `backend/package.json`):
- [x] ~~`comprehensive_chat_test.js`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`test_chat_flow.js`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`monitoring_session.js`~~ - **NOT FOUND** (removed) ✅

### Python Monitoring Utility:
- [ ] `simple_monitor.py` - Still exists

### Related Files:
- [x] ~~`chat_test_results.json`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`chat_test_results_comprehensive.json`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`phase_10_5_results.json`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`portfolio_context_smoke_test_report.json`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`chat_monitoring_report.json`~~ - **NOT FOUND** (removed) ✅

### Package.json Status:
- [ ] `backend/package.json` - **STILL EXISTS** - Used for Playwright in tests

**Action:** ✅ **MOSTLY COMPLETE** - JS harnesses removed. Keep `backend/package.json` for Playwright support (used by MCP tools for browser automation). Relocate `simple_monitor.py` to `scripts/monitoring/` with documentation.

---

## 5. Archive Error/Debug Documentation

### Files to Archive:
- [ ] `BACKEND_COMPUTE_ERROR.md` (86KB - very large)
- [ ] `backend_compute_Error_Sept.md`
- [ ] `TODO_9_18_DEBUG_REPORT.md`

**Constraints:** `OPENAI_STREAMING_BUG_REPORT.md` is explicitly whitelisted in root `.gitignore`; keep tracked with explanatory note.

**Action:** Move resolved items to `_archive/incidents/`.

---

## 6. Update or Remove Implementation Planning Docs

### Files to Update or Archive:
- [ ] `Target_Price_and_Investment_Classes_Implementation_Plan.md`
- [ ] `Target_Price_Summary_For_Ben_09-18-2025.md`
- [ ] `README_TARGET_PRICES_IMPORT.md`
- [ ] `IMPLEMENT_NEW_API_PROMPT.md`
- [ ] `TEST_NEW_API_PROMPT.md`

**Action:** Verify against current target-price workflows in `scripts/test_target_prices_api.py` and `data/target_prices_import.csv`. Archive under `_docs/`

---

## 7. Consolidate Workflow Guides

### Files to Review:
- [ ] `BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`
- [ ] `BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md`
- [ ] `ONBOARDING_NEW_ACCOUNT_PORTFOLIO.md`

**Action:** Move these guides to `setup-guides/archive/`.

---

## 8. Update Core Documentation

### Files Needing Updates:
- [ ] `README.md` (very brief - needs expansion) - Don't change this right now.
- [ ] `API_IMPLEMENTATION_STATUS.md` (deprecated placeholder) - Delete this file.
- [ ] `AGENTS.md` (align with CLAUDE.md)
- [ ] `CLAUDE.md` - **UPDATED** (Aug 2025) with current architecture ✅

**New Documentation to Reference:**
- `frontend/_docs/TAGGING_ARCHITECTURE.md` - Position tagging system architecture
- `frontend/_docs/CompanyProfilesTableRec.md` - Company profiles implementation
- `frontend/_docs/redotagging.md` - Tagging system redesign notes
- `ORGANIZE_PAGE_REDESIGN_PLAN.md` - Organize page architecture

**Action:** Expand README with current status, setup, API, and testing instructions. Delete deprecated API status file. Ensure `AI_AGENT_REFERENCE.md` references new architecture docs.

---

## 9. TODO Files

### Leave these files alone:
- [ ] `TODO1.md` (162KB) - Phase 1 complete
- [ ] `TODO2.md` (98KB) - Phase 2 complete
- [ ] `TODO3.md` (149KB) - Phase 3 active

### Delete this file:
- [ ] `TODO_9_18_DEBUG_REPORT.md` - Specific debug session

**Action:** Delete TODO_9_18_DEBUG_REPORT.md

---

## 10. Clean Up Miscellaneous Files

### Files to Review:
- [x] ~~`cookies.txt`~~ - **REMOVED** (Phase 1) ✅
- [x] ~~`mock_data_examples.json`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`server.log`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`main.py`~~ - **DELETED** (Phase 4 - obsolete placeholder) ✅
- [x] ~~`migrate_positions_to_strategies.py`~~ - **ARCHIVED** (Phase 6 - deprecated strategy system) ✅

**Action:** ✅ **COMPLETE** - All miscellaneous files cleaned up.

---

## 11. Organize Directories

### Directories to Review:
- [ ] `api_test_results/` - Test results shouldn't be committed
- [ ] `factor_etf_exports/` - Confirm long-term reference requirement
- [ ] `monitoring_screenshots/` - Screenshots shouldn't be committed
- [ ] `test_screenshots/` - Screenshots shouldn't be committed
- [ ] `data/` - Verify committed CSVs (e.g., `target_prices_import.csv`)
- [ ] `reports/` - Generated reports shouldn't be committed
- [ ] `logs/` - Remove committed log files
- [ ] `node_modules/` - **KEEP** (needed for Playwright/MCP) ⚠️
- [ ] `Tagging Project/` - **NEW** - Unclear purpose, investigate

**New Directories:**
- `.playwright-mcp/` - **NEW** - Playwright MCP screenshots (frontend) - Add to `.gitignore`

**Action:** Decide what archives, what becomes fixture/test data, what deletes. **DO NOT** remove `node_modules/` - it's required for MCP browser automation tools. Investigate `Tagging Project/` directory purpose.

---

## 12. Platform-Specific Files

### Files to Review:
- [ ] `QUICK_START_WINDOWS.md`
- [x] ~~`setup.bat`~~ - **NOT FOUND** (removed) ✅
- [x] ~~`setup.sh`~~ - **NOT FOUND** (removed) ✅

**Action:** Fold platform-specific steps into `setup-guides/README.md`. Archive `QUICK_START_WINDOWS.md` once consolidated guide published.

---

## 13. Configuration Files

### Files to Review:
- [x] ~~`railway.json`~~ - **NOT FOUND** (removed) ✅
- [ ] `.env.example` - Verify against current requirements
- [ ] `CASCADE_PROMPTS.md` - Still exists

**Action:** Align `.env.example` with required variables in `AI_AGENT_REFERENCE.md` and `README.md`. If `CASCADE_PROMPTS.md` remains useful, move to `setup-guides/` and link from developer docs; otherwise archive.

---

## 14. Update .gitignore

**Current Patterns Needed:**
```
# Test results
*.test.json
*test_results*

# Browser automation artifacts
monitoring_screenshots/
test_screenshots/
.playwright-mcp/

# Development artifacts
cookies.txt
*.cache

# Generated data
api_test_results/
reports/
factor_etf_exports/
```

**Action:** Confirm patterns applied in correct `.gitignore` files. Remove ignored artifacts from version control once rules in place.

---

## 15. Action Tracker (Work in Progress)

### Completed ✅
- [x] **Phase 1:** Removed cookies.txt, logs, updated .gitignore
- [x] **Phase 2:** Archived migration scripts (10 files) with README
- [x] **Phase 3:** Archived TODO1.md, TODO2.md, error reports, planning docs
- [x] **Phase 4:** Organized test/verification scripts, removed obsolete files
- [x] **Phase 5:** Archived Tagging Project docs, removed generated artifacts
- [x] **Phase 6:** Archived migrate_positions_to_strategies.py, updated docs

### Critical Priority 🔴
- [x] ~~Remove `cookies.txt` and rotate exposed credentials~~ - **COMPLETE** (Phase 1) ✅
- [x] ~~Remove committed logs from `logs/` directory~~ - **COMPLETE** (Phase 1) ✅
- [x] ~~Add `.playwright-mcp/` to `.gitignore`~~ - **COMPLETE** (Phase 1) ✅

### High Priority
- [x] ~~Document new position tagging migration scripts~~ - **COMPLETE** (Phase 2) ✅
- [x] ~~Archive TODO1.md and TODO2.md~~ - **COMPLETE** (Phase 3) ✅
- [ ] Update README.md with current architecture (OPTIONAL)
- [ ] Consolidate error reports into KNOWN_ISSUES.md (OPTIONAL)

### Medium Priority
- [x] ~~Move root-level test scripts to proper locations~~ - **COMPLETE** (Phase 4) ✅
- [x] ~~Relocate verification scripts to `scripts/verification/`~~ - **COMPLETE** (Phase 4) ✅
- [x] ~~Archive implementation planning docs~~ - **COMPLETE** (Phase 3) ✅
- [x] ~~Investigate `Tagging Project/` directory purpose~~ - **COMPLETE** (Phase 5) ✅

### Low Priority
- [x] ~~Archive old workflow guides~~ - **SKIPPED** (kept in backend root per user request) ✅
- [x] ~~Archive remaining git history snapshots~~ - **COMPLETE** (Phase 4) ✅
- [x] ~~Consolidate platform-specific setup docs~~ - **COMPLETE** (Phase 5 - archived to _archive/config/) ✅

---

## 16. Archive Position Tagging Migration Scripts

**Purpose:** The October 2025 migration from strategy tagging to position tagging introduced migration scripts. However, since we only have **demo data (no production users)**, we don't need to migrate - we can seed fresh portfolios directly with the new position tagging architecture.

**Key Decision:** Migration scripts should be **archived for reference** (useful if partner wants to preserve his dev data) but are NOT needed for fresh demo builds.

### Migration Scripts to Archive:

**Position Tagging Migration (archive to `_archive/migration-scripts/`):**
- [x] ~~`scripts/migrate_strategy_tags_to_positions.py`~~ - **ARCHIVED** (Phase 2) ✅
- [x] ~~`scripts/verify_position_tags_only.py`~~ - **ARCHIVED** (Phase 2) ✅
- [x] ~~`scripts/check_position_tags.py`~~ - **ARCHIVED** (Phase 2) ✅

**Strategy Cleanup (archive to `_archive/migration-scripts/`):**
- [x] ~~`scripts/separate_combined_strategies.py`~~ - **ARCHIVED** (Phase 2) ✅
- [x] ~~`scripts/check_combined_strategies.py`~~ - **ARCHIVED** (Phase 2) ✅
- [x] ~~`scripts/delete_empty_strategies.py`~~ - **ARCHIVED** (Phase 2) ✅
- [x] ~~`scripts/update_strategy_names.py`~~ - **ARCHIVED** (Phase 2) ✅
- [x] ~~`scripts/check_empty_strategy_positions.py`~~ - **ARCHIVED** (Phase 2) ✅
- [x] ~~`scripts/show_combined_strategy_positions.py`~~ - **ARCHIVED** (Phase 2) ✅

**Legacy Strategy System (archive to `_archive/migration-scripts/`):**
- [x] ~~`migrate_positions_to_strategies.py`~~ - **ARCHIVED** (Phase 6) ✅

**Data Integration (KEEP - still useful):**
- ✅ `scripts/populate_company_profiles.py` - Fetch company data (needed for fresh seeds)
- ✅ `scripts/test_yfinance_integration.py` - Test data provider (useful for validation)
- ✅ `scripts/monitor_provider_usage.py` - Track API costs (operational tool)

**Testing (evaluate individually):**
- ✅ `scripts/test_api_tags.py` - Test tagging endpoints (useful for API testing)
- [x] ~~`scripts/check_portfolios_tags.py`~~ - **ARCHIVED** (Phase 2) ✅

**Action Required:**
✅ **COMPLETE** (Phases 2 & 6):
1. ✅ Created `_archive/migration-scripts/` directory
2. ✅ Moved migration-specific scripts there (11 total)
3. ✅ Added `_archive/migration-scripts/README.md` with usage instructions
4. ✅ Kept data integration and API testing scripts in active `scripts/` directory

---

## 17. Frontend Cleanup Considerations

**Scope:** Frontend cleanup is **OUT OF SCOPE** for this backend repository cleanup effort.

**New Frontend Architecture Changes (Informational Only):**
- Deleted deprecated: `src/hooks/useStrategies.ts`
- Added: `src/hooks/usePositionTags.ts`
- Deleted: `src/components/strategies/` directory
- Added: `src/components/ui/alert-dialog.tsx`

**New Documentation:**
- `_docs/TAGGING_ARCHITECTURE.md` (496 lines)
- `_docs/CompanyProfilesTableRec.md` (859 lines)
- `_docs/redotagging.md` (343 lines)
- `_docs/redo organize` (280 lines) - Unusual filename without `.md`

**Action:** None - Frontend directory not part of backend cleanup scope.

---

## Priority Recommendations (UPDATED October 2025)

### CRITICAL (Do Immediately) 🔴
1. **Remove `cookies.txt` and rotate credentials** - Security risk
2. Add `.playwright-mcp/` to `.gitignore`
3. Clean up committed logs in `logs/` directory

### High Priority
1. Document position tagging migration scripts (new Section 16)
2. Archive completed TODO1.md and TODO2.md
3. Update README.md with current architecture (reference new tagging system)
4. Consolidate error reports into KNOWN_ISSUES.md

### Medium Priority
1. Move root-level test scripts to appropriate locations
2. Relocate verification scripts
3. Archive implementation planning docs
4. Investigate `Tagging Project/` directory purpose
5. Update `.env.example` with current requirements

### Low Priority
1. Archive workflow guides (SKIPPED - kept in backend root per user request)
2. Archive git history snapshots
3. Consolidate platform-specific docs

---

## Notes

- Before removing any file, verify it's not referenced in active code
- `_archive/` directory structure for historical documentation
- All removed files available in git history if needed
- **NEW:** Keep migration scripts documented - they're active tooling
- **NEW:** `backend/package.json` is intentional (Playwright for MCP)
- Consider GitHub Issues for task tracking instead of TODO files

---

**Last Review:** October 4, 2025
**Next Review:** After position tagging migration completion
