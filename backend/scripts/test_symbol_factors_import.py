"""Test that symbol_factors.py imports correctly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.calculations.symbol_factors import (
        calculate_universe_factors,
        get_all_active_symbols,
        get_uncached_symbols,
        calculate_symbol_ridge_factors,
        calculate_symbol_spread_factors,
        persist_symbol_factors,
        load_symbol_betas,
        BATCH_SIZE,
        MAX_CONCURRENT_BATCHES,
    )
    print("All imports successful!")
    print(f"  BATCH_SIZE: {BATCH_SIZE}")
    print(f"  MAX_CONCURRENT_BATCHES: {MAX_CONCURRENT_BATCHES}")
    print("  Functions available:")
    print("    - calculate_universe_factors()")
    print("    - get_all_active_symbols()")
    print("    - get_uncached_symbols()")
    print("    - calculate_symbol_ridge_factors()")
    print("    - calculate_symbol_spread_factors()")
    print("    - persist_symbol_factors()")
    print("    - load_symbol_betas()")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
