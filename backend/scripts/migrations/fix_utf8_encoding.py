#!/usr/bin/env python3
"""
Fix UTF-8 encoding issues in all Python scripts by adding proper encoding configuration
"""
import os
import sys
import io

# Set UTF-8 as default encoding for this script
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def add_utf8_handling(filepath):
    """Add UTF-8 handling to a Python file if it contains emojis"""
    
    # Read file with UTF-8 encoding
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Check if file contains emojis
    has_emoji = False
    for line in lines:
        if any(ord(char) > 127 for char in line):
            # Check if it's actually an emoji (not just accented characters)
            if any(ord(char) > 0x1F000 for char in line):
                has_emoji = True
                break
    
    if not has_emoji:
        return False
    
    # Check if UTF-8 handling already exists
    has_utf8_fix = False
    for i, line in enumerate(lines[:20]):  # Check first 20 lines
        if 'sys.stdout = io.TextIOWrapper' in line or 'PYTHONIOENCODING' in line:
            has_utf8_fix = True
            break
    
    if has_utf8_fix:
        print(f"✓ {filepath} - already has UTF-8 handling")
        return False
    
    # Find where to insert the UTF-8 handling (after imports)
    insert_index = 0
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Handle docstrings
        if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
            docstring_char = '"""' if stripped.startswith('"""') else "'''"
            if stripped.count(docstring_char) == 2:  # Single line docstring
                continue
            else:
                in_docstring = True
                continue
        elif in_docstring and docstring_char in stripped:
            in_docstring = False
            continue
        elif in_docstring:
            continue
            
        # Look for import statements
        if stripped.startswith('import ') or stripped.startswith('from '):
            insert_index = i + 1
        # Stop at first non-import, non-comment line
        elif stripped and not stripped.startswith('#'):
            if insert_index == 0:
                insert_index = i
            break
    
    # Add UTF-8 handling
    utf8_fix = [
        "\n",
        "# Configure UTF-8 output handling for Windows\n",
        "import sys\n",
        "import io\n",
        "sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')\n",
        "sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')\n",
        "\n"
    ]
    
    # Insert the fix
    for j, line in enumerate(utf8_fix):
        lines.insert(insert_index + j, line)
    
    # Write back the file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✅ Fixed {filepath}")
    return True

def main():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    fixed_count = 0
    
    # List of critical scripts to fix
    critical_scripts = [
        'run_batch_calculations.py',
        'run_batch_with_reports.py',
        'fetch_iwm_data.py',
        'test_factor_flexibility.py',
        'test_equity_calculations.py',
        'update_equity_values.py',
        'generate_all_reports.py',
        'verify_setup.py',
        'verify_demo_portfolios.py',
        'test_factor_calculations.py',
        'check_factor_exposures.py'
    ]
    
    print("Fixing UTF-8 encoding issues in Python scripts...")
    print("=" * 60)
    
    for script in critical_scripts:
        filepath = os.path.join(scripts_dir, script)
        if os.path.exists(filepath):
            if add_utf8_handling(filepath):
                fixed_count += 1
        else:
            print(f"⚠️  {script} - not found")
    
    # Also check batch processing modules
    batch_dir = os.path.join(os.path.dirname(scripts_dir), 'app', 'batch')
    if os.path.exists(batch_dir):
        for filename in os.listdir(batch_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(batch_dir, filename)
                if add_utf8_handling(filepath):
                    fixed_count += 1
    
    print("=" * 60)
    print(f"✅ Fixed {fixed_count} files")
    print("\nYou can now run scripts directly without PYTHONIOENCODING=utf-8")

if __name__ == "__main__":
    main()