# V2 Batch Validation Scripts
#
# Scripts for validating V2 batch processing against V1 baseline.
#
# Usage order:
#   1. capture_current_baseline.py - Capture V1/current calculations to JSON
#   2. clear_calculations_for_validation.py --dry-run - Preview deletions
#   3. clear_calculations_for_validation.py - Delete calculations
#   4. run_v2_recalculation.py - Re-run V2 batch for date range
#   5. compare_validation_results.py - Compare V2 results to baseline
