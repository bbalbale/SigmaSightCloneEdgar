# AI Chat Frontend Migration - Implementation Checklist

**AI Agent Executor:** Follow these steps in order. Check off each item as you complete it.

---

## Pre-Implementation

- [ ] Read `MIGRATION_PLAN.md` completely
- [ ] Verify frontend services exist in `frontend/services/api/`
- [ ] Confirm OpenAI API key is available
- [ ] Backup current chat implementation
- [ ] Create feature branch: `git checkout -b feature/frontend-ai-chat`

---

## Phase 1: Setup (30 minutes)

### 1.1 Install Dependencies
- [ ] `cd frontend && npm install openai`
- [ ] Verify installation: `npm list openai`

### 1.2 Create Directory Structure
- [ ] Create `frontend/services/ai/`
- [ ] Create `frontend/lib/ai/prompts/`
- [ ] Create `frontend/app/api/ai/`

### 1.3 Environment Configuration
- [ ] Add `OPENAI_API_KEY` to `.env.local`
- [ ] Add `OPENAI_MODEL=gpt-4-turbo-preview` to `.env.local`
- [ ] Test: `echo $OPENAI_API_KEY` (should show key)

---

## Phase 2: Create Services (1-2 hours)

### 2.1 OpenAI Service
- [ ] Create `frontend/services/ai/openaiService.ts`
- [ ] Implement initialization logic
- [ ] Test connection to OpenAI

### 2.2 Tool Definitions
- [ ] Create `frontend/services/ai/tools.ts`
- [ ] Copy tool definitions from backend
- [ ] Map each tool to existing frontend service:
  - [ ] `get_portfolio_complete` → `portfolioService.getComplete()`
  - [ ] `get_positions_details` → `positionsService.getDetails()`
  - [ ] `get_prices_historical` → `pricesService.getHistorical()`
  - [ ] `get_current_quotes` → `pricesService.getCurrentQuotes()`
  - [ ] `get_factor_etf_prices` → `pricesService.getFactorETFPrices()`
- [ ] Test each tool wrapper independently

### 2.3 Chat Service
- [ ] Create `frontend/services/ai/chatService.ts`
- [ ] Implement `streamResponse()` method
- [ ] Implement tool execution loop
- [ ] Implement continuation with tool results
- [ ] Add error handling

---

## Phase 3: Migrate Prompts (30 minutes)

### 3.1 Copy Prompt Files
- [ ] Copy `backend/app/agent/prompts/common_instructions.md` → `frontend/lib/ai/prompts/common_instructions.md`
- [ ] Copy `backend/app/agent/prompts/green_v001.md` → `frontend/lib/ai/prompts/green_v001.md`
- [ ] Copy `backend/app/agent/prompts/blue_v001.md` → `frontend/lib/ai/prompts/blue_v001.md`
- [ ] Copy `backend/app/agent/prompts/indigo_v001.md` → `frontend/lib/ai/prompts/indigo_v001.md`
- [ ] Copy `backend/app/agent/prompts/violet_v001.md` → `frontend/lib/ai/prompts/violet_v001.md`

### 3.2 Prompt Manager
- [ ] Create `frontend/lib/ai/promptManager.ts`
- [ ] Implement prompt loading
- [ ] Implement variable injection
- [ ] Test prompt generation

---

## Phase 4: Update UI (1 hour)

### 4.1 Find Current Chat Component
- [ ] Locate: `frontend/app/(authenticated)/chat/[id]/page.tsx` (or similar)
- [ ] Document current data flow
- [ ] Identify where messages are sent

### 4.2 Replace Backend Call
- [ ] Remove: Fetch to `/api/v1/chat/send`
- [ ] Add: Import `chatService`
- [ ] Replace: `handleSendMessage()` to use `chatService.streamResponse()`
- [ ] Update: State management for streaming

### 4.3 Update UI Handlers
- [ ] Implement `onToken` callback (update streaming text)
- [ ] Implement `onToolCall` callback (show tool execution)
- [ ] Implement `onToolResult` callback (show tool result)
- [ ] Implement `onError` callback (show error toast)
- [ ] Implement `onDone` callback (save message)

---

## Phase 5: Testing (1-2 hours)

### 5.1 Unit Tests
- [ ] Test tool execution: Each tool individually
- [ ] Test prompt manager: Load all modes
- [ ] Test chat service: Mock OpenAI responses

### 5.2 Integration Tests
- [ ] Test full flow: User message → AI response
- [ ] Test tool calls: AI calls tools correctly
- [ ] Test streaming: Tokens arrive in order
- [ ] Test errors: API failures handled gracefully

