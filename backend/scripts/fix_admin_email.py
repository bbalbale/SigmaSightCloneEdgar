"""Fix admin email typo."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

async def fix_email():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Update the email
        await conn.execute(text("""
            UPDATE admin_users
            SET email = 'bbalbale@gmail.com'
            WHERE email = 'bbalbale@gmailcom'
        """))
        print("Updated: bbalbale@gmailcom -> bbalbale@gmail.com")

    # Verify
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT email, full_name FROM admin_users"))
        rows = result.fetchall()
        print("\nAdmin Users:")
        for row in rows:
            print(f"  - {row[0]} ({row[1]})")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_email())
