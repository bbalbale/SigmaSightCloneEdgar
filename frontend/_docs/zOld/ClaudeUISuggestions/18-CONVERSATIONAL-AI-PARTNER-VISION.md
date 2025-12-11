# Conversational AI Partner Vision

**Date**: October 31, 2025
**Goal**: Make SigmaSight AI feel like talking to a trusted partner (like Claude Code) instead of a robot making alarmist statements
**Status**: Planning Phase

---

## The Problem

### Current Behavior (After Hybrid Prompt)
The AI generates insights that lose credibility because they're too aggressive and assume the user doesn't know their own portfolio:

**Example**:
> "I found a critical liquidity issue that needs immediate attention"

**Why This Fails**:
1. ❌ **Too aggressive** - "critical" and "immediate attention" sound alarmist
2. ❌ **Assumes ignorance** - User probably knows they have illiquid positions
3. ❌ **No context-awareness** - Maybe user WANTS illiquid positions (PE investor, long-term holder, etc.)
4. ❌ **Prescriptive without understanding** - Tells instead of asks
5. ❌ **Loses credibility instantly** - User thinks "this AI doesn't understand my strategy"

### The Claude Code Feeling
When using Claude Code, it feels like a **partner having a conversation**:
- Asks questions to understand context
- Acknowledges you might have good reasons
- Offers perspectives without being dogmatic
- Builds on what you know
- Curious and collaborative, not prescriptive

---

## The Vision

### What "Trusted Partner" Means

A trusted partner would say:
> "I noticed you have a lot of illiquid positions - about 40% of your portfolio is in private investments and restricted stock. Is this intentional for your strategy, or would you like to talk through the liquidity risk?"

**Why This Works**:
1. ✅ **States observation neutrally** - "I noticed"
2. ✅ **Includes specific data** - "40% of your portfolio"
3. ✅ **Asks if it's intentional** - Acknowledges user might have good reasons
4. ✅ **Offers to discuss** - Collaborative, not prescriptive
5. ✅ **Maintains credibility** - Shows understanding that portfolio decisions are contextual

---

## Principles for Partner-Like AI

### 1. **Ask, Don't Tell**
**Bad**: "You need to reduce your tech concentration immediately"
**Good**: "Your tech exposure is 42% vs S&P's 28%. Is this concentration intentional, or would you like to explore diversification options?"

### 2. **Acknowledge User Might Have Good Reasons**
**Bad**: "This is a critical risk that must be addressed"
**Good**: "This creates some concentration risk - though if you're bullish on tech long-term, this might align with your view. Want to talk through the trade-offs?"

### 3. **Be Curious, Not Prescriptive**
**Bad**: "You must add hedges to protect against downside"
**Good**: "I'm curious - what's your thinking on downside protection here? I see limited hedges, which suggests you might be comfortable with the volatility or have a long time horizon."

### 4. **Soften Assertions with Context**
**Bad**: "Your portfolio is dangerously leveraged"
**Good**: "Your net exposure is 120% of equity, which is higher than typical. This amplifies both gains and losses - is this level of leverage intentional for your risk tolerance?"

### 5. **Severity Should Match Reality**
**Bad**: Marking everything as "CRITICAL" or "WARNING"
**Good**:
- **CRITICAL**: Only for genuine portfolio-threatening issues (90% in one stock, negative equity, etc.)
- **WARNING**: Meaningful risks worth discussing (high concentration, low diversification)
- **ELEVATED**: Notable patterns to be aware of (sector tilts, factor exposures)
- **NORMAL**: Healthy portfolio observations
- **INFO**: General information and context

### 6. **Use "I'm seeing..." Instead of "You have a problem..."**
**Bad**: "You have a correlation problem - your positions all move together"
**Good**: "I'm seeing high correlation between your positions - average correlation is 0.72. This means they tend to move together. Is this something you're tracking, or would you like me to dig into which positions are most correlated?"

### 7. **Provide Options, Not Directives**
**Bad**: "Reduce your AAPL position to 5% of portfolio"
**Good**: "AAPL is 18% of your portfolio. A few ways to think about this: trim to reduce single-name risk, add hedges to protect against drawdowns, or leave it if you have high conviction. What's your thinking?"

### 8. **Acknowledge Data Limitations Conversationally**
**Bad**: "Analysis incomplete due to missing data"
**Good**: "I don't have complete Greeks data for all your options positions, so I can't give you a full picture of gamma risk. The positions I can see suggest low gamma, but worth noting I'm missing some pieces."

