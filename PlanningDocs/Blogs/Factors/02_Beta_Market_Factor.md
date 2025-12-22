# Beta: The One Number Every Investor Should Know

**Series**: What is Factor Investing? (Part 2 of 8)
**Reading Time**: 7 minutes
**Target Audience**: Sophisticated individual investors, HNWIs

---

## What Is Beta?

If you could only know one thing about your portfolio's risk, it should be beta.

Beta measures how sensitive your portfolio is to market movements. It answers a simple question: **When the market moves 1%, how much does my portfolio move?**

- **Beta = 1.0**: Your portfolio moves in lockstep with the market
- **Beta > 1.0**: Your portfolio is more volatile than the market (aggressive)
- **Beta < 1.0**: Your portfolio is less volatile than the market (defensive)

That's it. That's the core concept. But the implications are profound.

---

## Beta in Action: Real Numbers

Let's make this concrete with examples:

| Stock | Beta | Interpretation |
|-------|------|----------------|
| Utilities ETF (XLU) | 0.4 | Very defensive—moves 40% as much as market |
| Johnson & Johnson | 0.6 | Defensive—moves 60% as much as market |
| S&P 500 Index | 1.0 | The benchmark (by definition) |
| Apple | 1.2 | Somewhat aggressive |
| Tesla | 2.0 | Very aggressive—moves 2x the market |
| ARK Innovation ETF | 1.8 | Aggressive growth basket |

Now imagine a day when the S&P 500 drops 3%:

- **XLU** (beta 0.4): Expected drop of ~1.2%
- **Johnson & Johnson** (beta 0.6): Expected drop of ~1.8%
- **Apple** (beta 1.2): Expected drop of ~3.6%
- **Tesla** (beta 2.0): Expected drop of ~6.0%

On the flip side, when the market rises 3%:

- **XLU**: Expected gain of ~1.2%
- **Tesla**: Expected gain of ~6.0%

**Beta is a double-edged sword.** High beta amplifies gains AND losses.

---

## Your Portfolio Beta: What It Really Means

Individual stock betas are interesting, but what matters is your **portfolio beta**—the weighted average beta of all your holdings.

Here's why this matters:

### Scenario 1: The "Diversified" Growth Investor

Sarah thinks she's diversified. She owns:
- 20% Amazon (beta 1.3)
- 20% Nvidia (beta 1.8)
- 20% Microsoft (beta 1.1)
- 20% Google (beta 1.2)
- 20% Meta (beta 1.4)

Five different companies, five different businesses. Diversified, right?

**Portfolio beta: 1.36**

Sarah is taking 36% more market risk than the S&P 500. In a 20% market correction, she should expect to lose approximately 27%. That's not diversification—that's concentration in high-beta tech.

### Scenario 2: The Defensive Retiree

Tom, a retiree, wants stable income. He owns:
- 30% Vanguard Dividend ETF (beta 0.85)
- 25% Utilities ETF (beta 0.4)
- 25% Consumer Staples ETF (beta 0.65)
- 20% Treasury bonds (beta ~0)

**Portfolio beta: 0.48**

Tom will capture less than half of market gains. But he'll also experience less than half of market losses. In a 20% correction, he might only lose 9-10%. For a retiree who can't afford to wait for recovery, this makes sense.

### Scenario 3: The Unaware Investor

Mike "diversified" by buying whatever his friends recommended:
- 15% Tesla (beta 2.0)
- 15% AMD (beta 1.7)
- 15% Shopify (beta 1.9)
- 15% Netflix (beta 1.4)
- 15% SPY index fund (beta 1.0)
- 15% Berkshire Hathaway (beta 0.9)
- 10% Cash (beta 0)

Mike thinks he's balanced because he has some index funds and Berkshire. But:

**Portfolio beta: 1.32**

Mike is taking significantly more risk than he realizes. The "safe" SPY and Berkshire holdings barely move the needle against his high-beta growth stocks.

---

## The Math: How Beta Is Calculated

You don't need to calculate beta yourself—SigmaSight does it automatically. But understanding the concept helps:

Beta is calculated using regression analysis. We look at historical returns of a stock versus returns of the market (usually S&P 500) and measure the relationship.

```
Stock Return = Alpha + Beta × Market Return + Error
```

The beta coefficient tells us the sensitivity. If beta = 1.5, then historically, when the market returned 1%, the stock returned 1.5% (on average).

**Important caveats:**
- Beta is calculated from historical data, usually 2-5 years
- Past beta doesn't guarantee future beta (but it's a good guide)
- Beta can change as companies evolve
- Short-term beta can differ from long-term beta

