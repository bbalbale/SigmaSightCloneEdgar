#!/usr/bin/env python
"""Run ORM relationship test using subprocess."""
import subprocess
import os

def run_test():
    """Execute the test script using venv Python."""
    venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')

    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment Python not found at {venv_python}")
        return False

    try:
        print("Running ORM relationship tests...")
        result = subprocess.run(
            [venv_python, 'test_orm_relationships.py'],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.stderr:
            # Filter out SQLAlchemy INFO logs
            error_lines = [line for line in result.stderr.split('\n')
                          if 'INFO sqlalchemy' not in line and line.strip()]
            if error_lines:
                print("Errors:")
                print('\n'.join(error_lines))

        return result.returncode == 0

    except Exception as e:
        print(f"Error running test: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = run_test()
    sys.exit(0 if success else 1)