import asyncio
from uuid import UUID
from datetime import date
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models.market_data import FactorExposure, FactorDefinition, PositionFactorExposure
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot

async def check_quality_spread():
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')

    async with AsyncSessionLocal() as db:
        print('=' * 80)
        print('QUALITY SPREAD DIAGNOSTIC')
        print('=' * 80)

        # 1. Check Quality Spread exposure
        stmt = select(FactorExposure, FactorDefinition).join(
            FactorDefinition, FactorExposure.factor_id == FactorDefinition.id
        ).where(
            and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.calculation_date == date(2025, 10, 20),
                FactorDefinition.name == 'Quality Spread'
            )
        )

        result = await db.execute(stmt)
        row = result.first()

        if row:
            exp, fdef = row
            print(f'\nQuality Spread Factor Exposure:')
            print(f'  Beta (exposure_value): {float(exp.exposure_value):.4f}')
            print(f'  Dollar Exposure: ${float(exp.exposure_dollar):,.0f}')
            print(f'  ETF Proxy: {fdef.etf_proxy}')
            print(f'  Calculation Date: {exp.calculation_date}')

        # 2. Check portfolio composition
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )

        result = await db.execute(stmt)
        positions = result.scalars().all()

        print(f'\n\nPortfolio Composition:')
        print(f'  Total Positions: {len(positions)}')

        # Calculate total exposures
        total_long = sum(float(p.market_value) for p in positions if p.market_value and p.market_value > 0)
        total_short = sum(float(p.market_value) for p in positions if p.market_value and p.market_value < 0)
        net_exposure = total_long + total_short

        print(f'  Long Exposure: ${total_long:,.0f}')
        print(f'  Short Exposure: ${total_short:,.0f}')
        print(f'  Net Exposure: ${net_exposure:,.0f}')

        # 3. Check individual position exposures to Quality Spread
        stmt = select(PositionFactorExposure, Position, FactorDefinition).join(
            Position, PositionFactorExposure.position_id == Position.id
        ).join(
            FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id
        ).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None),
                FactorDefinition.name == 'Quality Spread',
                PositionFactorExposure.calculation_date == date(2025, 10, 20)
            )
        ).order_by(PositionFactorExposure.exposure_value)

        result = await db.execute(stmt)
        rows = result.all()

        if rows:
            print(f'\n\nPosition-Level Quality Spread Exposures:')
            print(f'  Found {len(rows)} positions with Quality Spread betas')
            print(f'\n  Top 10 Positions (by beta magnitude):')
            print(f'  {"Symbol":10s} | {"Type":6s} | {"Market Value":>15s} | {"Beta":>8s} | {"Contribution":>15s}')
            print('  ' + '-' * 80)

            sorted_rows = sorted(rows, key=lambda x: abs(float(x[0].exposure_value)), reverse=True)[:10]
            total_contribution = 0

            for pfe, pos, fdef in sorted_rows:
                beta = float(pfe.exposure_value)
                market_value = float(pos.market_value) if pos.market_value else 0
                contribution = market_value * beta
                total_contribution += contribution

                print(f'  {pos.symbol:10s} | {pos.position_type.value:6s} | ${market_value:>14,.0f} | {beta:>8.4f} | ${contribution:>14,.0f}')

            print('  ' + '-' * 80)
            print(f'  Top 10 Total Contribution: ${total_contribution:,.0f}')
        else:
            print(f'\n\nNo position-level Quality Spread exposures found!')
            print('  This means Quality Spread is calculated at portfolio level only,')
            print('  not from individual position regressions.')

        # 4. Check Quality and Market Beta for comparison
        stmt = select(FactorExposure, FactorDefinition).join(
            FactorDefinition, FactorExposure.factor_id == FactorDefinition.id
        ).where(
            and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.calculation_date == date(2025, 10, 20),
                FactorDefinition.name.in_(['Quality', 'Market Beta', 'Quality Spread'])
            )
        ).order_by(FactorDefinition.name)

        result = await db.execute(stmt)
        rows = result.all()

        print(f'\n\nComparison of Related Factors:')
        print(f'  {"Factor":20s} | {"Beta":>10s} | {"Dollar Exp":>15s}')
        print('  ' + '-' * 50)

        quality_beta = None
        market_beta = None
        quality_spread_beta = None
        quality_dollar = None
        market_dollar = None
        quality_spread_dollar = None

        for exp, fdef in rows:
            beta = float(exp.exposure_value)
            dollar = float(exp.exposure_dollar) if exp.exposure_dollar else 0
            print(f'  {fdef.name:20s} | {beta:>10.4f} | ${dollar:>14,.0f}')

            if fdef.name == 'Quality':
                quality_beta = beta
                quality_dollar = dollar
            elif fdef.name == 'Market Beta':
                market_beta = beta
                market_dollar = dollar
            elif fdef.name == 'Quality Spread':
                quality_spread_beta = beta
                quality_spread_dollar = dollar

        # 5. Analyze the math
        print(f'\n\nQuality Spread Mathematical Analysis:')
        print(f'  Definition: QUAL - SPY (Long Quality, Short Market)')
        print('-' * 80)

        # Get portfolio value
        stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio_id
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)

        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if snapshot:
            equity = float(snapshot.equity_balance)
            print(f'\nPortfolio Equity: ${equity:,.0f}')
            print(f'\nTheoretical Calculation (if spread = quality - market):')

            if quality_beta is not None and market_beta is not None:
                theoretical_spread_beta = quality_beta - market_beta
                theoretical_spread_dollar = quality_dollar - market_dollar

                print(f'  Quality Beta - Market Beta = {quality_beta:.4f} - {market_beta:.4f} = {theoretical_spread_beta:.4f}')
                print(f'  Quality $ - Market $ = ${quality_dollar:,.0f} - ${market_dollar:,.0f} = ${theoretical_spread_dollar:,.0f}')
                print(f'\nActual Stored Values:')
                print(f'  Quality Spread Beta: {quality_spread_beta:.4f}')
                print(f'  Quality Spread Dollar: ${quality_spread_dollar:,.0f}')
                print(f'\nDifferences:')
                print(f'  Beta Difference: {abs(quality_spread_beta - theoretical_spread_beta):.4f}')
                print(f'  Dollar Difference: ${abs(quality_spread_dollar - theoretical_spread_dollar):,.0f}')

                if abs(quality_spread_beta - theoretical_spread_beta) > 0.01:
                    print(f'\n  [FINDING] Spread beta does NOT match simple subtraction!')
                    print(f'            Quality Spread is calculated via REGRESSION on (QUAL - SPY) returns,')
                    print(f'            not simple arithmetic subtraction of Quality and Market betas.')
                    print(f'\n            This is actually the CORRECT approach for spread factors.')
                    print(f'            The regression captures the actual spread behavior, which may differ')
                    print(f'            from theoretical subtraction due to:')
                    print(f'              - Non-linear relationships')
                    print(f'              - Time-varying correlations')
                    print(f'              - Specific portfolio composition effects')
                else:
                    print(f'\n  [OK] Spread beta matches theoretical value (simple subtraction)')

                # Check if the large negative value makes sense
                print(f'\n\nInterpreting the Quality Spread Beta ({quality_spread_beta:.4f}):')
                if quality_spread_beta < -0.5:
                    print(f'  [WARNING] Extremely negative beta suggests portfolio has:')
                    print(f'    - Strong INVERSE relationship to Quality Spread')
                    print(f'    - When QUAL outperforms SPY, portfolio UNDERPERFORMS')
                    print(f'    - When QUAL underperforms SPY, portfolio OUTPERFORMS')
                    print(f'\n  Possible explanations:')
                    print(f'    1. Portfolio is SHORT quality stocks relative to market')
                    print(f'    2. Portfolio holds low-quality/speculative stocks')
                    print(f'    3. Regression error or data quality issue')
                    print(f'    4. Unusual portfolio composition during measurement period')

                # Calculate what this means for a quality spread scenario
                print(f'\n\nScenario Impact Analysis:')
                print(f'  If Quality Spread widens by 10% (QUAL outperforms SPY by 10%):')
                shock = 0.10
                impact = quality_spread_dollar * shock
                print(f'    Portfolio P&L: ${impact:,.0f}')
                if impact < 0:
                    print(f'    Portfolio LOSES money when quality outperforms! [UNUSUAL]')

asyncio.run(check_quality_spread())
