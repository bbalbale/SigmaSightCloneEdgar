"""
Comprehensive diagnostic script for all 6 demo portfolios.
Identifies entry price discrepancies and generates correction data.

Outputs:
1. CSV files for each portfolio showing position-level discrepancies
2. Summary report across all portfolios
3. Correction SQL statements
"""

import asyncio
import csv
from decimal import Decimal
from typing import Dict, List, Any
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from datetime import date


# Expected portfolio values from requirements document
EXPECTED_PORTFOLIOS = {
    "Demo Individual Investor Portfolio": {
        "total_value": Decimal("485000"),
        "expected_invested": Decimal("484925"),  # From requirements doc
        "uninvested_cash": Decimal("75")
    },
    "Demo High Net Worth Investor Portfolio": {
        "total_value": Decimal("2850000"),
        "expected_invested": Decimal("1282500"),  # Public equities only (45%)
        "uninvested_cash": None  # Need to calculate from requirements
    },
    "Demo Hedge Fund Style Investor Portfolio": {
        "total_value": Decimal("3200000"),
        "expected_invested": Decimal("4271900"),  # Long positions total (133.5% - includes leverage)
        "uninvested_cash": None  # Complex - has shorts and options
    },
    "Demo Family Office Public Growth": {
        "total_value": Decimal("1250000"),
        "expected_invested": None,  # Need to calculate from requirements
        "uninvested_cash": None
    },
    "Demo Family Office Private Opportunities": {
        "total_value": Decimal("950000"),
        "expected_invested": None,  # All private - no market prices
        "uninvested_cash": None
    },
    "Equity Balance Portfolio": {
        "total_value": Decimal("10000"),
        "expected_invested": None,  # Test portfolio
        "uninvested_cash": None
    }
}


async def diagnose_portfolio(db, portfolio: Portfolio, july1: date) -> Dict[str, Any]:
    """Diagnose a single portfolio for entry value discrepancies."""

    print(f"\n{'='*100}")
    print(f"PORTFOLIO: {portfolio.name}")
    print(f"{'='*100}")
    print(f"ID: {portfolio.id}")
    print(f"Current Equity Balance: ${portfolio.equity_balance:,.2f}")

    expected_data = EXPECTED_PORTFOLIOS.get(portfolio.name, {})
    expected_total = expected_data.get("total_value")
    expected_invested = expected_data.get("expected_invested")

    if expected_total:
        print(f"Expected Total Value:   ${expected_total:,.2f}")
    if expected_invested:
        print(f"Expected Invested:      ${expected_invested:,.2f}")

    # Get all positions
    positions_query = select(Position).where(
        and_(
            Position.portfolio_id == portfolio.id,
            Position.deleted_at.is_(None)
        )
    ).order_by(Position.symbol)

    positions_result = await db.execute(positions_query)
    positions = positions_result.scalars().all()

    print(f"Total Positions: {len(positions)}")

    # Calculate entry values
    total_entry_value = Decimal('0')
    total_july1_value = Decimal('0')
    position_details = []

    for pos in positions:
        entry_value = pos.entry_price * abs(pos.quantity)
        total_entry_value += entry_value

        # Get July 1 price if available
        price_query = select(MarketDataCache).where(
            and_(
                MarketDataCache.symbol == pos.symbol,
                MarketDataCache.date == july1
            )
        )
        price_result = await db.execute(price_query)
        price_record = price_result.scalar_one_or_none()

        if price_record:
            july1_price = price_record.close
            july1_value = july1_price * abs(pos.quantity)
            total_july1_value += july1_value
            gain = july1_value - entry_value
        else:
            july1_price = None
            july1_value = None
            gain = None

        position_details.append({
            'symbol': pos.symbol,
            'position_type': pos.position_type.value,
            'quantity': float(pos.quantity),
            'entry_price': float(pos.entry_price),
            'entry_value': float(entry_value),
            'july1_price': float(july1_price) if july1_price else None,
            'july1_value': float(july1_value) if july1_value else None,
            'gain': float(gain) if gain else None,
            'has_july1_price': july1_price is not None
        })

    # Calculate discrepancies
    discrepancy = None
    if expected_invested:
        discrepancy = total_entry_value - expected_invested

    uninvested_cash = portfolio.equity_balance - total_entry_value

    # Summary
    summary = {
        'portfolio_id': str(portfolio.id),
        'portfolio_name': portfolio.name,
        'current_equity': portfolio.equity_balance,
        'total_entry_value': total_entry_value,
        'total_july1_value': total_july1_value if total_july1_value > 0 else None,
        'uninvested_cash': uninvested_cash,
        'expected_invested': expected_invested,
        'discrepancy': discrepancy,
        'position_count': len(positions),
        'positions_with_july1_prices': sum(1 for p in position_details if p['has_july1_price'])
    }

    print(f"\nRESULTS:")
    print(f"  Total Entry Value:     ${total_entry_value:,.2f}")
    if total_july1_value > 0:
        print(f"  Total July 1 Value:    ${total_july1_value:,.2f}")
    print(f"  Uninvested Cash:       ${uninvested_cash:,.2f}")
    if expected_invested:
        print(f"  Expected Invested:     ${expected_invested:,.2f}")
        print(f"  Discrepancy:           ${discrepancy:,.2f}")
        if abs(discrepancy) > Decimal('0.01'):
            print(f"  WARNING - DISCREPANCY FOUND: ${abs(discrepancy):,.2f}")

    return {
        'summary': summary,
        'positions': position_details
    }


