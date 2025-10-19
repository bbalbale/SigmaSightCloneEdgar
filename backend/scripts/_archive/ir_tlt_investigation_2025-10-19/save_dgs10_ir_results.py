"""
Save DGS10 (Fed Interest Rate) IR Beta Results to JSON
Captures current baseline for comparison with TLT approach
"""
import asyncio
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.calculations.interest_rate_beta import calculate_portfolio_ir_beta, calculate_position_ir_beta
from app.core.logging import get_logger

logger = get_logger(__name__)


async def save_dgs10_results():
    """Run DGS10 IR beta analysis and save detailed results"""

    results = {
        "calculation_date": str(date.today()),
        "method": "DGS10",
        "description": "Fed 10-Year Treasury Yield Changes (basis points)",
        "portfolios": {}
    }

    async with get_async_session() as db:
        # Get demo users
        demo_emails = [
            "demo_individual@sigmasight.com",
            "demo_hnw@sigmasight.com",
            "demo_hedgefundstyle@sigmasight.com"
        ]

        stmt = select(User).where(User.email.in_(demo_emails))
        result = await db.execute(stmt)
        demo_users = result.scalars().all()

        user_ids = [u.id for u in demo_users]

        # Get portfolios
        stmt = select(Portfolio).where(
            Portfolio.user_id.in_(user_ids),
            Portfolio.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        portfolios = result.scalars().all()

        logger.info(f"Found {len(portfolios)} demo portfolios for DGS10 analysis")

        # Calculate IR beta for each portfolio
        for portfolio in portfolios:
            logger.info(f"\nAnalyzing portfolio: {portfolio.name}")

            # Calculate portfolio-level IR beta
            portfolio_result = await calculate_portfolio_ir_beta(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=date.today(),
                window_days=90,
                treasury_symbol='DGS10',
                persist=False  # Don't persist during comparison testing
            )

            if not portfolio_result['success']:
                logger.warning(f"Failed to calculate portfolio IR beta: {portfolio_result.get('error')}")
                continue

            # Get position details
            from app.models.positions import Position
            positions_stmt = select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.exit_date.is_(None)
            )
            positions_result = await db.execute(positions_stmt)
            positions = positions_result.scalars().all()

            position_details = []
            for position in positions:
                pos_result = await calculate_position_ir_beta(
                    db=db,
                    position_id=position.id,
                    calculation_date=date.today(),
                    window_days=90,
                    treasury_symbol='DGS10'
                )

                if pos_result['success']:
                    position_details.append({
                        "symbol": position.symbol,
                        "ir_beta": round(pos_result['ir_beta'], 6),
                        "r_squared": round(pos_result['r_squared'], 4),
                        "p_value": round(pos_result['p_value'], 4),
                        "is_significant": pos_result['is_significant'],
                        "sensitivity_level": pos_result['sensitivity_level'],
                        "market_value": float(position.market_value) if position.market_value else 0,
                        "observations": pos_result['observations']
                    })

            # Calculate stress test preview
            portfolio_equity = float(portfolio.equity_balance)
            portfolio_ir_beta = portfolio_result['portfolio_ir_beta']

            stress_50bp = portfolio_equity * portfolio_ir_beta * 0.005  # 50bp = 0.005
            stress_100bp = portfolio_equity * portfolio_ir_beta * 0.01  # 100bp = 0.01

            # Save portfolio results
            results["portfolios"][str(portfolio.id)] = {
                "name": portfolio.name,
                "equity_balance": portfolio_equity,
                "portfolio_ir_beta": round(portfolio_ir_beta, 6),
                "weighted_r_squared": round(portfolio_result['r_squared'], 4),
                "positions_count": len(position_details),
                "total_positions": len(positions),
                "sensitivity_level": portfolio_result['sensitivity_level'],
                "observations": portfolio_result['observations'],
                "positions": sorted(position_details, key=lambda x: abs(x['market_value']), reverse=True),
                "stress_test_preview": {
                    "50bp_shock_pnl": round(stress_50bp, 2),
                    "100bp_shock_pnl": round(stress_100bp, 2),
                    "50bp_shock_formatted": f"${stress_50bp:,.2f}",
                    "100bp_shock_formatted": f"${stress_100bp:,.2f}"
                }
            }

            logger.info(f"Portfolio IR Beta (DGS10): {portfolio_ir_beta:.6f}")
            logger.info(f"50bp stress: ${stress_50bp:,.2f}")
            logger.info(f"100bp stress: ${stress_100bp:,.2f}")

    # Save to JSON file
    output_path = Path(__file__).parent.parent / "analysis" / "dgs10_ir_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nDGS10 results saved to: {output_path}")
    logger.info(f"Analyzed {len(results['portfolios'])} portfolios")

    # Print summary
    print("\n" + "=" * 80)
    print("DGS10 (Fed Interest Rate) Analysis Complete")
    print("=" * 80)
    for portfolio_id, portfolio_data in results['portfolios'].items():
        print(f"\n{portfolio_data['name']}:")
        print(f"  Portfolio IR Beta: {portfolio_data['portfolio_ir_beta']:.6f}")
        print(f"  R-Squared: {portfolio_data['weighted_r_squared']:.4f}")
        print(f"  50bp Shock P&L: {portfolio_data['stress_test_preview']['50bp_shock_formatted']}")
        print(f"  Positions Analyzed: {portfolio_data['positions_count']}/{portfolio_data['total_positions']}")

    print(f"\nResults saved to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(save_dgs10_results())
