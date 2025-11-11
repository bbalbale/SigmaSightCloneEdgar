#!/usr/bin/env python3
"""
Diagnostic script to investigate inverse stress test behavior on HNW portfolio.

This script checks:
1. Portfolio factor exposures (Market Beta and exposure_dollar)
2. Position-level factor contributions
3. Position types and market values (sign verification)
4. Regression quality metrics

Run: uv run python scripts/analysis/diagnose_stress_test_issue.py
"""

import asyncio
from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position, PositionType
from app.models.market_data import FactorExposure, FactorDefinition, PositionFactorExposure


async def diagnose_stress_test_issue():
    """Main diagnostic function"""

    async with AsyncSessionLocal() as db:
        print("\n" + "="*80)
        print("STRESS TEST INVERSE BEHAVIOR DIAGNOSTIC")
        print("="*80 + "\n")

        # Step 1: Find HNW portfolio
        print("Step 1: Locating HNW Portfolio...")
        print("-" * 40)

        stmt = select(Portfolio).where(Portfolio.name.ilike('%high net worth%'))
        result = await db.execute(stmt)
        hnw_portfolio = result.scalar_one_or_none()

        if not hnw_portfolio:
            print("[X] HNW Portfolio not found!")
            return

        print(f"[OK] Found: {hnw_portfolio.name}")
        print(f"   Portfolio ID: {hnw_portfolio.id}")
        print(f"   Equity Balance: ${float(hnw_portfolio.equity_balance):,.2f}")
        print()

        # Step 2: Check portfolio-level factor exposures
        print("Step 2: Portfolio-Level Factor Exposures")
        print("-" * 40)

        # Get latest factor exposures
        factor_stmt = (
            select(FactorExposure, FactorDefinition)
            .join(FactorDefinition, FactorExposure.factor_id == FactorDefinition.id)
            .where(FactorExposure.portfolio_id == hnw_portfolio.id)
            .order_by(FactorExposure.calculation_date.desc())
        )

        factor_result = await db.execute(factor_stmt)
        factor_rows = factor_result.all()

        if not factor_rows:
            print("[X] No factor exposures found!")
            return

        # Get most recent calculation date
        latest_date = max(row[0].calculation_date for row in factor_rows)
        print(f"Latest calculation date: {latest_date}\n")

        # Filter to latest date and display
        latest_factors = [(exp, factor_def) for exp, factor_def in factor_rows
                         if exp.calculation_date == latest_date]

        market_beta = None
        market_exposure_dollar = None

        print("Factor Exposures:")
        for exposure, factor_def in latest_factors:
            beta_value = float(exposure.exposure_value)
            dollar_value = float(exposure.exposure_dollar) if exposure.exposure_dollar else 0.0

            # Highlight Market Beta
            if factor_def.name == "Market Beta":
                market_beta = beta_value
                market_exposure_dollar = dollar_value
                marker = " [!] MARKET FACTOR" if beta_value < 0 else " [OK] MARKET FACTOR"
            else:
                marker = ""

            print(f"   {factor_def.name:20s}: Beta={beta_value:+7.4f}  ${dollar_value:+15,.0f}{marker}")

        print()

        # Diagnose Market Beta
        if market_beta is not None:
            print("Market Beta Analysis:")
            print(f"   Beta Value: {market_beta:+.4f}")
            print(f"   Dollar Exposure: ${market_exposure_dollar:+,.0f}")

            if market_beta < 0:
                print("   [!] WARNING: Negative Market Beta for long-biased portfolio!")
                print("   This would cause inverse stress test behavior.")
                print("   A +5% market shock would result in negative P&L.")
            else:
                print("   [OK] Market Beta is positive (expected for long portfolio)")

            if market_exposure_dollar < 0:
                print("   [!] WARNING: Negative Market Dollar Exposure!")
                print("   This suggests net SHORT market exposure.")
            else:
                print("   [OK] Market Dollar Exposure is positive")

            # Calculate expected stress impact
            stress_shock = 0.05  # +5% market up scenario
            expected_pnl = market_exposure_dollar * stress_shock
            print(f"\n   Expected P&L for +5% market shock: ${expected_pnl:+,.0f}")

            if expected_pnl < 0:
                print("   [!] PROBLEM CONFIRMED: Portfolio loses money when market goes up!")
            else:
                print("   [OK] Portfolio should gain money when market goes up (correct)")

        print("\n")

        # Step 3: Check position-level contributions
        print("Step 3: Position-Level Factor Contributions")
        print("-" * 40)

        # Get all active positions
        pos_stmt = select(Position).where(
            and_(
                Position.portfolio_id == hnw_portfolio.id,
                Position.exit_date.is_(None)
            )
        )
        pos_result = await db.execute(pos_stmt)
        positions = pos_result.scalars().all()

        print(f"Active positions: {len(positions)}\n")

        # Get position-level Market Beta exposures
        pos_factor_stmt = (
            select(PositionFactorExposure, Position, FactorDefinition)
            .join(Position, PositionFactorExposure.position_id == Position.id)
            .join(FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id)
            .where(
                and_(
                    Position.portfolio_id == hnw_portfolio.id,
                    Position.exit_date.is_(None),
                    FactorDefinition.name == "Market Beta",
                    PositionFactorExposure.calculation_date == latest_date
                )
            )
        )

        pos_factor_result = await db.execute(pos_factor_stmt)
        pos_factor_rows = pos_factor_result.all()

        print(f"Positions with Market Beta: {len(pos_factor_rows)}\n")

        if pos_factor_rows:
            print("Position Contributions to Market Exposure:")
            print(f"{'Symbol':8s} {'Type':6s} {'Qty':>10s} {'Price':>10s} {'MktVal':>15s} {'Beta':>7s} {'Contribution':>15s}")
            print("-" * 95)

            total_contribution = 0.0
            negative_contributions = []

            for pos_exposure, position, factor_def in pos_factor_rows:
                position_beta = float(pos_exposure.exposure_value)
                market_value = float(position.market_value) if position.market_value else 0.0
                quantity = float(position.quantity)
                price = float(position.last_price) if position.last_price else 0.0
                pos_type = position.position_type.name if position.position_type else "UNKNOWN"

                # Calculate contribution (signed market value × beta)
                # Note: For SHORT positions, market_value should already be negative
                contribution = market_value * position_beta
                total_contribution += contribution

                if contribution < 0 and pos_type in ['LONG', 'LC', 'LP']:
                    negative_contributions.append((position.symbol, pos_type, contribution, position_beta, market_value))

                marker = " [!]" if contribution < 0 and pos_type in ['LONG', 'LC', 'LP'] else ""

                print(f"{position.symbol:8s} {pos_type:6s} {quantity:>10.2f} ${price:>9.2f} ${market_value:>14,.0f} {position_beta:>6.3f} ${contribution:>14,.0f}{marker}")

            print("-" * 95)
            print(f"{'Total Market Exposure':50s} ${total_contribution:>14,.0f}")

            if abs(total_contribution - market_exposure_dollar) > 1.0:
                print(f"\n[!] WARNING: Position contributions (${total_contribution:,.0f}) don't match ")
                print(f"   portfolio exposure_dollar (${market_exposure_dollar:,.0f})")
                print(f"   Difference: ${(total_contribution - market_exposure_dollar):,.0f}")

            if negative_contributions:
                print(f"\n[!] Found {len(negative_contributions)} LONG positions with negative market contribution:")
                for symbol, pos_type, contrib, beta, mv in negative_contributions:
                    print(f"   {symbol} ({pos_type}): contrib=${contrib:,.0f}, Beta={beta:.3f}, MV=${mv:,.0f}")
                    if mv < 0:
                        print(f"      → Problem: Market value is negative for LONG position!")
                    if beta < 0:
                        print(f"      → Problem: Market Beta is negative!")

        print("\n")

        # Step 4: Check position types and signs
        print("Step 4: Position Type & Sign Verification")
        print("-" * 40)

        position_type_counts = {}
        sign_issues = []

        for position in positions:
            pos_type = position.position_type.name if position.position_type else "UNKNOWN"
            position_type_counts[pos_type] = position_type_counts.get(pos_type, 0) + 1

            market_value = float(position.market_value) if position.market_value else 0.0
            quantity = float(position.quantity)

            # Check sign consistency
            is_short_type = pos_type in ['SHORT', 'SC', 'SP']
            is_negative_value = market_value < 0

            if is_short_type and not is_negative_value:
                sign_issues.append((position.symbol, pos_type, "SHORT type but positive market_value", market_value))
            elif not is_short_type and is_negative_value:
                sign_issues.append((position.symbol, pos_type, "LONG type but negative market_value", market_value))

        print("Position Type Distribution:")
        for pos_type, count in sorted(position_type_counts.items()):
            print(f"   {pos_type:10s}: {count:3d} positions")

        if sign_issues:
            print(f"\n[!] Found {len(sign_issues)} positions with sign inconsistencies:")
            for symbol, pos_type, issue, mv in sign_issues:
                print(f"   {symbol} ({pos_type}): {issue}, MV=${mv:,.0f}")
        else:
            print("\n[OK] All position signs are consistent with their types")

        print("\n")

        # Step 5: Summary and Recommendations
        print("="*80)
        print("DIAGNOSTIC SUMMARY")
        print("="*80)

        issues_found = []

        if market_beta is not None and market_beta == 0.0:
            issues_found.append("[X] Market Beta is ZERO (portfolio has no traditional market exposure calculated)")

        if market_beta and market_beta < 0:
            issues_found.append("[X] Market Beta is NEGATIVE (should be positive for long portfolio)")

        if market_exposure_dollar is not None and market_exposure_dollar == 0.0:
            issues_found.append("[X] Market Dollar Exposure is ZERO (no market sensitivity)")

        if market_exposure_dollar and market_exposure_dollar < 0:
            issues_found.append("[X] Market Dollar Exposure is NEGATIVE (suggests net short)")

        # Only check negative_contributions if it was populated
        if 'negative_contributions' in locals() and negative_contributions:
            issues_found.append(f"[X] {len(negative_contributions)} LONG positions have negative market contribution")

        if sign_issues:
            issues_found.append(f"[X] {len(sign_issues)} positions have sign inconsistencies")

        if issues_found:
            print("\n[!] ISSUES FOUND:\n")
            for i, issue in enumerate(issues_found, 1):
                print(f"{i}. {issue}")

            print("\n[FIX] RECOMMENDED FIXES:\n")

            if market_beta and market_beta < 0:
                print("1. Re-run factor calculation with fresh data")
                print("   - Check for data quality issues in factor returns")
                print("   - Review multicollinearity diagnostics (VIF scores)")
                print("   - Consider using Ridge Regression to stabilize market betas")

            if sign_issues:
                print("2. Fix position sign inconsistencies:")
                print("   - Review position data entry/import process")
                print("   - Correct position_type or market_value signs in database")

            if negative_contributions and not sign_issues:
                print("3. Investigate negative market beta values:")
                print("   - Check if individual stock market betas are truly negative")
                print("   - Review regression diagnostics for affected positions")
                print("   - Consider re-calculating with longer history window")

        else:
            print("\n[OK] NO OBVIOUS ISSUES FOUND")
            print("\nThe factor exposures look correct. Possible next steps:")
            print("1. Check stress test calculation logic directly")
            print("2. Review stress scenario configuration")
            print("3. Verify the specific stress test scenario being used")

        print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(diagnose_stress_test_issue())
