# Your Portfolio's Hidden DNA: A SigmaSight Walkthrough

**Series**: SigmaSight in Action (Part 2 of 5)
**Reading Time**: 6 minutes
**Target Audience**: New SigmaSight users, prospective users

---

## What You'll Learn

In this walkthrough, we'll take a real portfolio through SigmaSight's factor analysis. By the end, you'll understand:

- How to read your factor exposure dashboard
- What positive and negative exposures actually mean
- How to compare your portfolio to benchmarks
- How to identify unintended bets
- What actions to consider based on your exposures

Let's dive in.

---

## Step 1: Connecting Your Portfolio

After logging into SigmaSight, you'll import your holdings. You can:

- **Connect your broker** (Schwab, Fidelity, TD Ameritrade, etc.) for automatic sync
- **Upload a CSV** with your positions
- **Manual entry** for custom portfolios

For this walkthrough, we'll use a sample portfolio:

| Position | Shares | Market Value | Weight |
|----------|--------|--------------|--------|
| Apple (AAPL) | 150 | $28,500 | 14.3% |
| Microsoft (MSFT) | 80 | $33,600 | 16.8% |
| Amazon (AMZN) | 60 | $11,400 | 5.7% |
| JPMorgan (JPM) | 100 | $19,500 | 9.8% |
| Johnson & Johnson (JNJ) | 120 | $18,600 | 9.3% |
| Nvidia (NVDA) | 40 | $21,600 | 10.8% |
| Vanguard Total Bond (BND) | 200 | $15,400 | 7.7% |
| Berkshire Hathaway (BRK.B) | 50 | $22,500 | 11.3% |
| Coca-Cola (KO) | 150 | $9,000 | 4.5% |
| Home Depot (HD) | 50 | $19,900 | 10.0% |

**Total Portfolio Value**: $200,000

This looks like a "diversified" portfolio—10 positions across different sectors, plus some bonds. But what does factor analysis reveal?

---

## Step 2: The Factor Exposure Dashboard

Once your portfolio loads, SigmaSight calculates factor exposures within seconds. Here's what our sample portfolio shows:

### Factor Exposure Summary

| Factor | Your Exposure | S&P 500 | Difference |
|--------|---------------|---------|------------|
| **Beta (Market)** | 0.95 | 1.00 | -0.05 |
| **Size (SMB)** | -0.22 | -0.15 | -0.07 |
| **Value (HML)** | +0.18 | +0.02 | +0.16 |
| **Momentum (UMD)** | +0.08 | +0.05 | +0.03 |
| **Quality (QMJ)** | +0.25 | +0.10 | +0.15 |
| **Volatility** | 14.2% | 16.5% | -2.3% |

Let's decode what each of these means.

---

## Step 3: Understanding Each Exposure

### Beta: 0.95

**What it means**: Your portfolio moves about 95% as much as the market. When the S&P 500 goes up 10%, you'd expect roughly 9.5% gain. When it drops 10%, roughly 9.5% loss.

**Why it's this way**: The bond allocation (BND at 7.7%) and defensive holdings (JNJ, KO) reduce overall market sensitivity below 1.0.

**Is this good?** Depends on your goals. Slightly defensive—you'll underperform in strong bull markets but lose less in crashes.

### Size: -0.22

**What it means**: Negative exposure means you're tilted toward **large caps**. Your holdings are bigger companies than market average.

**Why it's this way**: Apple, Microsoft, Amazon, Nvidia, Berkshire—these are among the largest companies in the world. No small caps in the portfolio.

**Is this good?** You're missing the historical small cap premium (~2% annually). But large caps are less volatile. Trade-off.

### Value: +0.18

**What it means**: Positive exposure means you're tilted toward **cheaper stocks** (value) rather than expensive stocks (growth).

**Why it's this way**: JPMorgan, Berkshire, Coca-Cola, and Home Depot are all reasonably priced on traditional metrics. They offset the expensive tech names.

**Is this good?** You have meaningful value exposure—you'll benefit if value outperforms (as it did in 2022). But you'll lag if growth keeps winning.

### Momentum: +0.08

**What it means**: Slight positive exposure to recent winners. Your portfolio has some stocks that have been going up recently.

**Why it's this way**: Nvidia and Apple have had strong recent performance. But the portfolio isn't chasing momentum aggressively.

**Is this good?** Low momentum exposure is generally safer—you're not too exposed to a momentum crash.

### Quality: +0.25

**What it means**: Strong positive exposure to high-quality companies—profitable, stable, low leverage.

**Why it's this way**: Apple, Microsoft, JNJ, Coca-Cola, Home Depot, Berkshire—all highly profitable with strong balance sheets. Very few speculative names.

**Is this good?** Excellent for downside protection. Quality tends to outperform during market stress. This portfolio should hold up relatively well in a crash.

### Volatility: 14.2%

**What it means**: Your portfolio's expected annualized volatility is 14.2%—lower than the S&P 500's 16.5%.

**Why it's this way**: The bond allocation, defensive stocks, and high quality tilt all reduce volatility.

**Is this good?** Lower volatility means smoother ride but potentially lower returns. You're giving up some upside for stability.

---

## Step 4: The Factor Exposure Visualization

SigmaSight displays your exposures visually:

