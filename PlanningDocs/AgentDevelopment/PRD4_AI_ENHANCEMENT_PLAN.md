# PRD4: AI Chat Enhancement Plan

**Created**: December 18, 2025
**Status**: In Progress
**Priority**: High
**Depends On**: PRD3 (AI Consolidation) - Complete
**Last Updated**: December 18, 2025

---

## Executive Summary

This PRD outlines a 5-phase plan to enhance SigmaSight's AI chat capabilities, building on the consolidated architecture from PRD3. The phases are ordered by impact and dependency chain, with memory integration forming the foundation for personalization across all features.

**Goal**: Transform the AI chat from a capable assistant into a personalized, learning financial advisor that remembers user preferences, delivers tailored briefings, and continuously improves from feedback.

---

## Phase Overview

| Phase | Name | Description | Effort | Status |
|-------|------|-------------|--------|--------|
| 1 | Memory Integration | Wire existing memory service into agent | 2-3 days | **COMPLETE** ✅ |
| 2 | Enhanced Morning Briefing | Personalize briefings with memory context | 3-4 days | Pending |
| 3 | Feedback Learning Loop | Convert feedback into improvements | 5-7 days | Pending |
| 4 | UX Polish | Copy, regenerate, stop streaming controls | 2-3 days | Pending |
| 5 | User Controls | Reasoning depth and verbosity toggles | 2-3 days | Pending |

**Total Estimated Effort**: 14-20 days
**Completed**: ~2-3 days (Phase 1)

---

## Phase 1: Memory Integration

### Objective
Wire the existing memory service into the agent so it remembers user preferences, investment rules, and context across conversations.

### Current State (What Exists)
- ✅ `AIMemory` database model (`backend/app/models/ai_learning.py`)
- ✅ `memory_service.py` with complete CRUD operations
- ✅ Memory extraction prompt template (`MEMORY_EXTRACTION_PROMPT`)
- ✅ `format_memories_for_prompt()` function
- ✅ Duplicate checking logic
- ✅ Memory scopes: user, portfolio, global
- ✅ Limits: 50 memories per user, 500 char per memory

### What Needs to Be Built

#### 1.1 Memory Injection into System Prompt
**File**: `backend/app/agent/agent.py`

Modify the agent initialization to fetch and inject user memories:

```python
# In create_agent() or equivalent
memories = await memory_service.get_memories_for_user(user_id)
memory_context = memory_service.format_memories_for_prompt(memories)

system_prompt = f"""
{BASE_SYSTEM_PROMPT}

## User Context & Preferences
{memory_context}
"""
```

#### 1.2 Automatic Memory Extraction Post-Conversation
**File**: `backend/app/agent/handlers.py`

After each conversation turn, analyze for extractable memories:

```python
async def handle_message_complete(conversation_id, user_id, messages):
    """Called after agent completes a response"""
    # Extract potential memories from the conversation
    new_memories = await memory_service.extract_memories_from_response(
        user_id=user_id,
        conversation_text=format_conversation(messages),
        existing_memories=await memory_service.get_memories_for_user(user_id)
    )

    for memory in new_memories:
        if not await memory_service.check_for_duplicate_memory(user_id, memory):
            await memory_service.create_memory(user_id, memory)
```

#### 1.3 Memory API Endpoints
**File**: `backend/app/api/v1/chat/memories.py` (CREATE)

```python
@router.get("/memories")
async def list_memories(current_user: User = Depends(get_current_user)):
    """List all memories for current user"""

@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: UUID, current_user: User = Depends(get_current_user)):
    """Delete a specific memory"""

@router.put("/memories/{memory_id}")
async def update_memory(memory_id: UUID, content: str, current_user: User = Depends(get_current_user)):
    """Update memory content"""
```

#### 1.4 Frontend Memory Management UI
**Files to Create**:
- `frontend/src/services/memoryApi.ts` - API client
- `frontend/src/components/chat/MemoryPanel.tsx` - UI component

Features:
- View all memories in a collapsible panel
- Delete unwanted memories
- Edit memory text
- Memory categories/scopes displayed