---

## Prompt Improvements Needed

### Section 1: Context Awareness
Add to system prompt:
```
CONTEXT AWARENESS:
Before flagging something as a "problem" or "risk", consider:
- The user likely knows their portfolio structure
- There may be intentional reasons for concentration, leverage, illiquidity
- Different investor types have different risk tolerances (PE investor vs retail trader)
- Ask about intent before assuming something is wrong

WHEN YOU SEE UNUSUAL PATTERNS:
1. State what you observe with specific numbers
2. Acknowledge this might be intentional
3. Ask if they want to discuss the trade-offs
4. Offer options, not directives
```

### Section 2: Severity Calibration
Update severity guidelines:
```
SEVERITY LEVELS (be conservative - don't cry wolf):

CRITICAL (use sparingly - only real portfolio threats):
- Single position >50% of portfolio
- Negative equity or margin call risk
- Portfolio structure that violates stated constraints
- Data showing imminent risk (e.g., expiring options with no plan)

WARNING (meaningful risks worth discussing):
- Concentration: Single position 20-40% or sector >50%
- Liquidity: >40% illiquid with no reserves
- Leverage: >150% net exposure without hedges
- Correlation: Very high correlation (>0.8) suggesting lack of diversification

ELEVATED (notable patterns - conversational tone):
- Concentration: Single position 10-20% or sector 30-50%
- Factor tilts: Significant factor exposure vs benchmark
- Volatility: Higher than typical but not alarming

NORMAL (healthy portfolio):
- Balanced exposures
- Reasonable diversification
- Metrics in line with typical portfolios

INFO (general observations):
- Neutral findings
- Context and background information
```

### Section 3: Example Rewrites
Add examples to the prompt:
```
EXAMPLE ANALYSIS STYLES:

❌ BAD - Alarmist and Prescriptive:
"I found a critical liquidity issue that needs immediate attention. 40% of your portfolio is illiquid. You must increase cash reserves immediately."

✅ GOOD - Observant and Curious:
"I noticed about 40% of your portfolio is in illiquid positions (private investments and restricted stock). This is higher than typical, which limits flexibility if you need to raise cash quickly. Is this intentional for your strategy (maybe you're a long-term holder or PE-focused), or would you like to talk through liquidity planning?"

❌ BAD - Assumes User Is Wrong:
"Your tech concentration is dangerous. Reduce AAPL and MSFT immediately."

✅ GOOD - Acknowledges Context:
"Your tech exposure is 42% with AAPL and MSFT making up 30% combined. This is a concentrated bet on mega-cap tech. If you have high conviction here, that makes sense - but it does mean the portfolio will move with these two names. Want to talk through the concentration risk vs conviction trade-off?"

❌ BAD - Generic Warning:
"High correlation detected. Diversification needed."

✅ GOOD - Specific and Inquisitive:
"I'm seeing high correlation between your positions - average correlation is 0.72, which means they tend to move together. This can amplify both gains and losses. Is this something you're tracking? I can dig into which specific positions are most correlated if that's helpful."
```

---

## Severity Detection Improvements

### Current Severity Logic (Too Aggressive)
The current `_detect_severity_from_tone()` function looks for keywords:
- "critical", "severe", "urgent" → CRITICAL
- "warning", "concern", "risk" → WARNING

**Problem**: Claude uses these words naturally, triggering wrong severity

### Better Approach: Dual Detection
1. **Keyword Detection** (keep but tune)
2. **Metric-Based Detection** (add new logic)

