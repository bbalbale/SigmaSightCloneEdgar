#!/usr/bin/env python3
"""
Seed the AI Knowledge Base with initial documents.

This script populates the ai_kb_documents table with:
1. Tool documentation from TOOL_REFERENCE.md
2. Domain primers for portfolio analysis concepts
3. FAQ-style Q&A for common questions

Usage:
    python scripts/sigmasightai/seed_kb_documents.py

Note: Requires OPENAI_API_KEY for embedding generation.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Load .env file from backend directory
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.database import get_async_session
from app.agent.services.rag_service import upsert_kb_document, count_kb_documents
from app.core.logging import get_logger

logger = get_logger(__name__)


# Knowledge Base Documents to seed
KB_DOCUMENTS = [
    # ===========================================
    # TOOL DOCUMENTATION (scope: global)
    # ===========================================
    {
        "scope": "global",
        "title": "Portfolio Complete Tool - get_portfolio_complete",
        "content": """The get_portfolio_complete tool provides a comprehensive portfolio snapshot with positions, values, and optional data.

Parameters:
- portfolio_id (required): Portfolio UUID string
- include_holdings (optional, default: true): Include position details
- include_timeseries (optional, default: false): Include historical data
- include_attrib (optional, default: false): Include attribution analysis

Limits:
- Maximum 200 positions returned
- Maximum 180 days historical data

Use this tool when the user asks about:
- Overall portfolio value or summary
- Portfolio composition
- All holdings/positions at once
- General portfolio overview

The response includes:
- meta: timestamp, truncation info, position count
- portfolio: total_value, cash_balance, positions_value
- holdings: detailed position list
- data_quality: score and capability flags""",
        "metadata": {"type": "tool_doc", "tool_name": "get_portfolio_complete"},
    },
    {
        "scope": "global",
        "title": "Position Details Tool - get_positions_details",
        "content": """The get_positions_details tool provides detailed position information with P&L calculations.

Parameters:
- portfolio_id (conditional): Portfolio UUID - use this OR position_ids
- position_ids (conditional): Comma-separated position IDs
- include_closed (optional, default: false): Include closed positions

Use this tool when the user asks about:
- Specific position performance
- P&L (profit and loss) for positions
- Individual stock details
- Cost basis information
- Which positions are profitable/unprofitable

Response includes for each position:
- position_id, symbol, quantity
- entry_price, current_price
- market_value, cost_basis
- pnl_dollar, pnl_percent""",
        "metadata": {"type": "tool_doc", "tool_name": "get_positions_details"},
    },
    {
        "scope": "global",
        "title": "Historical Prices Tool - get_prices_historical",
        "content": """The get_prices_historical tool retrieves historical price data for portfolio symbols.

Parameters:
- portfolio_id (required): Portfolio UUID
- lookback_days (optional, default: 90): Days of history (max 180)
- include_factor_etfs (optional, default: false): Include factor ETF prices

Use this tool when the user asks about:
- Price history or charts
- Performance over time
- How a position has moved
- Comparing to market
- Historical returns

Business Logic:
- Automatically selects top 5 symbols by market value
- Can include factor ETFs for benchmark comparison
- Supports 30/90/180 day lookback periods""",
        "metadata": {"type": "tool_doc", "tool_name": "get_prices_historical"},
    },
    {
        "scope": "global",
        "title": "Current Quotes Tool - get_current_quotes",
        "content": """The get_current_quotes tool provides real-time market quotes for specified symbols.

Parameters:
- symbols (required): Comma-separated symbols (max 5)
- include_options (optional, default: false): Include options data

Use this tool when the user asks about:
- Current stock price
- What something is trading at
- Real-time quotes
- Today's price movement
- Bid/ask spread

Response includes:
- price, change, change_percent
- volume, bid, ask
- day_high, day_low""",
        "metadata": {"type": "tool_doc", "tool_name": "get_current_quotes"},
    },
    {
        "scope": "global",
        "title": "Factor ETF Prices Tool - get_factor_etf_prices",
        "content": """The get_factor_etf_prices tool provides historical prices for factor ETFs used in analysis.

