# Factor Exposure Hero Row Redesign

**Date**: 2025-11-17
**Component**: `FactorExposureHeroRow`
**Location**: `src/components/risk-metrics/FactorExposureHeroRow.tsx`
**Status**: Proposal

---

## Overview

Redesign the Factor Exposure Hero Row to provide educational commentary and rich explanations for each factor, similar to the existing Spread Factor Cards design. This will help users understand what each factor means and the implications for their portfolio.

---

## Current Design Issues

1. **Compact metric grid** - Limited space for explanations
2. **No context** - Users don't understand what beta values mean
3. **Inconsistent with Spread Cards** - Different visual treatment for similar data
4. **Not educational** - No guidance on factor implications

---

## Proposed Design

### ASCII Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Portfolio Factor Analysis                                                    │
│ Ridge regression factor betas (90-day) and long-short spread tilts (180-day)│
│                                                         As of Nov 17, 2025   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 Ridge Regression Factors (90-day window)                                 │
│ Disentangled factor exposures using ridge regression to isolate pure factor │
│ effects while controlling for correlations between factors                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐
│ Market Beta (1Y) │  │ Market Beta (90D)│  │ Momentum         │  │ Value    │
│                  │  │                  │  │                  │  │          │
│     +1.18        │  │     +1.23        │  │     +0.45        │  │  -0.18   │
│   ███████████    │  │   ████████████   │  │   ██████         │  │  ▓▓▓▓    │
│                  │  │                  │  │                  │  │          │
│ 🔵 High          │  │ 🔵 High          │  │ 🟢 Moderate      │  │ 🟡 Low   │
│ 📈 Long-term     │  │ 📈 Recent        │  │ 📊 Momentum Tilt │  │ 💰 Value │
│                  │  │                  │  │                  │  │          │
│ 1-year: Your     │  │ 90-day: +1.23    │  │ Positions with   │  │ Negative │
│ portfolio has    │  │ ⚠️ Recent HIGHER │  │ recent upward    │  │ tilt on  │
│ tracked market   │  │ than 1Y suggests │  │ momentum tend to │  │ cheap    │
│ closely. Beta of │  │ increasing       │  │ outperform when  │  │ stocks.  │
│ 1.18 = 18% more  │  │ volatility or    │  │ trends continue. │  │ May miss │
│ movement than    │  │ market exposure. │  │ Risk: Reversal   │  │ value    │
│ SPY.             │  │ Monitor closely. │  │ if fades.        │  │ recovery │
│                  │  │                  │  │                  │  │          │
│ $2.3M exposure   │  │ $2.4M exposure   │  │ $847K exposure   │  │ -$312K   │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐
│ Growth           │  │ Quality          │  │ Size             │  │ Low Vol  │
│     +0.62        │  │     +0.34        │  │     -0.22        │  │  +0.28   │
│   ████████       │  │   ███████        │  │   ▓▓▓▓▓          │  │  ██████  │
│                  │  │                  │  │                  │  │          │
│ 🟢 Moderate      │  │ 🟢 Moderate      │  │ 🟡 Low           │  │ 🟢 Mod.  │
│ 🚀 Growth Tilt   │  │ 💎 Quality Bias  │  │ 📉 Large Cap     │  │ 🛡️ Def.  │
│                  │  │                  │  │                  │  │          │
│ Tilted toward    │  │ Overweight in    │  │ Large cap bias.  │  │ Low-vol  │
│ high-growth      │  │ profitable,      │  │ More stable,     │  │ stocks.  │
│ companies.       │  │ stable firms     │  │ liquid, but may  │  │ Defensive│
│ Benefits in bull │  │ with strong      │  │ underperform in  │  │ in       │
│ markets. Higher  │  │ balance sheets.  │  │ small-cap        │  │ turmoil. │
│ valuation risk.  │  │ Defensive move.  │  │ rallies.         │  │          │
│                  │  │                  │  │                  │  │          │
│ $1.1M exposure   │  │ $623K exposure   │  │ -$489K exposure  │  │ $512K    │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────┘