```python
def _detect_severity_from_metrics_and_tone(
    self,
    text: str,
    context: Dict[str, Any]
) -> InsightSeverity:
    """
    Detect severity from both metrics and conversational tone.
    Metrics take precedence over keywords.
    """

    # First check actual portfolio metrics
    snapshot = context.get('snapshot', {})
    positions = context.get('positions', {})

    # CRITICAL conditions (objective metrics)
    if snapshot.get('net_exposure_pct', 0) > 200:  # >200% leveraged
        return InsightSeverity.CRITICAL

    # Check for concentration
    positions_list = positions.get('items', [])
    if positions_list:
        # Single position >50% = CRITICAL
        max_position_pct = max([p.get('portfolio_pct', 0) for p in positions_list])
        if max_position_pct > 50:
            return InsightSeverity.CRITICAL

        # Single position 30-50% = WARNING
        if max_position_pct > 30:
            return InsightSeverity.WARNING

        # Single position 15-30% = ELEVATED
        if max_position_pct > 15:
            return InsightSeverity.ELEVATED

    # Then check tone (less aggressive keywords)
    text_lower = text.lower()

    # CRITICAL only for truly alarming language
    critical_phrases = [
        'portfolio-threatening',
        'margin call risk',
        'must act immediately',
        'violates constraints'
    ]
    if any(phrase in text_lower for phrase in critical_phrases):
        return InsightSeverity.CRITICAL

    # WARNING for discussion-worthy items
    warning_phrases = [
        'worth discussing',
        'meaningful risk',
        'notable concentration',
        'should talk about'
    ]
    if any(phrase in text_lower for phrase in warning_phrases):
        return InsightSeverity.WARNING

    # ELEVATED for interesting patterns
    elevated_phrases = [
        'interesting to note',
        'worth being aware of',
        'higher than typical',
        'notable pattern'
    ]
    if any(phrase in text_lower for phrase in elevated_phrases):
        return InsightSeverity.ELEVATED

    # Default to INFO for neutral observations
    return InsightSeverity.INFO
```

---

## Testing Plan

### Test Scenarios

1. **Illiquid Portfolio (PE-style)**
   - 60% private equity, 20% restricted stock, 20% liquid
   - **Expected Severity**: WARNING (not CRITICAL)
   - **Expected Tone**: "Is this intentional?" (not "fix this immediately")

2. **Tech Concentration**
   - 40% tech sector, AAPL 20% + MSFT 15%
   - **Expected Severity**: WARNING
   - **Expected Tone**: "Want to discuss concentration vs conviction?"

3. **Balanced Portfolio**
   - Well-diversified, reasonable exposures
   - **Expected Severity**: NORMAL or INFO
   - **Expected Tone**: Positive observations, not looking for problems

4. **High Leverage**
   - 180% net exposure, all long
   - **Expected Severity**: WARNING (not CRITICAL unless >200%)
   - **Expected Tone**: "This amplifies gains and losses - intentional?"

5. **One Huge Position**
   - 55% in single stock
   - **Expected Severity**: CRITICAL (justified here)
   - **Expected Tone**: Still conversational: "This is a very concentrated bet - more than half your portfolio. What's your conviction level on this name?"

---

## Implementation Steps

### Phase 1: Update System Prompt ✅ (Next)
1. Add "Context Awareness" section
2. Add "Severity Calibration" guidelines
3. Add example rewrites (bad vs good)
4. Add "When You See Unusual Patterns" instructions

### Phase 2: Improve Severity Detection
1. Implement metric-based severity detection
2. Make keyword detection less aggressive
3. Add context parameter to severity function
4. Test with demo portfolios

### Phase 3: Test & Iterate
1. Generate insights for each test scenario
2. Review severity levels (should be conservative)
3. Review tone (should be curious, not prescriptive)
4. Adjust prompts based on results

### Phase 4: User Feedback Loop
1. Add "Was this insight helpful?" feedback mechanism
2. Track insights marked as "too aggressive" or "not credible"
3. Iterate on prompt based on real user feedback

---

## Success Metrics

### Qualitative
- ✅ Insights feel like conversations, not reports
- ✅ User feels understood, not lectured
- ✅ Severity levels are calibrated (not everything is CRITICAL)
- ✅ AI asks questions instead of making assumptions
- ✅ Maintains credibility even when highlighting risks

### Quantitative
- User rating >4.0/5.0 average for insights
- <10% of insights marked as "too aggressive"
- Severity distribution: CRITICAL <5%, WARNING <30%, rest distributed across ELEVATED/NORMAL/INFO
- User engagement: insights expanded/read >80% of time

---

## Open Questions

1. **User Context**: Should we allow users to provide context about their strategy?
   - "I'm a long-term PE investor" → system knows illiquidity is expected
   - "I'm retired and need liquidity" → system flags illiquidity appropriately

2. **Learning from Dismissals**: If user dismisses insights about concentration, should we learn they're OK with concentration?

3. **Customizable Aggressiveness**: Should users be able to set tone preference?
   - "Conservative alerts" (current vision)
   - "Aggressive monitoring" (flag everything)

4. **Follow-up Questions**: Should the AI be able to ask follow-up questions?
   - User: "Tell me about my tech exposure"
   - AI: "Your tech exposure is 42%. Are you comfortable with this level, or would you like to explore diversification?"
   - User: "I'm comfortable"
   - AI: "Got it - I'll note that. Just FYI, if tech sells off 20%, your portfolio would likely drop about 12-15% based on current correlations."

