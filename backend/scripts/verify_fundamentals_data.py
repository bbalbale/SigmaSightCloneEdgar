"""
Verify Fundamental Data Collection

Checks what fundamental data was collected during Phase 1.5:
- Income statements
- Balance sheets
- Cash flows
- Analyst estimates
"""
import asyncio
from sqlalchemy import select, func, distinct
from app.database import AsyncSessionLocal
from app.models.fundamentals import IncomeStatement, BalanceSheet, CashFlow
from app.models.market_data import CompanyProfile
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_fundamentals_data():
    """Verify fundamental data was stored correctly"""
    print("\n" + "=" * 80)
    print("  FUNDAMENTAL DATA VERIFICATION")
    print("=" * 80)
    print()

    async with AsyncSessionLocal() as db:
        # Count income statements
        income_count = await db.execute(select(func.count(IncomeStatement.id)))
        income_total = income_count.scalar()

        # Count balance sheets
        balance_count = await db.execute(select(func.count(BalanceSheet.id)))
        balance_total = balance_count.scalar()

        # Count cash flows
        cash_count = await db.execute(select(func.count(CashFlow.id)))
        cash_total = cash_count.scalar()

        # Count unique symbols in each table
        income_symbols_query = await db.execute(
            select(func.count(distinct(IncomeStatement.symbol)))
        )
        income_symbols = income_symbols_query.scalar()

        balance_symbols_query = await db.execute(
            select(func.count(distinct(BalanceSheet.symbol)))
        )
        balance_symbols = balance_symbols_query.scalar()

        cash_symbols_query = await db.execute(
            select(func.count(distinct(CashFlow.symbol)))
        )
        cash_symbols = cash_symbols_query.scalar()

        # Count company profiles with fundamentals_last_fetched
        profiles_count = await db.execute(
            select(func.count(CompanyProfile.symbol)).where(
                CompanyProfile.fundamentals_last_fetched.isnot(None)
            )
        )
        profiles_total = profiles_count.scalar()

        print(f"📋 Fundamental Data Summary:")
        print(f"   Income statements: {income_total} records ({income_symbols} unique symbols)")
        print(f"   Balance sheets: {balance_total} records ({balance_symbols} unique symbols)")
        print(f"   Cash flows: {cash_total} records ({cash_symbols} unique symbols)")
        print(f"   Company profiles with fundamentals: {profiles_total} symbols")
        print()

        # Show sample symbols with data
        if income_total > 0:
            sample_query = select(IncomeStatement.symbol).distinct().limit(10)
            sample_result = await db.execute(sample_query)
            symbols = [row[0] for row in sample_result.fetchall()]
            print(f"   Sample symbols with fundamental data:")
            print(f"   {', '.join(symbols)}")
            print()

            # Show detailed data for one symbol
            if symbols:
                test_symbol = symbols[0]
                print(f"   Detailed data for {test_symbol}:")

                # Income statements
                income_query = select(IncomeStatement).where(
                    IncomeStatement.symbol == test_symbol
                ).order_by(IncomeStatement.fiscal_year.desc(), IncomeStatement.frequency.desc()).limit(5)
                income_result = await db.execute(income_query)
                income_records = income_result.scalars().all()

                if income_records:
                    print(f"\n   Income Statements ({len(income_records)} records):")
                    for record in income_records:
                        print(f"      {record.fiscal_year} {record.frequency}: "
                              f"Revenue ${record.total_revenue:,.0f}" if record.total_revenue else "N/A")

                # Balance sheets
                balance_query = select(BalanceSheet).where(
                    BalanceSheet.symbol == test_symbol
                ).order_by(BalanceSheet.fiscal_year.desc(), BalanceSheet.frequency.desc()).limit(5)
                balance_result = await db.execute(balance_query)
                balance_records = balance_result.scalars().all()

                if balance_records:
                    print(f"\n   Balance Sheets ({len(balance_records)} records):")
                    for record in balance_records:
                        print(f"      {record.fiscal_year} {record.frequency}: "
                              f"Total Assets ${record.total_assets:,.0f}" if record.total_assets else "N/A")

                # Cash flows
                cash_query = select(CashFlow).where(
                    CashFlow.symbol == test_symbol
                ).order_by(CashFlow.fiscal_year.desc(), CashFlow.frequency.desc()).limit(5)
                cash_result = await db.execute(cash_query)
                cash_records = cash_result.scalars().all()

                if cash_records:
                    print(f"\n   Cash Flows ({len(cash_records)} records):")
                    for record in cash_records:
                        print(f"      {record.fiscal_year} {record.frequency}: "
                              f"Operating CF ${record.operating_cash_flow:,.0f}" if record.operating_cash_flow else "N/A")
                print()

        # Show symbols that were evaluated but skipped
        all_profiles_query = select(CompanyProfile.symbol, CompanyProfile.fundamentals_last_fetched)
        all_profiles_result = await db.execute(all_profiles_query)
        all_profiles = all_profiles_result.fetchall()

        with_fundamentals = [p[0] for p in all_profiles if p[1] is not None]
        without_fundamentals = [p[0] for p in all_profiles if p[1] is None]

        print(f"   Symbols WITH fundamental data: {len(with_fundamentals)}")
        print(f"   Symbols WITHOUT fundamental data: {len(without_fundamentals)}")

        if without_fundamentals:
            print(f"   Symbols without fundamentals (first 10): {', '.join(without_fundamentals[:10])}")
        print()

        print("=" * 80)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 80)
        print()


if __name__ == "__main__":
    print("\n" + "📊" * 40)
    print()
    asyncio.run(verify_fundamentals_data())
    print("📊" * 40)
    print()
