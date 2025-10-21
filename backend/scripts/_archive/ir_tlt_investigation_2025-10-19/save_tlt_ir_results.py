"""
Save TLT (Bond ETF) IR Beta Results to JSON
Captures TLT-based approach for comparison with DGS10 baseline
"""
import asyncio
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.calculations.interest_rate_beta_tlt import calculate_portfolio_ir_beta_tlt, calculate_position_ir_beta_tlt
from app.core.logging import get_logger

logger = get_logger(__name__)


async def save_tlt_results():
    """Run TLT IR beta analysis and save detailed results"""

    results = {
        "calculation_date": str(date.today()),
        "method": "TLT",
        "description": "iShares 20+ Year Treasury Bond ETF Returns (percentage)",
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

        logger.info(f"Found {len(portfolios)} demo portfolios for TLT analysis")

        # Calculate IR beta for each portfolio
        for portfolio in portfolios:
            logger.info(f"\nAnalyzing portfolio: {portfolio.name}")

            # Calculate portfolio-level IR beta using TLT
            portfolio_result = await calculate_portfolio_ir_beta_tlt(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=date.today(),
                window_days=90
            )

            if not portfolio_result['success']:
                logger.warning(f"Failed to calculate portfolio TLT beta: {portfolio_result.get('error')}")
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
                pos_result = await calculate_position_ir_beta_tlt(
                    db=db,
                    position_id=position.id,
                    calculation_date=date.today(),
                    window_days=90
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
            # For TLT: 50bp rate increase ≈ 2-3% TLT decline (duration ~17)
            # Using conservative 2.5% TLT move per 50bp rate change
            portfolio_equity = float(portfolio.equity_balance)
            portfolio_ir_beta = portfolio_result['portfolio_ir_beta']

            tlt_move_50bp = -0.025  # 50bp rate increase → 2.5% TLT decline
            tlt_move_100bp = -0.050  # 100bp rate increase → 5% TLT decline

            stress_50bp = portfolio_equity * portfolio_ir_beta * tlt_move_50bp
            stress_100bp = portfolio_equity * portfolio_ir_beta * tlt_move_100bp

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
                    "100bp_shock_formatted": f"${stress_100bp:,.2f}",
                    "note": "50bp ≈ 2.5% TLT move, 100bp ≈ 5% TLT move (duration ~17)"
                }
            }

            logger.info(f"Portfolio IR Beta (TLT): {portfolio_ir_beta:.6f}")
            logger.info(f"50bp stress (via TLT): ${stress_50bp:,.2f}")
            logger.info(f"100bp stress (via TLT): ${stress_100bp:,.2f}")

    # Save to JSON file
    output_path = Path(__file__).parent.parent / "analysis" / "tlt_ir_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nTLT results saved to: {output_path}")
    logger.info(f"Analyzed {len(results['portfolios'])} portfolios")

    # Print summary
    print("\n" + "=" * 80)
    print("TLT (Bond ETF) Analysis Complete")
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
    asyncio.run(save_tlt_results())
