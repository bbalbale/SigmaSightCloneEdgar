# Three Mock Investment Portfolios

> **Note on Entry Prices and Dates (Updated November 10, 2025)**: All positions have been adjusted to appear as if acquired on **June 30, 2025** at closing prices. This means:
> - **Entry Date**: June 30, 2025 for ALL positions (stocks, funds, options, private investments)
> - **Entry Prices**: June 30, 2025 market close prices for all PUBLIC stocks
> - **Quantities and Prices**: Adjusted to achieve exact or near-exact equity balances with whole number shares
> - **Result**: Tracking begins July 1, 2025 with zero unrealized P&L on the first day
>
> This adjustment ensures clean, predictable P&L calculations that are easier to debug. Portfolio equity balances have been fine-tuned to be at or just below target values.
>
> **Adjustment Scripts Used**:
> - `backend/scripts/database/adjust_entry_prices_to_june30.py` - Set June 30, 2025 prices
> - `backend/scripts/database/adjust_prices_for_exact_equity.py` - Adjust for exact equity with whole shares
> - `backend/scripts/database/fix_hedge_fund_exposure.py` - Fix hedge fund to 100% long / 50% short
> - `backend/scripts/database/monitor_equity_pnl.py` - Monitor daily equity changes
>
> **Final Equity Balances**:
> - Demo Individual Investor: $484,999.75 (target: $485,000)
> - Demo High Net Worth: $2,850,000.00 (target: $2,850,000) ✓ EXACT
> - Demo Hedge Fund: $1,599,688.91 NAV / $3,199,588.59 long / $1,599,899.68 short (100%/50% of $3.2M equity)
> - Demo Family Office Public: $1,249,992.95 (target: $1,250,000)
> - Demo Family Office Private: $950,000.00 (target: $950,000) ✓ EXACT

## Portfolio 1: "Balanced Individual Investor"
**Total Portfolio Value:** $485,000
**Equity Balance (NAV):** $485,000
**Investor Profile:** Individual investor with 401k, IRA, and taxable accounts
**Investment Strategy:** Core holdings with some growth tilt, heavy mutual fund allocation

### Asset Allocation
- **Mutual Funds & ETFs:** 68% ($330,000)
- **Individual Stocks:** 32% ($155,000)

### Holdings Breakdown

#### Mutual Funds & ETFs (68% allocation)
| Ticker | Asset Class | Allocation | Value | Description |
|--------|-------------|------------|-------|-------------|
| FXNAX | Large Cap Growth | 18% | $87,300 | Fidelity US Large Cap Growth |
| FCNTX | Large Cap Blend | 15% | $72,750 | Fidelity Contrafund |
| FMAGX | International | 12% | $58,200 | Fidelity Magellan |
| VTI | Total Market | 8% | $38,800 | Vanguard Total Stock Market |
| VTIAX | International | 6% | $29,100 | Vanguard Total International |
| BND | Bonds | 5% | $24,250 | Vanguard Total Bond Market |
| VNQ | REITs | 4% | $19,400 | Vanguard Real Estate ETF |

#### Individual Stocks (32% allocation)
| Ticker | Shares | Value | Allocation | Sector |
|--------|--------|-------|------------|---------|
| AAPL | 85 | $19,125 | 3.9% | Technology |
| MSFT | 45 | $18,900 | 3.9% | Technology |
| AMZN | 110 | $18,700 | 3.9% | Consumer Discretionary |
| GOOGL | 115 | $18,400 | 3.8% | Technology |
| TSLA | 70 | $17,850 | 3.7% | Consumer Discretionary |
| NVDA | 25 | $17,500 | 3.6% | Technology |
| JNJ | 105 | $16,800 | 3.5% | Healthcare |
| JPM | 85 | $14,450 | 3.0% | Financials |
| V | 50 | $13,400 | 2.8% | Financials |

**Key Characteristics:**
- Mix of growth and value through mutual funds
- Tech-heavy individual stock picks reflecting popular retail investor preferences
- Some dividend stocks (JNJ, JPM)
- International exposure through funds
- Small bond allocation for stability

---

## Portfolio 2: "Sophisticated High Net Worth"
**Total Portfolio Value:** $2,850,000
**Equity Balance (NAV):** $2,850,000
**Investor Profile:** High net worth individual with access to private investments
**Investment Strategy:** Diversified across public markets, private funds, and real estate