Parameters:
- lookback_days (optional, default: 90): Days of history (max 180)
- factors (optional): Comma-separated factor names

Available Factors:
- Market (SPY) - broad market beta
- Size (IWM) - small cap exposure
- Value (IWD) - value stocks
- Growth (IWF) - growth stocks
- Momentum (MTUM) - momentum factor
- Quality (QUAL) - quality factor
- Low Volatility (USMV) - low vol factor

Use this tool when the user asks about:
- Factor investing
- Market benchmarks
- Comparing to SPY/market
- Factor exposure analysis
- Style analysis""",
        "metadata": {"type": "tool_doc", "tool_name": "get_factor_etf_prices"},
    },
    {
        "scope": "global",
        "title": "Data Quality Tool - get_portfolio_data_quality",
        "content": """The get_portfolio_data_quality tool assesses portfolio data completeness and analysis feasibility.

Parameters:
- portfolio_id (required): Portfolio UUID
- check_factors (optional, default: true): Check factor data availability
- check_correlations (optional, default: true): Check correlation data

Use this tool when:
- Before running complex analyses
- User asks what analyses are available
- Data seems incomplete or missing
- Determining which features can be used

Response includes:
- data_quality_score: 0-1 score
- feasible_analyses: which analyses are possible
- missing_data: what's missing for full analysis
- _tool_recommendation: guidance message""",
        "metadata": {"type": "tool_doc", "tool_name": "get_portfolio_data_quality"},
    },
    {
        "scope": "global",
        "title": "Analytics Overview Tool - get_analytics_overview",
        "content": """The get_analytics_overview tool provides a portfolio analytics overview with key metrics.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Portfolio risk metrics
- Beta, Sharpe ratio, volatility
- Overall portfolio analytics
- Risk-adjusted returns
- Portfolio performance summary

Response includes:
- total_value: Current portfolio value
- returns: Period returns (daily, weekly, monthly, YTD)
- beta: Portfolio beta vs market
- volatility: Annualized volatility
- sharpe_ratio: Risk-adjusted return metric
- sector_breakdown: Allocation by sector

This is a good starting point for risk analysis before drilling into specific metrics.""",
        "metadata": {"type": "tool_doc", "tool_name": "get_analytics_overview"},
    },
    {
        "scope": "global",
        "title": "Factor Exposures Tool - get_factor_exposures",
        "content": """The get_factor_exposures tool provides portfolio factor exposures and betas.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Factor exposures
- What factors drive portfolio returns
- Style analysis (value, growth, momentum)
- Factor tilts
- Beta to different factors

Response includes:
- Factor betas for: Market, Size, Value, Momentum, Quality, Low Volatility
- R-squared: How much of returns are explained by factors
- Factor contribution to returns

Factors measured:
- Market (SPY): Overall market sensitivity
- Size (IWM): Small cap exposure
- Value (IWD): Value stock tilt
- Momentum (MTUM): Momentum exposure
- Quality (QUAL): Quality factor exposure
- Low Volatility (USMV): Defensive positioning""",
        "metadata": {"type": "tool_doc", "tool_name": "get_factor_exposures"},
    },
    {
        "scope": "global",
        "title": "Sector Exposure Tool - get_sector_exposure",
        "content": """The get_sector_exposure tool provides detailed sector allocation vs S&P 500 benchmark.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Sector allocation
- Which sectors they're overweight/underweight
- Sector diversification
- Industry exposure
- Comparing sector weights to benchmark

Response includes:
- sector_weights: Portfolio allocation by GICS sector
- benchmark_weights: S&P 500 sector weights
- over_underweights: Difference from benchmark
- top_holdings_per_sector: Largest positions in each sector

GICS Sectors covered:
Technology, Healthcare, Financials, Consumer Discretionary, Consumer Staples,
Industrials, Energy, Materials, Real Estate, Utilities, Communication Services""",
        "metadata": {"type": "tool_doc", "tool_name": "get_sector_exposure"},
    },
    {
        "scope": "global",
        "title": "Correlation Matrix Tool - get_correlation_matrix",
        "content": """The get_correlation_matrix tool shows how portfolio positions move relative to each other.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Position correlations
