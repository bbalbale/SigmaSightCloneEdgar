# AI Integration Architecture - Ambient AI System

**Document Version**: 1.0
**Last Updated**: October 30, 2025
**Status**: Detailed Specification

---

## Overview

Transform AI from siloed pages (SigmaSight AI, AI Chat) into an **ambient copilot** woven throughout the application. The AI should be accessible everywhere, contextually aware, and proactive (not just reactive).

### Current State

**Problem**:
- AI exists on 2 separate pages (SigmaSight AI, AI Chat)
- Two different AI systems:
  - **Backend**: OpenAI Responses API (conversational, tool-enabled, database access)
  - **Frontend**: Chat Completions API (faster, simpler)
- Users must navigate away to ask questions (context switching)
- No proactive insights (AI waits for user to ask)
- AI usage <20% (low discoverability)

### Target State

**Solution**:
- **Persistent AI Sidebar**: Accessible from all pages, follows user
- **Unified AI System**: Single backend (Responses API) with streaming
- **Auto-Context Injection**: AI knows current page, selections, filters
- **Contextual Quick Actions**: "AI Explain" buttons everywhere
- **Proactive Insights**: AI generates daily summaries, alerts, anomalies
- **Workflow Assistants**: Multi-step guided workflows (rebalancing, hedging)

---

## Architecture Components

### 1. Persistent AI Sidebar

**Layout**:
```
┌────────────────────────────────┬──────────────────────┐
│ Main Content                   │ AI Copilot      [×][_]│
│ (Command Center, Positions,etc)│ ──────────────────────│
│                                │ 💬 Ask about your     │
│                                │    portfolio...       │
│                                │ [________________]  ➤ │
│                                │                       │
│                                │ Quick Actions:        │
│                                │ • Explain my exposure │
│                                │ • Analyze risks       │
│                                │ • Suggest rebalancing │
│                                │ • What changed today? │
│                                │                       │
│                                │ Recent Conversation:  │
│                                │ User: What's my tech  │
│                                │       exposure?       │
│                                │ AI: You're 45% tech...│
│                                │                       │
│                                │ ✨ New Insights (3):  │
│                                │ • Tech concentration  │
│                                │ • Volatility spike    │
│                                │ • On track for goal   │
│                                │                       │
│                                │ [View History]        │
└────────────────────────────────┴──────────────────────┘
```

**States**:
1. **Expanded** (400px width): Full sidebar visible
2. **Collapsed** (60px width): Only AI icon visible, expands on hover
3. **Minimized**: Hidden completely, floating button shows badge

**Behavior**:
- Persists across page changes (global component)
- Maintains conversation context
- Auto-injects page context into prompts
- Resizable (drag left edge)
- Position saved to user preferences

---

### 2. Context Injection System

**Automatic Context Awareness**:

The AI should always know:
- **Current page**: Command Center, Positions, Risk Analytics, etc.
- **Active tab**: (if applicable) Long, Short, Factors, etc.
- **Selected positions**: If user has positions selected
- **Active filters**: Tags, sectors, P&L filters
- **Visible data**: What's currently on screen

**Implementation**:

```typescript
// Context Hook
function useAIContext() {
  const pathname = usePathname()
  const { selectedPositions } = usePositionsStore()
  const { activeFilters } = useFiltersStore()
  const { portfolioId } = usePortfolioStore()

  return {
    page: pathname, // '/positions/long'
    portfolio_id: portfolioId,
    selected_positions: selectedPositions, // ['NVDA', 'META']
    filters: activeFilters, // { tags: ['core'], sectors: ['tech'] }
    timestamp: new Date().toISOString()
  }
}

// AI Request with Context
async function sendAIMessage(userMessage: string) {
  const context = useAIContext()

  const prompt = `
    User is on page: ${context.page}
    Portfolio ID: ${context.portfolio_id}
    Selected positions: ${context.selected_positions.join(', ')}
    Active filters: ${JSON.stringify(context.filters)}

    User question: ${userMessage}

    Provide a contextual answer based on the user's current view.
  `

  // Send to backend AI endpoint
  const response = await fetch('/api/v1/chat/conversations/{id}/send', {
    method: 'POST',
    body: JSON.stringify({ message: prompt, context })
  })

  return response
}
```

**Context Examples**:

**User on Command Center, asks "What's my biggest risk?"**
```
Context: {
  page: '/command-center',
  portfolio_id: '123',
  visible_insights: ['Tech concentration alert', 'Volatility spike']
}

AI Response:
"Your biggest risk right now is tech concentration. You're 45% tech, +15% above S&P 500. If the tech sector declines 10%, your portfolio would drop ~$45K (-9%). I see you already have a volatility spike alert. Would you like me to suggest rebalancing options?"
```

