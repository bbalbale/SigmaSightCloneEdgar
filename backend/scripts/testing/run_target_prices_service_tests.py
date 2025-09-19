#!/usr/bin/env python
"""
Service-layer smoke tests for Target Prices (no HTTP required).

Runs a sequential flow:
- create → list → get → update → bulk create → bulk update → CSV import

Assumes:
- Database is running and backend/.env is configured
- Demo portfolios exist (uses the first portfolio found)

Outputs concise results for each step; exits non-zero on critical failure.
"""
import asyncio
from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy import select, and_, delete

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.target_prices import TargetPrice
from app.schemas.target_prices import TargetPriceCreate, TargetPriceUpdate
from app.services.target_price_service import TargetPriceService


async def get_first_portfolio_id() -> Optional[UUID]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Portfolio).limit(1))
        p = result.scalar_one_or_none()
        return p.id if p else None


async def delete_if_exists(db, portfolio_id: UUID, symbol: str, position_type: str = "LONG"):
    result = await db.execute(
        select(TargetPrice.id).where(
            and_(TargetPrice.portfolio_id == portfolio_id,
                 TargetPrice.symbol == symbol,
                 TargetPrice.position_type == position_type)
        )
    )
    row = result.first()
    if row:
        await db.execute(delete(TargetPrice).where(TargetPrice.id == row[0]))
        await db.commit()


async def main() -> int:
    svc = TargetPriceService()

    portfolio_id = await get_first_portfolio_id()
    if not portfolio_id:
        print("❌ No portfolio found; seed data first.")
        return 1
    print(f"📦 Using portfolio: {portfolio_id}")

    async with AsyncSessionLocal() as db:
        # Use test symbols unlikely to collide with real market data
        sym1, sym2, sym3, sym4, sym5 = "ZZTEST", "ZZTEST2", "ZZTEST3", "ZZTEST4", "ZZTEST5"

        # Cleanup any leftovers from prior runs
        for s in (sym1, sym2, sym3, sym4, sym5):
            await delete_if_exists(db, portfolio_id, s, "LONG")

        # 1) Create
        create_data = TargetPriceCreate(
            symbol=sym1,
            position_type="LONG",
            target_price_eoy=Decimal("120"),
            target_price_next_year=Decimal("130"),
            downside_target_price=Decimal("80"),
            current_price=Decimal("100"),  # used as fallback if no market data
        )
        tp = await svc.create_target_price(db, portfolio_id, create_data)
        print(f"✅ Create: {tp.symbol} id={tp.id} eoy_ret={tp.expected_return_eoy:.2f}%")

        # 2) List (filter by symbol)
        lst = await svc.get_portfolio_target_prices(db, portfolio_id)
        found = [t for t in lst if t.symbol == sym1 and t.position_type == "LONG"]
        print(f"✅ List: total={len(lst)}; found_sym1={len(found)}")

        # 3) Get by ID
        tp_get = await svc.get_target_price(db, tp.id)
        print(f"✅ Get: id={tp_get.id} symbol={tp_get.symbol} current={tp_get.current_price}")

        # 4) Update (change EOY target)
        upd = TargetPriceUpdate(target_price_eoy=Decimal("110"))
        tp_upd = await svc.update_target_price(db, tp.id, upd)
        print(f"✅ Update: new_eoy={tp_upd.target_price_eoy} new_ret={tp_upd.expected_return_eoy:.2f}%")

        # 5) Bulk create (2 symbols)
        bulk = [
            TargetPriceCreate(symbol=sym2, position_type="LONG", target_price_eoy=Decimal("105"), current_price=Decimal("100")),
            TargetPriceCreate(symbol=sym3, position_type="LONG", target_price_eoy=Decimal("210"), current_price=Decimal("200")),
        ]
        created = await svc.bulk_create_target_prices(db, portfolio_id, bulk)
        print(f"✅ Bulk create: created={len(created)}")

        # 6) Bulk update (by symbol + position_type)
        updates = [
            {"symbol": sym2, "position_type": "LONG", "target_price_eoy": Decimal("115")},
            {"symbol": sym3, "position_type": "LONG", "target_price_eoy": Decimal("220")},
        ]
        # Emulate API bulk-update loop
        updated_count = 0
        errors = []
        all_targets = await svc.get_portfolio_target_prices(db, portfolio_id)
        for item in updates:
            symbol = item["symbol"]
            pt = item.get("position_type", "LONG")
            tgt = next((x for x in all_targets if x.symbol == symbol and x.position_type == pt), None)
            if not tgt:
                errors.append(f"not found: {symbol} ({pt})")
                continue
            data = TargetPriceUpdate(**{k: v for k, v in item.items() if k not in ("symbol", "position_type")})
            await svc.update_target_price(db, tgt.id, data)
            updated_count += 1
        print(f"✅ Bulk update: updated={updated_count} errors={len(errors)}")

        # 7) CSV import (2 rows)
        csv_content = (
            "symbol,position_type,target_eoy,target_next_year,downside,current_price\n"
            f"{sym4},LONG,150,160,120,140\n"
            f"{sym5},LONG,90,100,70,80\n"
        )
        imp = await svc.import_from_csv(db, portfolio_id, csv_content, update_existing=False)
        print(f"✅ Import CSV: created={imp['created']} updated={imp['updated']} errors={len(imp['errors'])} total={imp['total']}")

        # Done
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

