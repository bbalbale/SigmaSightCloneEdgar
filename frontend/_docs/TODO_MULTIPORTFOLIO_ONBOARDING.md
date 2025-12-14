# TODO: Multi-Portfolio Onboarding Implementation

**Created**: 2025-12-13  
**Status**: 🚧 **Ready for Implementation**  
**Reference PRD**: `MULTI_PORTFOLIO_ONBOARDING_PRD.md`  
**Target**: Prototype/MVP implementation  

---

## 🎯 **Implementation Overview**

**Goal**: Enable users to add multiple portfolios during initial onboarding and via Settings page  
**Scope**: Prototype with essential features only  
**Architecture**: Build on existing proven foundation  

---

## 📋 **Phase 1: Enhanced Initial Onboarding**

### 1.1 ✅ **Enhance Zustand Portfolio Store**
**File**: `frontend/src/stores/portfolioStore.ts`

**Add onboarding session state:**
```typescript
onboardingSession: {
  isActive: boolean
  portfoliosAdded: string[]  // Portfolio IDs added this session
  currentStep: 'upload' | 'processing' | 'success'
  sessionStartedAt: string | null
} | null
```

**Add session management actions:**
- [ ] `startOnboardingSession()` - Begin session tracking
- [ ] `addToOnboardingSession(portfolioId)` - Add portfolio to session
- [ ] `completeOnboardingSession()` - End session, set default portfolio (first created)
- [ ] `resetForNextUpload()` - Clear upload state, keep session active

**Add session getters:**
- [ ] `getOnboardingPortfolios()` - Return session portfolios
- [ ] `isInOnboardingSession()` - Check session status
- [ ] `getOnboardingProgress()` - Count completed vs total
- [ ] `canAddAnotherPortfolio()` - Show "Add Another" button logic

