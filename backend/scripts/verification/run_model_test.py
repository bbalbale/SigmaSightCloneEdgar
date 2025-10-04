#!/usr/bin/env python
"""Run model import test using subprocess."""
import subprocess
import os

def run_test():
    """Execute the test script using venv Python."""
    venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')

    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment Python not found at {venv_python}")
        return False

    try:
        print("Running model import tests...")
        result = subprocess.run(
            [venv_python, 'test_model_imports.py'],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"Error running test: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = run_test()
    sys.exit(0 if success else 1)