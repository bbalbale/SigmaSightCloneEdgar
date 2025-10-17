"""
Script to remove sample implementation code from completed phases in RiskMetricsExecution.md
Keeps Alembic migration code, removes validation scripts and implementation examples.
"""

def clean_execution_doc():
    file_path = r"C:\Users\BenBalbale\CascadeProjects\SigmaSight\frontend\_docs\RiskMetricsExecution.md"

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Sections to remove (line ranges) - adjusting for 0-based indexing
    # Phase 0 - Remove Sections 2-5 (keep Section 1 - Alembic)
    remove_ranges = [
        (417, 1006),   # Section 2: Calculation Scripts
        (1006, 1040),  # Section 3: API Changes
        (1040, 1115),  # Section 4: Frontend Changes
        (1115, 1288),  # Section 5: Integration & Testing

        # Phase 1 - Remove Sections 2-5 (keep Section 1 - Alembic)
        (1488, 1856),  # Section 2: Benchmark Data Management
        (1856, 2251),  # Section 3: Sector Analysis Calculations
        (2251, 2285),  # Section 3: API Changes (duplicate)
        (2285, 2506),  # Section 4: Frontend Changes
        (2506, 2650),  # Section 5: Integration & Testing

        # Phase 2 - Remove Section 2 only (database/models/calc complete)
        (2904, 3555),  # Section 2: Calculation Scripts
    ]

    # Mark lines for removal
    keep_lines = [True] * len(lines)
    for start, end in remove_ranges:
        for i in range(start, min(end, len(lines))):
            keep_lines[i] = False

    # Keep lines that aren't marked for removal
    cleaned_lines = [line for i, line in enumerate(lines) if keep_lines[i]]

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

    print(f"Cleaned document: removed {len(lines) - len(cleaned_lines)} lines")
    print(f"Original: {len(lines)} lines")
    print(f"Cleaned: {len(cleaned_lines)} lines")

if __name__ == "__main__":
    clean_execution_doc()