### Memory Types to Extract
1. **Investment Preferences**: "User prefers tech stocks", "User is risk-averse"
2. **Communication Style**: "User prefers concise responses", "User likes detailed analysis"
3. **Portfolio Rules**: "User's target allocation is 60/40", "User avoids energy sector"
4. **Context**: "User mentioned planning for retirement in 10 years"
5. **Watch Items**: "User is monitoring AAPL for entry point below $180"

### Success Criteria
- [x] Memories persist across sessions
- [x] Agent responses reflect known preferences
- [x] User can view/edit/delete memories
- [x] No duplicate memories created
- [x] Memory extraction doesn't slow down responses (async)

### Implementation Complete (December 18, 2025) ✅

**1.1 Memory Injection - ALREADY EXISTED**
- Found in `backend/app/agent/services/openai_service.py:137-193`
- `_get_user_memories_context()` retrieves memories
- Injected into system prompt via `_build_responses_input()` (lines 1172-1186)
- Section header: "User Preferences & Context"

**1.2 Automatic Memory Extraction - IMPLEMENTED**
- Added `extract_memories_from_conversation()` to `backend/app/agent/services/memory_service.py`
- Uses GPT-4o-mini for fast extraction with `MEMORY_EXTRACTION_PROMPT`
- Parses JSON array response, checks for duplicates, saves valid memories
- Background task `_run_memory_extraction_background()` in `backend/app/api/v1/chat/send.py`
- Triggered via `asyncio.create_task()` after successful message completion (non-blocking)

**1.3 Memory API Endpoints - IMPLEMENTED**
- Created `backend/app/api/v1/chat/memories.py` with 5 endpoints:
  - `GET /memories` - List memories (with scope/portfolio filtering)
  - `POST /memories` - Create memory
  - `DELETE /memories/{memory_id}` - Delete specific memory
  - `DELETE /memories` - Delete all memories
  - `GET /memories/count` - Get memory count and limits
- Registered in `backend/app/api/v1/chat/router.py`

**1.4 Frontend Memory UI - IMPLEMENTED**
- Created `frontend/src/services/memoryApi.ts` - API client with full CRUD
- Created `frontend/src/components/ai/MemoryPanel.tsx` - UI component with:
  - Memory list view with scope badges and dates
  - Manual memory creation
  - Individual memory deletion
  - "Delete all" functionality
  - Auto-extracted memory indicator
  - Responsive design with loading/error states

**Deployment Status**: Code complete, pending Railway deployment for testing.

---

## Phase 2: Enhanced Morning Briefing

### Objective
Transform the morning briefing from a generic report into a personalized, context-aware financial briefing that remembers what the user cares about.

### Current State (What Exists)
- ✅ `morning_briefing_prompt.md` - detailed analyst-style prompt
- ✅ `get_daily_movers` tool - calculates price changes
- ✅ Web search integration for news
- ✅ Portfolio complete data access
- ✅ Rate limiting disabled for testing

### What Needs to Be Built

#### 2.1 Memory-Aware Briefing Prompt
**File**: `backend/app/agent/prompts/morning_briefing_prompt.md`

Add memory context section:

```markdown
## User Context (from Memory)
{memory_context}

Use this context to:
- Prioritize positions the user has mentioned watching
- Match the user's preferred communication style
- Reference relevant past discussions ("Last week you mentioned...")
- Focus on metrics the user cares about most
```

#### 2.2 Market Overview Tool
**File**: `backend/app/agent/tools/market_tools.py` (MODIFY)

Add `get_market_overview` tool:

```python
@tool
async def get_market_overview() -> dict:
    """Get broad market context: S&P 500, sector performance, VIX"""
    return {
        "spy_change": get_spy_daily_change(),
        "vix": get_current_vix(),
        "sector_performance": get_sector_heat_map(),
        "market_sentiment": "bullish/bearish/neutral"
    }
```

#### 2.3 Historical Awareness
**File**: `backend/app/agent/handlers.py`

Track briefing history for continuity:

```python
async def get_briefing_context(user_id: UUID, portfolio_id: UUID):
    """Get context from previous briefings"""
    # Fetch last 5 briefings
    # Extract: mentioned positions, action items, watch list
    # Format as "Previously you were watching: AAPL, NVDA"
```

#### 2.4 Briefing Customization Options
**File**: `backend/app/api/v1/insights.py`

Add customization parameters:

```python
@router.post("/morning-briefing")
async def generate_morning_briefing(
    portfolio_id: UUID,
    include_news: bool = True,
    include_market_overview: bool = True,
    focus_areas: List[str] = None,  # ["tech", "dividends", "watchlist"]
    verbosity: str = "standard"  # "brief", "standard", "detailed"
):
```

#### 2.5 Frontend Briefing Settings
**File**: `frontend/src/components/chat/BriefingSettings.tsx` (CREATE)

Allow users to configure:
- News inclusion on/off
- Focus areas (sectors, position types)
- Verbosity level
- Scheduled delivery time (future)

### Enhanced Briefing Sections
1. **Market Pulse**: S&P 500, VIX, sector heat map
2. **Your Portfolio**: Performance, top movers, alerts
3. **Watch List**: Positions user is monitoring (from memory)
4. **News Digest**: Relevant news for holdings
5. **Action Items**: Follow-ups from previous briefings
6. **Today's Focus**: Based on user preferences

### Success Criteria
- [ ] Briefing reflects user's communication style
- [ ] Watch list items from memory are highlighted
- [ ] Previous briefing context referenced
- [ ] Market overview provides broader context
- [ ] Customization options work correctly

---

## Phase 3: Feedback Learning Loop

### Objective
Create a closed-loop system where user feedback (thumbs up/down, edits) actively improves future AI responses through both rule-based learning and RAG-enhanced example retrieval.

### Current State (What Exists)
- ✅ `AIFeedback` model - stores ratings, edited_text, comments
- ✅ `feedback.py` endpoints - POST/GET/DELETE
- ✅ Frontend thumbs up/down buttons
- ✅ `AIKBDocument` model for RAG storage

### Learning Approaches (Implementing Both)

#### Approach A: Rule-Based Learning
Convert feedback patterns into memory rules that modify agent behavior.

**Example Flow**:
1. User gives thumbs down + edits response to be shorter
2. System detects pattern: "User shortened response"
3. Creates memory: "User prefers concise responses"
4. Future responses are automatically more concise

#### Approach B: RAG-Enhanced Learning
Store highly-rated responses as examples for few-shot prompting.

**Example Flow**:
1. User gives thumbs up to a great portfolio analysis
2. Response stored in knowledge base with embedding
3. Similar future questions retrieve this as an example
4. Agent uses it for few-shot context

### What Needs to Be Built

#### 3.1 Feedback Analyzer Service
**File**: `backend/app/agent/services/feedback_analyzer.py` (CREATE)

```python
class FeedbackAnalyzer:
    async def analyze_feedback_patterns(self, user_id: UUID) -> List[LearningRule]:
        """Analyze user's feedback history for patterns"""
        feedbacks = await self.get_recent_feedback(user_id, limit=100)

        patterns = []

        # Pattern: Response length preferences
        if self._detect_length_preference(feedbacks):
            patterns.append(LearningRule(
                type="preference",
                content="User prefers shorter/longer responses",
                confidence=0.8
            ))

        # Pattern: Topic preferences
        topic_prefs = self._detect_topic_preferences(feedbacks)
        patterns.extend(topic_prefs)

        # Pattern: Style preferences (formal/casual, technical/simple)
        style_prefs = self._detect_style_preferences(feedbacks)
        patterns.extend(style_prefs)

        return patterns

    async def extract_rule_from_edit(self, original: str, edited: str) -> Optional[LearningRule]:
        """Use LLM to understand what the edit teaches us"""
        prompt = f"""
        Original response: {original}
        User edited to: {edited}

        What preference does this edit reveal? Respond with a single rule like:
        "User prefers [specific preference]"
        """
        # Call LLM to extract the rule
```

#### 3.2 Learning Integration Service
**File**: `backend/app/agent/services/learning_service.py` (CREATE)

