# Ask Your Portfolio Anything: SigmaSight's AI Analyst

**Series**: SigmaSight in Action (Part 5 of 5)
**Reading Time**: 6 minutes
**Target Audience**: All SigmaSight users

---

## Your Personal Portfolio Analyst

Imagine having a portfolio analyst available 24/7.

Someone who knows every position you own. Who can instantly calculate factor exposures, correlation impacts, and risk metrics. Who can explain complex concepts in plain English and answer any question about your investments.

That's what SigmaSight's AI Analyst provides.

No more digging through dashboards trying to find insights. No more wondering what some metric actually means. Just ask your question and get an intelligent, data-driven answer.

---

## How It Works

The AI Analyst is built on advanced language models combined with real-time access to your portfolio data. When you ask a question:

1. **The AI understands your intent** — Natural language processing interprets what you're really asking
2. **It accesses your live portfolio** — Current positions, factor exposures, correlations, risk metrics
3. **It performs relevant calculations** — On-the-fly analysis specific to your question
4. **It explains clearly** — Plain English answers with supporting data

You're not searching through menus or learning query languages. You're having a conversation.

---

## What You Can Ask

### Category 1: Portfolio Understanding

**"Why did my portfolio drop more than the market yesterday?"**

> Your portfolio dropped 2.3% while the S&P 500 fell 1.8%. This is explained by your factor exposures:
>
> - **Beta of 1.15**: Your portfolio is 15% more sensitive to market moves
> - **Growth tilt**: Growth stocks fell 2.5% yesterday, and your HML exposure is -0.25
> - **Nvidia contributed 0.4%** of your loss despite being 10% of the portfolio
>
> In short: Your above-market beta and growth tilt amplified yesterday's market decline.

**"What's driving my returns this month?"**

> Your portfolio is up 4.2% this month. Here's the breakdown:
>
> - **Market exposure (beta)**: +3.1% (market up 2.7% × your 1.15 beta)
> - **Factor tilts**: +0.8% (value outperforming, you have +0.15 value exposure)
> - **Stock selection**: +0.3% (your specific stocks slightly outperformed factor expectations)
>
> Most of your return came from market exposure. Your value tilt added modestly.

### Category 2: Factor Analysis

**"What are my biggest factor bets?"**

> Your most significant factor exposures:
>
> 1. **Quality (+0.28)**: Strong tilt toward profitable, stable companies
> 2. **Value (+0.18)**: Moderate tilt toward cheaper stocks
> 3. **Size (-0.22)**: Strong tilt toward large caps (negative = large cap)
>
> Notable: You have almost no momentum exposure (0.03), which is good for avoiding crash risk but means you're not participating in recent winners.

**"How does my value exposure compare to a typical value investor?"**

> Your value exposure (HML) is +0.18. Here's context:
>
> - **S&P 500**: +0.02 (nearly neutral)
> - **Vanguard Value ETF (VTV)**: +0.42
> - **DFA US Large Value**: +0.55
>
> You have meaningful value exposure—more than the index—but less than dedicated value funds. This is a moderate value tilt, not a concentrated value bet.

### Category 3: Risk Assessment

**"How risky is my portfolio?"**

> Here's your risk profile:
>
> - **Volatility**: 14.8% annualized (vs. 16.2% for S&P 500)
> - **Beta**: 0.95 (slightly below market)
> - **Maximum drawdown (historical)**: -32% (vs. -34% for S&P)
> - **Diversification score**: 58/100 (moderately diversified)
>
> Overall: You're taking slightly less risk than the market. Your quality tilt and bond allocation provide some defense. However, 42% tech exposure creates concentration risk in that sector.

**"What would happen to my portfolio if rates rose 1%?"**

> Based on your positions' interest rate sensitivity:
>
> - **Expected portfolio impact**: -3.2%
> - **Most affected**: Your bond allocation (BND: -5.5%)
> - **Also affected**: High-duration growth stocks (NVDA: -4%, AMZN: -3%)
> - **Partially offset**: Financials benefit from higher rates (JPM: +2%)
>
> Your portfolio is moderately rate-sensitive. The bond allocation increases this sensitivity, but financials provide partial hedge.

### Category 4: Position-Specific Questions

**"Should I be worried about my Nvidia position?"**

> Here's the analysis on your Nvidia (NVDA) position:
>
> **Position size**: 10.8% of portfolio
> **Risk contribution**: 18.2% of portfolio volatility (disproportionately high)
>
> **Concerns**:
> - Single-stock concentration in a volatile name
> - Contributes more risk than its weight suggests
> - Highly correlated with your other tech positions
>
> **Positives**:
> - Strong momentum (+45% YTD)
> - Quality metrics are good (high margins, low debt)
>
> **Suggestion**: Consider whether 10.8% matches your conviction. A 5-7% position would still provide meaningful exposure with less concentration risk.

**"Which positions are most correlated with each other?"**

