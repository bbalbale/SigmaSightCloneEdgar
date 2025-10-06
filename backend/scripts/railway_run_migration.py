#!/usr/bin/env python3
"""
Run Alembic migration on Railway
Automatically converts DATABASE_URL to use asyncpg driver
"""
import os
import subprocess
import sys

# Fix Railway DATABASE_URL format (postgresql:// -> postgresql+asyncpg://)
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print(f"✅ Converted DATABASE_URL to use asyncpg driver")

print("🚀 Running Alembic migration...")
result = subprocess.run(['python', '-m', 'alembic', 'upgrade', 'head'], check=False)

if result.returncode == 0:
    print("✅ Migration completed successfully!")
else:
    print("❌ Migration failed!")
    sys.exit(1)