```
                    YOUR PORTFOLIO vs S&P 500

Beta      ████████████████████░░░░  0.95 (Market: 1.00)
Size      ██████░░░░░░░░░░░░░░░░░░  -0.22 (Large Cap Tilt)
Value     ████████████████████████  +0.18 (Value Tilt)
Momentum  ██████████░░░░░░░░░░░░░░  +0.08 (Neutral)
Quality   ██████████████████████████████  +0.25 (Quality Tilt)

Legend: █ = Your exposure   ░ = Below benchmark
```

At a glance, you can see:
- **Slightly defensive** (beta below 1)
- **Large cap focused** (negative size)
- **Value tilted** (positive HML)
- **Quality focused** (strong positive)

---

## Step 5: Position-Level Factor Contribution

Which positions are driving these exposures? SigmaSight breaks it down:

### Positions Driving Value Exposure
| Position | Value Contribution |
|----------|-------------------|
| JPMorgan (JPM) | +0.08 |
| Berkshire (BRK.B) | +0.05 |
| Coca-Cola (KO) | +0.03 |
| Home Depot (HD) | +0.02 |

### Positions Driving Quality Exposure
| Position | Quality Contribution |
|----------|---------------------|
| Microsoft (MSFT) | +0.07 |
| Apple (AAPL) | +0.05 |
| Johnson & Johnson (JNJ) | +0.05 |
| Coca-Cola (KO) | +0.04 |
| Berkshire (BRK.B) | +0.04 |

### Positions Increasing Volatility
| Position | Volatility Contribution |
|----------|------------------------|
| Nvidia (NVDA) | +2.8% |
| Amazon (AMZN) | +1.2% |
| Apple (AAPL) | +1.1% |

**Insight**: Nvidia alone contributes nearly 20% of portfolio volatility despite being only 10.8% of the portfolio. High-volatility positions punch above their weight.

---

## Step 6: Identifying Unintended Bets

Now the key question: **Are these exposures intentional?**

### Potentially Unintended Bets in This Portfolio

**1. Large Cap Concentration**
- No small cap exposure at all
- Missing ~2% historical annual premium
- All eggs in mega-cap basket

*Question to ask yourself*: Did you intentionally avoid small caps, or did it happen by accident?

**2. High Quality Tilt**
- Strong quality exposure (+0.25)
- Will underperform in "junk rallies" off market bottoms
- Trade-off for downside protection

*Question to ask yourself*: Are you okay underperforming during market recoveries in exchange for crash protection?

**3. Nvidia Concentration Risk**
- 10.8% of portfolio value
- 20% of portfolio volatility
- Single-stock risk in a volatile name

*Question to ask yourself*: Is this position sized appropriately for its volatility?

---

## Step 7: Comparing to Your Goals

SigmaSight helps you evaluate whether your exposures match your objectives:

### If Your Goal Is: **Maximum Growth**
- **Issue**: Beta is below 1.0, quality is high, volatility is low
- **Your portfolio is more defensive than optimal for growth**
- Consider: Reducing bond allocation, adding high-beta names

### If Your Goal Is: **Wealth Preservation**
- **Alignment**: Low beta, high quality, lower volatility—all aligned
- **Your portfolio is well-positioned for defense**
- Consider: This is working. Maybe add more bonds for even lower volatility.

### If Your Goal Is: **Factor Diversification**
- **Issue**: Missing small cap exposure entirely
- **Gap in factor diversification**
- Consider: Adding a small cap value allocation (10-15%)

---

## Step 8: Taking Action

Based on this analysis, here are potential actions:

### Option 1: Do Nothing
Your portfolio is reasonably constructed. Slightly defensive with quality tilt. If this matches your goals, no changes needed.

### Option 2: Add Small Cap Exposure
Sell 10% of large cap positions, buy a small cap value ETF (like VBR). This would:
- Add the missing size factor
- Increase value tilt
- Add factor diversification

### Option 3: Reduce Nvidia Concentration
Trim Nvidia from 10.8% to 5%. Reallocate to:
- Broader tech exposure (QQQ), or
- Defensive positions (more JNJ, KO)

This reduces single-stock risk without abandoning tech exposure.

### Option 4: Increase/Decrease Defense
- More defensive? Add bonds, reduce beta
- More aggressive? Reduce bonds, add growth

---

## Key Takeaways

After this walkthrough, you now understand:

1. **Factor exposures tell you more than sector allocations** — Knowing you have 15% tech is less useful than knowing your beta is 0.95 and quality is +0.25

2. **Every portfolio has hidden tilts** — This "balanced" portfolio has meaningful value and quality tilts that will affect performance

3. **Position sizing matters for volatility** — A 10% position can contribute 20% of risk if it's highly volatile

4. **Factor exposures should match goals** — A growth-oriented investor shouldn't have low beta and high quality

5. **SigmaSight makes this visible** — What took professionals hours now takes seconds

---

## Your Turn

Ready to see what your portfolio really looks like?

1. Log into SigmaSight
2. Connect or upload your holdings
3. Review your factor exposures
4. Compare to benchmarks
5. Identify any unintended bets

**The first step to better investing is understanding what you actually own.**

---

*[Analyze Your Portfolio Now →]*

---

**Next**: [Are Your Stocks Really Diversified? How to Find Out →]