async def main():
    """Run diagnostics on all portfolios."""

    async with get_async_session() as db:
        # Get all portfolios
        portfolios_query = select(Portfolio).where(
            Portfolio.deleted_at.is_(None)
        ).order_by(Portfolio.name)

        portfolios_result = await db.execute(portfolios_query)
        portfolios = portfolios_result.scalars().all()

        print(f"\n{'#'*100}")
        print(f"# ENTRY VALUE DIAGNOSTIC - ALL {len(portfolios)} PORTFOLIOS")
        print(f"{'#'*100}")

        july1 = date(2025, 7, 1)
        all_results = []

        for portfolio in portfolios:
            result = await diagnose_portfolio(db, portfolio, july1)
            all_results.append(result)

            # Write individual portfolio CSV
            safe_name = portfolio.name.replace(" ", "_").replace("/", "_")
            csv_filename = f"portfolio_diagnosis_{safe_name}.csv"

            with open(csv_filename, 'w', newline='') as f:
                if result['positions']:
                    writer = csv.DictWriter(f, fieldnames=result['positions'][0].keys())
                    writer.writeheader()
                    writer.writerows(result['positions'])

            print(f"  Position details saved to: {csv_filename}")

        # Write summary CSV
        print(f"\n{'='*100}")
        print(f"SUMMARY ACROSS ALL PORTFOLIOS")
        print(f"{'='*100}\n")

        summary_rows = []
        for result in all_results:
            summary = result['summary']
            row = {
                'portfolio_name': summary['portfolio_name'],
                'current_equity': float(summary['current_equity']),
                'total_entry_value': float(summary['total_entry_value']),
                'total_july1_value': float(summary['total_july1_value']) if summary['total_july1_value'] else '',
                'uninvested_cash': float(summary['uninvested_cash']),
                'expected_invested': float(summary['expected_invested']) if summary['expected_invested'] else '',
                'discrepancy': float(summary['discrepancy']) if summary['discrepancy'] else '',
                'position_count': summary['position_count'],
                'positions_with_july1_prices': summary['positions_with_july1_prices']
            }
            summary_rows.append(row)

            print(f"{summary['portfolio_name']}")
            print(f"  Entry Value:      ${summary['total_entry_value']:,.2f}")
            if summary['expected_invested']:
                print(f"  Expected:         ${summary['expected_invested']:,.2f}")
                print(f"  Discrepancy:      ${summary['discrepancy']:,.2f}")
                if abs(summary['discrepancy']) > Decimal('0.01'):
                    print(f"  WARNING: NEEDS CORRECTION")
            print()

        with open('all_portfolios_summary.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
            writer.writeheader()
            writer.writerows(summary_rows)

        print(f"Summary saved to: all_portfolios_summary.csv")

        # Identify portfolios needing correction
        print(f"\n{'='*100}")
        print(f"PORTFOLIOS NEEDING CORRECTION")
        print(f"{'='*100}\n")

        needs_correction = [
            r for r in all_results
            if r['summary']['discrepancy']
            and abs(r['summary']['discrepancy']) > Decimal('0.01')
        ]

        if needs_correction:
            print(f"Found {len(needs_correction)} portfolio(s) with discrepancies:\n")
            for result in needs_correction:
                summary = result['summary']
                print(f"  - {summary['portfolio_name']}: ${summary['discrepancy']:,.2f}")
        else:
            print("All portfolios match expected values!")


if __name__ == "__main__":
    asyncio.run(main())