┌──────────────────┐
│ IR Beta          │
│     -0.15        │
│   ▓▓▓            │
│                  │
│ 🟡 Low           │
│ 🏦 Rate Sens.    │
│                  │
│ Portfolio falls  │
│ when rates rise  │
│ (duration risk). │
│ Consider hedging │
│ if Fed tightens. │
│                  │
│ -$276K exposure  │
└──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📉 Long-Short Spread Factors (180-day window)                               │
│ Portfolio sensitivity to spread returns between long/short ETF pairs.        │
│ Captures style tilts through direct regression on spread returns.           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐
│ Growth-Value     │  │ Momentum Spread  │  │ Size Spread      │  │ Quality  │
│ Spread           │  │                  │  │                  │  │ Spread   │
│                  │  │                  │  │                  │  │          │
│     +0.58        │  │     +0.42        │  │     -0.19        │  │  +0.31   │
│   ████████       │  │   ███████        │  │   ▓▓▓▓           │  │  ██████  │
│                  │  │                  │  │                  │  │          │
│ 🟢 Moderate      │  │ 🟢 Moderate      │  │ 🟡 Weak          │  │ 🟢 Mod.  │
│ 🎯 Growth Bias   │  │ 📈 Momentum      │  │ 🏢 Large Cap     │  │ 💎 Qual. │
│                  │  │                  │  │                  │  │          │
│ VUG-VTV: +0.58   │  │ MTUM-SPY: +0.42  │  │ IWM-SPY: -0.19   │  │ QUAL-SPY │
│ Your portfolio   │  │ Portfolio tilted │  │ Negative spread  │  │ +0.31    │
│ captures 58% of  │  │ toward stocks    │  │ beta means       │  │ captures │
│ the pure growth  │  │ with strong      │  │ portfolio favors │  │ quality  │
│ premium over     │  │ recent price     │  │ large caps over  │  │ premium  │
│ value stocks.    │  │ momentum.        │  │ small caps.      │  │ over SPY │
│                  │  │                  │  │                  │  │          │
│ $1.05M exposure  │  │ $798K exposure   │  │ -$421K exposure  │  │ $587K    │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 💡 What's the Difference?                                                   │
│                                                                              │
│ Ridge Regression Factors (90-day):                                          │
│ • Disentangles correlated factors (e.g., Growth and Momentum)               │
│ • Isolates PURE factor exposure using statistical controls                  │
│ • Shows what happens when you change ONE factor, holding others constant    │
│ • Example: Growth beta shows growth effect independent of momentum          │
│                                                                              │
│ Spread Factors (180-day):                                                   │
│ • Direct regression on long-short ETF pair returns (e.g., VUG-VTV)         │
│ • Captures REALIZED spread return sensitivity                               │
│ • Shows how portfolio moves with actual market factor spreads               │
│ • Example: Growth-Value spread shows sensitivity to VUG outperforming VTV   │
│                                                                              │
│ Both are valuable! Ridge factors show pure exposures. Spreads show realized │
│ sensitivity to tradeable long-short strategies.                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Card Component Structure

### TypeScript Interface

```typescript
interface FactorCardProps {
  name: string
  beta: number
  exposure_dollar?: number
  explanation: string
  magnitude: 'Strong' | 'Moderate' | 'Weak'
  direction: 'Positive' | 'Negative' | 'Neutral'
  risk_level: 'low' | 'medium' | 'high'
  icon?: string  // Emoji for visual reference
}
```

### Visual Elements (Per Card)

1. **Header**: Factor name (e.g., "Market Beta (90D)")
2. **Beta value**: Large, prominent number (e.g., "+1.23")
3. **Progress bar**: Visual magnitude indicator
4. **Badges**:
   - Magnitude badge (Strong/Moderate/Weak)
   - Direction badge (Positive/Negative/Neutral)
5. **Icon/Emoji**: Quick visual reference
6. **Explanation**: 2-3 sentence description
7. **Dollar exposure**: If available (e.g., "$2.4M exposure")

---

## Factor Explanations & Commentary

### 1. Market Beta (90D)

**Icon**: 📈
**Name**: "Market Beta (90D)"

#### Magnitude Classification
- **Beta > 1.3**: "High - Amplified Market Moves"
- **Beta 0.8-1.2**: "Moderate - Tracks Market Closely"
- **Beta < 0.8**: "Low - Defensive Positioning"