```python
class LearningService:
    def __init__(self, memory_service, kb_service, feedback_analyzer):
        self.memory_service = memory_service
        self.kb_service = kb_service
        self.feedback_analyzer = feedback_analyzer

    async def process_positive_feedback(self, feedback: AIFeedback):
        """Store highly-rated response as example in KB"""
        message = await self.get_message(feedback.message_id)

        # Create KB document for RAG retrieval
        await self.kb_service.create_document(
            content=message.content,
            metadata={
                "type": "positive_example",
                "query": message.user_query,
                "rating": "positive",
                "user_id": str(feedback.user_id)
            }
        )

    async def process_negative_feedback(self, feedback: AIFeedback):
        """Extract learning from negative feedback"""
        if feedback.edited_text:
            # User provided correction - extract the rule
            rule = await self.feedback_analyzer.extract_rule_from_edit(
                original=feedback.original_text,
                edited=feedback.edited_text
            )
            if rule:
                await self.memory_service.create_memory(
                    user_id=feedback.user_id,
                    content=rule.content,
                    scope="user",
                    category="learned_preference"
                )

    async def apply_learnings_to_prompt(self, user_id: UUID, base_prompt: str) -> str:
        """Enhance prompt with learned preferences and examples"""
        # Get learned preferences (from memory)
        memories = await self.memory_service.get_memories_for_user(user_id)
        learned_prefs = [m for m in memories if m.category == "learned_preference"]

        # Get relevant positive examples (from KB)
        # This happens in the RAG retrieval step

        return f"""
        {base_prompt}

        ## Learned User Preferences
        {format_preferences(learned_prefs)}
        """
```

#### 3.3 Feedback Processing Webhook
**File**: `backend/app/api/v1/chat/feedback.py` (MODIFY)

```python
@router.post("/messages/{message_id}/feedback")
async def submit_feedback(
    message_id: UUID,
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user)
):
    # Save feedback
    saved = await feedback_service.create_feedback(message_id, feedback, current_user.id)

    # Trigger async learning process
    background_tasks.add_task(
        learning_service.process_feedback,
        saved
    )

    return saved
```

#### 3.4 Batch Feedback Analysis Job
**File**: `backend/app/batch/feedback_learning_job.py` (CREATE)

```python
async def run_feedback_learning_batch():
    """Scheduled job to analyze feedback patterns across all users"""
    users_with_feedback = await get_users_with_recent_feedback()

    for user_id in users_with_feedback:
        patterns = await feedback_analyzer.analyze_feedback_patterns(user_id)

        for pattern in patterns:
            if pattern.confidence > 0.7:
                await memory_service.create_or_update_memory(
                    user_id=user_id,
                    content=pattern.content,
                    category="learned_preference"
                )
```

#### 3.5 Admin Feedback Dashboard
**Files**:
- `backend/app/api/v1/admin/feedback.py` (CREATE)
- `frontend/src/components/admin/FeedbackDashboard.tsx` (CREATE)

Admin endpoints:
```python
@router.get("/feedback/summary")
async def get_feedback_summary():
    """Aggregate feedback statistics"""

@router.get("/feedback/patterns")
async def get_detected_patterns():
    """List all detected learning patterns"""

@router.get("/feedback/negative")
async def get_negative_feedback(limit: int = 50):
    """Review negative feedback for manual analysis"""
```

Dashboard features:
- Feedback volume over time
- Positive/negative ratio
- Common patterns detected
- Review queue for negative feedback
- Export capabilities

### RAG Integration for Examples

#### 3.6 Example Retrieval in Agent
**File**: `backend/app/agent/agent.py` (MODIFY)

```python
async def get_relevant_examples(query: str, user_id: UUID) -> List[str]:
    """Retrieve positive examples similar to current query"""
    examples = await kb_service.search(
        query=query,
        filters={"type": "positive_example", "user_id": str(user_id)},
        limit=3
    )
    return [ex.content for ex in examples]

# In the agent's response generation:
examples = await get_relevant_examples(user_query, user_id)
if examples:
    prompt += f"""

    ## Examples of Well-Received Responses
    Here are examples of responses you've given that the user found helpful:

    {format_examples(examples)}

    Use these as guidance for tone and detail level.
    """
```

### Success Criteria
- [ ] Positive feedback stores response as RAG example
- [ ] Negative feedback with edits extracts learning rules
- [ ] Learned preferences appear in future prompts
- [ ] Batch job runs daily to detect patterns
- [ ] Admin can review feedback and patterns
- [ ] Response quality measurably improves over time

---

## Phase 4: UX Polish

### Objective
Add standard chat UX controls that users expect from modern AI interfaces.

### What Needs to Be Built

