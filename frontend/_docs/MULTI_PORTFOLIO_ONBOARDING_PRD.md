# Multi-Portfolio Onboarding - Product Requirements Document

**Created**: 2025-12-13
**Last Updated**: 2025-12-13
**Status**: ✅ **REQUIREMENTS COMPLETE - Ready for Implementation**
**Implementation Quality**: Building on existing excellent foundation

---

## Overview

**What We're Building**: Enhanced onboarding experience that allows users to add multiple portfolios during initial onboarding flow, plus post-onboarding portfolio addition capabilities.

**Problem Statement**: Current onboarding only supports single portfolio upload. Users with multiple investment accounts (IRAs, 401ks, taxable accounts, trusts) must use manual position entry for additional portfolios, which is cumbersome for bulk imports.

**Solution**: 
1. **Enhanced Initial Onboarding**: Add "Add Another Portfolio" option to onboarding success screen
2. **Enhanced Settings Flow**: Upgrade "+ Add Portfolio" to offer CSV upload or manual entry options

---

## ✅ Requirements Determined

### 1. **User Experience Philosophy** 
- **Approach**: "Adding accounts to existing profile"
- **Reference**: Follow existing family office demo pattern (`demo_familyoffice@sigmasight.com`)
- **Portfolio Relationships**: Leverage existing aggregation/consolidation features (out of scope for this PRD)

### 2. **Portfolio Limits**
- **Maximum**: Follow existing implementation limits, otherwise unlimited
- **Rationale**: Existing backend already handles multiple portfolios

### 3. **Initial Onboarding Flow Timing**
- **When**: After first portfolio is fully processed (calculations complete)
- **Why**: Simplest implementation - reuses existing flow without state complexity
- **User Journey**: Upload → Process → Success → "Add Another Portfolio" or "Continue to Dashboard"

### 4. **Success Screen Evolution**
- **Single Portfolio**: Show individual portfolio success
- **Multiple Portfolios**: Show cumulative list of all portfolios added during session
- **Format**: 
  ```
  🎉 Portfolio Ready!
  
  ✅ Schwab IRA - 45 positions imported
  ✅ Fidelity 401k - 23 positions imported  
  ✅ Personal Brokerage - 67 positions imported (just completed)
  
  [Add Another Portfolio] [Continue to Dashboard]
  ```

### 5. **Settings Entry Point**
- **Location**: Settings page "+ Add Portfolio" button (already partially implemented)
- **Current Status**: Exists at `https://sigmasight-fe-production.up.railway.app/settings`
- **Enhancement Needed**: Upgrade from single manual flow to dual option flow

### 6. **Enhanced Settings Dialog Design**
- **Current**: Single "Create Portfolio" form (manual entry only)
- **New**: Two-option approach:
  1. **"Create Portfolio from CSV"** → Redirect to adapted onboarding flow
  2. **"Create Portfolio Manually"** → Enhanced version of current manual flow

### 7. **Processing Approach for CSV Option**
- **Method**: Redirect to dedicated upload page (reuse existing onboarding page)
- **Adaptation**: Update copy/context for "additional portfolio" vs "first portfolio"
- **Flow**: Settings → CSV option → Onboarding-style upload page → Success → Back to dashboard

### 8. **Form Field Standardization**
**Both CSV and Manual flows will use identical base fields:**
- **Portfolio Name** (required) → `portfolio.name`
- **Account Name** (required) → `portfolio.account_name` 
- **Account Type** (required dropdown) → `portfolio.account_type`
- **Description** (optional) → `portfolio.description`

**Additional fields per flow:**
- **CSV Flow**: + Equity Balance (required) + CSV File Upload (required)
- **Manual Flow**: (no additional fields)

**Current Issue**: Manual flow currently missing Portfolio Name field - needs to be added for consistency.

### 9. **Portfolio Switching Interface**
- **Method**: Use existing dropdown pattern from family office demo
- **Current Implementation**: Already exists in `AccountFilter.tsx`
- **Display Format**: Two-line layout:
  ```
  Account Name (bold)
  Account Type • X positions (muted)
  ```
- **Examples**: 
  - "Demo Family Office Public Growth"
    *Taxable • 12 positions*
  - "All Accounts" 
    *View combined data from 2 accounts*

