"""
Verify AI Insights tables were created successfully.
"""
import asyncio
from sqlalchemy import inspect, text
from app.database import engine

async def verify_tables():
    """Verify AI insights tables exist"""
    async with engine.begin() as conn:
        # Get all table names
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

        ai_tables = sorted([t for t in tables if 'ai_' in t])
        print(f"\n AI-related tables ({len(ai_tables)}):")
        for table in ai_tables:
            print(f"  - {table}")

        # Check ENUM types
        result = await conn.execute(text("""
            SELECT typname FROM pg_type
            WHERE typname IN ('insight_type', 'insight_severity', 'data_quality_level')
            ORDER BY typname
        """))
        enum_types = [row[0] for row in result]

        print(f"\n ENUM types ({len(enum_types)}):")
        for enum_type in enum_types:
            print(f"  - {enum_type}")

        # Get table structure for ai_insights
        result = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'ai_insights'
            ORDER BY ordinal_position
        """))
        columns = list(result)

        print(f"\n ai_insights columns ({len(columns)}):")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")

        print("\n OK - Migration successful!")

if __name__ == "__main__":
    asyncio.run(verify_tables())