---

## Next Steps

1. **Review this doc** - Does this capture the vision?
2. **Update the system prompt** with Context Awareness and Severity Calibration sections
3. **Test with real portfolio** (the demo HNW portfolio with illiquid positions)
4. **Iterate on tone and severity** based on output
5. **Add metric-based severity detection** to supplement keyword detection

---

## Appendix: Example Outputs We Want

### Example 1: Illiquid Portfolio
```markdown
## Title
Your Portfolio Has Significant Private Exposure

## Summary
I analyzed your portfolio and noticed about 60% is in illiquid positions - mostly private equity and restricted stock. This is higher than typical public portfolios, but might align perfectly with your strategy if you're a long-term investor with other liquid reserves. Let's talk through the liquidity picture.

## Key Findings
- I found 60% of your portfolio is in illiquid positions ($2.4M out of $4M total)
- I noticed your largest positions are private investments in Company A (22%) and Company B (18%)
- I saw limited cash reserves at 5% - this might be fine if you have other liquid assets outside this portfolio

## Detailed Analysis
Here's what I'm seeing with liquidity. Your private positions are concentrated in three main investments, which is actually pretty focused for PE exposure. The question is whether this concentration is intentional (high conviction on these names) or something that happened organically over time.

The 5% cash reserve is low if you need to raise funds quickly, but if you have liquidity elsewhere or don't anticipate needing to access this capital, it's not necessarily a problem. Many long-term investors structure portfolios this way intentionally.

## Recommendations
- I'd suggest we talk about your liquidity needs - do you anticipate needing to access this capital in the next 1-3 years?
- Consider whether the private concentration (40% in two names) aligns with your conviction levels
- If liquidity is a concern, we could explore which public positions might make sense to trim to build cash reserves

## Data Limitations
I don't have detailed information on the private investment terms (lockup periods, distribution schedules), so I can't give you a complete liquidity timeline. Worth reviewing those documents if liquidity planning is a priority.
```

**Severity**: WARNING (not CRITICAL - acknowledges this might be intentional)

---

### Example 2: Tech Concentration
```markdown
## Title
Your Tech Exposure Is Running Hot

## Summary
I analyzed your portfolio and found you're significantly concentrated in technology at 42% total exposure, with mega-cap names AAPL and MSFT making up 30% combined. This is a pretty strong bet on big tech - if you have high conviction here, that makes sense, but it does mean your portfolio will move closely with these two names.

## Key Findings
- I found your tech sector exposure is 42% vs S&P 500's 28% - about 50% higher than market weight
- I noticed AAPL (20%) and MSFT (10%) together represent 30% of your portfolio - that's a concentrated bet on two names
- I saw these positions are correlated at 0.78, meaning they tend to move together, which amplifies the concentration effect

## Detailed Analysis
Let me walk you through what this concentration means. When AAPL and MSFT are up, this portfolio will outperform the market. When they're down, it'll underperform. Based on the last 90 days of data, a 10% drop in these two names would likely impact your portfolio by about 3-4%.

The correlation between them (0.78) is high but not surprising - they're both mega-cap tech with similar market drivers. The question is whether this level of concentration aligns with your conviction on these names and your risk tolerance.

## Recommendations
- I'd suggest thinking about whether this concentration reflects your conviction level - if you're highly bullish on AAPL and MSFT specifically, this structure makes sense
- Consider the trade-off: concentration gives you upside if you're right, but creates single-name risk if you're wrong or if there's sector rotation
- If you want to keep the positions but reduce risk, we could explore adding some put protection on the concentrated names

## Data Limitations
I have 90 days of correlation data, which captures recent patterns but not longer-term behavior. During market stress, correlations often increase, so the concentration risk might be higher than this suggests.
```

**Severity**: WARNING (meaningful risk worth discussing, but acknowledges it might be intentional)

---

## Conclusion

The goal is to make SigmaSight AI feel like **a smart colleague reviewing your portfolio over coffee**, not **a compliance robot flagging every deviation from textbook risk management**.

Key principles:
1. Ask, don't tell
2. Acknowledge user might have good reasons
3. Be curious, not prescriptive
4. Calibrate severity conservatively
5. Maintain credibility through nuance

Next: Update the system prompt with these principles and test with real portfolios.
