# Plan: Morning Meeting AI Briefing Feature

## Objective
Transform the AI insights generation from generic YTD summaries into a real-time "morning meeting" style briefing that covers:
- What happened to the portfolio in the past day/week
- Key movers (top gainers/losers)
- News affecting positions in the portfolio (via OpenAI web search)
- Actionable analyst-style commentary

## User Requirements (Confirmed)
1. **Output**: Generate BOTH insight card (left panel) AND chat context (right panel) for follow-up
2. **News**: Use OpenAI's built-in web search (no new backend news API)
3. **Timeframe**: Past Day + Week performance data
4. **LLM**: OpenAI consistently (already migrated - uses gpt-4o-mini)

---

## Current State (Verified)

### Insights System - Already Using OpenAI ✅
- Endpoint: `POST /api/v1/insights/generate` in `backend/app/api/v1/insights.py`
- Service: `backend/app/services/analytical_reasoning_service.py` → calls `openai_service.generate_insight()`
- LLM: `gpt-4o-mini` via OpenAI Responses API
- Prompt: `backend/app/agent/prompts/daily_insight_prompt.md` (already has good structure)

### Existing InsightType Enum (line 16-24 in ai_insights.py)
```python
DAILY_SUMMARY, VOLATILITY_ANALYSIS, CONCENTRATION_RISK,
HEDGE_QUALITY, FACTOR_EXPOSURE, STRESS_TEST_REVIEW, CUSTOM
```

### get_daily_movers Tool (lines 952-1051 in handlers.py)
- Currently calculates daily changes only
- Returns: gainers, losers, portfolio_daily_change, biggest_winner/loser
- **Needs**: Weekly data calculation added

### OpenAI Web Search
- Already configured (`WEB_SEARCH_ENABLED=True` in config)
- Smart routing detects keywords like "today", "recent", "news"
- Just needs to be enabled for morning briefing insight type

---

## Implementation Plan

### Phase 1: Backend - Add MORNING_BRIEFING Insight Type
**File**: `backend/app/models/ai_insights.py`

Add to InsightType enum (line 18):
```python
MORNING_BRIEFING = "morning_briefing"
```

### Phase 2: Backend - Create Morning Briefing Prompt
**New File**: `backend/app/agent/prompts/morning_briefing_prompt.md`

Create analyst-style prompt with required sections:
1. **Title** - Punchy headline (e.g., "Tech Rally Lifts Portfolio +2.3%")
2. **Performance Snapshot** - Yesterday + this week
3. **Top Movers: Yesterday** - Top 3 gainers/losers with % change
4. **Top Movers: This Week** - Top 3 weekly gainers/losers
5. **News Driving Moves** - 3-5 relevant news items (via web search)
6. **Market Context** - Broader market/macro context
7. **Watch List** - 2-3 items to monitor
8. **Action Items** - 0-2 actionable recommendations

Key differences from daily_insight_prompt.md:
- Emphasizes WEEKLY trends alongside daily
- Explicitly requires web search for news
- Morning meeting tone (analyst presenting to team)

### Phase 3: Backend - Enhance get_daily_movers with Weekly Data
**File**: `backend/app/agent/tools/handlers.py` (lines 952-1051)

Add weekly performance calculation:
```python
async def get_daily_movers(
    self,
    portfolio_id: str,
    threshold_pct: float = 2.0,
    include_weekly: bool = True,  # NEW parameter
    **kwargs
) -> Dict[str, Any]:
```

New return fields:
- `weekly_gainers`: Top 5 weekly gainers
- `weekly_losers`: Top 5 weekly losers
- `portfolio_weekly_change`: { pnl_dollar, pnl_pct }
- `biggest_weekly_winner`, `biggest_weekly_loser`

Weekly calculation logic:
1. Fetch position prices from 5 trading days ago (via existing `get_prices_historical`)
2. Calculate weekly change % and $ for each position
3. Sort and return top movers

### Phase 4: Backend - Enable Web Search for Morning Briefing
**File**: `backend/app/agent/services/openai_service.py`

4a. Add morning briefing keywords to smart routing (around line 69):
```python
self._web_search_keywords = [
    # existing...
    "morning briefing", "morning brief", "morning update"
]
```

4b. Update `generate_insight()` method to:
- Load `morning_briefing_prompt.md` when `insight_type == "morning_briefing"`
- Always enable web_search tool for morning briefing type

### Phase 5: Frontend - Add Morning Briefing Button
**File**: `frontend/src/services/insightsApi.ts`

Add to InsightType union:
```typescript
export type InsightType =
  | 'daily_summary'
  | 'morning_briefing'  // NEW
  | 'volatility_analysis'
  // ... rest unchanged
```

**File**: `frontend/src/containers/SigmaSightAIContainer.tsx`

Add prominent "Morning Briefing" button:
```tsx
<button
  onClick={() => {
    handleGenerateInsight({ insightType: 'morning_briefing' });
    // Prefill chat for follow-up
    setPrefillMessage("I just generated a morning briefing. What questions do you have about today's portfolio performance or the news items mentioned?");
  }}
  className="bg-gradient-to-r from-amber-500 to-orange-500 text-white..."
>
  Morning Briefing
</button>
```

Also add `morning_briefing` to:
- Insight type dropdown (line ~113)
- Filter dropdown (line ~168)

---

## Files to Modify

| File | Changes | Lines Est. |
|------|---------|------------|
| `backend/app/models/ai_insights.py` | Add MORNING_BRIEFING enum | 1 |
| `backend/app/agent/prompts/morning_briefing_prompt.md` | **NEW FILE** - Morning briefing prompt | ~120 |
| `backend/app/agent/tools/handlers.py` | Enhance get_daily_movers with weekly data | ~60 |
| `backend/app/agent/services/openai_service.py` | Load correct prompt, enable web search | ~25 |
| `frontend/src/services/insightsApi.ts` | Add morning_briefing to InsightType | 1 |
| `frontend/src/containers/SigmaSightAIContainer.tsx` | Add Morning Briefing button + prefill | ~25 |

---

## Data Flow

```
1. User clicks "Morning Briefing" button
   ↓
2. Frontend: POST /api/v1/insights/generate { insight_type: "morning_briefing" }
   ↓
3. insights.py → analytical_reasoning_service.investigate_portfolio()
   ↓
4. openai_service.generate_insight():
   - Loads morning_briefing_prompt.md
   - Gets tools INCLUDING web_search (auto-enabled)
   - Calls OpenAI Responses API
   ↓
5. OpenAI executes tools:
   a. get_daily_movers (with weekly data)
   b. get_portfolio_complete
   c. web_search (for news on top holdings)
   ↓
6. OpenAI generates structured response
   ↓
7. Response → AIInsight saved to DB → returned to frontend
   ↓
8. Frontend:
   - Displays insight card (left panel)
   - Prefills chat with follow-up context (right panel)
```

---

## Implementation Order

1. **Phase 1**: Add MORNING_BRIEFING enum (required first - DB enum)
2. **Phase 2**: Create morning_briefing_prompt.md (no dependencies)
3. **Phase 3**: Enhance get_daily_movers with weekly data (no dependencies)
4. **Phase 4**: Update openai_service.py for prompt loading + web search (depends on 2)
5. **Phase 5**: Frontend changes (depends on 1)

---

## Testing Checklist

- [ ] Generate morning briefing for each demo portfolio
- [ ] Verify daily movers includes weekly data
- [ ] Verify web search is triggered (check for news items)
- [ ] Verify insight card displays correctly
- [ ] Verify chat prefill works for follow-up questions
- [ ] Test with market open vs closed scenarios
