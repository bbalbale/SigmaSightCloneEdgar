# Volatility Isn't Just Risk—It's Information

**Series**: Risk Management Essentials (Part 3 of 3)
**Reading Time**: 8 minutes
**Target Audience**: Intermediate investors, risk-conscious investors

---

## Beyond "Stocks Are Volatile"

Every investor knows stocks are volatile. Prices go up and down. Some days are green, some are red. Water is wet.

But most investors don't truly understand volatility—what it measures, what causes it, how to forecast it, and most importantly, how to use it.

Volatility isn't just risk to be minimized. It's information to be used. Understanding volatility transforms you from a passive observer of market swings to an informed manager of portfolio risk.

---

## What Volatility Actually Measures

### The Technical Definition

Volatility is the **standard deviation of returns** over a period. It measures how much returns deviate from their average.

**Example**:
- Stock A: Returns of +5%, +6%, +4%, +5%, +5% (average 5%)
- Stock B: Returns of +15%, -5%, +20%, -10%, +5% (average 5%)

Same average return. Completely different experience.

- **Stock A volatility**: ~0.7% (very low)
- **Stock B volatility**: ~12% (very high)

### Annualized Volatility

Volatility is typically stated in annual terms:

- **Low volatility**: <15% annually (utilities, bonds, staples)
- **Market volatility**: 15-20% annually (S&P 500 average)
- **High volatility**: 20-30% annually (growth stocks, small caps)
- **Very high volatility**: >30% annually (speculative stocks, crypto)

A stock with 30% annual volatility might reasonably move ±30% in a year. Within a single standard deviation, which occurs about 68% of the time.

### What the Numbers Mean

For a stock with 20% annual volatility:
- 68% of the time: Returns between -20% and +20%
- 95% of the time: Returns between -40% and +40%
- 99.7% of the time: Returns between -60% and +60%

Volatility tells you the **range of normal outcomes**. Higher volatility = wider range of possible results.

---

## Types of Volatility

### Historical Volatility

Looking backward: "How volatile has this been?"

Calculated from past returns—typically 30, 60, or 252 trading days. It's factual but backward-looking.

**Use**: Understanding what volatility has been. Basis for risk models.

### Implied Volatility

Looking forward: "How volatile does the market expect this to be?"

Extracted from options prices. If options are expensive, implied volatility is high—the market expects big moves.

**Use**: Understanding market expectations. Trading opportunities when historical vs. implied diverge.

### Realized Volatility

What actually happened: "How volatile was this over the measured period?"

Calculated after the fact. The ground truth against which forecasts are judged.

**Use**: Evaluating forecast accuracy. Understanding actual risk experienced.

### Forecasted Volatility

Prediction: "How volatile will this likely be?"

Uses models (like HAR) to estimate future volatility based on patterns.

**Use**: Forward-looking risk management. Position sizing. Portfolio construction.

---

## Why Volatility Clusters

Here's a crucial insight: **volatility clusters**.

High-volatility days tend to follow high-volatility days. Low-volatility periods persist. This isn't random—it's one of the most robust findings in finance.

### The Volatility Clustering Pattern

```
Low Vol Regime:  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
Transition:      ▁▁▁▂▃▅▆█
High Vol Regime: █████████████████████
Transition:      █▆▅▃▂▁▁▁▁
Low Vol Regime:  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
```

Transitions between regimes are sudden. Regimes themselves are persistent.

### Why Does This Happen?

Several mechanisms:
1. **Information arrives in clusters** — Earnings season, Fed meetings, crises
2. **Feedback loops** — Volatility triggers selling, which triggers more volatility
3. **Leverage effects** — Falling prices increase leverage ratios, increasing risk
4. **Behavioral cascades** — Fear and panic spread through markets

### The Practical Implication

**Today's volatility predicts tomorrow's volatility.**

If the market was calm yesterday, it's likely calm today. If yesterday was chaotic, expect more chaos today.

This persistence makes volatility forecastable—unlike returns, which are nearly impossible to predict.

---

## HAR: Forecasting Volatility

SigmaSight uses the **Heterogeneous Autoregressive (HAR)** model for volatility forecasting. Here's why it works:

### The HAR Insight

Different market participants operate on different time horizons:
- **Day traders** react to daily volatility
- **Swing traders** respond to weekly patterns
- **Institutional investors** consider monthly trends

The HAR model captures all three:

```
Future Volatility = f(Daily Vol, Weekly Vol, Monthly Vol)
```

By incorporating multiple timeframes, HAR produces more accurate forecasts than simple historical averages.

### HAR in Practice

**Inputs**:
- Average volatility over past day
- Average volatility over past week
- Average volatility over past month

**Output**:
- Forecasted volatility for coming day/week

**Accuracy**: HAR typically explains 40-60% of volatility variation—vastly better than assuming historical average continues.

---

## Volatility and Your Portfolio

### Position-Level Volatility

Each position has its own volatility profile:

| Position | Weight | Volatility | Vol Contribution |
|----------|--------|------------|------------------|
| Apple | 15% | 25% | 3.8% |
| Nvidia | 10% | 45% | 4.5% |
| J&J | 10% | 18% | 1.8% |
| S&P 500 ETF | 40% | 16% | 6.4% |
| Bond ETF | 25% | 6% | 1.5% |
| **Portfolio** | 100% | | **~14%** |

**Key insight**: Nvidia is 10% of the portfolio but contributes more volatility than Apple (15%) or the entire bond allocation (25%). High-vol positions punch above their weight.

### Portfolio Volatility ≠ Average Position Volatility

Portfolio volatility is less than the weighted average of position volatilities. Why? **Diversification.**

Positions don't move perfectly together. When some zig, others zag. This reduces combined volatility.

