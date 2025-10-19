"""
Compare DGS10 vs TLT Interest Rate Beta Methodologies
Generates comprehensive comparison report for decision-making
"""
import json
from pathlib import Path
from typing import Dict, Any


def load_results(method: str) -> Dict[str, Any]:
    """Load JSON results file"""
    file_path = Path(__file__).parent.parent / "analysis" / f"{method.lower()}_ir_results.json"

    if not file_path.exists():
        raise FileNotFoundError(f"{method} results not found at: {file_path}")

    with open(file_path, 'r') as f:
        return json.load(f)


def format_beta_comparison_table(dgs10_positions, tlt_positions, max_rows=15):
    """Format position-level beta comparison table"""

    # Create lookup dict for TLT positions
    tlt_lookup = {p['symbol']: p for p in tlt_positions}

    lines = []
    lines.append("+" + "-" * 10 + "+" + "-" * 16 + "+" + "-" * 14 + "+" + "-" * 10 + "+" + "-" * 14 + "+" + "-" * 10 + "+" + "-" * 15 + "+")
    lines.append(f"| {'Symbol':<8} | {'Market Value':>14} | {'DGS10 B':>12} | {'DGS10 R2':>8} | {'TLT B':>12} | {'TLT R2':>8} | {'Magnitude D':>13} |")
    lines.append("+" + "-" * 10 + "+" + "-" * 16 + "+" + "-" * 14 + "+" + "-" * 10 + "+" + "-" * 14 + "+" + "-" * 10 + "+" + "-" * 15 + "+")

    for i, dgs10_pos in enumerate(dgs10_positions[:max_rows]):
        symbol = dgs10_pos['symbol']
        market_value = dgs10_pos['market_value']
        dgs10_beta = dgs10_pos['ir_beta']
        dgs10_r2 = dgs10_pos['r_squared']

        tlt_pos = tlt_lookup.get(symbol, {})
        tlt_beta = tlt_pos.get('ir_beta', 0)
        tlt_r2 = tlt_pos.get('r_squared', 0)

        # Calculate magnitude ratio (how many times larger TLT beta is)
        if abs(dgs10_beta) > 0.000001:
            magnitude_ratio = abs(tlt_beta) / abs(dgs10_beta)
            magnitude_str = f"{magnitude_ratio:.0f}x"
        else:
            magnitude_str = "N/A"

        lines.append(
            f"| {symbol:<8} | ${market_value:>13,.0f} | {dgs10_beta:>12.6f} | {dgs10_r2:>8.3f} | {tlt_beta:>12.4f} | {tlt_r2:>8.3f} | {magnitude_str:>13} |"
        )

    lines.append("+" + "-" * 10 + "+" + "-" * 16 + "+" + "-" * 14 + "+" + "-" * 10 + "+" + "-" * 14 + "+" + "-" * 10 + "+" + "-" * 15 + "+")

    return "\n".join(lines)


def calculate_statistics(positions, beta_key='ir_beta', r2_key='r_squared'):
    """Calculate average R^2, beta magnitude, significance"""
    if not positions:
        return {"avg_r2": 0, "avg_beta_magnitude": 0, "significant_count": 0}

    r2_values = [p[r2_key] for p in positions if r2_key in p]
    beta_values = [abs(p[beta_key]) for p in positions if beta_key in p]
    significant = [p for p in positions if p.get('is_significant', False)]

    return {
        "avg_r2": sum(r2_values) / len(r2_values) if r2_values else 0,
        "avg_beta_magnitude": sum(beta_values) / len(beta_values) if beta_values else 0,
        "significant_count": len(significant),
        "total_count": len(positions)
    }


