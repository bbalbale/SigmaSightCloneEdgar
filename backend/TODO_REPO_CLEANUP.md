# TODO: Repository Cleanup Tasks

**Created:** 2025-09-23
**Purpose:** Clean up the backend repository by removing outdated files and updating documentation to reflect current state
**Last Reviewed:** 2025-09-27

> ℹ️ Follow CLAUDE/AGENTS guardrails. Where a section calls out `AGENTS.md` or other instruction files, avoid edits unless the owning document explicitly allows them.

## 1. Rationalize Root-Level Manual Test Scripts

### Files to Relocate or Merge:
- [ ] `test_auth_dependency.py` (manually pokes auth dependency)
- [ ] `test_auth.py` (HTTP smoketest using `requests`)
- [ ] `test_minimal_api.py`
- [ ] `test_service_direct.py`
- [ ] `test_target_prices_api.py`
- [ ] `test_target_prices_comprehensive.py`
- [ ] `test_target_prices_detailed.py`

**Action:** Migrate any scripts still useful to `scripts/manual_tests/` (or convert them into pytest cases under `tests/`). Eliminate duplicates that already exist under `scripts/` (for example, `scripts/test_target_prices_api.py` supersedes the root version). Update documentation to surface the new location.

---

## 2. Rehome Legacy Verification Scripts

### Files to Relocate/Update:
- [ ] `check_equity_values.py`
- [ ] `get_demo_portfolio.py`
- [ ] `manual_test_ids.py`
- [ ] `seed_positions_only.py`
- [ ] `verify_portfolio_ids.py`
- [ ] `verify_target_prices.py`

**Action:** Move still-relevant helpers into `scripts/verification/` (or extend existing scripts there). `check_portfolio.py` no longer exists—remove it from the checklist. Document any retained workflows in `scripts/README.md`.

---

## 3. Archive Historical Git History Files

### Files to Archive/Remove:
- [ ] `detailed_git_history_ending_0720.txt`
- [ ] `detailed_git_history_ending_0808.txt`
- [ ] `detailed_git_history_ending_0810.txt`
- [ ] `detailed_git_history_ending_0905.txt`

**Action:** Move historical snapshots into `_archive/git-history/` or delete them after confirming no onboarding guide still references them.

---

## 4. Clean Up Chat/Monitoring Harnesses

### JavaScript Harnesses (depend on `backend/package.json`):
- [ ] `comprehensive_chat_test.js`
- [ ] `test_chat_flow.js`
- [ ] `monitoring_session.js`

### Python Monitoring Utility:
- [ ] `simple_monitor.py`

### Related Files to Purge or Archive:
- [ ] `chat_test_results.json`
- [ ] `chat_test_results_comprehensive.json`
- [ ] `phase_10_5_results.json`
- [ ] `portfolio_context_smoke_test_report.json`
- [ ] `chat_monitoring_report.json`

**Action:** Decide whether to keep the Puppeteer-based workflow; if yes, document usage in `setup-guides/` and move artifacts into `scripts/monitoring/`. If no, remove the JS harnesses along with `backend/package.json` and `node_modules/`. Retain `simple_monitor.py` but relocate it under `scripts/monitoring/` with updated instructions. Delete committed result JSON files and add patterns to `.gitignore` (see Section 14).

---

## 5. Consolidate Error/Debug Documentation

### Files to Consolidate:
- [ ] `BACKEND_COMPUTE_ERROR.md` (86KB - very large)
- [ ] `backend_compute_Error_Sept.md`
- [ ] `TODO_9_18_DEBUG_REPORT.md`

**Constraints:** `OPENAI_STREAMING_BUG_REPORT.md` is explicitly whitelisted in the root `.gitignore`; keep it tracked with an explanatory note.

**Action:** Merge overlapping incident reports into a maintained `KNOWN_ISSUES.md` (or move resolved items to `_archive/incidents/`). Update remaining docs with links back to the canonical source.

---

## 6. Update or Remove Implementation Planning Docs

### Files to Update or Archive:
- [ ] `Target_Price_and_Investment_Classes_Implementation_Plan.md`
- [ ] `Target_Price_Summary_For_Ben_09-18-2025.md`
- [ ] `README_TARGET_PRICES_IMPORT.md`
- [ ] `IMPLEMENT_NEW_API_PROMPT.md`
- [ ] `TEST_NEW_API_PROMPT.md`

**Action:** Verify against the current target-price workflows (`scripts/test_target_prices_api.py`, `data/target_prices_import.csv`). Update the docs if still accurate, otherwise archive them under `_docs/planning/legacy/` with a pointer in `AI_AGENT_REFERENCE.md`.

---

## 7. Consolidate Workflow Guides

### Files to Review:
- [ ] `BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`
- [ ] `BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md`
- [ ] `ONBOARDING_NEW_ACCOUNT_PORTFOLIO.md`

**Action:** Confirm these guides are superseded by the curated materials in `setup-guides/`. If so, move them to `_archive/workflows/` while adding cross-links in the active onboarding guide so history is preserved.

---

## 8. Update Core Documentation