### 5.3 Manual Testing
- [ ] Create new conversation
- [ ] Send: "Show me my portfolio"
  - [ ] Verify: AI calls `get_portfolio_complete`
  - [ ] Verify: Portfolio data displays correctly
- [ ] Test each tool:
  - [ ] "Show me position details"
  - [ ] "Get historical prices for AAPL"
  - [ ] "What's the current price of MSFT?"
  - [ ] "Show me factor ETF prices"
- [ ] Test mode switching:
  - [ ] `/mode green` (educational)
  - [ ] `/mode blue` (quantitative)
  - [ ] `/mode indigo` (strategic)
  - [ ] `/mode violet` (risk-focused)
- [ ] Test with different portfolios
- [ ] Test error cases:
  - [ ] Invalid portfolio ID
  - [ ] Network error
  - [ ] OpenAI API error

### 5.4 Performance Testing
- [ ] Measure: Time to first token
- [ ] Measure: Time per tool call
- [ ] Compare: Frontend vs Backend (should be 50-80ms faster)
- [ ] Profile: Memory usage
- [ ] Check: No memory leaks in streaming

---

## Phase 6: Cleanup (30 minutes)

### 6.1 Backend Deprecation
- [ ] Add deprecation notice to `backend/app/api/v1/chat/send.py`
- [ ] Document: Why deprecated, where new implementation is
- [ ] Update: API documentation

### 6.2 Documentation
- [ ] Update: Frontend README with new architecture
- [ ] Document: How to run tests
- [ ] Document: How to add new tools
- [ ] Document: OpenAI key setup

### 6.3 Code Quality
- [ ] Run: `npm run lint` (fix all issues)
- [ ] Run: `npm run type-check` (fix all TypeScript errors)
- [ ] Format: `npm run format`
- [ ] Review: Remove console.logs

---

## Phase 7: Deployment (1 hour)

### 7.1 Environment Setup
- [ ] Add `OPENAI_API_KEY` to production env
- [ ] Verify: Key is encrypted/secure
- [ ] Test: Key works in production

### 7.2 Build
- [ ] Run: `npm run build`
- [ ] Fix: Any build errors
- [ ] Test: Production build locally

### 7.3 Deploy
- [ ] Deploy: To staging environment
- [ ] Test: Full flow in staging
- [ ] Monitor: Logs for errors
- [ ] Deploy: To production (if staging passes)

### 7.4 Post-Deployment
- [ ] Monitor: OpenAI API usage
- [ ] Monitor: Error rates
- [ ] Monitor: Performance metrics
- [ ] Get: User feedback

---

## Rollback Plan (if needed)

### If Critical Issues Found
- [ ] Revert: Git commit
  ```bash
  git revert HEAD
  git push origin main --force
  ```
- [ ] Redeploy: Previous version
- [ ] Remove: Deprecation notice from backend
- [ ] Communicate: Issue to team

---

## Success Criteria

Must achieve ALL before considering complete:

- [ ] ✅ Chat interface works identically to before
- [ ] ✅ All 5 tools execute correctly
- [ ] ✅ 50-80ms latency improvement measured
- [ ] ✅ No errors in console
- [ ] ✅ Mode switching works
- [ ] ✅ Message history persists
- [ ] ✅ Error handling works
- [ ] ✅ Performance is better or equal

---

## Time Estimate

**Total: 5-7 hours**

- Phase 1: 30 min
- Phase 2: 1-2 hours
- Phase 3: 30 min
- Phase 4: 1 hour
- Phase 5: 1-2 hours
- Phase 6: 30 min
- Phase 7: 1 hour

---

## Need Help?

**Common Issues:**

1. **OpenAI API errors**
   - Check: API key is valid
   - Check: Account has credits
   - Check: Rate limits

2. **Tool execution failures**
   - Check: Frontend services are working
   - Check: Authentication token is passed
   - Check: Network requests in DevTools

3. **Streaming not working**
   - Check: Response headers
   - Check: SSE format is correct
   - Check: Browser supports EventSource

4. **Performance not improved**
   - Measure: Each phase of the flow
   - Profile: With Chrome DevTools
   - Compare: Network waterfall

**Reference Files:**
- Main plan: `MIGRATION_PLAN.md`
- Architecture: `ARCHITECTURE.md`
- Backend code: `backend/app/agent/`
- Frontend services: `frontend/services/api/`

---

**Good luck! 🚀**