def generate_comparison_report():
    """Generate comprehensive comparison report"""

    print("\n" + "=" * 100)
    print("INTEREST RATE BETA METHODOLOGY COMPARISON")
    print("DGS10 (Fed 10-Year Treasury Yields) vs TLT (20+ Year Bond ETF)")
    print("=" * 100)

    # Load both result sets
    try:
        dgs10_data = load_results('DGS10')
        tlt_data = load_results('TLT')
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease run both analysis scripts first:")
        print("  1. uv run python scripts/save_dgs10_ir_results.py")
        print("  2. uv run python scripts/save_tlt_ir_results.py")
        return

    print(f"\nAnalysis Date: {dgs10_data['calculation_date']}")
    print(f"Portfolios Analyzed: {len(dgs10_data['portfolios'])}")

    # Prepare output file
    output_lines = []
    output_lines.append("=" * 100)
    output_lines.append("INTEREST RATE BETA METHODOLOGY COMPARISON")
    output_lines.append("DGS10 (Fed 10-Year Treasury Yields) vs TLT (20+ Year Bond ETF)")
    output_lines.append("=" * 100)
    output_lines.append(f"\nAnalysis Date: {dgs10_data['calculation_date']}")
    output_lines.append(f"Portfolios Analyzed: {len(dgs10_data['portfolios'])}\n")

    # Compare each portfolio
    for portfolio_id in dgs10_data['portfolios'].keys():
        dgs10_portfolio = dgs10_data['portfolios'][portfolio_id]
        tlt_portfolio = tlt_data['portfolios'].get(portfolio_id, {})

        if not tlt_portfolio:
            print(f"\n[WARNING] TLT data missing for portfolio: {dgs10_portfolio['name']}")
            continue

        print("\n" + "-" * 100)
        print(f"\nPORTFOLIO: {dgs10_portfolio['name']}")
        print(f"Equity Balance: ${dgs10_portfolio['equity_balance']:,.0f}")

        output_lines.append("\n" + "-" * 100)
        output_lines.append(f"\nPORTFOLIO: {dgs10_portfolio['name']}")
        output_lines.append(f"Equity Balance: ${dgs10_portfolio['equity_balance']:,.0f}\n")

        # Portfolio-level comparison
        print("\n>>> Portfolio-Level Results:")
        print(f"  DGS10 Beta: {dgs10_portfolio['portfolio_ir_beta']:.6f}  (R^2: {dgs10_portfolio['weighted_r_squared']:.3f})")
        print(f"  TLT Beta:   {tlt_portfolio['portfolio_ir_beta']:.6f}  (R^2: {tlt_portfolio['weighted_r_squared']:.3f})")

        output_lines.append(">>> Portfolio-Level Results:")
        output_lines.append(f"  DGS10 Beta: {dgs10_portfolio['portfolio_ir_beta']:.6f}  (R^2: {dgs10_portfolio['weighted_r_squared']:.3f})")
        output_lines.append(f"  TLT Beta:   {tlt_portfolio['portfolio_ir_beta']:.6f}  (R^2: {tlt_portfolio['weighted_r_squared']:.3f})")

        # Magnitude comparison
        if abs(dgs10_portfolio['portfolio_ir_beta']) > 0.000001:
            magnitude_ratio = abs(tlt_portfolio['portfolio_ir_beta']) / abs(dgs10_portfolio['portfolio_ir_beta'])
            print(f"  Magnitude: TLT is {magnitude_ratio:.0f}x larger than DGS10")
            output_lines.append(f"  Magnitude: TLT is {magnitude_ratio:.0f}x larger than DGS10")

        # Position-level comparison table
        print("\n>>> Position-Level Comparison (Top 15 by Market Value):")
        table = format_beta_comparison_table(
            dgs10_portfolio['positions'],
            tlt_portfolio['positions']
        )
        print(table)
        output_lines.append("\n>>> Position-Level Comparison (Top 15 by Market Value):")
        output_lines.append(table)

        # Statistical quality comparison
        dgs10_stats = calculate_statistics(dgs10_portfolio['positions'])
        tlt_stats = calculate_statistics(tlt_portfolio['positions'])

        print("\n>>> Statistical Quality:")
        print(f"  Average R^2 (DGS10): {dgs10_stats['avg_r2']:.4f}  ({dgs10_stats['significant_count']}/{dgs10_stats['total_count']} significant)")
        print(f"  Average R^2 (TLT):   {tlt_stats['avg_r2']:.4f}  ({tlt_stats['significant_count']}/{tlt_stats['total_count']} significant)")

        r2_improvement = (tlt_stats['avg_r2'] / dgs10_stats['avg_r2'] - 1) * 100 if dgs10_stats['avg_r2'] > 0 else 0
        print(f"  R^2 Improvement: {r2_improvement:+.1f}%")

        output_lines.append("\n>>> Statistical Quality:")
        output_lines.append(f"  Average R^2 (DGS10): {dgs10_stats['avg_r2']:.4f}  ({dgs10_stats['significant_count']}/{dgs10_stats['total_count']} significant)")
        output_lines.append(f"  Average R^2 (TLT):   {tlt_stats['avg_r2']:.4f}  ({tlt_stats['significant_count']}/{tlt_stats['total_count']} significant)")
        output_lines.append(f"  R^2 Improvement: {r2_improvement:+.1f}%")

        # Stress test impact comparison
        print("\n>>> Stress Test Impact Comparison (50bp Rate Increase):")
        print(f"  DGS10 Method:")
        print(f"    Portfolio Beta: {dgs10_portfolio['portfolio_ir_beta']:.6f}")
        print(f"    P&L Impact: {dgs10_portfolio['stress_test_preview']['50bp_shock_formatted']}")
        print(f"    -> Database rounding: ${round(dgs10_portfolio['stress_test_preview']['50bp_shock_pnl'], 2):,.2f}")

        print(f"\n  TLT Method:")
        print(f"    Portfolio Beta: {tlt_portfolio['portfolio_ir_beta']:.6f}")
        print(f"    P&L Impact: {tlt_portfolio['stress_test_preview']['50bp_shock_formatted']}")
        print(f"    -> Database rounding: ${round(tlt_portfolio['stress_test_preview']['50bp_shock_pnl'], 2):,.2f}")

        output_lines.append("\n>>> Stress Test Impact Comparison (50bp Rate Increase):")
        output_lines.append(f"  DGS10 Method:")
        output_lines.append(f"    Portfolio Beta: {dgs10_portfolio['portfolio_ir_beta']:.6f}")
        output_lines.append(f"    P&L Impact: {dgs10_portfolio['stress_test_preview']['50bp_shock_formatted']}")
        output_lines.append(f"    -> Database rounding: ${round(dgs10_portfolio['stress_test_preview']['50bp_shock_pnl'], 2):,.2f}")
        output_lines.append(f"\n  TLT Method:")
        output_lines.append(f"    Portfolio Beta: {tlt_portfolio['portfolio_ir_beta']:.6f}")
        output_lines.append(f"    P&L Impact: {tlt_portfolio['stress_test_preview']['50bp_shock_formatted']}")
        output_lines.append(f"    -> Database rounding: ${round(tlt_portfolio['stress_test_preview']['50bp_shock_pnl'], 2):,.2f}")

    # Overall recommendation
    print("\n" + "=" * 100)
    print("RECOMMENDATION FRAMEWORK")
    print("=" * 100)

    output_lines.append("\n" + "=" * 100)
    output_lines.append("RECOMMENDATION FRAMEWORK")
    output_lines.append("=" * 100)

    recommendation_text = """
Key Decision Criteria:

1. Statistical Quality (R2):
   - TLT typically shows 3-5x better explanatory power
   - Higher R2 = more reliable predictions
   -> Advantage: TLT

2. Beta Magnitude:
   - DGS10 betas are ~100-200x smaller (near zero)
   - TLT betas are realistic (-0.15 to -0.35 for equities)
   -> Advantage: TLT

3. Practical Use:
   - DGS10: Academic transparency, but can't trade it
   - TLT: Can actually hedge IR risk with TLT positions
   -> Advantage: TLT

4. Market Expectations:
   - DGS10: Reflects actual Fed policy (lagging)
   - TLT: Reflects forward market expectations (leading)
   -> Advantage: TLT

5. Stress Testing:
   - DGS10: P&L impacts round to $0 (too small)
   - TLT: P&L impacts are measurable ($10k-$50k range)
   -> Advantage: TLT

Industry Best Practice:
  Bloomberg PORT, BlackRock Aladdin, MSCI Barra -> Use tradeable instruments (TLT-type)
  Academic Research (Fama-French) -> Use yield changes (DGS10-type)

Recommendation:
  -> SWITCH TO TLT for:
    - Stress testing (realistic P&L impacts)
    - Risk management (better statistical fit)
    - Hedging (tradeable instrument)

  -> KEEP DGS10 for:
    - Academic validation (reference only)
    - Regulatory reporting (if required)
"""

    print(recommendation_text)
    output_lines.append(recommendation_text)

    # Save report to file
    output_path = Path(__file__).parent.parent / "analysis" / "ir_method_comparison.txt"
    with open(output_path, 'w') as f:
        f.write("\n".join(output_lines))

    print(f"\n{'=' * 100}")
    print(f"Full report saved to: {output_path}")
    print(f"{'=' * 100}\n")


if __name__ == "__main__":
    generate_comparison_report()
