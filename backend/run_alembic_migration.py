#!/usr/bin/env python
"""Run Alembic migrations using the virtual environment."""
import subprocess
import sys
import os

def run_migration():
    """Execute alembic upgrade head command."""
    # Get the venv Python path
    venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')

    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment Python not found at {venv_python}")
        return False

    # Run alembic upgrade head using the venv Python
    try:
        print("Running Alembic migration...")
        result = subprocess.run(
            [venv_python, '-m', 'alembic', 'upgrade', 'head'],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("SUCCESS: Migration completed successfully!")
            print(result.stdout)
            return True
        else:
            print("ERROR: Migration failed with error:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"ERROR: Error running migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)