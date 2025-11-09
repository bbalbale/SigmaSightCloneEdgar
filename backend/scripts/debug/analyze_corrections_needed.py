"""
Analyze exactly what corrections are needed for each portfolio.
This script calculates the precise entry price adjustments needed.
"""

import asyncio
import csv
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position, PositionType
from datetime import date


async def analyze_individual_investor(db):
    """Analyze Individual Investor portfolio corrections."""

    print("\n" + "="*100)
    print("INDIVIDUAL INVESTOR PORTFOLIO")
    print("="*100)

    portfolio = await db.execute(
        select(Portfolio).where(Portfolio.name == "Demo Individual Investor Portfolio")
    )
    portfolio = portfolio.scalar_one()

    positions = await db.execute(
        select(Position).where(
            and_(
                Position.portfolio_id == portfolio.id,
                Position.deleted_at.is_(None)
            )
        ).order_by(Position.symbol)
    )
    positions = positions.scalars().all()

    current_total = sum(p.entry_price * p.quantity for p in positions)
    target_total = Decimal("484925")
    delta = target_total - current_total

    print(f"Current Total: ${current_total:,.2f}")
    print(f"Target Total:  ${target_total:,.2f}")
    print(f"Delta:         ${delta:,.2f}")

    # Find VTI and VNQ
    vti = next((p for p in positions if p.symbol == "VTI"), None)
    vnq = next((p for p in positions if p.symbol == "VNQ"), None)

    if vti and vnq:
        # Split delta: Give VTI 70%, VNQ 30% (roughly proportional to their values)
        vti_delta = (delta * Decimal("0.7")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vnq_delta = delta - vti_delta  # Remainder goes to VNQ to ensure exact match

        vti_new_entry = vti.entry_price + (vti_delta / vti.quantity)
        vnq_new_entry = vnq.entry_price + (vnq_delta / vnq.quantity)

        print(f"\nVTI Adjustment:")
        print(f"  Current: {vti.quantity} × ${vti.entry_price} = ${vti.entry_price * vti.quantity:,.2f}")
        print(f"  New:     {vti.quantity} × ${vti_new_entry:.4f} = ${vti_new_entry * vti.quantity:,.2f}")
        print(f"  Delta:   ${vti_delta:,.2f}")

        print(f"\nVNQ Adjustment:")
        print(f"  Current: {vnq.quantity} × ${vnq.entry_price} = ${vnq.entry_price * vnq.quantity:,.2f}")
        print(f"  New:     {vnq.quantity} × ${vnq_new_entry:.4f} = ${vnq_new_entry * vnq.quantity:,.2f}")
        print(f"  Delta:   ${vnq_delta:,.2f}")

        # Verify
        new_total = sum(
            (vti_new_entry * vti.quantity if p.symbol == "VTI" else
             vnq_new_entry * vnq.quantity if p.symbol == "VNQ" else
             p.entry_price * p.quantity)
            for p in positions
        )
        print(f"\nVerification:")
        print(f"  New Total: ${new_total:,.2f}")
        print(f"  Target:    ${target_total:,.2f}")
        print(f"  Match:     {abs(new_total - target_total) < Decimal('0.01')}")

        return [
            {"position_id": str(vti.id), "symbol": "VTI", "old_entry_price": float(vti.entry_price), "new_entry_price": float(vti_new_entry)},
            {"position_id": str(vnq.id), "symbol": "VNQ", "old_entry_price": float(vnq.entry_price), "new_entry_price": float(vnq_new_entry)}
        ]


async def analyze_high_net_worth(db):
    """Analyze High Net Worth portfolio corrections."""

    print("\n" + "="*100)
    print("HIGH NET WORTH PORTFOLIO")
    print("="*100)

    portfolio = await db.execute(
        select(Portfolio).where(Portfolio.name == "Demo High Net Worth Investor Portfolio")
    )
    portfolio = portfolio.scalar_one()

    positions = await db.execute(
        select(Position).where(
            and_(
                Position.portfolio_id == portfolio.id,
                Position.deleted_at.is_(None)
            )
        ).order_by(Position.symbol)
    )
    positions = positions.scalars().all()

    # Separate public vs private
    public_positions = [p for p in positions if p.investment_class == "PUBLIC"]
    private_positions = [p for p in positions if p.investment_class == "PRIVATE"]

    current_public_total = sum(p.entry_price * p.quantity for p in public_positions)
    current_private_total = sum(p.entry_price * p.quantity for p in private_positions)
    target_public_total = Decimal("1282500")

    print(f"Public Positions:  {len(public_positions)}")
    print(f"Private Positions: {len(private_positions)}")
    print(f"\nCurrent Public Total:  ${current_public_total:,.2f}")
    print(f"Target Public Total:   ${target_public_total:,.2f}")
    print(f"Delta:                 ${target_public_total - current_public_total:,.2f}")
    print(f"\nCurrent Private Total: ${current_private_total:,.2f} (should remain unchanged)")

    delta = target_public_total - current_public_total

    if abs(delta) < Decimal("0.01"):
        print("\nPublic equities already match target!")
        return []

    # Distribute delta proportionally across all public positions
    corrections = []
    adjustment_factor = target_public_total / current_public_total

    print(f"\nAdjustment Factor: {adjustment_factor:.6f}")
    print(f"\nProposed Corrections:")

    for p in public_positions:
        old_entry = p.entry_price
        new_entry = (old_entry * adjustment_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        old_value = old_entry * p.quantity
        new_value = new_entry * p.quantity

        print(f"  {p.symbol:10s}: ${old_entry:8.2f} -> ${new_entry:8.2f}  (${old_value:12,.2f} -> ${new_value:12,.2f})")

        corrections.append({
            "position_id": str(p.id),
            "symbol": p.symbol,
            "old_entry_price": float(old_entry),
            "new_entry_price": float(new_entry)
        })

    # Verify
    new_total = sum(
        Decimal(str(next((c["new_entry_price"] for c in corrections if c["position_id"] == str(p.id)), float(p.entry_price)))) * p.quantity
        for p in public_positions
    )

    print(f"\nVerification:")
    print(f"  New Public Total: ${new_total:,.2f}")
    print(f"  Target:           ${target_public_total:,.2f}")
    print(f"  Difference:       ${abs(new_total - target_public_total):,.2f}")

    return corrections


async def analyze_hedge_fund(db):
    """Analyze Hedge Fund Style portfolio corrections."""

    print("\n" + "="*100)
    print("HEDGE FUND STYLE PORTFOLIO")
    print("="*100)

    portfolio = await db.execute(
        select(Portfolio).where(Portfolio.name == "Demo Hedge Fund Style Investor Portfolio")
    )
    portfolio = portfolio.scalar_one()

    positions = await db.execute(
        select(Position).where(
            and_(
                Position.portfolio_id == portfolio.id,
                Position.deleted_at.is_(None)
            )
        ).order_by(Position.symbol)
    )
    positions = positions.scalars().all()

    # Categorize positions
    long_stocks = [p for p in positions if p.position_type == PositionType.LONG and p.quantity > 0]
    short_stocks = [p for p in positions if p.position_type == PositionType.SHORT and p.quantity < 0]
    options = [p for p in positions if p.position_type in (PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP)]

    current_long_total = sum(p.entry_price * abs(p.quantity) for p in long_stocks)
    current_short_total = sum(p.entry_price * abs(p.quantity) for p in short_stocks)
    current_options_total = sum(p.entry_price * abs(p.quantity) for p in options)

    target_long_total = Decimal("4960000")  # Longs including options
    target_short_total = Decimal("2240000")  # Shorts (absolute value)

    print(f"Long Stocks:  {len(long_stocks)}")
    print(f"Short Stocks: {len(short_stocks)}")
    print(f"Options:      {len(options)}")

    print(f"\nCurrent Long Total:    ${current_long_total:,.2f}")
    print(f"Current Short Total:   ${current_short_total:,.2f}")
    print(f"Current Options Total: ${current_options_total:,.2f}")

    print(f"\nTarget Long Total (stocks only, options = 0):  ${target_long_total:,.2f}")
    print(f"Target Short Total:                            ${target_short_total:,.2f}")

    corrections = []

    # Set all options to entry_price = 0
    print(f"\nOptions Corrections (set all to $0):")
    for p in options:
        print(f"  {p.symbol:10s} {p.position_type.value:4s}: ${p.entry_price:8.2f} -> $0.00")
        corrections.append({
            "position_id": str(p.id),
            "symbol": p.symbol,
            "position_type": p.position_type.value,
            "old_entry_price": float(p.entry_price),
            "new_entry_price": 0.0
        })

    # Adjust long stocks to hit target
    delta_long = target_long_total - current_long_total
    if abs(delta_long) > Decimal("0.01"):
        adjustment_factor_long = target_long_total / current_long_total
        print(f"\nLong Stocks Adjustment Factor: {adjustment_factor_long:.6f}")
        print(f"Long Stocks Corrections:")

        for p in long_stocks:
            old_entry = p.entry_price
            new_entry = (old_entry * adjustment_factor_long).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            print(f"  {p.symbol:10s}: ${old_entry:8.2f} -> ${new_entry:8.2f}")

            corrections.append({
                "position_id": str(p.id),
                "symbol": p.symbol,
                "position_type": "LONG",
                "old_entry_price": float(old_entry),
                "new_entry_price": float(new_entry)
            })

    # Adjust short stocks to hit target
    delta_short = target_short_total - current_short_total
    if abs(delta_short) > Decimal("0.01"):
        adjustment_factor_short = target_short_total / current_short_total
        print(f"\nShort Stocks Adjustment Factor: {adjustment_factor_short:.6f}")
        print(f"Short Stocks Corrections:")

        for p in short_stocks:
            old_entry = p.entry_price
            new_entry = (old_entry * adjustment_factor_short).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            print(f"  {p.symbol:10s}: ${old_entry:8.2f} -> ${new_entry:8.2f}")

            corrections.append({
                "position_id": str(p.id),
                "symbol": p.symbol,
                "position_type": "SHORT",
                "old_entry_price": float(old_entry),
                "new_entry_price": float(new_entry)
            })

    # Verify
    new_long_total = sum(
        Decimal(str(next((c["new_entry_price"] for c in corrections if c["position_id"] == str(p.id)), float(p.entry_price)))) * abs(p.quantity)
        for p in long_stocks
    )
    new_short_total = sum(
        Decimal(str(next((c["new_entry_price"] for c in corrections if c["position_id"] == str(p.id)), float(p.entry_price)))) * abs(p.quantity)
        for p in short_stocks
    )

    print(f"\nVerification:")
    print(f"  New Long Total:  ${new_long_total:,.2f} (target: ${target_long_total:,.2f})")
    print(f"  New Short Total: ${new_short_total:,.2f} (target: ${target_short_total:,.2f})")
    print(f"  Options Total:   $0.00")

    return corrections


async def main():
    """Run analysis on all portfolios needing correction."""

    async with get_async_session() as db:
        print("\n" + "#"*100)
        print("# CORRECTION ANALYSIS - PORTFOLIOS NEEDING FIXES")
        print("#"*100)

        all_corrections = {}

        # Individual Investor
        individual_corrections = await analyze_individual_investor(db)
        all_corrections["Individual Investor"] = individual_corrections

        # High Net Worth
        hnw_corrections = await analyze_high_net_worth(db)
        all_corrections["High Net Worth"] = hnw_corrections

        # Hedge Fund
        hedge_corrections = await analyze_hedge_fund(db)
        all_corrections["Hedge Fund"] = hedge_corrections

        # Save corrections to CSV
        print("\n" + "="*100)
        print("SAVING CORRECTION PLAN")
        print("="*100)

        all_corrections_flat = []
        for portfolio_name, corrections in all_corrections.items():
            for corr in corrections:
                corr["portfolio"] = portfolio_name
                all_corrections_flat.append(corr)

        if all_corrections_flat:
            # Normalize fieldnames - use all unique keys
            all_keys = set()
            for corr in all_corrections_flat:
                all_keys.update(corr.keys())
            fieldnames = sorted(all_keys)

            with open("entry_price_corrections_plan.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_corrections_flat)

            print(f"Corrections plan saved to: entry_price_corrections_plan.csv")
            print(f"Total corrections needed: {len(all_corrections_flat)}")


if __name__ == "__main__":
    asyncio.run(main())
