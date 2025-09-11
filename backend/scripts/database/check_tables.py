#!/usr/bin/env python3
"""Check if market_data_cache table exists in the database."""

import asyncio
from sqlalchemy import text
from app.database import get_db

async def check_tables():
    """Check which tables exist in the database."""
    async for db in get_db():
        try:
            # Check if market_data_cache table exists
            result = await db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'market_data_cache'
            """))
            
            table_exists = result.scalar() is not None
            
            if table_exists:
                print("✅ market_data_cache table already exists")
                
                # Check table structure
                columns_result = await db.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'market_data_cache'
                    ORDER BY ordinal_position
                """))
                
                print("\nTable columns:")
                for row in columns_result:
                    print(f"  - {row.column_name}: {row.data_type} (nullable: {row.is_nullable})")
            else:
                print("❌ market_data_cache table does not exist")
                
            # List all tables
            all_tables = await db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            print("\nAll tables in database:")
            for row in all_tables:
                print(f"  - {row.table_name}")
                
        except Exception as e:
            print(f"Error checking tables: {e}")
        finally:
            await db.close()
            break

if __name__ == "__main__":
    asyncio.run(check_tables())