- How holdings move together
- Diversification analysis
- Which positions are correlated
- Portfolio diversification quality

Response includes:
- correlation_matrix: Pairwise correlations between positions
- highly_correlated_pairs: Pairs with correlation > 0.7
- low_correlation_pairs: Pairs with correlation < 0.3
- diversification_score: Overall diversification metric

Interpretation:
- Correlation of 1.0: Positions move perfectly together
- Correlation of 0: No relationship
- Correlation of -1.0: Positions move opposite
- High correlations reduce diversification benefits""",
        "metadata": {"type": "tool_doc", "tool_name": "get_correlation_matrix"},
    },
    {
        "scope": "global",
        "title": "Stress Test Tool - get_stress_test_results",
        "content": """The get_stress_test_results tool shows portfolio impact under various market scenarios.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Stress testing
- What if scenarios
- How would portfolio perform in a crash
- Market crisis impact
- Downside scenarios

Response includes stress scenarios:
- 2008 Financial Crisis: ~-50% market drop
- COVID Crash (Mar 2020): ~-34% rapid decline
- Interest Rate Shock: Rising rates impact
- Tech Bubble Burst: Technology sector crash
- Recession scenario: Economic downturn
- Black Monday: Single-day crash

For each scenario:
- estimated_loss: Portfolio impact in dollars
- estimated_loss_pct: Impact as percentage
- positions_most_affected: Highest impact holdings

Use this for risk awareness and contingency planning.""",
        "metadata": {"type": "tool_doc", "tool_name": "get_stress_test_results"},
    },
    {
        "scope": "global",
        "title": "Concentration Metrics Tool - get_concentration_metrics",
        "content": """The get_concentration_metrics tool provides portfolio concentration risk analysis.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Portfolio concentration
- Position sizing
- Largest holdings
- HHI (Herfindahl-Hirschman Index)
- Diversification level
- Single stock risk

Response includes:
- hhi_score: Concentration index (0-10000 scale)
- top_5_weight: Percentage in top 5 positions
- top_10_weight: Percentage in top 10 positions
- max_position_weight: Largest single position
- position_count: Total number of positions
- concentration_risk_level: Low/Medium/High/Extreme

Interpretation:
- HHI < 1500: Well diversified
- HHI 1500-2500: Moderate concentration
- HHI > 2500: Highly concentrated
- Single position > 20%: High single-stock risk""",
        "metadata": {"type": "tool_doc", "tool_name": "get_concentration_metrics"},
    },
    {
        "scope": "global",
        "title": "Volatility Analysis Tool - get_volatility_analysis",
        "content": """The get_volatility_analysis tool provides portfolio volatility metrics and forecasts.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Portfolio volatility
- Risk level
- VaR (Value at Risk)
- Expected volatility
- Risk forecasting
- Volatility forecast

Response includes:
- historical_volatility: Realized volatility over past period
- annualized_volatility: Volatility expressed annually
- var_95: 95% Value at Risk (1-day)
- var_99: 99% Value at Risk (1-day)
- har_forecast: HAR model volatility forecast
- volatility_trend: Rising/Stable/Falling

HAR (Heterogeneous Autoregressive) Forecasting:
- Uses daily, weekly, monthly volatility components
- Provides forward-looking volatility estimate
- Useful for risk budgeting and position sizing

Volatility ranges:
- <15%: Low volatility
- 15-25%: Normal volatility
- 25-40%: High volatility
- >40%: Very high volatility""",
        "metadata": {"type": "tool_doc", "tool_name": "get_volatility_analysis"},
    },
    {
        "scope": "global",
        "title": "Company Profile Tool - get_company_profile",
        "content": """The get_company_profile tool provides company information for a specific symbol.

Parameters:
- symbol (required): Stock symbol (e.g., 'AAPL', 'MSFT')

Use this tool when the user asks about:
- Company information
- What does a company do
- Company sector/industry
- Market cap
- Company description
- Business overview