---

## 🔧 Technical Requirements

### Backend Validation Needed
1. **Concurrent Batch Processing**: Validate that backend can handle multiple batch jobs for same user
   - If NOT safe: Implement queue/sequential processing in frontend
   - If SAFE: Allow parallel portfolio processing

2. **All Accounts Aggregation**: Research how backend/frontend handles portfolio aggregation
   - Does it happen automatically when multiple portfolios exist?
   - Do we need to manually trigger aggregation after all portfolios are processed?
   - Document the current aggregation service behavior

### Frontend Architecture
- **State Management**: Enhance existing Zustand portfolio store for multi-portfolio onboarding session tracking
- **Routing**: Adapt existing onboarding routes to handle "additional portfolio" context
- **Success Screen**: Update to show cumulative session progress

---

## 📋 Implementation Scope

### Phase 1: Enhanced Initial Onboarding
1. **Success Screen Enhancement**
   - Add "Add Another Portfolio" button to existing success screen
   - Implement cumulative portfolio list display
   - Track session-level portfolio creation

2. **Onboarding Flow Adaptation** 
   - Add context awareness (first vs additional portfolio)
   - Update copy/messaging for additional portfolio flow
   - Maintain all existing functionality (validation, processing, etc.)

### Phase 2: Enhanced Settings Flow
1. **Dialog Upgrade**
   - Replace current single-option form with two-option approach
   - Add missing Portfolio Name field to manual flow
   - Add Description field to CSV flow

2. **CSV Option Implementation**
   - Redirect to adapted onboarding page
   - Return to dashboard after completion
   - Update navigation breadcrumbs

### Phase 3: Integration & Polish
1. **Portfolio Switching**
   - Ensure dropdown works properly with newly created portfolios
   - Validate aggregation service integration
   - Test progressive disclosure behavior

2. **Error Handling**
   - Handle partial failures in multi-portfolio sessions
   - Validate batch processing queue management
   - Test concurrent user scenarios

---

## 🎯 User Journey Examples

### Initial Onboarding (Multi-Portfolio)
1. User completes registration → auto-login
2. Upload Portfolio 1 (Schwab IRA) → processing → success screen shows Portfolio 1
3. Click "Add Another Portfolio" → return to upload form (cleared)
4. Upload Portfolio 2 (Fidelity 401k) → processing → success screen shows Portfolio 1 + Portfolio 2
5. Click "Add Another Portfolio" → repeat process
6. Click "Continue to Dashboard" → see all portfolios in dropdown

### Post-Onboarding Addition
1. User in dashboard → Settings → "+ Add Portfolio"
2. Dialog with two options: CSV or Manual
3. Choose "CSV" → redirect to upload page (adapted copy)
4. Complete upload → return to dashboard with new portfolio in dropdown
5. OR choose "Manual" → enhanced form → create empty portfolio → add positions later

---

## ✅ Additional Requirements Finalized

### 12. **Default Portfolio Selection**
- **Decision**: First created portfolio
- **Rationale**: Provides consistent, predictable user experience

### 13. **URL Structure** 
- **Decision**: Keep current state-based implementation
- **Current Pattern**: Static URLs (e.g., `/command-center`) with portfolio selection via Zustand store
- **Benefits**: Smooth switching without page reloads, existing proven architecture

### 14. **State Persistence**
- **Decision**: Keep current behavior
- **Current**: Last viewed portfolio persists across sessions via localStorage
- **No changes**: Portfolio-specific settings and navigation state remain as-is

### 15. **Backward Compatibility**
- **Decision**: Keep current progressive disclosure pattern
- **Behavior**: Portfolio selector automatically appears when user has 2+ portfolios
- **Single-portfolio users**: UI remains clean and simple

### 16. **Partial Failures**
- **Decision**: Show accurate status for each portfolio
- **Support**: Mixed states (import success + batch failure, import failure, etc.)
- **User flow**: Can continue to dashboard and retry failed operations later
- **Example**: ✅ Schwab IRA (complete), ⚠️ Fidelity 401k (analytics pending), ❌ Personal Brokerage (import failed)

