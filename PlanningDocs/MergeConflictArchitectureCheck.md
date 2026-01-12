Merge Conflict Analysis: Architecture V2 vs Current Main (Phase 7.4.1 + 7.6)

  Executive Summary

  The Architecture V2 Implementation Plan fundamentally restructures the batch processing to decouple symbol-level data from portfolio-level analytics. This will conflict significantly with the Phase 7.4.1 and 7.6 changes just deployed, particularly because:

  1. Phase 7.x tracking infrastructure - We just enhanced it; V2 deprecates it for onboarding
  2. Unified progress screen (Phase 7.6) - We just built a 9-phase tracker; V2 eliminates the 15-30 min wait entirely

  ---
  High-Risk Conflict Files
  File: batch_orchestrator.py
  Our Changes (Phase 7.4.1/7.6): Added is_final_date param
  V2 Changes: Remove symbol processing entirely
  Conflict Severity: 🔴 HIGH
  ────────────────────────────────────────
  File: OnboardingProgress.tsx
  Our Changes (Phase 7.4.1/7.6): Full rewrite for unified screen
  V2 Changes: DEPRECATED - onboarding is instant
  Conflict Severity: 🔴 HIGH
  ────────────────────────────────────────
  File: useOnboardingStatus.ts
  Our Changes (Phase 7.4.1/7.6): Added partial to terminal states
  V2 Changes: SIMPLIFIED - no 9-phase tracking
  Conflict Severity: 🔴 HIGH
  ────────────────────────────────────────
  File: progress/page.tsx
  Our Changes (Phase 7.4.1/7.6): Unified component routing
  V2 Changes: Simplified to ready/pending/error
  Conflict Severity: 🔴 HIGH
  ---
  Detailed Conflict Analysis

  1. backend/app/batch/batch_orchestrator.py

  Our Phase 7.4.1 change:
  # Added is_final_date parameter
  async def _run_phases_2_through_6(
      ...
      is_final_date: bool = False,
  ):
      is_historical = calculation_date < date.today() and not is_final_date

  V2 wants:
  # Remove symbol processing entirely
  # Portfolio batch NO LONGER runs symbol calculations
  # Phase 1.5 REMOVED - now in separate symbol_batch_runner

  Impact: V2 will rewrite this file significantly. The is_final_date fix becomes irrelevant because V2's onboarding doesn't run any phases - it uses pre-computed symbol data.

  ---
  2. frontend/src/components/onboarding/OnboardingProgress.tsx

  Our Phase 7.6 changes:
  - Unified screen for running/completed/partial/failed states
  - 9-phase progress visualization retained on completion
  - Activity log preserved
  - ~270 lines of code

  V2 wants:
  // Section 10.7: Onboarding is <5 seconds, not 15-30 minutes
  // Case 1: Immediate success
  <div className="onboarding-complete">
    <h2>✅ Your portfolio is ready!</h2>
    <Button onClick={() => navigate('/dashboard')}>
      View Analytics
    </Button>
  </div>

  Impact: Our entire unified progress screen becomes OBSOLETE. V2's onboarding is instant - there's no 9-phase progress to track. The component we just built would be deprecated.

  ---
  3. frontend/src/hooks/useOnboardingStatus.ts

  Our Phase 7.6 changes:
  // Added partial to terminal states
  if (response.status === 'completed' || response.status === 'partial' || response.status === 'failed') {
    // Stop polling
  }

  V2 wants:
  // Section 10.3.2: Simplified status response
  interface OnboardingStatusResponse {
    portfolio_id: string
    status: 'ready' | 'pending' | 'error'  // NO 'running', 'completed', 'partial', 'failed'
    analytics_available: boolean
    pending_symbols: string[] | null
    estimated_seconds_remaining: number | null
    message: string
  }

  Impact: The status enum changes completely. Our partial addition becomes meaningless. The 2-second polling for 15+ minutes becomes 5-second polling for <60 seconds.

  ---
  4. backend/app/batch/batch_run_tracker.py

  Our Phase 7.4 additions:
  - BatchActivityLogHandler for capturing logs
  - 9-phase tracking with PHASE_ORDER
  - CompletedRunStatus with 60-second TTL

  V2 says:
  "KEEP AS-IS - Reused by symbol_batch_runner for Phase 7.x tracking"

  Impact: LOW conflict - V2 keeps this for the daily symbol batch. However, it won't be used for onboarding anymore.

  ---
  What Becomes Obsolete
  ┌──────────────────────────────────────┬────────────┬─────────────────────────────────────────────┐
  │              Component               │   Status   │                   Reason                    │
  ├──────────────────────────────────────┼────────────┼─────────────────────────────────────────────┤
  │ OnboardingProgress.tsx (Phase 7.6)   │ DEPRECATED │ Onboarding is instant, no 9-phase UI needed │
  ├──────────────────────────────────────┼────────────┼─────────────────────────────────────────────┤
  │ OnboardingComplete.tsx               │ DEPRECATED │ Already marked deprecated, V2 confirms      │
  ├──────────────────────────────────────┼────────────┼─────────────────────────────────────────────┤
  │ OnboardingError.tsx                  │ DEPRECATED │ Already marked deprecated, V2 confirms      │
  ├──────────────────────────────────────┼────────────┼─────────────────────────────────────────────┤
  │ useOnboardingStatus.ts polling logic │ SIMPLIFIED │ From 15-30 min to <60 sec                   │
  ├──────────────────────────────────────┼────────────┼─────────────────────────────────────────────┤
  │ is_final_date fix (7.4.1)            │ IRRELEVANT │ Onboarding doesn't run phases               │
  └──────────────────────────────────────┴────────────┴─────────────────────────────────────────────┘
  ---
  What Gets Preserved
  ┌────────────────────────────┬────────┬───────────────────────────────────┐
  │         Component          │ Status │              Reason               │
  ├────────────────────────────┼────────┼───────────────────────────────────┤
  │ batch_run_tracker.py       │ REUSED │ For daily symbol batch monitoring │
  ├────────────────────────────┼────────┼───────────────────────────────────┤
  │ Phase 7.x admin visibility │ KEPT   │ Admin can monitor symbol batch    │
  ├────────────────────────────┼────────┼───────────────────────────────────┤
  │ Activity logging           │ KEPT   │ For symbol batch, not onboarding  │
  └────────────────────────────┴────────┴───────────────────────────────────┘
  ---
  Recommended Merge Strategy

  1. Don't merge yet - V2 is a fundamental architectural change
  2. Implement V2 first - The Phase 7.6 unified screen becomes obsolete
  3. Keep Phase 7.x infrastructure - Repurpose for symbol batch monitoring
  4. Remove onboarding-specific tracking - V2 makes onboarding instant

  ---
  Timeline Consideration

  Per V2 Section 5: Migration takes ~6 weeks:
  - Week 1: Database schema
  - Week 2: Symbol batch runner
  - Week 3: Portfolio cache service
  - Week 4: Integration
  - Week 5: Onboarding flow
  - Week 6: Cleanup

  The Phase 7.6 work would be replaced in Week 5 when V2's instant onboarding is implemented.

  ---
  Summary
  ┌────────────┬────────────────┬──────────────────────────────────┐
  │ Risk Level │ Files Affected │            Resolution            │
  ├────────────┼────────────────┼──────────────────────────────────┤
  │ 🔴 High    │ 4 files        │ V2 replaces our changes entirely │
  ├────────────┼────────────────┼──────────────────────────────────┤
  │ 🟡 Medium  │ 2 files        │ V2 simplifies/modifies           │
  ├────────────┼────────────────┼──────────────────────────────────┤
  │ 🟢 Low     │ 3 files        │ V2 keeps/reuses                  │
  └────────────┴────────────────┴──────────────────────────────────┘
  Bottom line: The Phase 7.4.1/7.6 work was designed for the current 15-30 minute onboarding flow. Architecture V2 eliminates that flow entirely, making our unified progress screen obsolete. The merge would be a rewrite, not a conflict resolution.