Response includes:
- name: Company name
- symbol: Ticker symbol
- sector: GICS sector
- industry: Specific industry
- market_cap: Market capitalization
- description: Business description
- employees: Number of employees
- headquarters: Location
- website: Company website
- ceo: Chief Executive Officer

Use for researching individual holdings or understanding what a company does.""",
        "metadata": {"type": "tool_doc", "tool_name": "get_company_profile"},
    },
    {
        "scope": "global",
        "title": "Target Prices Tool - get_target_prices",
        "content": """The get_target_prices tool retrieves analyst target prices for portfolio positions.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Target prices
- Price targets
- Analyst estimates
- Upside/downside potential
- Expected returns

Response includes for each position:
- symbol: Stock ticker
- current_price: Current market price
- target_price: User's target price
- upside_percent: Potential upside to target
- time_horizon: Target timeframe
- notes: Any notes on the target

Target price analysis helps:
- Identify positions with upside potential
- Set exit points
- Prioritize positions for review
- Track investment thesis""",
        "metadata": {"type": "tool_doc", "tool_name": "get_target_prices"},
    },
    {
        "scope": "global",
        "title": "Position Tags Tool - get_position_tags",
        "content": """The get_position_tags tool retrieves tags/labels assigned to portfolio positions.

Parameters:
- portfolio_id (required): Portfolio UUID

Use this tool when the user asks about:
- Position tags or labels
- How positions are categorized
- Investment themes
- Position groupings
- Custom classifications

Response includes:
- positions with their assigned tags
- tag names and colors
- tag counts

Common tag use cases:
- Investment themes: 'AI Play', 'Dividend', 'Growth'
- Position type: 'Core Holding', 'Tactical', 'Hedge'
- Time horizon: 'Long-term', 'Trading', 'Swing'
- Risk level: 'High Risk', 'Conservative'
- Source: 'Inherited', 'Research Pick'

Tags help organize and filter portfolio positions by custom criteria.""",
        "metadata": {"type": "tool_doc", "tool_name": "get_position_tags"},
    },

    # ===========================================
    # DOMAIN PRIMERS (scope: global)
    # ===========================================
    {
        "scope": "global",
        "title": "Understanding Portfolio Beta",
        "content": """Beta measures a portfolio's sensitivity to market movements.

Key concepts:
- Beta = 1.0: Moves with the market
- Beta > 1.0: More volatile than market (amplifies movements)
- Beta < 1.0: Less volatile than market (dampens movements)
- Beta = 0: No correlation to market
- Negative beta: Moves opposite to market

Calculation:
Beta is calculated using regression analysis against a market benchmark (typically SPY/S&P 500) over a lookback period.

Portfolio beta is the weighted average of individual position betas.

Common questions:
- "What's my portfolio beta?" - Use get_portfolio_complete for overall metrics
- "Which positions have high beta?" - Use get_positions_details to see individual betas
- "How can I reduce beta?" - Consider adding low-beta positions or hedges""",
        "metadata": {"type": "domain_primer", "topic": "beta"},
    },
    {
        "scope": "global",
        "title": "Understanding Volatility",
        "content": """Volatility measures the degree of price variation over time.

Key concepts:
- Historical volatility: Calculated from past price movements
- Annualized volatility: Expressed as annual percentage
- Higher volatility = Higher risk (and potential reward)
- Lower volatility = More stable returns

Common metrics:
- Standard deviation of returns
- Variance
- VaR (Value at Risk)
- Max drawdown

Interpreting volatility:
- 10-15% annual: Low volatility (utility stocks, bonds)
- 15-25% annual: Normal volatility (large cap stocks)
- 25-40% annual: High volatility (growth stocks, small caps)
- 40%+ annual: Very high volatility (speculative stocks)

Use get_prices_historical to see price movements for volatility context.""",
        "metadata": {"type": "domain_primer", "topic": "volatility"},
    },
    {
        "scope": "global",
        "title": "Understanding Sector Exposure",
        "content": """Sector exposure shows how a portfolio is allocated across industry sectors.