#### Commentary Template
```
"Your portfolio moves {X}% {more/less} than the market.
{Higher/Lower} risk, {higher/lower} potential returns."

Additional context if Beta > 1.3:
"Consider hedging strategies during volatility."
```

#### Examples
- **Beta = 1.23**: "Your portfolio moves 23% more than the market. Higher risk, higher potential returns."
- **Beta = 0.85**: "Your portfolio moves 15% less than the market. Lower risk, more defensive positioning."

---

### 2. Momentum

**Icon**: 📊
**Name**: "Momentum"

#### Magnitude Classification
- **Beta > +0.3**: "Strong Momentum Tilt"
- **Beta +0.1 to +0.3**: "Moderate Momentum Tilt"
- **Beta -0.1 to +0.1**: "Momentum Neutral"
- **Beta < -0.1**: "Contrarian Positioning"

#### Commentary Templates

**Positive Beta** (> +0.1):
```
"Positions with recent upward momentum tend to outperform when trends continue.
Risk: Performance reversal if momentum fades."
```

**Negative Beta** (< -0.1):
```
"Contrarian bet on reversals. May underperform in strong trending markets
but capture value during mean reversion."
```

**Neutral** (-0.1 to +0.1):
```
"Balanced momentum exposure. Portfolio is neither chasing trends nor
betting on reversals."
```

---

### 3. Value

**Icon**: 💰
**Name**: "Value"

#### Magnitude Classification
- **Beta > +0.3**: "Strong Value Tilt"
- **Beta +0.1 to +0.3**: "Moderate Value Tilt"
- **Beta -0.1 to +0.1**: "Value Neutral"
- **Beta < -0.3**: "Strong Growth Tilt (Anti-Value)"

#### Commentary Templates

**Positive Beta** (> +0.1):
```
"Overweight in undervalued stocks with low P/E, P/B ratios.
Performs well when value premiums expand."
```

**Negative Beta** (< -0.1):
```
"Underweight in value stocks. May miss value recovery cycles
but avoids value traps."
```

**Neutral** (-0.1 to +0.1):
```
"Balanced value exposure. Portfolio has neutral positioning
between value and growth characteristics."
```

---

### 4. Growth

**Icon**: 🚀
**Name**: "Growth"

#### Magnitude Classification
- **Beta > +0.3**: "Strong Growth Tilt"
- **Beta +0.1 to +0.3**: "Moderate Growth Tilt"
- **Beta -0.1 to +0.1**: "Growth Neutral"
- **Beta < -0.3**: "Strong Value Tilt (Anti-Growth)"

#### Commentary Templates

**Positive Beta** (> +0.1):
```
"Tilted toward high-growth companies. Benefits in bull markets
and low-rate environments. Higher valuation risk."
```

**Negative Beta** (< -0.1):
```
"Defensive against growth stock corrections. May underperform
in strong risk-on rallies."
```

**Neutral** (-0.1 to +0.1):
```
"Balanced growth exposure. Portfolio has neutral positioning
between growth and value characteristics."
```

---

### 5. Quality

**Icon**: 💎
**Name**: "Quality"

#### Magnitude Classification
- **Beta > +0.3**: "High Quality Bias"
- **Beta +0.1 to +0.3**: "Moderate Quality Tilt"
- **Beta -0.1 to +0.1**: "Quality Neutral"
- **Beta < -0.3**: "Speculative Positioning"

#### Commentary Templates

**Positive Beta** (> +0.1):
```
"Overweight in profitable, stable companies with strong balance sheets.
Defensive during uncertainty."
```

**Negative Beta** (< -0.1):
```
"Exposure to higher-risk, lower-quality firms. Higher return potential
but elevated downside risk."
```

**Neutral** (-0.1 to +0.1):
```
"Balanced quality exposure. Portfolio has mix of high-quality
and speculative positions."
```

---

### 6. Size

**Icon**: 📏
**Name**: "Size"

#### Magnitude Classification
- **Beta > +0.3**: "Small Cap Tilt"
- **Beta +0.1 to +0.3**: "Moderate Small Cap Tilt"
- **Beta -0.1 to +0.1**: "Size Neutral"
- **Beta < -0.3**: "Large Cap Tilt"

