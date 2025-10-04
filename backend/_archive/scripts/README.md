# Archived Scripts

Scripts that have been completed and are no longer needed for active development.

**Archived**: 2025-10-04

---

## 📁 Directory Structure

```
_archive/scripts/
├── migrations/        # Completed one-time data migrations and fixes
├── deprecated/        # Deprecated scripts replaced by newer versions
├── tests/            # Completed version-specific and one-time test scripts
└── debug/            # Completed debug and analysis scripts
```

---

## 📋 Archived Scripts Summary

### migrations/ (20 scripts)
**One-time data migrations and classification tasks - All completed**

#### Root Migration Scripts:
- `add_missing_hnw_positions.py` - Added missing HNW portfolio positions (completed)
- `add_private_positions.py` - Added private position data (completed)
- `backfill_strategies.py` - Backfilled strategy data (completed)
- `backfill_strategy_categorization.py` - Categorized strategies (completed)
- `check_private_positions.py` - Verification for private positions (completed)
- `classify_positions.py` - Position classification (completed)
- `cleanup_orphaned_strategies.py` - Cleaned orphaned strategies (completed)
- `debug_hnw_audit.py` - HNW audit debugging (completed)
- `enforce_not_null_strategy_id.py` - Enforced NOT NULL constraint (completed)
- `final_classification_summary.py` - Classification summary (completed)
- `fix_classification_three_classes.py` - Fixed 3-class classification (completed)
- `update_classification_for_private.py` - Updated private position classification (completed)
- `update_investment_classes.py` - Updated investment class data (completed)
- `update_position_subtypes.py` - Updated position subtypes (completed)
- `verify_categorization.py` - Verified categorization (completed)
- `verify_final_classification.py` - Verified final classification (completed)
- `verify_private_positions.py` - Verified private positions (completed)

#### Migrations Directory Scripts:
- `fix_utf8_encoding.py` - Fixed UTF-8 encoding issues (completed - verified in guides)
- `migrate_datetime_now.py` - Migrated datetime.now() usage (completed - verified in guides)
- `update_equity_values.py` - Updated equity values (completed - equity values set)

### deprecated/ (1 script)
**Scripts replaced by newer versions**

- `run_batch_calculations.py` - DEPRECATED: Replaced by `run_batch_with_reports.py --skip-reports`

### tests/ (14 scripts)
**Completed version-specific and one-time test scripts**

#### Root Test Scripts (misplaced):
- `test_api_tags.py` - Tag API testing (should be in pytest or testing/)
- `test_backwards_compat.py` - Backward compatibility testing (completed)
- `test_investment_classification.py` - Classification testing (one-time)
- `test_target_prices_api.py` - Target prices API testing (covered elsewhere)
- `test_yfinance_integration.py` - yfinance integration (yfinance removed from project)

#### Version-Specific Tests:
- `test_6_1_fixes.py` - Version 6.1 fixes verified (completed)
- `test_data_preservation.py` - Data preservation feature tested (completed)
- `test_datetime_changes.py` - Datetime migration verified (completed)
- `test_factor_analysis_fix.py` - Factor analysis fix verified (completed)
- `test_phase_10_5.py` - Phase 10.5 testing (completed)
- `test_phase3_datetime_format.py` - Phase 3 datetime format verified (completed)
- `test_position_factor_exposures_3_0_3_15.py` - Version 3.0.3.15 specific (completed)
- `test_post_yfinance_removal.py` - yfinance removal verified (completed)
- `test_stress_test_3_0_3_14.py` - Version 3.0.3.14 stress test (completed)

### debug/ (3 scripts)
**Completed debug and analysis scripts**

- `analyze_demo_calculation_engine_failures.py` - Debug calculation failures (completed)
- `analyze_demo_portfolio_calculation_failure.py` - Debug portfolio calculation (completed)
- `portfolio_context_smoke_test.py` - Portfolio context smoke test (artifact exists in JSON)

---

## ⚠️ Important Notes

### Before Final Deletion:

1. **Verify git history preserved** - All scripts moved with `git mv` to preserve history
2. **Check for imports** - Search codebase for any remaining references
3. **Review migration completion** - Confirm all one-time tasks actually completed
4. **Keep for reference** - These may provide context for future similar issues

### Restoration:

If any script needs to be restored:
```bash
# From project root
git mv backend/_archive/scripts/{category}/{script_name}.py backend/scripts/{destination}/
```

### Complete Deletion:

When ready to permanently delete:
```bash
# After thorough verification
rm -rf backend/_archive/scripts/
git add -A
git commit -m "chore: remove archived scripts after verification"
```

---

## 📊 Statistics

- **Total Archived**: 38 scripts
- **Migrations**: 20 scripts
- **Deprecated**: 1 script
- **Tests**: 14 scripts
- **Debug**: 3 scripts

**Disk Space Saved**: ~180KB (scripts themselves, excludes git history)

---

## 🔍 Verification Checklist

Before permanent deletion, verify:

- [ ] All migrations actually completed successfully
- [ ] No active imports or references in codebase
- [ ] Git history preserved for all moved files
- [ ] Similar functionality available in active scripts
- [ ] Documentation updated to remove references
- [ ] No planned rollback or reversion scenarios

**Last Reviewed**: 2025-10-04