GICS Sectors:
1. Technology - Software, hardware, semiconductors
2. Healthcare - Pharma, biotech, medical devices
3. Financials - Banks, insurance, asset management
4. Consumer Discretionary - Retail, autos, travel
5. Consumer Staples - Food, beverages, household products
6. Industrials - Manufacturing, aerospace, transportation
7. Energy - Oil, gas, renewable energy
8. Materials - Chemicals, mining, construction materials
9. Real Estate - REITs, property development
10. Utilities - Electric, gas, water utilities
11. Communication Services - Telecom, media, entertainment

Why sector exposure matters:
- Diversification: Avoid overconcentration in one sector
- Cyclical vs defensive: Different sectors perform differently in economic cycles
- Benchmark comparison: Compare to S&P 500 sector weights

Use get_portfolio_complete with include_holdings=true to see position sectors.""",
        "metadata": {"type": "domain_primer", "topic": "sectors"},
    },
    {
        "scope": "global",
        "title": "Understanding Concentration Risk",
        "content": """Concentration risk occurs when a portfolio has large positions in few holdings.

Key metrics:
- Top 5 concentration: % of portfolio in top 5 positions
- Herfindahl-Hirschman Index (HHI): Statistical measure of concentration
- Single position max: Largest individual position weight

Risk levels:
- Low concentration: Top 5 < 30%, many small positions
- Moderate: Top 5 between 30-50%
- High: Top 5 > 50%, few large positions
- Extreme: Single position > 20%

Why it matters:
- Single stock risk: One bad position can heavily impact returns
- Liquidity risk: Hard to exit large positions
- Regulatory limits: Some accounts have position limits

To analyze concentration:
- Use get_portfolio_complete to see all holdings
- Sort by market_value to identify large positions
- Calculate position weights as % of total portfolio""",
        "metadata": {"type": "domain_primer", "topic": "concentration"},
    },
    {
        "scope": "global",
        "title": "Understanding P&L (Profit and Loss)",
        "content": """P&L shows gains or losses on investments.

Key P&L concepts:
- Unrealized P&L: Paper gains/losses on open positions
- Realized P&L: Actual gains/losses from closed positions
- Dollar P&L: Absolute dollar amount gained/lost
- Percentage P&L: Return as percentage of cost basis

Calculation:
- P&L Dollar = Market Value - Cost Basis
- P&L Percent = (Market Value - Cost Basis) / Cost Basis * 100
- Cost Basis = Entry Price * Quantity

Important considerations:
- Does not include dividends (unless reinvested)
- Does not account for fees/commissions
- Tax implications differ for short-term vs long-term gains

Use get_positions_details to see P&L for each position with:
- entry_price, current_price
- cost_basis, market_value
- pnl_dollar, pnl_percent""",
        "metadata": {"type": "domain_primer", "topic": "pnl"},
    },
    {
        "scope": "global",
        "title": "Understanding Factor Investing",
        "content": """Factor investing targets specific drivers of returns.

Common factors:
1. Market (Beta): Exposure to overall market
2. Size: Small caps tend to outperform over time
3. Value: Cheap stocks relative to fundamentals
4. Momentum: Recent winners continue winning
5. Quality: High profitability, low debt
6. Low Volatility: Less volatile stocks for stability

Factor ETFs:
- SPY: Market beta (S&P 500)
- IWM: Size factor (small caps)
- IWD: Value factor
- IWF: Growth factor
- MTUM: Momentum factor
- QUAL: Quality factor
- USMV: Low volatility factor

How to analyze factor exposure:
- Use get_factor_etf_prices for factor benchmark data
- Use get_prices_historical with include_factor_etfs=true
- Compare portfolio returns to factor returns

Factor tilts can explain portfolio performance beyond stock selection.""",
        "metadata": {"type": "domain_primer", "topic": "factors"},
    },

    # ===========================================
    # FAQ / Q&A (scope: global)
    # ===========================================
    {
        "scope": "global",
        "title": "FAQ: How do I check my portfolio performance?",
        "content": """To check portfolio performance:

1. Get current portfolio value:
   Use get_portfolio_complete with portfolio_id
   Returns: total_value, positions_value, cash_balance

2. See individual position P&L:
   Use get_positions_details with portfolio_id
   Returns: pnl_dollar, pnl_percent for each position

3. View historical performance:
   Use get_prices_historical with portfolio_id
   Set lookback_days to desired period (30, 90, or 180)

4. Compare to market:
   Use get_factor_etf_prices to get SPY/market returns
   Compare your portfolio return to SPY return

Best practice: Start with get_portfolio_complete for overview, then drill into specific positions as needed.""",
        "metadata": {"type": "faq", "question_type": "performance"},
    },
    {
        "scope": "global",
        "title": "FAQ: What is my biggest position?",
        "content": """To find your biggest positions:

Use get_positions_details with portfolio_id
The response includes market_value for each position

Sort positions by market_value descending to find:
- Largest single holding
- Top 5 positions
- Position weights (market_value / total_portfolio_value)

Concentration tips:
- Consider if any single position > 10% of portfolio
- Check if top 5 positions > 50% of portfolio
- Evaluate if sector concentration is too high

Large positions may need:
- Rebalancing consideration
- Position sizing review
- Risk management attention""",
        "metadata": {"type": "faq", "question_type": "positions"},
    },
    {
        "scope": "global",
        "title": "FAQ: How do I compare my portfolio to the market?",
        "content": """To compare your portfolio to the market:

1. Get portfolio historical data:
   Use get_prices_historical with portfolio_id
   Set desired lookback_days (30, 90, 180)

2. Get market benchmark data:
   Use get_factor_etf_prices with factors="Market"
   This returns SPY (S&P 500) prices

3. Calculate returns:
   - Your portfolio return: (current value - starting value) / starting value
   - Market return: (current SPY - starting SPY) / starting SPY

4. Compare:
   - If your return > market return: outperforming
   - If your return < market return: underperforming
   - Beta-adjusted: Consider your portfolio's beta

Alternative:
Use get_prices_historical with include_factor_etfs=true
This includes factor ETF data alongside your positions for easy comparison.""",
        "metadata": {"type": "faq", "question_type": "benchmark"},
    },
    {
        "scope": "global",
        "title": "FAQ: What analyses can I run on my portfolio?",
        "content": """To see what analyses are available:

Use get_portfolio_data_quality with portfolio_id
This checks data completeness and returns:
- data_quality_score: 0-1 overall score
- feasible_analyses: which analyses can run

Available analyses depend on data:
1. Basic Performance (usually always available)
   - P&L calculation
   - Position values
   - Portfolio total

2. Factor Analysis (requires factor data)
   - Beta calculation
   - Factor exposures
   - Style analysis

3. Correlation Analysis (requires price history)
   - Position correlations
   - Diversification metrics

4. Attribution Analysis (requires multiple data points)
   - Return attribution
   - Sector contribution