### Asset Allocation
- **Public Equities (Stocks/ETFs):** 45% ($1,282,500)
- **Private Funds:** 25% ($712,500)
- **Real Estate:** 20% ($570,000)
- **Alternative Investments:** 7% ($199,500)
- **Cash/Fixed Income:** 3% ($85,500)

### Holdings Breakdown

#### Public Equities (45% allocation)
| Ticker | Shares | Value | Allocation | Category |
|--------|--------|-------|------------|----------|
| SPY | 400 | $212,000 | 7.4% | Core Index |
| QQQ | 450 | $189,000 | 6.6% | Tech Index |
| VTI | 800 | $184,000 | 6.5% | Total Market |
| AAPL | 400 | $90,000 | 3.2% | Individual Stock |
| MSFT | 200 | $84,000 | 2.9% | Individual Stock |
| AMZN | 480 | $81,600 | 2.9% | Individual Stock |
| GOOGL | 500 | $80,000 | 2.8% | Individual Stock |
| BRK.B | 180 | $79,200 | 2.8% | Individual Stock |
| JPM | 350 | $59,500 | 2.1% | Individual Stock |
| JNJ | 310 | $49,600 | 1.7% | Individual Stock |
| NVDA | 70 | $49,000 | 1.7% | Individual Stock |
| META | 90 | $47,700 | 1.7% | Individual Stock |
| UNH | 85 | $46,375 | 1.6% | Individual Stock |
| V | 170 | $45,560 | 1.6% | Individual Stock |
| HD | 125 | $43,750 | 1.5% | Individual Stock |
| PG | 250 | $41,250 | 1.4% | Individual Stock |

#### Private Funds (25% allocation)
| Fund Type | Investment | Value | Allocation | Description |
|-----------|------------|-------|------------|-------------|
| Private Equity | Blackstone BX Fund | $285,000 | 10.0% | Large buyout fund |
| Venture Capital | Andreessen Horowitz Fund | $142,500 | 5.0% | Tech-focused VC |
| Private REIT | Starwood Real Estate | $142,500 | 5.0% | Commercial real estate |
| Hedge Fund | Two Sigma Spectrum | $142,500 | 5.0% | Quantitative strategies |

#### Real Estate (20% allocation)
| Property Type | Investment | Value | Allocation | Details |
|---------------|------------|-------|------------|---------|
| Primary Residence | Home Equity | $285,000 | 10.0% | $950k value, $665k mortgage |
| Rental Property 1 | Condo | $142,500 | 5.0% | $285k value, $142.5k mortgage |
| Rental Property 2 | Single Family | $142,500 | 5.0% | $285k value, $142.5k mortgage |

#### Alternative Investments (7% allocation)
| Investment | Value | Allocation | Description |
|------------|-------|------------|-------------|
| Gold ETF (GLD) | $71,250 | 2.5% | Inflation hedge |
| Commodities (DJP) | $57,000 | 2.0% | Diversified commodities |
| Cryptocurrency | $42,750 | 1.5% | Bitcoin/Ethereum |
| Art/Collectibles | $28,500 | 1.0% | Alternative assets |

#### Cash & Fixed Income (3% allocation)
| Investment | Value | Allocation | Description |
|------------|-------|------------|-------------|
| Money Market | $57,000 | 2.0% | Liquidity reserve |
| Treasury Bills | $28,500 | 1.0% | Short-term bonds |

**Key Characteristics:**
- Significant private market exposure
- Real estate diversification (personal + investment)
- Access to institutional-quality hedge funds and PE
- Alternative investments for inflation protection
- Lower cash allocation due to illiquid investments

---

## Portfolio 3: "Long/Short Equity Hedge Fund Style"
**Starting Equity:** ~$3,200,000
**Equity Balance:** ~$3,200,000 (starting capital)
**Investor Profile:** Sophisticated trader with derivatives access
**Investment Strategy:** Long/short equity with controlled leverage

### Portfolio Metrics
- **Long Exposure:** ~$3,200,000 (100% of equity)
- **Short Exposure:** ~$1,600,000 (50% of equity)
- **Gross Exposure:** ~$4,800,000 (150% of equity)
- **NAV (Net Market Exposure):** ~$1,600,000 (50% of equity)
- **Leverage Ratio:** 1.5x gross exposure