### 17. **Portfolio Deletion**
- **Decision**: Keep current soft delete with improved UX messaging
- **Current**: Soft delete preserves all data, sets `deleted_at` timestamp
- **Enhancement**: Update dialog text to "Archive portfolio? Data can be recovered by contacting support"
- **Safety**: Cannot delete last portfolio, user ownership validation maintained

### 18. **Portfolio Validation**
- **Account Names**: Keep current uniqueness requirement per user
- **Account Types**: Allow multiple (e.g., multiple IRAs from different brokers)
- **Equity Balance**: Minimum $1, no maximum limit
- **Additional**: Portfolio name (1-255 chars), description (0-1000 chars), account name format validation

### 19. **Calculation Dependencies**
- **Decision**: Out of scope for onboarding PRD
- **Current**: Portfolios calculate independently, then aggregate for "All Accounts" view
- **Rationale**: Backend architecture decision, not onboarding flow requirement

### 20. **Implementation Scope (MVP)**
- **Decision**: Option C - Enhanced onboarding + enhanced Settings + field standardization
- **Includes**: "Add Another Portfolio" button, dual-option Settings dialog, Portfolio Name field addition
- **Phase 1 scope**: Complete consistent multi-portfolio experience

### 21. **Future Features**
- **Decision**: Future enhancements TBD
- **Rationale**: Keep PRD focused, avoid scope creep

### 22. **Visual Design**
- **Decision**: Follow current implementation
- **Pattern**: Same dashboard with portfolio selector dropdown
- **Proven**: Already working well in family office demo

### 23. **Breadcrumb Strategy**
- **Decision**: Follow current implementation  
- **Pattern**: Portfolio name displayed in dropdown selector
- **Format**: Two-line display (Account Name + Account Type • X positions)

### 24. **State Management Integration**
- **Decision**: Enhance existing Zustand store
- **Approach**: Add onboarding session tracking overlay to current architecture
- **Benefits**: Builds on proven foundation, maintains backward compatibility

---

## 🔍 Research & Validation Required

### Technical Investigation Needed:
1. **Backend Batch Processing**: Test concurrent batch job safety
2. **Aggregation Service**: Document automatic vs manual aggregation triggers  
3. **Existing Settings Implementation**: Validate what works/doesn't work with current "+ Add Portfolio"
4. **Family Office Demo**: Analyze existing multi-portfolio patterns and UX

### Dependencies:
- Backend team validation of concurrent processing capabilities
- Frontend investigation of aggregation service integration
- UX review of family office demo account functionality

---

## 🎨 Design Patterns to Follow

### Established Patterns (Keep Consistent):
- **Progressive Disclosure**: Hide complexity for single-portfolio users
- **Two-Line Dropdown Format**: Account name + metadata display
- **Sequential Processing**: One portfolio at a time to avoid complexity
- **Field Standardization**: Portfolio Name + Account Name + Account Type + Description

### Enhancement Patterns:
- **Session Awareness**: Track cumulative onboarding progress
- **Context Adaptation**: Different copy for first vs additional portfolios
- **Option Disclosure**: Present CSV vs Manual options clearly
- **Graceful Degradation**: Handle failures without losing previous progress

## 📋 Zustand Store Enhancements Required

### Onboarding Session State
```typescript
onboardingSession: {
  isActive: boolean
  portfoliosAdded: string[]  // Portfolio IDs added this session
  currentStep: 'upload' | 'processing' | 'success'
  sessionStartedAt: string | null
} | null
```

### New Actions Needed
- `startOnboardingSession()` - Begin session tracking
- `addToOnboardingSession(portfolioId)` - Add portfolio to session
- `completeOnboardingSession()` - End session, set default portfolio
- `resetForNextUpload()` - Clear upload state, keep session active

### New Getters Needed  
- `getOnboardingPortfolios()` - Return session portfolios
- `isInOnboardingSession()` - Check session status
- `getOnboardingProgress()` - Count completed vs total
- `canAddAnotherPortfolio()` - Show "Add Another" button logic

### Integration Notes
- Session state is **temporary** (doesn't persist to localStorage)
- Build on existing portfolio CRUD operations
- Maintain full backward compatibility
- Use for cumulative success screen display

---

## ✅ **Implementation Ready**

All requirements defined. This PRD provides complete specifications for implementing multi-portfolio onboarding while leveraging the existing excellent foundation. Ready for development planning and execution.