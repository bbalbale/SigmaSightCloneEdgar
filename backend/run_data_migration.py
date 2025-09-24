#!/usr/bin/env python
"""Run the data migration to wrap positions in strategies."""
import subprocess
import os


def run_migration():
    """Execute the migration script using venv Python."""
    venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')

    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment Python not found at {venv_python}")
        return False

    try:
        print("Running data migration to create strategies for existing positions...")
        print("-" * 60)

        result = subprocess.run(
            [venv_python, 'migrate_positions_to_strategies.py'],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.stderr:
            # Filter out INFO logs from stderr
            error_lines = [line for line in result.stderr.split('\n')
                          if 'INFO' not in line and line.strip()]
            if error_lines:
                print("Errors:")
                print('\n'.join(error_lines))

        return result.returncode == 0

    except Exception as e:
        print(f"Error running migration: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\nData migration completed successfully!")
    else:
        print("\nData migration failed!")