> **Note**: Equity represents starting capital. NAV represents net market exposure (Long - Short).

### Long Positions (60% of portfolio)

> **Tagging Note**: `Suggested Tags` mirror the tags applied in the seed data so the frontend can organize positions without strategy containers.

#### Growth/Momentum Longs
| Ticker | Shares | Value | Allocation | Suggested Tags |
|--------|--------|-------|------------|----------------|
| NVDA | 800 | $560,000 | 17.5% | Long Momentum, AI Play |
| MSFT | 1,000 | $420,000 | 13.1% | Long Momentum, Cloud Dominance |
| AAPL | 1,500 | $337,500 | 10.5% | Long Momentum, Ecosystem Moat |
| GOOGL | 1,800 | $288,000 | 9.0% | Long Momentum, AI & Search |
| META | 1,000 | $265,000 | 8.3% | Long Momentum, Metaverse |
| AMZN | 1,400 | $238,000 | 7.4% | Long Momentum, AWS Growth |
| TSLA | 800 | $204,000 | 6.4% | Long Momentum, EV Revolution |
| AMD | 1,200 | $194,400 | 6.1% | Long Momentum, Data Center |

#### Quality/Value Longs
| Ticker | Shares | Value | Allocation | Suggested Tags |
|--------|--------|-------|------------|----------------|
| BRK.B | 600 | $264,000 | 8.3% | Long Value, Quality |
| JPM | 1,000 | $170,000 | 5.3% | Long Value, Bank Quality |
| JNJ | 800 | $128,000 | 4.0% | Long Value, Healthcare Defensive |
| UNH | 200 | $109,200 | 3.4% | Long Value, Healthcare Quality |
| V | 350 | $93,800 | 2.9% | Long Value, Payment Network |

**Total Long Positions:** $4,271,900 (133.5% of NAV)

### Short Positions (25% of portfolio)

#### Overvalued Growth Shorts
| Ticker | Shares | Value | Allocation | Suggested Tags |
|--------|--------|-------|------------|----------------|
| NFLX | -600 | -$294,000 | -9.2% | Short Value Traps |
| SHOP | -1,000 | -$195,000 | -6.1% | Short Value Traps |
| ZM | -2,000 | -$140,000 | -4.4% | Short Value Traps |
| PTON | -3,000 | -$120,000 | -3.8% | Short Value Traps |
| ROKU | -1,800 | -$108,000 | -3.4% | Short Value Traps |

#### Cyclical/Value Shorts
| Ticker | Shares | Value | Allocation | Suggested Tags |
|--------|--------|-------|------------|----------------|
| XOM | -2,000 | -$220,000 | -6.9% | Short Value Traps |
| F | -10,000 | -$120,000 | -3.8% | Short Value Traps |
| GE | -800 | -$112,000 | -3.5% | Short Value Traps |
| C | -2,000 | -$110,000 | -3.4% | Short Value Traps |

**Total Short Positions:** -$1,419,000 (-44.3% of NAV)

### Options Positions (15% of portfolio)

#### Long Options (Upside/Volatility)
| Ticker | Type | Strike | Expiry | Contracts | Premium | Suggested Tags |
|--------|------|--------|--------|-----------|---------|----------------|
| SPY | Call | $460 | 2025-09-19 | 200 | $140,000 | Options Overlay |
| QQQ | Call | $420 | 2025-08-15 | 150 | $105,000 | Options Overlay |
| VIX | Call | $25 | 2025-07-16 | 300 | $75,000 | Options Overlay |
| NVDA | Call | $800 | 2025-10-17 | 50 | $62,500 | Options Overlay |

#### Short Options (Premium Collection)
| Ticker | Type | Strike | Expiry | Contracts | Premium | Suggested Tags |
|--------|------|--------|--------|-----------|---------|----------------|
| AAPL | Put | $200 | 2025-08-15 | -100 | -$45,000 | Options Overlay |
| MSFT | Put | $380 | 2025-09-19 | -80 | -$40,000 | Options Overlay |
| TSLA | Call | $300 | 2025-08-15 | -60 | -$48,000 | Options Overlay |
| META | Put | $450 | 2025-09-19 | -50 | -$37,500 | Options Overlay |