#### Commentary Templates

**Positive Beta** (> +0.1):
```
"Overweight small caps (IWM vs SPY). Higher growth potential
but greater volatility and liquidity risk."
```

**Negative Beta** (< -0.1):
```
"Large cap bias. More stable, liquid, but may underperform
in small-cap rallies."
```

**Neutral** (-0.1 to +0.1):
```
"Balanced size exposure. Portfolio has mix of large and small
cap positions."
```

---

### 7. Low Volatility

**Icon**: 🛡️
**Name**: "Low Volatility"

#### Magnitude Classification
- **Beta > +0.3**: "Low Vol Tilt"
- **Beta +0.1 to +0.3**: "Moderate Low Vol Tilt"
- **Beta -0.1 to +0.1**: "Volatility Neutral"
- **Beta < -0.3**: "High Vol Tilt"

#### Commentary Templates

**Positive Beta** (> +0.1):
```
"Positioned in stable, low-volatility stocks. Defensive during
market turbulence. May lag in strong rallies."
```

**Negative Beta** (< -0.1):
```
"Exposure to higher-volatility names. Greater upside capture
but increased downside risk."
```

**Neutral** (-0.1 to +0.1):
```
"Balanced volatility exposure. Portfolio has mix of stable
and volatile positions."
```

---

### 8. IR Beta (Interest Rate)

**Icon**: 🏦
**Name**: "IR Beta"

#### Magnitude Classification
- **Beta > +0.3**: "Rate-Sensitive (Negative)"
- **Beta +0.1 to +0.3**: "Moderate Rate Sensitivity"
- **Beta -0.1 to +0.1**: "Rate Neutral"
- **Beta < -0.3**: "Rate-Beneficiary"

#### Commentary Templates

**Positive Beta** (> +0.1):
```
"Falls when rates rise (duration risk). Consider hedging if
Fed tightening expected."
```

**Negative Beta** (< -0.1):
```
"Benefits from rising rates (financials, value). Vulnerable
to rate cuts."
```

**Neutral** (-0.1 to +0.1):
```
"Balanced interest rate exposure. Portfolio has neutral
sensitivity to rate changes."
```

---

## Grid Layout

### Desktop (≥1024px)
- **Primary factors**: 4 columns (Market Beta, Momentum, Value, Growth)
- **Secondary factors**: 4 columns (Quality, Size, Low Vol, IR Beta)

### Tablet (768px - 1023px)
- **Primary factors**: 2 columns
- **Secondary factors**: 2 columns

### Mobile (<768px)
- **All factors**: 1 column

### Tailwind Classes
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* Factor cards */}
</div>
```

---

## Implementation Plan

### Step 1: Create FactorExposureCards Component

**File**: `src/components/risk-metrics/FactorExposureCards.tsx`

#### Features
- Individual card component for each factor
- Dynamic commentary based on beta value
- Progress bar visualization
- Badge system (magnitude + direction)
- Dollar exposure display
- Consistent with SpreadFactorCards design

### Step 2: Add Helper Functions

```typescript
// Determine magnitude from beta value
const getMagnitude = (beta: number): 'Strong' | 'Moderate' | 'Weak' => {
  const abs = Math.abs(beta)
  if (abs > 0.5) return 'Strong'
  if (abs > 0.2) return 'Moderate'
  return 'Weak'
}

// Determine direction
const getDirection = (beta: number): 'Positive' | 'Negative' | 'Neutral' => {
  if (beta > 0.1) return 'Positive'
  if (beta < -0.1) return 'Negative'
  return 'Neutral'
}

// Get commentary based on factor name and beta
const getFactorCommentary = (name: string, beta: number): string => {
  // Switch statement based on factor name
  // Return appropriate commentary template
}

