# The "Too Much of a Good Thing" Problem: Understanding Concentration Risk

**Series**: Risk Management Essentials (Part 1 of 3)
**Reading Time**: 7 minutes
**Target Audience**: All investors, especially those with concentrated positions

---

## The Danger Hiding in Plain Sight

Your best investment might be your biggest risk.

That tech stock that's tripled? It's now 30% of your portfolio. Those three positions that have crushed it? Together they're 60% of your net worth. The company you work for, whose stock you've accumulated for years? It dominates your financial future.

This is concentration risk—and it's destroyed more wealth than bad stock picks ever have.

Enron employees held 62% of their 401(k)s in company stock. When it collapsed, they lost both their jobs and their retirement savings simultaneously.

Concentration risk doesn't announce itself. It accumulates silently while you celebrate your winners. By the time you notice, you may be one bad earnings report away from financial devastation.

---

## What Is Concentration Risk?

Concentration risk is the potential for outsized losses due to having too much exposure to a single position, sector, factor, or correlated group of investments.

It comes in several forms:

### 1. Single Position Concentration

The most obvious form: one stock is too large a percentage of your portfolio.

**Example**: After a 5x gain, your $20,000 position in Nvidia is now $100,000—and represents 40% of your $250,000 portfolio.

### 2. Sector Concentration

Multiple positions that seem different but share the same sector risks.

**Example**: You own Apple, Microsoft, Google, Amazon, and Nvidia. Five stocks, but effectively one bet on tech.

### 3. Factor Concentration

Positions with similar factor exposures that will move together.

**Example**: You own Tesla, Shopify, Coinbase, and Roku. Four different companies, but all high-beta, high-momentum, growth stocks. They'll crash together.

### 4. Correlation Concentration

Positions that historically move together regardless of sector or factor classifications.

**Example**: Your "diversified" portfolio of 20 stocks has an average pairwise correlation of 0.75. It behaves like 5 stocks.

### 5. Human Capital Concentration

Your job, your stock options, and your investments all depend on the same company or industry.

**Example**: You work at a tech startup, have unvested options, and your portfolio is 50% tech stocks. A tech crash affects your income, your options, and your investments simultaneously.

---

## The Mathematics of Concentration

### The Problem of Weighted Impact

If one position is 5% of your portfolio and drops 50%, you lose 2.5%.
If one position is 30% of your portfolio and drops 50%, you lose 15%.

Same stock. Same decline. Six times the damage.

### The Herfindahl-Hirschman Index (HHI)

SigmaSight uses the HHI to measure concentration. It's simple but powerful:

**HHI = Sum of (weight of each position)²**

**Example Portfolio A**: 10 positions at 10% each
- HHI = 10 × (0.10)² = 0.10 or 1,000 points
- Interpretation: Well diversified

**Example Portfolio B**: 1 position at 50%, 5 positions at 10% each
- HHI = (0.50)² + 5 × (0.10)² = 0.25 + 0.05 = 0.30 or 3,000 points
- Interpretation: Highly concentrated

| HHI Score | Interpretation |
|-----------|----------------|
| < 1,000 | Highly diversified |
| 1,000 - 1,800 | Moderately diversified |
| 1,800 - 2,500 | Moderately concentrated |
| > 2,500 | Highly concentrated |

### Effective Number of Positions

Another useful metric: **Effective Number = 1 / HHI**

This tells you how many equal-weighted positions your portfolio behaves like.

| Portfolio | HHI | Effective Positions |
|-----------|-----|---------------------|
| 20 stocks, equal weight | 0.05 | 20 |
| 20 stocks, but one is 40% | 0.18 | 5.5 |
| 5 stocks, equal weight | 0.20 | 5 |
| 3 stocks, equal weight | 0.33 | 3 |

That "20-stock portfolio" with one 40% position? It behaves like a 5-stock portfolio.

---

## Famous Concentration Disasters

### Enron (2001)

- Employees held 62% of 401(k) assets in Enron stock
- Many had 90%+ in company stock
- Stock went from $90 to $0.26
- $2 billion in employee retirement savings vanished
- Thousands lost both jobs AND retirement simultaneously

