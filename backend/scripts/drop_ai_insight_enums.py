"""
Drop AI Insight ENUM types from database.

This script drops the ENUM types so Alembic migration can create them cleanly.
"""
import psycopg2
from app.config import settings

def drop_enums():
    """Drop AI insight ENUM types"""
    # Parse async DATABASE_URL to get sync connection string
    db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        print("Dropping AI insight ENUM types...")
        cursor.execute("DROP TYPE IF EXISTS insight_type CASCADE")
        print("OK - Dropped insight_type")

        cursor.execute("DROP TYPE IF EXISTS insight_severity CASCADE")
        print("OK - Dropped insight_severity")

        cursor.execute("DROP TYPE IF EXISTS data_quality_level CASCADE")
        print("OK - Dropped data_quality_level")

        print("\nOK - All AI insight ENUM types dropped successfully")

    except Exception as e:
        print(f"ERROR: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    drop_enums()