**Total Options Premium:** $212,000 net long

### Performance Targets
- **Target Beta:** 0.85 (market neutral bias)
- **Expected Sharpe Ratio:** 2.0+
- **Target Annual Return:** 15-20%
- **Maximum Drawdown Target:** <8%

**Key Characteristics:**
- Market-neutral with slight long bias
- High gross exposure through leverage
- Significant options overlay for income and hedging
- Focus on factor-neutral pairs trading
- Volatility trading component
- Risk management through position sizing and correlation limits

---

## Portfolio Comparison Summary

| Metric | Individual | High Net Worth | Long/Short |
|--------|------------|----------------|------------|
| **Total Value** | $485K | $2.85M | $3.2M |
| **Equity Balance (NAV)** | $485K | $2.85M | $3.2M |
| **Complexity** | Low | Medium | High |
| **Liquidity** | High (90%+) | Medium (55%) | High (85%) |
| **Risk Level** | Conservative | Moderate | Aggressive |
| **Expected Return** | 8-10% | 10-12% | 15-20% |
| **Volatility** | Medium | Medium-Low | Medium-High |
| **Diversification** | Good | Excellent | Concentrated |

Each portfolio reflects different levels of sophistication, risk tolerance, and access to investment vehicles, providing realistic examples for testing portfolio analysis tools.

---

## Multi-Portfolio User: "Family Office Mandates"

**User Goal:** Model a family office that separates its public markets growth sleeve from a private alternatives allocation.

### Portfolio A: "Public Growth Sleeve"
**Total Portfolio Value:** $1,250,000  
**Focus:** Thematic technology exposure paired with quality compounders and defensive income positions.

| Ticker | Shares | Entry Price | Allocation Focus | Notes |
|--------|--------|-------------|------------------|-------|
| XLK | 600 | $180.00 | Tech ETF | Core technology allocation |
| SMH | 500 | $210.00 | Semiconductors | High-conviction chip exposure |
| IGV | 400 | $330.00 | Software | Cloud/SaaS overweight |
| XLY | 450 | $185.00 | Consumer Discretionary | Cyclical participation |
| COST | 220 | $720.00 | Quality Compounder | Defensive growth anchor |
| AVGO | 140 | $1,350.00 | Quality Compounder | Cash-flow powerhouse |
| ASML | 160 | $960.00 | International Tech | European lithography leader |
| LULU | 300 | $380.00 | Consumer Discretionary | Lifestyle growth story |
| NEE | 500 | $70.00 | Defensive Yield | Clean energy utility exposure |
| SCHD | 650 | $75.00 | Defensive Yield | Dividend growth ballast |
| JEPQ | 700 | $54.00 | Income & Options Overlay | Enhanced income sleeve |
| BIL | 900 | $91.50 | Liquidity | Treasury-bill cash management |

### Portfolio B: "Private Opportunities Sleeve"
**Total Portfolio Value:** $950,000  
**Focus:** Income-oriented and diversifying private market commitments for inflation protection and non-correlated returns.

| Instrument | Commitment | Category | Rationale |
|------------|------------|----------|-----------|
| FO_PRIVATE_CREDIT_FUND | $225,000 | Private Credit | Senior secured direct lending income |
| FO_GROWTH_PE_FUND | $210,000 | Private Equity | Growth buyout exposure |
| FO_VC_SECONDARIES_FUND | $145,000 | Venture Capital | Late-stage secondary diversification |
| FO_REAL_ASSET_REIT | $110,000 | Private REIT | Core real assets allocation |
| FO_INFRASTRUCTURE_FUND | $90,000 | Infrastructure | Inflation-linked cash flows |
| FO_HOME_RENTAL_PORTFOLIO | $85,000 | Real Estate | Scaled single-family rental strategy |
| FO_IMPACT_LENDING_FUND | $55,000 | Impact Investing | Community lending with sustainability mandate |
| FO_ART_COLLECTIVE | $30,000 | Alternative Assets | Cultural and collectible diversification |
| FO_CRYPTO_DIGITAL_TRUST | $30,000 | Digital Assets | Institutional crypto exposure |

This multi-portfolio user demonstrates the new capability to model separate sleeves under a single investor profile while keeping position sets distinct across public and private mandates.
