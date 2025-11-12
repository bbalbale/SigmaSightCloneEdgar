#!/usr/bin/env python3
"""
Railway migration script.
This script should be run via Railway CLI or as a one-off command in Railway dashboard.
"""
import subprocess
import sys
import os

def main():
    print("🚀 Starting Railway database migrations...")

    # Set migration mode
    os.environ["MIGRATION_MODE"] = "1"

    try:
        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("✅ Migrations completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