> Your highest correlation pairs:
>
> 1. **Apple ↔ Microsoft**: 0.78
> 2. **Microsoft ↔ Nvidia**: 0.74
> 3. **Apple ↔ Nvidia**: 0.71
> 4. **Microsoft ↔ Home Depot**: 0.52 (surprisingly high for different sectors)
>
> Your tech positions (AAPL, MSFT, NVDA) form a correlation cluster. They'll move together in most scenarios, limiting diversification benefit among them.

### Category 5: What-If Scenarios

**"What if I sold half my Nvidia and bought bonds?"**

> Simulating: Sell 5.4% NVDA, buy 5.4% BND
>
> **Before → After**:
> - Beta: 0.95 → 0.88
> - Volatility: 14.8% → 13.1%
> - 2008 stress loss: -48% → -43%
> - Expected return: Slightly lower (bonds yield less than equity)
>
> This change would meaningfully reduce risk. You'd give up some upside in exchange for more stability and crash protection.

**"How would adding small cap value change my factor profile?"**

> Simulating: Add 10% allocation to small cap value (VBR), funded equally from existing positions
>
> **Factor changes**:
> - Size: -0.22 → -0.08 (more balanced)
> - Value: +0.18 → +0.26 (stronger value tilt)
> - Diversification score: 58 → 64 (improvement)
>
> This would address your current large cap concentration and add the historically highest-returning segment (small cap value). Trade-off: Higher volatility.

### Category 6: Educational Questions

**"What is beta, exactly?"**

> Beta measures how sensitive your portfolio is to market movements.
>
> - **Beta = 1.0**: Moves exactly with the market
> - **Beta > 1.0**: More volatile than market (moves more, both up and down)
> - **Beta < 1.0**: Less volatile than market (moves less)
>
> Your portfolio beta is 0.95. This means if the market rises 10%, you'd expect to rise about 9.5%. If it falls 10%, you'd expect to fall about 9.5%.
>
> Beta below 1.0 is considered defensive. You'll lag in strong bull markets but lose less in corrections.

**"Why does factor diversification matter?"**

> Factor diversification matters because stocks can move together due to shared factor exposures, not just sector similarities.
>
> Example: A tech stock and a retail stock might seem diversified (different sectors). But if they're both high-beta, small-cap, growth stocks, they share three factor exposures. They'll often move together despite the sector difference.
>
> True diversification requires diversifying across factors (beta, size, value, momentum, quality)—not just across sectors or stock names.
>
> Your portfolio is well-diversified on quality and value, but concentrated in large cap and high beta.

---

## Pro Tips for Using the AI Analyst

### Be Specific

❌ "Tell me about my portfolio"
✅ "What are my three biggest risk exposures?"

### Ask Follow-Ups

First: "Why did I underperform this week?"
Then: "Which position contributed most to that underperformance?"
Then: "Should I reduce that position?"

### Request Comparisons

✅ "How does my volatility compare to the S&P 500?"
✅ "Is my value exposure higher or lower than Berkshire Hathaway?"

### Ask for Explanations

✅ "Explain my factor exposures like I'm new to investing"
✅ "What does a negative size factor mean in plain English?"

### Test Scenarios

✅ "What would happen if I rebalanced to equal weight?"
✅ "How would selling my bottom 3 performers affect my factor profile?"

---

## Limitations to Understand

### It's Analysis, Not Advice

The AI Analyst provides data-driven insights, not personalized financial advice. It can tell you your risk exposures but can't tell you if those exposures are right for your specific situation.

### It Uses Historical Data

Factor sensitivities and correlations are based on historical relationships. These generally persist but can change over time.

### It's Not a Crystal Ball

The AI can stress test and analyze but can't predict future market movements. Use it for understanding and preparation, not prediction.

### Complex Situations Need Humans

For tax optimization, estate planning, or highly personalized situations, human advisors add value the AI can't replicate.

---

## Getting Started

Using the AI Analyst is simple:

1. **Connect your portfolio** (if you haven't already)
2. **Click the chat icon** in SigmaSight
3. **Type your question** in plain English
4. **Read the response** and ask follow-ups

No special syntax. No query language. Just ask what you want to know.

---

## Key Takeaways

1. **Natural language interface** — Ask questions in plain English

2. **Real-time portfolio access** — Answers based on your actual holdings

3. **On-demand calculations** — Factor analysis, stress tests, correlations

4. **Educational support** — Learn concepts while analyzing your portfolio

5. **What-if scenarios** — Test changes before making them

6. **Always available** — 24/7 access to portfolio intelligence

---

## Your Questions Answered

What's the first question you want to ask about your portfolio?

Log in to SigmaSight and find out. The AI Analyst is ready.

---

*[Start Asking Questions →]*

---

**Series Complete!**

You've now explored all five SigmaSight capabilities:
1. What SigmaSight Is
2. Understanding Factor Exposures
3. Correlation Analysis
4. Stress Testing
5. AI Analyst

Ready to see your portfolio the way professionals do?

**[Get Started with SigmaSight →]**
