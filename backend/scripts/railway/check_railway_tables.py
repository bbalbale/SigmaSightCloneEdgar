#!/usr/bin/env python
"""Check what tables exist in Railway database."""
import os
os.environ["MIGRATION_MODE"] = "1"

from sqlalchemy import create_engine, text

railway_url = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"
engine = create_engine(railway_url)

print("=" * 60)
print("RAILWAY DATABASE TABLES")
print("=" * 60)

with engine.connect() as conn:
    # Check if alembic_version table exists
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
    ))
    has_alembic = result.scalar()

    if has_alembic:
        # Get current version
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"Alembic version table: EXISTS")
        print(f"Current version: {version}")
    else:
        print(f"Alembic version table: DOES NOT EXIST")

    print()
    print("All tables:")
    print("-" * 60)

    # List all tables
    result = conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    ))
    tables = [row[0] for row in result]
    for table in tables:
        print(f"  - {table}")

    print()
    print(f"Total tables: {len(tables)}")
    print("=" * 60)