### Files Needing Updates:
- [ ] `README.md` (very brief)
- [ ] `API_IMPLEMENTATION_STATUS.md` (deprecated placeholder pointing to `_docs/requirements/API_SPECIFICATIONS_V1.4.5.md`)
- [ ] `AGENTS.md`

**Action:** Expand the README with current status, setup, API, and testing instructions. Decide whether to delete the deprecated API status file or replace it with a short redirect summary. `AGENTS.md` must remain aligned with `CLAUDE.md`; do not expand it unless the owning instructions change. Ensure `AI_AGENT_REFERENCE.md` continues to carry canonical agent guidance.

---

## 9. Review TODO Files

### Files to Consolidate:
- [ ] `TODO1.md` (162KB)
- [ ] `TODO2.md` (98KB)
- [ ] `TODO3.md` (149KB)

**Action:** Identify still-open tasks and migrate them to the active tracking system (GitHub Issues or a new `TODO4.md`). Archive completed sections under `_archive/todos/` but leave breadcrumbs so historical context remains accessible.

---

## 10. Clean Up Miscellaneous Files

### Files to Review:
- [ ] `cookies.txt` (exists in repo root and backend)
- [ ] `mock_data_examples.json`
- [ ] `server.log`
- [ ] `main.py`

**Action:** Remove both copies of `cookies.txt` and rotate any exposed tokens. Move `mock_data_examples.json` into `tests/fixtures/` or delete if obsolete. Drop `server.log` plus the `logs/` directory contents after ensuring logging configuration reproduces them. Evaluate whether `main.py` is still required; if not, delete it or replace it with a module docstring explaining its purpose.

---

## 11. Organize Directories

### Directories to Review:
- [ ] `api_test_results/` - Test results shouldn't be committed
- [ ] `factor_etf_exports/` - Confirm if long-term reference is required
- [ ] `monitoring_screenshots/` - Screenshots shouldn't be committed
- [ ] `test_screenshots/` - Screenshots shouldn't be committed
- [ ] `data/` - Verify any committed CSVs (e.g., `target_prices_import.csv`)
- [ ] `reports/` - Generated reports probably shouldn't be committed
- [ ] `logs/` (backend and repo root) - Remove committed log files
- [ ] `node_modules/` (repo root and backend) - Remove committed directories (already ignored)

**Action:** Decide what moves to `_archive/`, what becomes fixture/test data, and what should be deleted entirely. Update documentation to explain any retained generated assets.

---

## 12. Platform-Specific Files

### Files to Review:
- [ ] `QUICK_START_WINDOWS.md`
- [ ] `setup.bat`
- [ ] `setup.sh`

**Action:** Fold platform-specific steps into `setup-guides/README.md` (or the expanded `README.md`). Move superseded files into `_archive/setup/` once the consolidated guide is published.

---

## 13. Configuration Files

### Files to Review:
- [ ] `railway.json`
- [ ] `.env.example`
- [ ] `CASCADE_PROMPTS.md`

**Action:** Verify `railway.json` against current deployment targets. Align `.env.example` with the required variables listed in `backend/AI_AGENT_REFERENCE.md` and `README.md`. If `CASCADE_PROMPTS.md` remains useful, move it under `setup-guides/` and link it from the developer onboarding doc; otherwise archive it.

---

## 14. Update .gitignore

```
# Test results
*.test.json
*test_results*

# Browser automation artifacts
monitoring_screenshots/
test_screenshots/

# Development artifacts
cookies.txt
*.cache

# Generated data
api_test_results/
reports/
factor_etf_exports/
```

**Action:** Confirm each pattern is applied in the correct `.gitignore` (`../.gitignore` vs. `backend/.gitignore`). Remove already-ignored artifacts from version control once rules are in place.

---

## Priority Recommendations

### High Priority (Do First):
1. Purge committed secrets/logs (`cookies.txt`, `server.log`, `logs/`) and rotate any exposed credentials
2. Relocate or modernize root-level manual test scripts (Sections 1 and 2)
3. Decide on the chat/monitoring tooling strategy and clean up related artifacts (Section 4)
4. Add/update `.gitignore` rules, then delete ignored files from git history (Section 14)

### Medium Priority:
1. Consolidate TODO files
2. Update README.md with current information
3. Archive old error reports
4. Move test results out of repository

### Low Priority:
1. Reorganize documentation structure
2. Archive historical git exports
3. Consolidate platform-specific setup guides

---

## Notes

- Before removing any file, verify it's not referenced in active code
- Consider creating an `_archive/` directory for historical documentation
- All removed files will still be available in git history if needed
- Consider using GitHub Issues instead of TODO files for task tracking

---

## 15. Action Tracker (Work in Progress)

- [ ] Confirm whether to keep or retire the Puppeteer chat harness; update Section 4 accordingly and clean up `backend/package.json` + `node_modules/`
- [ ] Move manual auth/target-price test scripts into `scripts/` (or convert to pytest) and update documentation references
- [ ] Remove committed tokens/logs, rotate credentials, and ensure `.gitignore` coverage for regenerated artifacts
- [ ] Archive superseded workflow and planning docs while leaving breadcrumbs in active guides (`setup-guides/`, `AI_AGENT_REFERENCE.md`)
- [ ] Extract open items from `TODO1/2/3.md`, capture them in the active tracker, and archive historical sections safely