**Example**:
- Two stocks, each 25% volatility
- If perfectly correlated (correlation = 1): Portfolio vol = 25%
- If uncorrelated (correlation = 0): Portfolio vol = 17.7%
- If negatively correlated (correlation = -0.5): Portfolio vol = 12.5%

The lower the correlations, the more diversification benefit, the lower the portfolio volatility.

---

## Volatility Regimes and What They Signal

### Low Volatility Regime

**Characteristics**:
- VIX below 15
- Daily moves of <1% are normal
- Markets grind higher slowly
- Complacency builds

**What to know**:
- Low vol regimes can persist for years
- But they always end—often suddenly
- Low vol doesn't mean low risk; it means low perceived risk
- This is when to check your hedges

### High Volatility Regime

**Characteristics**:
- VIX above 25
- Daily moves of 2-3%+ are common
- Sharp rallies and selloffs
- Fear dominates

**What to know**:
- High vol regimes are usually shorter than low vol
- Big down days AND big up days occur
- Worst days to sell (buying opportunity)
- Best days to add hedges (expensive though)

### Regime Transitions

The most dangerous times are regime transitions:

**Low → High**: The shock. 2008, 2020. Suddenly everything moves.
**High → Low**: The normalization. Gradual, feels safe, invites complacency.

SigmaSight tracks volatility regime indicators to help you stay aware.

---

## Using Volatility for Better Decisions

### Application 1: Position Sizing

Basic principle: **Size positions inversely to their volatility**.

If Position A has 2x the volatility of Position B, it should be half the size to contribute equal risk.

**Example Risk Parity Sizing**:
| Position | Volatility | Target Risk | Implied Weight |
|----------|------------|-------------|----------------|
| Stock A | 30% | 5% | 16.7% |
| Stock B | 15% | 5% | 33.3% |
| Bonds | 6% | 5% | 83.3% |

(Weights don't sum to 100% because risk parity often uses leverage)

### Application 2: Setting Expectations

Volatility tells you the range of normal outcomes.

**Portfolio volatility**: 15%
**Expected return**: 8%

One-year range (68% confidence): -7% to +23%
One-year range (95% confidence): -22% to +38%

When your portfolio drops 10%, is that unexpected? With 15% volatility, drops of 10% are well within the normal range. Don't panic at normal.

### Application 3: Stress Test Calibration

Volatility helps calibrate stress tests:

**Rule of thumb**: 3-sigma moves happen occasionally
- 15% volatility → 45% crash is plausible (3 × 15%)
- 30% volatility → 90% crash is plausible (3 × 30%)

Does your portfolio survive a 3-sigma move? Volatility tells you how big that move might be.

### Application 4: Option Strategy Selection

Implied volatility guides options decisions:

**High implied vol**: Options are expensive
- Favor selling options (collecting premium)
- Avoid buying options (paying up)

**Low implied vol**: Options are cheap
- Favor buying options (cheap protection)
- Avoid selling options (small premium)

### Application 5: Dynamic Allocation

Some investors adjust allocation based on volatility regime:

**Low vol regime**:
- Increase equity allocation
- Reduce hedges (they're cheap but decaying)
- Accept more beta

**High vol regime**:
- Reduce equity allocation
- Add/maintain hedges
- Reduce beta

This is market timing—difficult to execute well. But volatility-based signals are more reliable than price-based signals.

---

## SigmaSight Volatility Features

### Portfolio Volatility Dashboard
- Current realized volatility
- HAR forecasted volatility
- Volatility regime indicator
- Historical volatility chart

### Position Volatility Analysis
- Individual position volatilities
- Volatility contribution by position
- Identifying outsized risk contributors

### Volatility Attribution
- What's driving portfolio volatility?
- Which positions/factors contribute most?
- Correlation impact on total volatility

### Volatility Scenarios
- What if volatility doubled?
- Stress test under high-vol regime
- Impact of volatility spike on options/hedges

### Volatility Forecasts
- Daily/weekly/monthly forecasts
- HAR model outputs
- Confidence intervals around forecasts

---

## Common Volatility Mistakes

### Mistake 1: Confusing Low Volatility with Low Risk

Low volatility means low *recent* volatility. Volatility can spike without warning. Low vol is not the same as safe.

### Mistake 2: Selling During High Volatility

High-vol periods include both the worst AND best days. Selling locks in losses and misses the recoveries that follow.

### Mistake 3: Ignoring Volatility in Position Sizing

A 10% position in a 40% vol stock contributes more risk than a 10% position in a 15% vol stock. Size accordingly.

### Mistake 4: Assuming Past Volatility Predicts Returns

Volatility predicts future volatility. It doesn't predict returns. Low vol doesn't mean low returns; high vol doesn't mean high returns.

### Mistake 5: Chasing Low Volatility

Low-vol strategies are popular. When everyone wants them, they become overpriced. The "low vol anomaly" premium shrinks.

---

## Key Takeaways

1. **Volatility measures outcome dispersion** — It's the range of normal results, not just "risk"

2. **Volatility clusters** — Today's vol predicts tomorrow's vol; regimes persist

3. **HAR improves forecasting** — Multiple timeframes capture different market participants

4. **Position vol ≠ Portfolio vol** — Diversification reduces combined volatility

5. **Use volatility for sizing** — Higher vol positions deserve smaller weights

6. **Regime awareness matters** — Low vol regimes end suddenly; high vol regimes mean opportunity and danger

---

*Want to see your portfolio's volatility profile? [Analyze with SigmaSight →]*

---

**Series Complete!**

You've now learned the essentials of risk management:
1. Concentration Risk — The danger of too much in one place
2. Sector Exposure — The hidden bets in your allocation
3. Volatility — The information in market swings

Ready to apply these concepts to your portfolio?

**[Get Started with SigmaSight →]**
