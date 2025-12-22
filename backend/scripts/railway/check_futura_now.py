#!/usr/bin/env python
"""Quick check of Futura portfolio status."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

async def check():
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, name, equity_balance FROM portfolios WHERE name ILIKE '%futura%'"))
        row = result.fetchone()
        if row:
            pid, name, equity = row
            print(f"Portfolio: {name}")
            print(f"ID: {pid}")
            print(f"Current equity_balance: ${float(equity):,.2f}")
            print()
            result = await conn.execute(text(f"SELECT snapshot_date, equity_balance, daily_pnl FROM portfolio_snapshots WHERE portfolio_id = '{pid}' ORDER BY snapshot_date ASC LIMIT 5"))
            snaps = result.fetchall()
            if snaps:
                print("First 5 snapshots:")
                for s in snaps:
                    print(f"  {s[0]}: equity=${float(s[1]):,.2f}, daily_pnl=${float(s[2] or 0):,.2f}")
            else:
                print("No snapshots found")
        else:
            print("Futura portfolio not found")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