// Get icon for factor
const getFactorIcon = (name: string): string => {
  const icons: Record<string, string> = {
    'Market Beta (90D)': '📈',
    'Momentum': '📊',
    'Value': '💰',
    'Growth': '🚀',
    'Quality': '💎',
    'Size': '📏',
    'Low Volatility': '🛡️',
    'IR Beta': '🏦'
  }
  return icons[name] || '📊'
}
```

### Step 3: Update RiskMetricsContainer

**File**: `src/containers/RiskMetricsContainer.tsx`

Replace:
```tsx
<FactorExposureHeroRow ... />
```

With:
```tsx
<FactorExposureCards
  factors={factorExposures.factors}
  loading={factorExposures.loading}
  error={factorErrorMessage}
  calculationDate={factorExposures.calculationDate}
  onRefetch={factorExposures.refetch}
/>
```

Keep spread factors separate below.

### Step 4: Backend Support (Optional)

If explanations should come from backend:

**Add to factor exposure response**:
```python
{
  "name": "Market Beta (90D)",
  "beta": 1.23,
  "exposure_dollar": 2400000,
  "explanation": "Your portfolio moves 23% more than the market...",
  "magnitude": "High",
  "direction": "Positive",
  "risk_level": "high",
  "icon": "📈"
}
```

**Pros**: Centralized logic, easier to update
**Cons**: Additional backend work

**Alternative**: Keep logic in frontend (recommended for now)

---

## Benefits of This Design

### 1. Educational
- Users learn what each factor means
- Clear explanations of implications
- Actionable insights

### 2. Contextual
- Explanation tied to specific beta value
- Dynamic commentary based on magnitude
- Relevant to user's portfolio

### 3. Consistent
- Matches SpreadFactorCards design
- Same visual treatment for similar data
- Unified look and feel

### 4. Scannable
- Icon + magnitude badge for quick insights
- Progress bar for visual magnitude
- Color-coded badges

### 5. Actionable
- Commentary suggests implications
- Risk warnings when appropriate
- Clear direction on what beta means

---

## Color Coding

### Magnitude Badges
- **Strong**: Purple (`bg-purple-500`)
- **Moderate**: Blue (`bg-blue-500`)
- **Weak**: Gray (`bg-gray-400`)

### Direction Badges
- **Positive**: Green border/text
- **Negative**: Red border/text
- **Neutral**: Gray border/text

### Risk Level (Background)
- **High**: Red tint
- **Medium**: Yellow tint
- **Low**: Green tint

---

## Accessibility Considerations

1. **Color is not sole indicator**: Use icons, text, and badges
2. **Screen reader support**: Proper ARIA labels
3. **Keyboard navigation**: Tab through cards
4. **Contrast ratios**: WCAG AA compliance
5. **Tooltips**: Additional context on hover/focus

---

## Future Enhancements

### Phase 2
- **Interactive tooltips**: Deeper explanations on click
- **Historical charts**: Show factor beta over time
- **Comparison mode**: Compare to benchmark factor exposures
- **Custom thresholds**: User-defined magnitude boundaries

### Phase 3
- **Factor contribution**: Show P&L attribution by factor
- **Scenario analysis**: "What if" factor beta changes
- **Recommendations**: Suggest rebalancing based on factor exposures
- **Export**: Download factor report as PDF

---

## Questions for Product Review

1. **Should we show all 8 factors** or prioritize top 4-6?
2. **Dollar exposure**: Always show or only when available?
3. **Backend vs frontend**: Where should commentary logic live?
4. **Card height**: Fixed height or flexible based on content?
5. **Mobile**: Single column or 2 columns on larger phones?
6. **Comparison**: Show vs benchmark factor exposures?

---

## Success Metrics

### User Engagement
- Time spent on Risk Metrics page
- Click-through rate on factor cards
- Tooltip/explanation interactions

### User Comprehension
- Reduced support tickets about "what is beta?"
- Increased usage of factor-based insights
- User survey feedback on clarity

### Technical
- Page load time impact
- Component render performance
- Mobile responsiveness scores

---

## File Locations

### New Files
- `src/components/risk-metrics/FactorExposureCards.tsx` (new component)
- `src/lib/factorCommentary.ts` (helper functions)
- `src/types/factors.ts` (TypeScript interfaces)

### Modified Files
- `src/containers/RiskMetricsContainer.tsx` (swap components)
- `src/hooks/useFactorExposures.ts` (potential updates)

### Documentation
- `frontend/_docs/ClaudeUISuggestions/FactorExposureHeroRowRedesign.md` (this file)

---

**End of Proposal**