If data is incomplete, the tool will suggest what's missing and what can still be analyzed.""",
        "metadata": {"type": "faq", "question_type": "capabilities"},
    },
    {
        "scope": "global",
        "title": "FAQ: How risky is my portfolio?",
        "content": """To assess portfolio risk:

1. Get overall risk metrics:
   Use get_analytics_overview with portfolio_id
   Returns: beta, volatility, Sharpe ratio

2. Check concentration risk:
   Use get_concentration_metrics with portfolio_id
   Returns: HHI score, top position weights

3. Analyze volatility in detail:
   Use get_volatility_analysis with portfolio_id
   Returns: VaR, HAR forecast, volatility trend

4. Run stress tests:
   Use get_stress_test_results with portfolio_id
   Returns: Impact under various crisis scenarios

5. Check correlations:
   Use get_correlation_matrix with portfolio_id
   Returns: How positions move together

Risk interpretation:
- High beta (>1.2): More market sensitivity
- High volatility (>25%): More price swings
- High concentration (HHI>2500): Single-stock risk
- High correlations: Less diversification benefit""",
        "metadata": {"type": "faq", "question_type": "risk"},
    },
    {
        "scope": "global",
        "title": "FAQ: What sectors am I exposed to?",
        "content": """To analyze sector exposure:

1. Get detailed sector breakdown:
   Use get_sector_exposure with portfolio_id
   Returns: Sector weights vs S&P 500 benchmark

2. For quick sector overview:
   Use get_analytics_overview with portfolio_id
   Returns: sector_breakdown in response

3. See positions by sector:
   Use get_portfolio_complete with include_holdings=true
   Each position includes sector information

Key sector analysis questions:
- Am I overweight any sector vs benchmark?
- Do I have technology concentration?
- Am I underweight defensive sectors (utilities, staples)?
- Is my sector allocation intentional or accidental?

Sector allocation is important for:
- Diversification across economic cycles
- Managing sector-specific risks
- Aligning with investment views""",
        "metadata": {"type": "faq", "question_type": "sectors"},
    },
    {
        "scope": "global",
        "title": "FAQ: What factors drive my portfolio returns?",
        "content": """To understand what drives your returns:

1. Get factor exposures:
   Use get_factor_exposures with portfolio_id
   Returns: Beta to Market, Size, Value, Momentum, Quality, Low Vol

2. Get factor benchmark prices:
   Use get_factor_etf_prices
   Returns: Historical prices for factor ETFs

Factor analysis reveals:
- How much of your returns come from market beta
- Whether you have style tilts (value, growth, momentum)
- Quality and volatility factor exposures
- What's driving performance beyond stock selection

Common factor interpretations:
- High market beta: Returns driven by market moves
- Value tilt: Exposed to cheap stocks
- Momentum tilt: Benefiting from trending stocks
- Quality tilt: Holding profitable, stable companies
- Low vol tilt: Defensive positioning

Use factors to:
- Understand return sources
- Manage risk exposures
- Make intentional style decisions""",
        "metadata": {"type": "faq", "question_type": "factors"},
    },

    # ===========================================
    # ADVANCED DOMAIN PRIMERS (scope: global)
    # ===========================================
    {
        "scope": "global",
        "title": "Understanding Sharpe Ratio",
        "content": """The Sharpe ratio measures risk-adjusted returns.

Formula:
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility

Interpretation:
- Sharpe < 0: Returns below risk-free rate (poor)
- Sharpe 0-0.5: Low risk-adjusted returns
- Sharpe 0.5-1.0: Acceptable risk-adjusted returns
- Sharpe 1.0-2.0: Good risk-adjusted returns
- Sharpe > 2.0: Excellent (but verify data period)

Why it matters:
- Compares returns per unit of risk taken
- Allows comparison between different strategies
- Higher is better (more return per risk)

Caveats:
- Assumes returns are normally distributed
- Sensitive to time period chosen
- May not capture tail risks
- Past Sharpe doesn't guarantee future

Use get_analytics_overview to see portfolio Sharpe ratio.""",
        "metadata": {"type": "domain_primer", "topic": "sharpe_ratio"},
    },
    {
        "scope": "global",
        "title": "Understanding Value at Risk (VaR)",
        "content": """VaR estimates the maximum potential loss over a time period at a confidence level.

Key concepts:
- VaR 95%: 5% chance of losing more than this amount
- VaR 99%: 1% chance of losing more than this amount
- Time horizon: Usually 1-day or 10-day
- Expressed in dollars or percentage

Example:
"1-day 95% VaR of $10,000" means:
- On 95% of days, you won't lose more than $10,000
- On 5% of days (about 13 per year), you might lose more

VaR types:
- Historical VaR: Based on actual past returns
- Parametric VaR: Assumes normal distribution
- Monte Carlo VaR: Uses simulations

Limitations:
- Doesn't say HOW MUCH you might lose beyond VaR
- Assumes market conditions similar to history
- May underestimate tail risks

Use get_volatility_analysis for portfolio VaR estimates.""",
        "metadata": {"type": "domain_primer", "topic": "var"},
    },
    {
        "scope": "global",
        "title": "Understanding Long/Short Portfolios",
        "content": """Long/short portfolios hold both long and short positions.

Key concepts:
- Long position: Own the stock, profit when it rises
- Short position: Borrowed stock sold, profit when it falls
- Gross exposure: Long + Short (total market exposure)
- Net exposure: Long - Short (directional exposure)

Example:
- Long exposure: $1,000,000
- Short exposure: $500,000
- Gross exposure: $1,500,000 (150% of capital if $1M capital)
- Net exposure: $500,000 (50% net long)

Why use long/short:
- Hedge market risk
- Profit from both rising and falling stocks
- Reduce portfolio volatility
- Express relative value views

Metrics to track:
- Gross exposure: Total risk deployed
- Net exposure: Directional market bet
- Beta: Market sensitivity after hedging
- Alpha: Returns above what beta explains

SigmaSight supports long (positive) and short (negative) positions.""",
        "metadata": {"type": "domain_primer", "topic": "long_short"},
    },
    {
        "scope": "global",
        "title": "Understanding Correlation in Portfolios",
        "content": """Correlation measures how positions move relative to each other.

Correlation values:
- +1.0: Perfect positive correlation (move together)
- 0.0: No correlation (independent)
- -1.0: Perfect negative correlation (move opposite)

Portfolio implications:
- High correlations: Positions amplify each other
- Low correlations: Better diversification
- Negative correlations: Natural hedging

Diversification benefit:
- Portfolio with correlated stocks: Risk reduction limited
- Portfolio with uncorrelated stocks: Significant risk reduction
- A well-diversified portfolio has low average correlation

Common correlations:
- Stocks in same sector: Often highly correlated (0.6-0.9)
- Stocks vs bonds: Often negatively correlated (-0.2 to -0.5)
- Tech stocks with each other: Highly correlated
- Utilities vs tech: Lower correlation

Use get_correlation_matrix to see position correlations.""",
        "metadata": {"type": "domain_primer", "topic": "correlation"},
    },
    {
        "scope": "global",
        "title": "Understanding Options Greeks",
        "content": """Options Greeks measure sensitivities of option prices to various factors.

Key Greeks:
- Delta: Price change per $1 move in underlying
  - Call delta: 0 to 1 (positive)
  - Put delta: -1 to 0 (negative)
  - At-the-money: ~0.5 or -0.5

- Gamma: Rate of change of delta
  - Highest for at-the-money options
  - Shows delta instability

- Theta: Time decay per day
  - Usually negative (option loses value over time)
  - Accelerates near expiration

- Vega: Price change per 1% change in volatility
  - Higher for longer-dated options
  - Long options have positive vega

- Rho: Price change per 1% change in interest rates
  - Usually small effect

Portfolio Greeks:
- Sum of position Greeks weighted by position size
- Delta-adjusted exposure: Stock equivalent exposure
- Vega exposure: Volatility sensitivity

SigmaSight calculates Greeks for options positions.""",
        "metadata": {"type": "domain_primer", "topic": "greeks"},
    },
]


async def seed_kb_documents():
    """Seed the knowledge base with initial documents."""
    logger.info("Starting KB document seeding...")

    async with get_async_session() as db:
        # Check current document count
        current_count = await count_kb_documents(db)
        logger.info(f"Current KB document count: {current_count}")

        # Seed each document
        success_count = 0
        error_count = 0

        for doc in KB_DOCUMENTS:
            try:
                doc_id = await upsert_kb_document(
                    db,
                    scope=doc["scope"],
                    title=doc["title"],
                    content=doc["content"],
                    metadata=doc.get("metadata", {}),
                )
                logger.info(f"Seeded: {doc['title'][:50]}... (id={doc_id})")
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to seed '{doc['title']}': {e}")
                error_count += 1

        # Final count
        final_count = await count_kb_documents(db)
        logger.info(f"\nSeeding complete!")
        logger.info(f"  Documents seeded: {success_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info(f"  Total KB documents: {final_count}")


if __name__ == "__main__":
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("The RAG service requires OpenAI for embedding generation.")
        sys.exit(1)

    asyncio.run(seed_kb_documents())