**Integration notes:**
- [ ] Session state is temporary (doesn't persist to localStorage)
- [ ] Build on existing portfolio CRUD operations
- [ ] Maintain full backward compatibility

---

### 1.2 ✅ **Update Success Screen Component**
**File**: `frontend/src/components/onboarding/UploadSuccess.tsx`

**Current behavior**: Shows individual portfolio success  
**New behavior**: Shows cumulative session progress

**Enhancements needed:**
- [ ] **Import session hooks**: `useOnboardingSession`, `useOnboardingPortfolios`
- [ ] **Cumulative display**: Show all portfolios added in current session
- [ ] **Add Another button**: Conditionally show based on `canAddAnotherPortfolio()`
- [ ] **Session progress**: Display format from PRD:
  ```
  🎉 Portfolio Ready!
  
  ✅ Schwab IRA - 45 positions imported
  ✅ Fidelity 401k - 23 positions imported  
  ✅ Personal Brokerage - 67 positions imported (just completed)
  
  [Add Another Portfolio] [Continue to Dashboard]
  ```

**Navigation logic:**
- [ ] **"Add Another Portfolio"** → `resetForNextUpload()` → return to upload form
- [ ] **"Continue to Dashboard"** → `completeOnboardingSession()` → navigate to `/command-center`

**Celebration requirement:**
- [ ] **Console logging only**: `console.log('🎉 Portfolio upload successful!')`
- [ ] **No confetti library dependency** for prototype

---

### 1.3 ✅ **Update Upload Form Integration**
**Files**: `frontend/src/hooks/usePortfolioUpload.ts`, `frontend/app/onboarding/upload/page.tsx`

**Session integration:**
- [ ] **Start session**: Call `startOnboardingSession()` on first portfolio upload
- [ ] **Add to session**: Call `addToOnboardingSession(portfolioId)` after successful upload
- [ ] **Track progress**: Maintain session state through processing steps

**Navigation enhancement:**
- [ ] **Context awareness**: Update copy for "additional portfolio" vs "first portfolio"
- [ ] **Form reset**: Clear form when returning from "Add Another Portfolio"

---

## 📋 **Phase 2: Enhanced Settings Flow**

### 2.1 ✅ **Upgrade Settings Portfolio Management**
**File**: `frontend/src/components/settings/PortfolioManagement.tsx`

**Current**: Single manual portfolio creation form  
**New**: Two-option approach

**UI Enhancement:**
- [ ] **Replace single form** with two-option dialog:
  - [ ] **"Create Portfolio from CSV"** button
  - [ ] **"Create Portfolio Manually"** button

**CSV Option Flow:**
- [ ] **Redirect to onboarding**: Navigate to adapted onboarding upload page
- [ ] **Context parameter**: Pass "additional_portfolio" context
- [ ] **Return navigation**: After completion, return to dashboard (not continue onboarding)

**Manual Option Enhancement:**
- [ ] **Add Portfolio Name field**: Currently missing, needed for consistency
- [ ] **Keep existing fields**: Account Name, Account Type, Description
- [ ] **Field standardization**: Match onboarding form structure

---

### 2.2 ✅ **Adapt Onboarding for Additional Portfolios**
**File**: `frontend/app/onboarding/upload/page.tsx`

**Context awareness:**
- [ ] **Check URL params**: Detect if called from Settings vs initial onboarding
- [ ] **Adapt copy**: 
  - Initial: "Let's get your positions loaded into SigmaSight"
  - Additional: "Add another portfolio to your account"
- [ ] **Navigation target**: 
  - Initial onboarding: Success screen with "Add Another" option
  - Additional portfolio: Direct return to dashboard after completion

**Integration points:**
- [ ] **Skip session management**: Don't use onboarding session for Settings-initiated uploads
- [ ] **Direct completion**: Complete and redirect to dashboard immediately

---

### 2.3 ✅ **Field Standardization**
**Ensure consistent fields across both flows:**

**Standard Fields (All Flows)**:
- [ ] **Portfolio Name** (required) → `portfolio.name`
- [ ] **Account Name** (required) → `portfolio.account_name` 
- [ ] **Account Type** (required dropdown) → `portfolio.account_type`
- [ ] **Description** (optional) → `portfolio.description`

**Flow-Specific Fields**:
- [ ] **CSV Flow**: + Equity Balance (required) + CSV File Upload (required)
- [ ] **Manual Flow**: (no additional fields)

**Validation Enhancement:**
- [ ] **Portfolio Name**: 1-255 characters
- [ ] **Account Name**: Unique per user, alphanumeric + punctuation
- [ ] **Description**: 0-1000 characters  
- [ ] **Equity Balance**: Minimum $1, no maximum

---

## 📋 **Phase 3: Integration & Testing**

### 3.1 ✅ **Portfolio Switching Integration**
**File**: `frontend/src/components/portfolio/AccountFilter.tsx`

**Verification needed:**
- [ ] **New portfolios appear**: Ensure newly created portfolios show in dropdown
- [ ] **Default selection**: First created portfolio selected on login
- [ ] **Progressive disclosure**: Dropdown appears when user has 2+ portfolios

**Testing:**
- [ ] **Single → Multi transition**: Add second portfolio, verify dropdown appears
- [ ] **Session persistence**: Last viewed portfolio remembered across sessions
- [ ] **Navigation consistency**: Portfolio selection works across all pages

---

### 3.2 ✅ **Error Handling & Edge Cases**
**Basic error handling for prototype:**

**Partial Failures:**
- [ ] **Mixed states support**: Show accurate status per portfolio:
  - ✅ Full success (import + analytics complete)
  - ⚠️ Partial success (import complete, analytics failed)
  - ❌ Import failed (validation errors)
- [ ] **Continue to dashboard**: Allow navigation even with partial failures
- [ ] **Retry later**: Failed analytics can be retried from dashboard

**Basic Edge Cases:**
- [ ] **Session interruption**: Handle page reload during onboarding session
- [ ] **Duplicate names**: Prevent duplicate account names per user
- [ ] **Last portfolio**: Cannot delete last remaining portfolio

---

### 3.3 ✅ **Backend Validation Requirements**
**Research and validation needed:**

**Concurrent Batch Processing:**
- [ ] **Test concurrent batches**: Verify backend handles multiple batch jobs for same user
- [ ] **If unsafe**: Implement frontend queue (wait for current batch before allowing next)
- [ ] **If safe**: Allow parallel portfolio processing

**Aggregation Service:**
- [ ] **Research "All Accounts"**: How does aggregation happen?
- [ ] **Manual trigger needed?**: Does aggregation occur automatically?
- [ ] **Document behavior**: Update PRD with findings

---

## 🔧 **Technical Implementation Notes**

### **File Structure Changes**
```
frontend/src/
├── stores/portfolioStore.ts          # Enhanced with session state
├── components/onboarding/
│   └── UploadSuccess.tsx             # Cumulative display + Add Another button
├── components/settings/
│   └── PortfolioManagement.tsx       # Two-option dialog approach
├── hooks/usePortfolioUpload.ts       # Session integration
└── app/onboarding/upload/page.tsx    # Context awareness
```

### **Dependencies**
- [ ] **No new dependencies**: Use existing libraries and patterns
- [ ] **No confetti library**: Console logging only for prototype
- [ ] **Existing validation**: Use current CSV template and error handling

### **Testing Strategy**
- [ ] **Use demo accounts**: Test with existing family office demo
- [ ] **Incremental testing**: Test each phase before moving to next
- [ ] **Cross-browser**: Verify dropdown and navigation work consistently

---

## ✅ **Prototype Definition of Done**

**Success Criteria:**
- [ ] **Initial Onboarding**: User can add multiple portfolios with cumulative success screen
- [ ] **Settings Addition**: User can add portfolios via CSV or Manual from Settings
- [ ] **Field Consistency**: All flows use Portfolio Name + Account Name + Description
- [ ] **Navigation**: "Continue to Dashboard" goes to `/command-center`
- [ ] **Portfolio Switching**: Dropdown works with newly created portfolios
- [ ] **Error Handling**: Basic mixed states supported, can continue with failures
- [ ] **Backend Integration**: Concurrent processing validated and handled appropriately

**Deferred for Post-Prototype:**
- Advanced error messaging
- Complex edge case handling  
- Mobile optimizations
- Detailed CSV schema documentation
- Metrics and telemetry
- Advanced timeout handling

---

## 📚 **References**

- **PRD**: `MULTI_PORTFOLIO_ONBOARDING_PRD.md` - Complete requirements
- **Existing Implementation**: Family office demo (`demo_familyoffice@sigmasight.com`)
- **Current Architecture**: Investigation shows progressive disclosure already working
- **API Docs**: Backend supports multiple portfolios via existing endpoints

---

**Ready for Implementation!** 🚀  
Start with Phase 1.1 (Zustand store enhancements) and work through each phase sequentially.