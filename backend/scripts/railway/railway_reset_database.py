#!/usr/bin/env python3
"""
Reset and reseed Railway database completely
DESTRUCTIVE: Drops all tables and recreates from scratch
"""
import os
import subprocess
import sys

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver")

print("⚠️  WARNING: This will DROP ALL TABLES and reseed the database!")
print("⚠️  All existing data will be PERMANENTLY DELETED!")
print("")

# Run reset and seed
print("🚀 Starting database reset and reseed...")
result = subprocess.run(
    ['python', 'scripts/database/reset_and_seed.py', 'reset', '--confirm'],
    check=False
)

if result.returncode == 0:
    print("\n✅ Database reset and reseed completed successfully!")
    print("\n📊 Demo data created:")
    print("  - 3 portfolios with 75 positions")
    print("  - 130 position-tag relationships")
    print("  - 8 factor definitions")
    print("  - 18 stress test scenarios")
    print("\n🔐 Demo accounts:")
    print("  - demo_individual@sigmasight.com")
    print("  - demo_hnw@sigmasight.com")
    print("  - demo_hedgefundstyle@sigmasight.com")
    print("  Password (all): demo12345")
else:
    print("\n❌ Database reset failed!")
    sys.exit(1)