### Lehman Brothers (2008)

- Employees held significant portions of wealth in company stock
- Senior executives had majority of net worth in Lehman
- Declared bankruptcy: stock went to zero
- Partners who had $50M+ in Lehman stock lost everything

### WorldCom (2002)

- Similar to Enron: employees concentrated in company stock
- $180 billion in shareholder value destroyed
- Employees lost jobs, stock, and retirement savings together

### Individual Investor Patterns

- **Average tech worker in 2021**: 40%+ net worth in employer + tech stocks
- **Crypto enthusiasts in 2022**: 80%+ in crypto, often a single coin
- **Meme stock traders**: All-in on single positions

The pattern repeats: concentration feels great on the way up, catastrophic on the way down.

---

## Why Smart People Get Concentrated

Concentration isn't stupidity. Often, it's the result of success:

### 1. Winners Grow

You bought $10,000 each of 10 stocks. One went up 500%. Now it's $50,000 of your $95,000 portfolio (53%). You didn't concentrate—winning concentrated you.

### 2. Emotional Attachment

"This stock made me rich. Why would I sell it?" The emotional connection to winners overrides rational risk management.

### 3. Tax Avoidance

Selling that winner triggers a massive capital gains bill. Better to hold, right? (Not always—we'll discuss this.)

### 4. Conviction

"I know this company. I believe in it. Why diversify into things I know less well?" This is the Peter Lynch trap.

### 5. Compensation

Stock options, RSUs, and company stock in 401(k)s create concentration automatically.

### 6. Anchoring

"It was 50% of my portfolio when it hit $100. I'll sell when it gets back there." Meanwhile, it keeps falling.

---

## How to Identify Concentration Risk

### Metric 1: Position Weight

Basic but essential. What percentage is your largest position?

| Largest Position | Risk Level |
|------------------|------------|
| < 5% | Low |
| 5-10% | Moderate |
| 10-20% | Elevated |
| 20-30% | High |
| > 30% | Critical |

### Metric 2: Top 5 Concentration

What percentage do your top 5 positions represent?

| Top 5 Weight | Risk Level |
|--------------|------------|
| < 30% | Low |
| 30-50% | Moderate |
| 50-70% | Elevated |
| > 70% | High |

### Metric 3: HHI Score

As discussed above. SigmaSight calculates this automatically.

### Metric 4: Correlation-Adjusted Concentration

Even if positions look diversified by weight, high correlations create concentration.

**Effective HHI** adjusts for correlations. 20 positions with 0.80 average correlation might have effective HHI equivalent to 5 positions.

### Metric 5: Human Capital Overlap

Do your largest positions correlate with your job/income? If yes, true concentration is worse than portfolio metrics suggest.

---

## The SigmaSight Concentration Dashboard

SigmaSight provides comprehensive concentration analysis:

### Position Concentration
- Individual position weights
- Top 5 / Top 10 concentration
- HHI score and interpretation
- Effective number of positions

### Sector Concentration
- Sector weights vs. benchmark
- Over/underweight by sector
- Sector-level HHI

### Factor Concentration
- Factor exposure summary
- Which factors are concentrated
- Factor-level effective positions

### Correlation-Adjusted View
- Correlation clusters
- Effective diversification
- Hidden concentration from correlations

### Risk Contribution
- Which positions contribute most to portfolio risk
- Risk weight vs. dollar weight
- Concentration in risk terms

---

## Managing Concentration Risk

### Strategy 1: Systematic Trimming

Set rules before emotions kick in:

- **"Any position above 10% gets trimmed to 10%"**
- **"Rebalance quarterly to target weights"**
- **"Sell 20% of any position that doubles"**

Rules remove the emotional decision. You're not "selling your winner"—you're following your system.

### Strategy 2: Tax-Efficient De-Concentration

High taxes shouldn't prevent de-concentration:

**Option A: Charitable Giving**
- Donate appreciated stock to charity
- Deduct fair market value
- Avoid capital gains entirely
- Replace with diversified position using cash

**Option B: Tax-Loss Harvesting Offset**
- Realize losses elsewhere to offset gains
- Net effect: reduced tax bill on concentrated position sale

**Option C: Qualified Opportunity Zones**
- Defer and potentially reduce gains
- Complex but powerful for large positions

**Option D: Exchange Funds**
- Pool concentrated position with others
- Receive diversified portfolio
- Defer gains until ultimate sale
- Requires accredited investor status

**Option E: Staged Selling**
- Sell 10-20% annually
- Spread gains across tax years
- Potentially lower brackets

### Strategy 3: Options Hedging

Protect without selling:

**Protective Puts**
- Buy put options on concentrated position
- Limits downside while maintaining upside
- Cost: 2-5% annually for meaningful protection

**Collars**
- Buy puts (protection) + Sell calls (reduce cost)
- Limits both downside AND upside
- Can be structured for near-zero cost

**Prepaid Variable Forwards**
- Complex instrument for large positions
- Provides liquidity while deferring taxes
- Requires specialized advice

### Strategy 4: Dollar-Cost Averaging Out

- Set a schedule to reduce position over time
- "Sell $10,000 monthly until position is 5%"
- Reduces timing risk of single sale

### Strategy 5: Portfolio Completion

Instead of selling concentrated position, add diversifying assets around it:

- Concentrated in growth? Add value
- Concentrated in large cap? Add small cap
- Concentrated in stocks? Add bonds
- Concentrated in US? Add international

Dilute concentration through addition rather than subtraction.

---

## The Psychology of De-Concentration

### The Regret Asymmetry

Investors fear two outcomes:
1. **Selling and it goes higher** (regret of action)
2. **Holding and it crashes** (regret of inaction)

Research shows we feel #1 more acutely, even though #2 is often worse financially. This biases us toward holding.

### Reframe the Decision

Instead of "Should I sell my winner?", ask:
- "If I had cash equal to this position, would I buy this much of this stock today?"
- "Is this position sized appropriately for its risk?"
- "What would I tell a friend to do in this situation?"

### Remember the Counterfactual

You're not choosing between "keep the gain" and "lose the gain." You're choosing between:
- Keeping concentrated exposure to this one stock
- Converting to diversified exposure to many stocks

The expected return of a diversified portfolio isn't zero—it's the market return.

---

## A Concentration Risk Checklist

Use this to evaluate your portfolio:

**Single Position Risk**
- [ ] No single position > 10% of portfolio
- [ ] If >10%, there's a documented reason and exit plan
- [ ] Largest position isn't correlated with my income/job

**Sector Risk**
- [ ] No sector > 25% of portfolio (unless intentional)
- [ ] If sector-concentrated, I understand and accept the risk
- [ ] Sector concentration doesn't overlap with career risk

**Factor Risk**
- [ ] Factor exposures are intentional, not accidental
- [ ] No extreme factor tilts without documented rationale
- [ ] Factor diversification exists (not all growth, all value, etc.)

**Correlation Risk**
- [ ] Average pairwise correlation < 0.60
- [ ] Effective number of positions > 10
- [ ] Identified and understand correlation clusters

**Human Capital Risk**
- [ ] Portfolio doesn't over-concentrate in employer/industry
- [ ] Total exposure (job + portfolio) to any company < 30%
- [ ] Emergency fund exists outside concentrated positions

---

## Key Takeaways

1. **Concentration kills more portfolios than bad picks** — One catastrophic loss can erase years of gains

2. **Success creates concentration** — Winners grow; you must actively manage this

3. **HHI reveals true concentration** — It's about weight distribution, not just position count

4. **Correlation multiplies concentration** — 20 correlated positions ≠ 20-way diversification

5. **Tax concerns are manageable** — Multiple strategies exist to de-concentrate tax-efficiently

6. **Rules beat willpower** — Set systematic rebalancing rules before you need them

---

*Want to see your concentration risk? [Analyze your portfolio with SigmaSight →]*

---

**Next**: [Are You Betting on Tech Without Knowing It? →]
