# TODO: Repository Cleanup Tasks

**Created:** 2025-09-23
**Purpose:** Clean up the backend repository by removing outdated files and updating documentation to reflect current state

## 1. Remove Outdated Test Files in Root Directory

### Files to Remove:
- [ ] `test_auth_dependency.py`
- [ ] `test_auth.py`
- [ ] `test_minimal_api.py`
- [ ] `test_service_direct.py`
- [ ] `test_target_prices_api.py`
- [ ] `test_target_prices_comprehensive.py`
- [ ] `test_target_prices_detailed.py`

**Rationale:** These test files are in the root directory instead of the `tests/` folder. They appear to be ad-hoc testing scripts from development. Proper tests should be in the tests directory and run via pytest.

---

## 2. Remove Old Development/Debug Scripts

### Files to Remove:
- [ ] `check_equity_values.py`
- [ ] `get_demo_portfolio.py`
- [ ] `manual_test_ids.py`
- [ ] `seed_positions_only.py`
- [ ] `verify_portfolio_ids.py`
- [ ] `verify_target_prices.py`
- [ ] `check_portfolio.py`

**Rationale:** These appear to be one-off debugging/verification scripts. If any functionality is still needed, it should be moved to the `scripts/` directory with proper documentation.

---

## 3. Archive Historical Git History Files

### Files to Archive/Remove:
- [ ] `detailed_git_history_ending_0720.txt`
- [ ] `detailed_git_history_ending_0808.txt`
- [ ] `detailed_git_history_ending_0810.txt`

**Rationale:** These are snapshots of git history from August 2025. Git already maintains this history, so these text files are redundant. If needed for reference, they could be moved to a `_archive/` directory.

---

## 4. Clean Up Chat/Monitoring Test Files

### Files to Review and Potentially Remove:
- [ ] `comprehensive_chat_test.js`
- [ ] `test_chat_flow.js`
- [ ] `monitoring_session.js`
- [ ] `simple_monitor.py`

**Rationale:** These appear to be frontend/integration test files that belong in the frontend repository or a dedicated integration test directory. The backend shouldn't contain JavaScript test files.

### Related Files to Review:
- [ ] `chat_test_results.json`
- [ ] `chat_test_results_comprehensive.json`
- [ ] `phase_10_5_results.json`
- [ ] `portfolio_context_smoke_test_report.json`
- [ ] `chat_monitoring_report.json`

**Rationale:** Test result JSON files should not be committed to the repository. Consider adding these patterns to `.gitignore`.

---

## 5. Consolidate Error/Debug Documentation

### Files to Consolidate:
- [ ] `BACKEND_COMPUTE_ERROR.md` (86KB - very large)
- [ ] `backend_compute_Error_Sept.md`
- [ ] `TODO_9_18_DEBUG_REPORT.md`
- [ ] `OPENAI_STREAMING_BUG_REPORT.md`

**Rationale:** Multiple error documentation files create confusion. Should consolidate into a single `KNOWN_ISSUES.md` or move resolved issues to an archive.

---

## 6. Update or Remove Implementation Planning Docs

### Files to Update or Archive:
- [ ] `Target_Price_and_Investment_Classes_Implementation_Plan.md`
- [ ] `Target_Price_Summary_For_Ben_09-18-2025.md`
- [ ] `README_TARGET_PRICES_IMPORT.md`
- [ ] `IMPLEMENT_NEW_API_PROMPT.md`
- [ ] `TEST_NEW_API_PROMPT.md`

**Rationale:** These appear to be planning documents for features that may already be implemented. Should either update to reflect current state or move to `_docs/planning/` if still relevant.

---

## 7. Consolidate Workflow Guides

### Files to Review:
- [ ] `BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`
- [ ] `BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md`
- [ ] `ONBOARDING_NEW_ACCOUNT_PORTFOLIO.md`

**Rationale:** Multiple workflow guides might have overlapping content. Consider consolidating into a single `DEVELOPER_GUIDE.md` with clear sections.

---

## 8. Update Core Documentation

### Files Needing Updates:
- [ ] `README.md` - Very brief (2KB), needs expansion with:
  - Current project status
  - Complete setup instructions
  - API documentation links
  - Testing instructions

- [ ] `API_IMPLEMENTATION_STATUS.md` - Only 229 bytes, seems incomplete
  - Should provide comprehensive status of all endpoints
  - Include which return mock vs real data

- [ ] `AGENTS.md` - Only 235 bytes
  - Either expand with agent documentation or remove if obsolete

---

## 9. Review TODO Files

### Files to Consolidate:
- [ ] `TODO1.md` (162KB)
- [ ] `TODO2.md` (98KB)
- [ ] `TODO3.md` (149KB)

**Rationale:** Over 400KB of TODO files. Should extract incomplete items into GitHub Issues and archive completed work. Consider keeping only active TODO items in a single `TODO.md`.

---

## 10. Clean Up Miscellaneous Files

### Files to Review:
- [ ] `cookies.txt` - Should not be in repository
- [ ] `token.txt` - Security risk if contains actual tokens
- [ ] `mock_data_examples.json` - Move to `tests/fixtures/` if still needed
- [ ] `server.log` - Logs should not be committed
- [ ] `main.py` - Only 85 bytes, appears to be a stub

**Rationale:** These files appear to be development artifacts that shouldn't be in version control.

---

## 11. Organize Directories

### Directories to Review:
- [ ] `api_test_results/` - Test results shouldn't be committed
- [ ] `factor_etf_exports/` - Check if this data should be in repository
- [ ] `monitoring_screenshots/` - Screenshots shouldn't be in repository
- [ ] `test_screenshots/` - Move to `.gitignore`
- [ ] `data/` - Review what's in here and if it should be committed
- [ ] `reports/` - Generated reports probably shouldn't be committed
- [ ] `node_modules/` - Should definitely be in `.gitignore`

---

## 12. Platform-Specific Files

### Files to Review:
- [ ] `QUICK_START_WINDOWS.md` - Consolidate with main README
- [ ] `setup.bat` - Windows-specific setup
- [ ] `setup.sh` - Unix-specific setup

**Rationale:** Platform-specific instructions should be sections in the main documentation, not separate files.

---

## 13. Configuration Files

### Files to Review:
- [ ] `railway.json` - Deployment config, check if current
- [ ] `.env.example` - Ensure it matches actual requirements
- [ ] `CASCADE_PROMPTS.md` - Unclear purpose, review necessity

---

## 14. Update .gitignore

### Add these patterns:
```
# Test results
*.test.json
*test_results*
test_*.py  # In root directory only
*.log

# Screenshots
screenshots/
*.png
*.jpg

# Development artifacts
cookies.txt
token.txt
*.cache

# Node modules (if frontend build happens here)
node_modules/

# Generated reports
reports/
exports/

# IDE
.idea/
.vscode/
*.swp
```

---

## Priority Recommendations

### High Priority (Do First):
1. Remove security-sensitive files (cookies.txt, token.txt)
2. Clean up root directory test files
3. Add proper .gitignore entries
4. Remove node_modules if present

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