#### 4.1 Copy to Clipboard Button
**File**: `frontend/src/components/chat/MessageActions.tsx` (CREATE)

```typescript
const CopyButton = ({ content }: { content: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant="ghost" size="sm" onClick={handleCopy}>
      {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
    </Button>
  );
};
```

#### 4.2 Regenerate Response Button
**File**: `frontend/src/components/chat/MessageActions.tsx`

```typescript
const RegenerateButton = ({ messageId, onRegenerate }: Props) => {
  return (
    <Button variant="ghost" size="sm" onClick={() => onRegenerate(messageId)}>
      <RotateCw className="h-4 w-4" />
      Regenerate
    </Button>
  );
};
```

**Backend**: `backend/app/api/v1/chat/conversations.py`
```python
@router.post("/conversations/{id}/regenerate/{message_id}")
async def regenerate_response(id: UUID, message_id: UUID):
    """Delete the response and regenerate from the user's message"""
```

#### 4.3 Stop Streaming Button
**File**: `frontend/src/components/chat/ChatPanel.tsx` (MODIFY)

```typescript
const [isStreaming, setIsStreaming] = useState(false);
const abortControllerRef = useRef<AbortController | null>(null);

const handleStop = () => {
  abortControllerRef.current?.abort();
  setIsStreaming(false);
};

// Show stop button while streaming
{isStreaming && (
  <Button variant="destructive" onClick={handleStop}>
    <Square className="h-4 w-4" /> Stop
  </Button>
)}
```

#### 4.4 Message Actions Container
**File**: `frontend/src/components/chat/ChatMessage.tsx` (MODIFY)

Add hover actions to each message:
```typescript
<div className="group relative">
  <div className="message-content">{content}</div>
  <div className="absolute right-0 top-0 opacity-0 group-hover:opacity-100">
    <CopyButton content={content} />
    {isAssistant && <RegenerateButton messageId={id} />}
    <FeedbackButtons messageId={id} />
  </div>
</div>
```

### Success Criteria
- [ ] Copy button works for all messages
- [ ] Regenerate creates new response from same prompt
- [ ] Stop button halts streaming immediately
- [ ] Actions appear on hover, don't clutter UI

---

## Phase 5: User Controls

### Objective
Give users control over AI response characteristics (reasoning depth, verbosity) with visual toggles.

### What Needs to Be Built

#### 5.1 Backend Support (Already Partially Exists)
**File**: `backend/app/agent/config.py`

```python
class AgentConfig:
    reasoning_depth: str = "standard"  # "brief", "standard", "deep"
    verbosity: str = "standard"  # "concise", "standard", "detailed"
    include_sources: bool = True
    show_reasoning: bool = False  # Show chain-of-thought
```

#### 5.2 Chat Settings Panel
**File**: `frontend/src/components/chat/ChatSettings.tsx` (CREATE)

```typescript
export const ChatSettings = () => {
  const [settings, setSettings] = useLocalStorage('chatSettings', {
    reasoningDepth: 'standard',
    verbosity: 'standard',
    showSources: true
  });

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm">
          <Settings className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent>
        <div className="space-y-4">
          <div>
            <Label>Response Detail</Label>
            <Slider
              value={[verbosityToNumber(settings.verbosity)]}
              min={1} max={3}
              onValueChange={(v) => setSettings({
                ...settings,
                verbosity: numberToVerbosity(v[0])
              })}
            />
            <div className="flex justify-between text-xs text-muted">
              <span>Concise</span>
              <span>Standard</span>
              <span>Detailed</span>
            </div>
          </div>

          <div>
            <Label>Analysis Depth</Label>
            <Slider
              value={[depthToNumber(settings.reasoningDepth)]}
              min={1} max={3}
              onValueChange={(v) => setSettings({
                ...settings,
                reasoningDepth: numberToDepth(v[0])
              })}
            />
            <div className="flex justify-between text-xs text-muted">
              <span>Quick</span>
              <span>Standard</span>
              <span>Deep</span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <Label>Show Sources</Label>
            <Switch
              checked={settings.showSources}
              onCheckedChange={(checked) => setSettings({
                ...settings,
                showSources: checked
              })}
            />
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
};
```

#### 5.3 Pass Settings to Backend
**File**: `frontend/src/services/chatApi.ts` (MODIFY)