**User on Positions page (Long tab), NVDA selected, asks "Should I trim this?"**
```
Context: {
  page: '/positions/long',
  selected_positions: ['NVDA'],
  position_details: { value: $88K, pnl: +15.8%, beta: 1.85 }
}

AI Response:
"NVDA is your largest position at $88K (17.6% of portfolio), up 15.8%. From a risk perspective:
• Concentration: 17.6% in single stock (high)
• Correlation with MSFT: 0.92 (reduces diversification)
• Tech exposure: Already at 45% (+15% vs S&P 500)

Considerations:
• Trimming 20% would reduce concentration and lock in gains
• However, NVDA has strong momentum (+2.1σ factor exposure)

Would you like me to calculate specific trim scenarios with tax impacts?"
```

---

### 3. Contextual Quick Actions

**"AI Explain" Buttons Everywhere**:

Every component should have contextual AI buttons:

**On Position Card**:
```
[AI Explain NVDA] → "NVDA is your largest position at $88K (17.6%). It's up 15.8% due to strong AI chip demand. However, concentration risk is elevated. Consider trimming or hedging."
```

**On Factor Exposure**:
```
[Explain Growth Factor] → "Your Growth tilt of +2.1σ means your portfolio has high exposure to growth stocks (NVDA, META, TSLA). These stocks typically outperform in bull markets but underperform in value rotations."
```

**On Sector Exposure**:
```
[Explain Tech Overweight] → "You're 45% tech vs S&P 500's 30% (+15% overweight). This creates concentration risk. If tech drops 10%, your portfolio loses ~$45K."
```

**On Volatility Metric**:
```
[Explain Volatility Spike] → "Your portfolio volatility jumped from 15% to 21% this week due to tech sector rotation. NVDA alone contributes 8.2% (39% of total volatility). Your portfolio is more sensitive to market swings right now."
```

**Implementation**:

```typescript
<AIExplainButton
  context={{
    type: 'position',
    symbol: 'NVDA',
    value: 88000,
    pnl_pct: 0.158
  }}
  prompt="Explain this position and whether I should consider trimming"
/>

// Component
function AIExplainButton({ context, prompt }) {
  const handleClick = () => {
    openAISidebar()
    sendAIMessage(prompt, context)
  }

  return (
    <button onClick={handleClick} className="ai-explain-btn">
      ✨ AI Explain
    </button>
  )
}
```

---

### 4. Proactive AI Insights

**Daily AI Summary** (Generated nightly by backend batch job):

```
Good morning! Here's what you should know today (Oct 30, 2025):

📊 Portfolio Health: 82/100 (Good)
• Your portfolio is well-positioned overall

⚠️ Risks to Watch:
• Tech concentration: 45% (+15% vs S&P 500)
  → Consider diversifying if tech weakness continues
• Volatility spike: 21% (from 15% last week)
  → Portfolio more sensitive to market swings

✅ Wins:
• YTD return: +8.2% (on track for 12% annual goal)
• NVDA: +$12K (+15.8%) this month - strong performance

💡 Suggested Actions:
• Review tech exposure (rebalancing opportunity)
• 3 positions near target prices (NVDA, META, AAPL)

📅 Upcoming Events:
• NVDA earnings: Nov 15 (potential catalyst)
• FOMC meeting: Nov 1 (rate decision)

[View Full Report] [Start Rebalancing] [Dismiss]
```

**Anomaly Detection Alerts**:

Backend monitors portfolio continuously, generates alerts when:
- Volatility spike > 20% increase
- Correlation changes > 0.15
- Sector concentration exceeds threshold
- Position P&L moves > 10% in a day
- Factor exposure drifts > 0.5σ

**Alert UI**:
```
┌─────────────────────────────────────────────────┐
│ 🔔 New Alert                              [×]   │
│ ───────────────────────────────────────────────  │
│ NVDA-MSFT Correlation Increased                 │
│ Correlation jumped from 0.75 to 0.92 (high).    │
│ This reduces diversification benefits.          │
│                                                  │
│ [Show Details] [Suggest Hedge] [Dismiss]        │
└─────────────────────────────────────────────────┘
```

---

### 5. AI Workflow Assistants

**Multi-Step Guided Workflows**:

Instead of just answering questions, AI guides users through complex tasks.

**Example: Rebalancing Workflow**

