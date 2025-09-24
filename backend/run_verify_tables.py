#!/usr/bin/env python
"""Run table verification using subprocess."""
import subprocess
import os

def run_verification():
    """Execute the verification script using venv Python."""
    venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')

    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment Python not found at {venv_python}")
        return False

    try:
        print("Verifying strategy tables...")
        result = subprocess.run(
            [venv_python, 'verify_strategy_tables.py'],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"Error running verification: {e}")
        return False

if __name__ == "__main__":
    run_verification()