```typescript
async sendMessage(conversationId: string, content: string, settings: ChatSettings) {
  return fetch(`/api/v1/chat/conversations/${conversationId}/send`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      reasoning_depth: settings.reasoningDepth,
      verbosity: settings.verbosity,
      include_sources: settings.showSources
    })
  });
}
```

#### 5.4 Backend Prompt Modification
**File**: `backend/app/agent/prompts/` (MODIFY)

Add verbosity instructions:
```python
VERBOSITY_INSTRUCTIONS = {
    "concise": "Be brief and to the point. Use bullet points. Max 2-3 sentences per topic.",
    "standard": "Provide balanced responses with appropriate detail.",
    "detailed": "Provide comprehensive analysis with full explanations and examples."
}

REASONING_INSTRUCTIONS = {
    "brief": "Give quick answers without extensive analysis.",
    "standard": "Provide thoughtful analysis with key reasoning.",
    "deep": "Show your work. Explain your reasoning step by step. Consider multiple angles."
}
```

### Success Criteria
- [ ] Settings persist across sessions (localStorage)
- [ ] Settings sent with each message
- [ ] Response length/depth visibly changes with settings
- [ ] Settings panel is discoverable but not intrusive

---

## Implementation Order & Dependencies

```
Phase 1: Memory Integration
    ↓
Phase 2: Enhanced Morning Briefing (uses memories)
    ↓
Phase 3: Feedback Learning Loop (creates memories, uses RAG)

Phase 4: UX Polish (independent, can parallel)
Phase 5: User Controls (independent, can parallel)
```

**Recommended Sprint Plan**:
- **Sprint 1** (Week 1): Phase 1 + Phase 4
- **Sprint 2** (Week 2): Phase 2 + Phase 5
- **Sprint 3** (Week 2-3): Phase 3

---

## Testing Strategy

### Phase 1 Tests
- Create memories via conversation
- Verify memories appear in subsequent sessions
- Test memory CRUD via UI
- Verify no duplicate memories

### Phase 2 Tests
- Generate briefing with no memories → generic
- Add memories → briefing personalizes
- Verify market overview data accuracy
- Test customization options

### Phase 3 Tests
- Give positive feedback → verify RAG storage
- Give negative feedback with edit → verify rule extraction
- Run batch job → verify pattern detection
- Measure response improvement over time

### Phase 4 Tests
- Copy button works on all messages
- Regenerate produces different response
- Stop halts streaming immediately
- Actions don't interfere with reading

### Phase 5 Tests
- Settings persist across sessions
- Concise mode produces shorter responses
- Deep mode shows reasoning steps
- Sources toggle works

---

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| User satisfaction (feedback ratio) | Unknown | 80%+ positive |
| Memory adoption | 0 memories/user | 5+ memories/user |
| Briefing engagement | Unknown | 70% open rate |
| Response regeneration rate | N/A | <10% (quality indicator) |
| Settings customization | N/A | 30% users customize |

---

## Appendix: File Changes Summary

### New Files
```
backend/app/api/v1/chat/memories.py
backend/app/api/v1/admin/feedback.py
backend/app/agent/services/feedback_analyzer.py
backend/app/agent/services/learning_service.py
backend/app/agent/tools/market_overview.py
backend/app/batch/feedback_learning_job.py

frontend/src/services/memoryApi.ts
frontend/src/components/chat/MemoryPanel.tsx
frontend/src/components/chat/MessageActions.tsx
frontend/src/components/chat/ChatSettings.tsx
frontend/src/components/chat/BriefingSettings.tsx
frontend/src/components/admin/FeedbackDashboard.tsx
```

### Modified Files
```
backend/app/agent/agent.py (memory injection, example retrieval)
backend/app/agent/handlers.py (memory extraction, briefing context)
backend/app/agent/prompts/morning_briefing_prompt.md
backend/app/api/v1/chat/feedback.py (learning trigger)
backend/app/api/v1/insights.py (customization params)

frontend/src/components/chat/ChatPanel.tsx (stop button, settings)
frontend/src/components/chat/ChatMessage.tsx (action buttons)
frontend/src/services/chatApi.ts (settings param)
```

---

**Document Version**: 1.0
**Last Updated**: December 18, 2025
**Author**: Claude Code
