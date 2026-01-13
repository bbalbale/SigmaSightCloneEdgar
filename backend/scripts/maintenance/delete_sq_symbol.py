#!/usr/bin/env python3
"""
Delete SQ from symbol_universe (XYZ already exists)

Usage:
    python scripts/maintenance/delete_sq_symbol.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import get_async_session


async def main():
    print("Deleting SQ from symbol_universe...")

    async with get_async_session() as db:
        # Check if SQ exists
        check = await db.execute(
            text("SELECT symbol FROM symbol_universe WHERE symbol = 'SQ'")
        )
        row = check.fetchone()

        if row:
            await db.execute(
                text("DELETE FROM symbol_universe WHERE symbol = 'SQ'")
            )
            await db.commit()
            print("[OK] Deleted SQ from symbol_universe")
        else:
            print("[SKIP] SQ not found in symbol_universe")


if __name__ == "__main__":
    asyncio.run(main())