---

## Common Misconceptions About Beta

### Misconception 1: "Beta = Risk"

Not quite. Beta measures **systematic risk**—the risk that comes from being invested in the market at all. It doesn't capture:

- **Company-specific risk**: Fraud, product failures, management disasters
- **Sector risk**: Regulation changes affecting one industry
- **Factor risks**: Value/growth rotations, momentum crashes

A stock can have beta of 1.0 and still be very risky if it has high company-specific risk.

### Misconception 2: "Low Beta = Safe"

Low beta means less sensitive to market moves. But "the market" might not be your main risk.

In 2022, bond funds (very low beta to stocks) got crushed because interest rates spiked. Beta to the stock market was low. Risk was high.

### Misconception 3: "High Beta = Better Long-Term Returns"

The textbook says investors should be compensated for taking more risk. In practice, **high-beta stocks have historically underperformed** on a risk-adjusted basis.

This is called the "low volatility anomaly"—one of the most persistent findings in finance. We'll cover it later in this series.

### Misconception 4: "Beta Is Constant"

Beta changes over time. Tesla's beta was much higher five years ago when it was smaller and less established. As companies mature, beta often declines.

This is why SigmaSight calculates rolling beta, showing you how your exposure has changed over time.

---

## How to Use Beta in Your Portfolio

### Step 1: Know Your Number

First, find out your portfolio beta. This single number tells you more about your risk than any pie chart.

With SigmaSight, you see this immediately on your dashboard. Without it, you'd need to calculate the weighted average beta of all positions manually.

### Step 2: Decide If It's Right For You

There's no universally "correct" beta. It depends on:

**Time horizon**: Longer horizon → can tolerate higher beta
**Income needs**: Need to withdraw soon → lower beta
**Risk tolerance**: Honest assessment of how you'll react to drops
**Other assets**: Real estate, pension, business → can offset portfolio beta

A 30-year-old saving for retirement in 35 years might be fine with beta of 1.2-1.3.

A 65-year-old living off their portfolio might want beta of 0.5-0.8.

### Step 3: Adjust If Needed

If your beta is too high:
- Add defensive sectors (utilities, consumer staples, healthcare)
- Add bonds or cash
- Reduce concentrated positions in high-beta stocks

If your beta is too low (for your goals):
- Reduce cash allocation
- Tilt toward growth sectors
- Consider small caps (higher beta)

### Step 4: Monitor Over Time

Beta isn't set-and-forget. As markets move and positions change, your portfolio beta drifts. A position that was 10% of your portfolio might grow to 20% after a big run—changing your beta.

SigmaSight tracks this automatically, alerting you when your risk profile shifts significantly.

---

## Beta During Market Stress

Here's where beta really matters: **during crashes**.

In calm markets, beta differences feel small. Whether your portfolio is up 1.1% or 0.9% on a day the market gains 1%—who cares?

But in a crisis:

| Market Drop | Beta 0.7 | Beta 1.0 | Beta 1.5 |
|-------------|----------|----------|----------|
| -10% | -7% | -10% | -15% |
| -20% | -14% | -20% | -30% |
| -30% | -21% | -30% | -45% |
| -40% | -28% | -40% | -60% |

A 40% market crash (think 2008-2009) turns into a 60% wipeout for a high-beta portfolio. That's the difference between being down $400,000 versus $600,000 on a $1 million portfolio.

**Beta matters most when markets matter most.**

---

## SigmaSight Feature: Portfolio Beta Analysis

When you connect your portfolio to SigmaSight, you immediately see:

1. **Current Portfolio Beta**: Your weighted-average beta versus S&P 500
2. **Beta Contribution by Position**: Which holdings are driving your beta
3. **Historical Beta Trend**: How your beta has changed over time
4. **Scenario Analysis**: Expected portfolio move for different market scenarios
5. **Beta vs. Benchmarks**: How your beta compares to common indices

You'll never have to wonder why your portfolio dropped more than the market. You'll know—and you'll know before it happens.

---

## Key Takeaways

1. **Beta measures market sensitivity**—how much your portfolio moves when the market moves
2. **Portfolio beta is what matters**, not individual stock betas
3. **High beta amplifies gains AND losses**—it's not free returns
4. **Know your number**—it's the single most important risk metric
5. **There's no "right" beta**—it depends on your situation and goals
6. **Beta matters most in crashes**—when you can least afford surprises

---

*Want to know your portfolio beta? [Connect your portfolio to SigmaSight →]*

---

**Up Next**: [Small Caps vs. Large Caps: More Than Just Company Size →]
