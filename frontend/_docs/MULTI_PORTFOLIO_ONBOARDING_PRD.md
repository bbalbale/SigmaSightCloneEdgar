# Multi-Portfolio Onboarding - Product Requirements Document

**Created**: 2025-12-13
**Last Updated**: 2025-12-13
**Status**: 🚧 **DRAFT - Requirements Gathering in Progress**
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

## 🚧 Open Questions for Future Discussion

### **Question 12: Default Portfolio**
Which portfolio should be displayed when user logs in?
- Most recently viewed?
- Largest by balance? 
- User-designated primary?
- First created?

### **Question 13: URL Structure** 
How should portfolio-specific pages be addressed?
- `/portfolio/{portfolio-id}/dashboard`?
- `/dashboard?portfolio={id}`?
- Keep current URLs with state management?

### **Question 14: State Persistence**
Should the app remember:
- Last viewed portfolio across sessions?
- Portfolio-specific settings/preferences?
- Navigation state per portfolio?

### **Question 15: Backward Compatibility**
How should existing single-portfolio users be handled?
- Automatically upgrade their experience?
- Keep current flow for simplicity?
- Opt-in to multi-portfolio features?

### **Question 16: Partial Failures**
If user uploads 3 portfolios and 1 fails:
- Show success for completed portfolios?
- Treat entire batch as failed?
- Allow retry of failed portfolios only?

### **Question 17: Portfolio Deletion**
Should users be able to:
- Delete portfolios after creation?
- Archive vs permanently delete?
- What happens to calculations/history?

### **Question 18: Portfolio Validation**
Should there be restrictions on:
- Duplicate account names across portfolios?
- Same account type multiple times?
- Minimum/maximum equity balance per portfolio?

### **Question 19: Calculation Dependencies**
Should portfolio calculations:
- Run independently for each portfolio?
- Consider cross-portfolio correlations? 
- Share market data across portfolios?

### **Question 20: Implementation Scope Prioritization**
What's the minimum viable multi-portfolio experience?
- Just the additional portfolio flow?
- Basic portfolio switching?
- Full multi-portfolio dashboard?

### **Question 21: Future Features**
What advanced multi-portfolio features might come later?
- Portfolio comparison views?
- Cross-portfolio rebalancing suggestions?
- Consolidated reporting?

### **Question 22: Visual Design**
Should multi-portfolio users see:
- Same dashboard with portfolio selector?
- Portfolio-specific dashboards?
- Combined overview dashboard + individual views?

### **Question 23: Breadcrumb Strategy**
How should users understand which portfolio they're viewing?
- Portfolio name in page title?
- Persistent indicator/badge?
- Context-aware navigation?

### **Question 24: Existing Implementation Integration**
Should we:
- Extend existing Zustand store to handle multiple portfolios?
- Create new multi-portfolio state management?
- Keep single-portfolio approach with switching logic?

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

---

**Next Steps**: Complete open questions 12-24 to finalize PRD and begin implementation planning.