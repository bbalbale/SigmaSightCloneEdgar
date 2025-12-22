# Are Your Stocks Really Diversified? How to Find Out

**Series**: SigmaSight in Action (Part 3 of 5)
**Reading Time**: 7 minutes
**Target Audience**: SigmaSight users, investors concerned about diversification

---

## The Diversification Illusion

"I own 30 stocks. I'm diversified."

This is one of the most common—and dangerous—misconceptions in investing.

The number of stocks you own tells you almost nothing about diversification. What matters is how those stocks move together. If your 30 stocks all drop 20% when the market drops 15%, you're not diversified. You just have 30 ways to lose money simultaneously.

**True diversification is about correlation, not count.**

---

## What Is Correlation?

Correlation measures how two things move in relation to each other.

- **Correlation of +1.0**: Perfect positive correlation. They move exactly together.
- **Correlation of 0**: No relationship. Movements are independent.
- **Correlation of -1.0**: Perfect negative correlation. When one goes up, the other goes down.

For portfolio diversification:
- **High correlation (0.7+)**: Positions move together. Limited diversification benefit.
- **Moderate correlation (0.3-0.7)**: Some independent movement. Meaningful diversification.
- **Low correlation (<0.3)**: Mostly independent. Strong diversification benefit.
- **Negative correlation**: Rare in stocks, excellent for risk reduction.

---

## A Real Example: The "Diversified" Tech Portfolio

Let's look at a portfolio that seems diversified:

| Position | Sector | Weight |
|----------|--------|--------|
| Apple | Technology | 15% |
| Microsoft | Technology | 15% |
| Google | Technology | 15% |
| Amazon | Consumer/Tech | 15% |
| Meta | Technology | 10% |
| Nvidia | Technology | 10% |
| Salesforce | Technology | 10% |
| Adobe | Technology | 10% |

Eight different companies. Eight different businesses. Diversified?

### The Correlation Matrix

Here's what SigmaSight reveals:

|  | AAPL | MSFT | GOOGL | AMZN | META | NVDA | CRM | ADBE |
|--|------|------|-------|------|------|------|-----|------|
| **AAPL** | 1.00 | 0.78 | 0.72 | 0.68 | 0.65 | 0.71 | 0.64 | 0.67 |
| **MSFT** | 0.78 | 1.00 | 0.76 | 0.72 | 0.68 | 0.74 | 0.71 | 0.73 |
| **GOOGL** | 0.72 | 0.76 | 1.00 | 0.74 | 0.72 | 0.69 | 0.67 | 0.70 |
| **AMZN** | 0.68 | 0.72 | 0.74 | 1.00 | 0.67 | 0.65 | 0.63 | 0.66 |
| **META** | 0.65 | 0.68 | 0.72 | 0.67 | 1.00 | 0.61 | 0.59 | 0.62 |
| **NVDA** | 0.71 | 0.74 | 0.69 | 0.65 | 0.61 | 1.00 | 0.58 | 0.64 |
| **CRM** | 0.64 | 0.71 | 0.67 | 0.63 | 0.59 | 0.58 | 1.00 | 0.69 |
| **ADBE** | 0.67 | 0.73 | 0.70 | 0.66 | 0.62 | 0.64 | 0.69 | 1.00 |

**Average pairwise correlation: 0.68**

This is extremely high. These eight stocks behave almost like a single position.

### What This Means

When the market—especially tech—declines:
- You don't have 8 independent bets
- You have 8 variations of the same bet
- A 20% tech decline means roughly 20% portfolio decline
- No position provides meaningful offset

**This isn't 8x diversification. It's 8x concentration.**

---

## How SigmaSight Analyzes Correlation

### The Correlation Matrix View

SigmaSight generates an interactive correlation matrix for your entire portfolio. Color-coded for quick interpretation:

- **Dark Red (0.8-1.0)**: Extremely high correlation—basically the same position
- **Red (0.6-0.8)**: High correlation—limited diversification
- **Yellow (0.4-0.6)**: Moderate correlation—some diversification
- **Light Green (0.2-0.4)**: Low correlation—good diversification
- **Green (0.0-0.2)**: Very low correlation—excellent diversification
- **Blue (negative)**: Negative correlation—rare, excellent hedge

### The Diversification Score

SigmaSight calculates an overall **Diversification Score** from 0-100:

- **0-25**: Highly concentrated. Portfolio acts like few positions.
- **25-50**: Moderately concentrated. Some diversification benefit.
- **50-75**: Well diversified. Meaningful risk reduction.
- **75-100**: Highly diversified. Strong correlation benefits.

Our tech portfolio example? **Score: 22** — Highly concentrated.

### Effective Number of Positions

Another metric: **Effective Number of Positions**

This answers: "How many truly independent bets do I have?"

- 8 positions with 0.68 average correlation = **~3 effective positions**
- 8 positions with 0.30 average correlation = **~6 effective positions**
- 8 positions with 0.00 average correlation = **8 effective positions**

You can own 50 stocks and have 10 effective positions. Or 10 stocks and 8 effective positions. Correlation determines the difference.

---

## Finding Hidden Concentration

Beyond the obvious (all tech stocks), correlation analysis reveals subtle concentration:

### Sector Correlation Isn't Always Obvious

Consider these pairs that seem different but correlate highly:

| Pair | Why They Seem Different | Actual Correlation |
|------|------------------------|-------------------|
| Home Depot + Lowe's | Different companies | 0.85 |
| Visa + Mastercard | Competitors | 0.88 |
| Coca-Cola + PepsiCo | Rivals | 0.82 |
| Disney + Netflix | Different business models | 0.71 |
| Exxon + Chevron | Different operations | 0.89 |

Owning "competitors" doesn't provide diversification—they respond to the same forces.

### Factor Correlation

