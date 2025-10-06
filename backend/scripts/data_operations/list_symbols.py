"""
List unique ticker symbols from the database.

Usage examples:
  uv run python backend/scripts/list_symbols.py
  uv run python backend/scripts/list_symbols.py --format json
  uv run python backend/scripts/list_symbols.py --no-include-underlying
  uv run python backend/scripts/list_symbols.py --all
  uv run python backend/scripts/list_symbols.py --portfolio-id <uuid>

Requires environment variables configured in backend/.env (DATABASE_URL, etc.)
and a running database (Docker).
"""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Iterable, Optional, Set

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.positions import Position, PositionType


def _normalize_symbol(sym: Optional[str]) -> Optional[str]:
    if sym is None:
        return None
    s = sym.strip().upper()
    return s or None


async def fetch_symbols(
    session: AsyncSession,
    *,
    include_underlying: bool = True,
    active_only: bool = True,
    exclude_options: bool = False,
    portfolio_ids: Optional[list[str]] = None,
) -> Set[str]:
    conditions = []
    if active_only:
        conditions.append(Position.exit_date.is_(None))
        conditions.append(Position.deleted_at.is_(None))
    if portfolio_ids:
        conditions.append(Position.portfolio_id.in_(portfolio_ids))
    if exclude_options:
        conditions.append(
            Position.position_type.notin_(
                [PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP]
            )
        )

    # Distinct main symbols
    stmt_symbols = select(func.distinct(Position.symbol))
    if conditions:
        stmt_symbols = stmt_symbols.where(*conditions)

    result = await session.execute(stmt_symbols)
    symbols: Set[str] = set()
    for (sym,) in result.fetchall():
        ns = _normalize_symbol(sym)
        if ns:
            symbols.add(ns)

    if include_underlying:
        stmt_under = select(func.distinct(Position.underlying_symbol)).where(Position.underlying_symbol.is_not(None))
        if conditions:
            stmt_under = stmt_under.where(*conditions)
        result2 = await session.execute(stmt_under)
        for (usym,) in result2.fetchall():
            ns = _normalize_symbol(usym)
            if ns:
                symbols.add(ns)

    return symbols


async def main() -> int:
    parser = argparse.ArgumentParser(description="List unique ticker symbols from Positions")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument(
        "--include-underlying",
        dest="include_underlying",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include underlying_symbol for options (default: true)",
    )
    parser.add_argument(
        "--active-only",
        dest="active_only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only include active (non-exited, non-deleted) positions (default: true)",
    )
    parser.add_argument(
        "--all",
        dest="active_only",
        action="store_false",
        help="Include all positions (overrides --active-only)",
    )
    parser.add_argument(
        "--portfolio-id",
        dest="portfolio_ids",
        action="append",
        help="Filter to one or more portfolio UUIDs (repeatable)",
    )
    parser.add_argument(
        "--exclude-options",
        dest="exclude_options",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Exclude option contract positions (LC/LP/SC/SP) from symbol list",
    )

    args = parser.parse_args()

    async with get_async_session() as session:
        symbols = await fetch_symbols(
            session,
            include_underlying=args.include_underlying,
            active_only=args.active_only,
            exclude_options=args.exclude_options,
            portfolio_ids=args.portfolio_ids,
        )

    sorted_syms = sorted(symbols)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "count": len(sorted_syms),
                    "symbols": sorted_syms,
                    "filters": {
                        "include_underlying": args.include_underlying,
                        "active_only": args.active_only,
                        "portfolio_ids": args.portfolio_ids or [],
                    },
                },
                indent=2,
            )
        )
    else:
        for s in sorted_syms:
            print(s)
        print(f"\nCOUNT: {len(sorted_syms)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