```
Step 1: User Intent
User: "I want to reduce my tech exposure"

AI: "Got it. What's your target tech allocation?
     Current: 45% (+15% vs S&P 500)
     Options:
     1. Match S&P 500 (30%)
     2. Slight overweight (35-40%)
     3. Custom target"

Step 2: User Selection
User: "Option 2, target 38%"

AI: "To reach 38% tech (from 45%), you need to reduce by $35K. Here are 3 approaches:

     A. Trim top tech positions (NVDA, META) proportionally
        → Sell $17.5K NVDA, $17.5K META
        → Tax impact: ~$5K (short-term gains)

     B. Rotate into underweight sectors (Financials, Energy)
        → Trim tech, add JPM + XLE
        → Tax impact: ~$5K, new positions for diversification

     C. Add tech hedge (buy SPY puts or short QQQ)
        → No trimming, use options to offset risk
        → Cost: ~$2K for 3-month put spread

     Which approach do you prefer?"

Step 3: User Choice
User: "Option A"

AI: "Here's the detailed plan for Option A:

     Trades:
     • Sell NVDA 40 shares @ $440 = $17,600
     • Sell META 21 shares @ $420 = $8,820
     Total proceeds: $26,420

     Tax Impact:
     • NVDA gain: $2,400 (short-term, 30% rate = $720 tax)
     • META gain: $1,480 (short-term, 30% rate = $444 tax)
     • Total estimated tax: $1,164

     Portfolio Impact After Trades:
     • Tech exposure: 45% → 38% ✓
     • Concentration (HHI): 0.082 → 0.074 (better)
     • Beta: 1.15 → 1.12 (less volatile)
     • Portfolio health score: 82 → 85 (improved)

     Ready to generate order list?"

Step 4: Order Generation
User: "Yes"

AI: "Order list generated:

     1. SELL NVDA 40 shares @ MARKET
     2. SELL META 21 shares @ MARKET

     [Download CSV] [Copy to Clipboard] [Send to Email]

     Note: These are market orders. Review before submitting to your broker.

     Would you like me to monitor this and send a reminder to execute?"
```

**Other Workflow Examples**:
- Tax-loss harvesting (identify loss positions, suggest pairs trades)
- Hedge construction (analyze risk, suggest hedge instruments)
- Smart tagging (AI suggests tags based on position characteristics)
- Performance attribution (explain what drove P&L changes)

---

## System Unification

### Merge Backend + Frontend AI

**Current**:
- Backend: Responses API (slow 25-30s, but tool-enabled, conversational)
- Frontend: Chat Completions (fast, but no tools, no persistence)

**New Unified Architecture**:

```
Frontend (Persistent Sidebar)
    ↓ SSE Streaming
Backend (/api/v1/chat/conversations/{id}/send)
    ↓ OpenAI Responses API
    ↓ Tools: [get_portfolio_data, run_stress_test, calculate_trades, etc.]
    ↓ Database: Conversation history, context, insights
```

**Benefits**:
- Single conversation history (not fragmented)
- Tool access (AI can fetch live data, run calculations)
- Streaming responses (no 25-30s wait, show tokens as they arrive)
- Persistence (conversations saved, searchable)

**Implementation**:

```typescript
// Frontend: Stream AI Response
async function streamAIResponse(message: string, context: object) {
  const response = await fetch(`/api/v1/chat/conversations/${convId}/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, context })
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6))
        if (data.type === 'content') {
          appendToMessage(data.text)  // Show token by token
        }
      }
    }
  }
}
```

**Backend Enhancement**:
- Add SSE streaming to existing Responses API endpoint
- Ensure <2s to first token (fast perceived performance)
- Show "AI is thinking..." indicator while processing

---

## Implementation Roadmap

### Week 1-2: Core Infrastructure
- [ ] Build persistent AI sidebar component
- [ ] Implement context injection system
- [ ] Unify backend AI (SSE streaming)
- [ ] Add AI sidebar to all pages

### Week 3-4: Contextual Actions
- [ ] Add "AI Explain" buttons to all components
- [ ] Build quick action templates
- [ ] Implement context-aware prompts

### Week 5-6: Proactive Insights
- [ ] Backend batch job for daily summaries
- [ ] Anomaly detection system
- [ ] Insight cards on Command Center
- [ ] Notification system

### Week 7-8: Workflow Assistants
- [ ] Rebalancing workflow
- [ ] Hedge recommendation workflow
- [ ] Tax-loss harvesting workflow

---

## Success Metrics

**Engagement**:
- AI interactions per session: 3+ (target, vs <1 currently)
- AI sidebar open rate: 60%+ of sessions
- "AI Explain" button clicks: 50%+ of users

**Utility**:
- Users rate AI as "helpful": 80%+
- AI-suggested actions taken: 40%+
- Workflow completion rate: 60%+

**Performance**:
- Time to first token: <2s
- Full response time: <15s (vs 25-30s currently)
- Sidebar load time: <500ms

**Next**: See `07-COMPONENT-LIBRARY.md` for reusable component specifications.