Even cross-sector stocks can correlate through shared factor exposures:

- Two high-beta stocks in different sectors: Correlated through market factor
- Two small caps in different sectors: Correlated through size factor
- Two growth stocks in different sectors: Correlated through value factor

**Factor diversification > Sector diversification**

---

## Building a Better Correlation Profile

### Step 1: Identify Correlation Clusters

SigmaSight automatically groups your positions by correlation:

**Example Clusters from a Portfolio:**

**Cluster 1: Tech/Growth** (correlation 0.65-0.85)
- Apple, Microsoft, Google, Amazon, Nvidia
- Average intra-cluster correlation: 0.72

**Cluster 2: Financials** (correlation 0.60-0.80)
- JPMorgan, Bank of America, Goldman Sachs
- Average intra-cluster correlation: 0.71

**Cluster 3: Defensive** (correlation 0.50-0.70)
- Johnson & Johnson, Procter & Gamble, Coca-Cola
- Average intra-cluster correlation: 0.58

**Cluster 4: Independent**
- Bond ETF (0.15 correlation with stocks)
- Gold ETF (0.10 correlation with stocks)

### Step 2: Analyze Cross-Cluster Correlations

The real diversification comes between clusters:

| Cluster Pair | Correlation |
|--------------|-------------|
| Tech ↔ Financials | 0.52 |
| Tech ↔ Defensive | 0.38 |
| Financials ↔ Defensive | 0.45 |
| Stocks ↔ Bonds | 0.18 |
| Stocks ↔ Gold | 0.08 |

**Key insight**: Low cross-cluster correlation is where diversification lives.

### Step 3: Look for Correlation Gaps

What's missing from your correlation profile?

- **No low-correlation assets?** Consider bonds, gold, real assets
- **No negative correlation?** Consider treasury bonds, volatility strategies
- **All domestic?** International stocks often correlate 0.5-0.7 with US

---

## Correlation During Crisis: The Problem

Here's the uncomfortable truth: **correlations spike during crises.**

During normal markets:
- Stock A and Stock B: 0.40 correlation
- Meaningful diversification benefit

During market crisis:
- Stock A and Stock B: 0.80 correlation
- Diversification disappears when you need it most

### Historical Crisis Correlations

| Crisis | Normal Correlation | Crisis Correlation |
|--------|-------------------|-------------------|
| 2008 Financial Crisis | ~0.45 | ~0.85 |
| 2020 COVID Crash | ~0.50 | ~0.82 |
| 2022 Rate Shock | ~0.48 | ~0.75 |

**Diversification is a fair-weather friend.** When markets panic, everything falls together.

### What Actually Diversifies in Crises?

| Asset | Normal Stock Correlation | Crisis Correlation |
|-------|-------------------------|-------------------|
| Treasury Bonds | +0.10 | -0.30 to -0.50 |
| Gold | +0.05 | -0.10 to +0.20 |
| Cash | 0.00 | 0.00 |
| Managed Futures | -0.05 | -0.20 to +0.30 |

Only truly uncorrelated or negatively correlated assets protect during crises.

---

## The SigmaSight Correlation Dashboard

### What You'll See

**1. Full Correlation Matrix**
- Every position vs. every other position
- Color-coded heatmap
- Click to drill into any pair

**2. Correlation Clusters**
- Automatic grouping of similar positions
- Identifies redundant holdings
- Shows cluster weights

**3. Diversification Metrics**
- Diversification Score (0-100)
- Effective Number of Positions
- Correlation concentration index

**4. Stress Correlation Analysis**
- How correlations might change in crisis
- Historical stress correlation estimates
- Worst-case correlation scenarios

**5. Diversification Opportunities**
- What assets would improve diversification?
- Current gaps in correlation profile
- Specific suggestions based on your portfolio

---

## Practical Actions

Based on correlation analysis, here's how to improve diversification:

### If Correlations Are Too High (>0.6 average)

**Option 1: Trim Redundant Positions**
- If you own 5 stocks with 0.85 correlation, consider owning 2
- Consolidate to best conviction names
- Reallocate to uncorrelated assets

**Option 2: Add Uncorrelated Assets**
- Bonds (negative to low correlation with stocks)
- International stocks (0.5-0.7 correlation with US)
- Alternatives (real estate, commodities, gold)

**Option 3: Factor Diversification**
- Add positions with different factor profiles
- If heavy growth, add value
- If heavy large cap, add small cap

### If Correlations Are Moderate (0.3-0.6 average)

You're in reasonable shape. Consider:
- Maintaining current allocation
- Minor tilts to reduce highest correlations
- Adding small allocation to truly uncorrelated assets

### If Correlations Are Low (<0.3 average)

Excellent diversification. But verify:
- Are you giving up returns for diversification?
- Do correlations rise in stress? (They usually do)
- Is there still a coherent investment thesis?

---

## Key Takeaways

1. **Count doesn't equal diversification** — 50 correlated stocks < 10 uncorrelated stocks

2. **Correlation matrices reveal the truth** — Visual, quantifiable, actionable

3. **Correlations spike in crises** — Don't assume normal correlations hold

4. **Factor correlation matters** — Sector diversification isn't enough

5. **Effective positions matter** — How many independent bets do you really have?

6. **Bonds and alternatives help** — True diversifiers are uncorrelated or negative

---

## Your Correlation Analysis

Ready to see if you're really diversified?

1. Connect your portfolio to SigmaSight
2. Navigate to the Correlation Analysis dashboard
3. Review your correlation matrix
4. Check your Diversification Score
5. Identify correlation clusters
6. Find opportunities to improve

**Real diversification could save your portfolio in the next crisis.**

---

*[Check Your Correlations Now →]*

---

**Next**: [What If 2008 Happened Again? Stress Testing Your Portfolio →]
