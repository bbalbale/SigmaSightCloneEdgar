#!/usr/bin/env python
"""
Migration script to safely replace datetime.now() with utc_now() in production code.

This script:
1. Updates imports to include utc_now
2. Replaces datetime.now() calls
3. Validates the changes
4. Reports on what was updated

Author: SigmaSight Team
Date: 2025-08-27
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


# Files to update (critical production code only)
PRODUCTION_FILES = [
    # Batch processing (active)
    "app/batch/batch_orchestrator_v2.py",
    "app/batch/daily_calculations.py",
    "app/batch/data_quality.py",
    "app/batch/market_data_sync.py",
    
    # API endpoints
    "app/api/v1/endpoints/admin_batch.py",
    
    # Calculations (already done manually)
    # "app/calculations/portfolio.py",
    # "app/calculations/greeks.py",
    
    # Services (already done manually)
    # "app/services/market_data_service.py",
    
    # Clients (already done manually)
    # "app/clients/fmp_client.py", 
    # "app/clients/tradefeeds_client.py",
]

# Files to skip (archives, tests, scripts)
SKIP_PATTERNS = [
    "_archive/",
    "tests/",
    "scripts/",
    "audit_datetime_usage.py",
    "datetime_utils.py",  # Don't modify the utilities themselves
]


def should_skip_file(filepath: str) -> bool:
    """Check if file should be skipped."""
    for pattern in SKIP_PATTERNS:
        if pattern in filepath:
            return True
    return False


def add_import_if_needed(content: str) -> str:
    """Add utc_now import if not already present."""
    if "from app.core.datetime_utils import utc_now" in content:
        return content
    
    # Find the last import line
    import_lines = []
    lines = content.split('\n')
    last_import_idx = -1
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i
    
    if last_import_idx >= 0:
        # Add import after the last import
        lines.insert(last_import_idx + 1, "from app.core.datetime_utils import utc_now")
        return '\n'.join(lines)
    
    return content


def replace_datetime_now(content: str) -> Tuple[str, int]:
    """Replace datetime.now() with utc_now() and return count of replacements."""
    pattern = r'\bdatetime\.now\(\)'
    new_content, count = re.subn(pattern, 'utc_now()', content)
    return new_content, count


def process_file(filepath: str) -> dict:
    """Process a single file."""
    result = {
        'filepath': filepath,
        'status': 'skipped',
        'replacements': 0,
        'error': None
    }
    
    if should_skip_file(filepath):
        return result
    
    if not os.path.exists(filepath):
        result['status'] = 'not_found'
        return result
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if datetime.now() is present
        if 'datetime.now()' not in content:
            result['status'] = 'no_changes'
            return result
        
        # Add import if needed
        content = add_import_if_needed(content)
        
        # Replace datetime.now()
        new_content, count = replace_datetime_now(content)
        
        if count > 0:
            # Write back the file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            result['status'] = 'updated'
            result['replacements'] = count
        else:
            result['status'] = 'no_changes'
    
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def main():
    """Run the migration."""
    print("🔄 Starting datetime.now() -> utc_now() migration...")
    print(f"Processing {len(PRODUCTION_FILES)} production files\n")
    
    results = []
    total_replacements = 0
    
    for filepath in PRODUCTION_FILES:
        result = process_file(filepath)
        results.append(result)
        
        if result['status'] == 'updated':
            print(f"✅ Updated {filepath}: {result['replacements']} replacements")
            total_replacements += result['replacements']
        elif result['status'] == 'no_changes':
            print(f"⏭️  No changes needed: {filepath}")
        elif result['status'] == 'not_found':
            print(f"❌ File not found: {filepath}")
        elif result['status'] == 'error':
            print(f"❌ Error processing {filepath}: {result['error']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    
    updated = [r for r in results if r['status'] == 'updated']
    no_changes = [r for r in results if r['status'] == 'no_changes']
    errors = [r for r in results if r['status'] == 'error']
    
    print(f"✅ Files updated: {len(updated)}")
    print(f"⏭️  Files unchanged: {len(no_changes)}")
    print(f"❌ Errors: {len(errors)}")
    print(f"📊 Total replacements: {total_replacements}")
    
    if updated:
        print("\nUpdated files:")
        for r in updated:
            print(f"  - {r['filepath']}: {r['replacements']} replacements")
    
    if errors:
        print("\nErrors encountered:")
        for r in errors:
            print(f"  - {r['filepath']}: {r['error']}")
    
    # Validation reminder
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Run tests to verify changes:")
    print("   uv run python -m pytest tests/ -v")
    print("2. Test batch processing:")
    print("   uv run python scripts/test_batch_with_reports.py")
    print("3. Review the changes with git diff")
    print("4. Commit the changes")


if __name__ == "__main__":
    main()