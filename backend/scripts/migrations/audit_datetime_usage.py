#!/usr/bin/env python
"""
Audit script to identify datetime usage patterns in the codebase.

This script helps identify:
1. All instances of datetime.now() that should be replaced with datetime.utcnow()
2. All instances of .isoformat() that may need standardization
3. Mixed timezone representations

Author: SigmaSight Team
Date: 2025-08-27
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple


def find_python_files(root_dir: str = "app") -> List[Path]:
    """Find all Python files in the specified directory."""
    root_path = Path(root_dir)
    return list(root_path.rglob("*.py"))


def audit_datetime_now(files: List[Path]) -> Dict[str, List[Tuple[int, str]]]:
    """Find all instances of datetime.now() usage."""
    pattern = re.compile(r'datetime\.now\(\)')
    results = {}
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            matches = []
            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    matches.append((line_num, line.strip()))
            
            if matches:
                results[str(filepath)] = matches
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return results


def audit_isoformat(files: List[Path]) -> Dict[str, List[Tuple[int, str]]]:
    """Find all instances of .isoformat() usage."""
    pattern = re.compile(r'\.isoformat\(\)')
    results = {}
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            matches = []
            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    matches.append((line_num, line.strip()))
            
            if matches:
                results[str(filepath)] = matches
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return results


def audit_timezone_offsets(files: List[Path]) -> Dict[str, List[Tuple[int, str]]]:
    """Find strings that look like timezone offsets (+00:00)."""
    pattern = re.compile(r'\+00:00|timezone|tzinfo|astimezone|pytz')
    results = {}
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            matches = []
            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    matches.append((line_num, line.strip()))
            
            if matches:
                results[str(filepath)] = matches
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return results


def print_results(title: str, results: Dict[str, List[Tuple[int, str]]]):
    """Print audit results in a formatted way."""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print('=' * 80)
    
    if not results:
        print("✅ No instances found")
    else:
        total_count = sum(len(matches) for matches in results.values())
        print(f"⚠️  Found {total_count} instances in {len(results)} files:\n")
        
        for filepath, matches in sorted(results.items()):
            print(f"\n📄 {filepath}")
            for line_num, line_content in matches:
                print(f"   Line {line_num}: {line_content[:100]}")


def generate_migration_script(datetime_now_results: Dict[str, List[Tuple[int, str]]]):
    """Generate a migration script to fix datetime.now() usages."""
    if not datetime_now_results:
        return
    
    print("\n" + "=" * 80)
    print("MIGRATION SCRIPT")
    print("=" * 80)
    print("\n# Add this import at the top of affected files:")
    print("from app.core.datetime_utils import utc_now")
    print("\n# Then run these sed commands to replace datetime.now():")
    
    for filepath in sorted(datetime_now_results.keys()):
        # Generate sed command for each file
        print(f"sed -i '' 's/datetime\\.now()/utc_now()/g' {filepath}")
    
    print("\n# Or use this Python script:")
    print("""
import fileinput
import sys

files_to_fix = [
""")
    for filepath in sorted(datetime_now_results.keys()):
        print(f'    "{filepath}",')
    print("""]

for filepath in files_to_fix:
    with fileinput.FileInput(filepath, inplace=True) as file:
        for line in file:
            print(line.replace('datetime.now()', 'utc_now()'), end='')
""")


def main():
    """Run the datetime audit."""
    print("🔍 Auditing datetime usage in SigmaSight backend...")
    
    # Find all Python files
    app_files = find_python_files("app")
    script_files = find_python_files("scripts")
    test_files = find_python_files("tests")
    
    all_files = app_files + script_files + test_files
    print(f"Found {len(all_files)} Python files to audit")
    
    # Run audits
    datetime_now_results = audit_datetime_now(all_files)
    isoformat_results = audit_isoformat(all_files)
    timezone_results = audit_timezone_offsets(all_files)
    
    # Print results
    print_results("DATETIME.NOW() USAGE (needs replacement with utc_now())", 
                  datetime_now_results)
    print_results("ISOFORMAT() USAGE (may need standardization)", 
                  isoformat_results)
    print_results("TIMEZONE-RELATED CODE (review for consistency)", 
                  timezone_results)
    
    # Generate migration script
    if datetime_now_results:
        generate_migration_script(datetime_now_results)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ datetime.now() instances to fix: {sum(len(m) for m in datetime_now_results.values())}")
    print(f"📋 .isoformat() instances to review: {sum(len(m) for m in isoformat_results.values())}")
    print(f"🌍 Timezone-related code to check: {sum(len(m) for m in timezone_results.values())}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("1. Replace all datetime.now() with utc_now() from datetime_utils")
    print("2. Review .isoformat() calls and add 'Z' suffix where appropriate")
    print("3. Ensure all timezone-aware datetimes are converted to UTC")
    print("4. Add linting rule to prevent future datetime.now() usage")
    print("5. Update Pydantic schemas to use standardized serialization")


if __name__ == "__main__":
    main()