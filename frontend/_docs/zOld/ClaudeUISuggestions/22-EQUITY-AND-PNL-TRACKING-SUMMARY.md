# Equity & P&L Tracking - Master Summary Plan

**Created**: November 3, 2025
**Status**: Execution Prep - Phase 0 backend complete, equity flows pending (see [25-EQUITY-AND-PNL-EXECUTION-PLAN.md](./25-EQUITY-AND-PNL-EXECUTION-PLAN.md))
**Priority**: Critical
**Total Estimated Effort**: 8-12 days

---

## Executive Summary

This master plan addresses a critical gap in portfolio equity tracking and P&L calculation. The system currently lacks:

1. **Realized P&L tracking** when positions are closed (sold)
2. **Capital flow tracking** (contributions and withdrawals)
3. **Accurate performance measurement** (returns should exclude capital flows)

These features are interdependent and must be implemented in sequence to ensure accurate equity rollforward and return calculations.

### Status Update - 2025-11-04
- OK: Realized P&L backend changes are merged (schemas, service logic, batch rollforward).
- Attention: Command Center inline sell flow still needs `close_quantity` payload before full QA sign-off.
- Next: Kick off equity change implementation per [25-EQUITY-AND-PNL-EXECUTION-PLAN.md](./25-EQUITY-AND-PNL-EXECUTION-PLAN.md) once Phase 0 UX gap is closed.
- Decisions: Backdating equity flows is supported, edits lock after 7 days, and an export endpoint will be delivered; no extra downstream reporting work required.

---

## 🚨 Critical Issue Discovered

**Problem**: The current P&L calculator only tracks **unrealized P&L** (mark-to-market) but ignores **realized P&L** from closing positions.

**Impact**:
- When users sell positions via ManagePositionsSidePanel, the realized gains/losses are not recorded
- `positions.realized_pnl` field exists in database but is never populated
- `exit_price` and `exit_date` are sent from frontend but silently ignored by backend
- Portfolio equity calculations are incomplete

**Severity**: High - Affects all portfolios with position exits

> Update (2025-11-04): Backend service and calculator changes are merged; remaining blocker is the inline sell payload fix noted above.

---

## Implementation Phases

### Phase 0: Realized P&L Tracking 🔴 **PREREQUISITE**

**Status**: Backend complete; pending UX validation (inline sell payload fix)
**Effort**: 2-3 days
**Document**: [23-REALIZED-PNL-TRACKING-PLAN.md](./23-REALIZED-PNL-TRACKING-PLAN.md)

**Objectives**:
- Fix position update endpoint to accept `exit_price` and `exit_date`
- Calculate and store `realized_pnl` when positions are closed
- Track daily/cumulative realized P&L at portfolio snapshot level
- Update P&L calculator to include realized P&L in equity rollforward

**Dependencies**: None (can start immediately)

**Deliverables**:
1. ✅ Updated `UpdatePositionRequest` schema with exit/entry fields **and** `close_quantity` for partial exits
2. ✅ Realized P&L calculation logic in `PositionService` (uses `close_quantity`, accumulates increments)
3. ✅ `position_realized_events` table + service helper to persist each realized trade
4. ✅ `daily_realized_pnl` and `cumulative_realized_pnl` fields in `PortfolioSnapshot`
5. ✅ Enhanced P&L calculator including realized gains/losses sourced from realized events
6. ✅ Attention: Frontend updates so `ManagePositionsSidePanel` and Command Center inline sell send `close_quantity` + remaining quantity (in progress)
7. ✅ Database migration for new snapshot/event fields
8. ✅ Tests for realized P&L calculations (full + partial closes)

---

### Phase 1: Equity Changes Tracking

**Status**: Ready to implement after Phase 0
**Effort**: 5-8 days
**Document**: [21-EQUITY-CHANGES-TRACKING-PLAN.md](./21-EQUITY-CHANGES-TRACKING-PLAN.md) *(Updated)*

**Objectives**:
- Track capital contributions and withdrawals separately from P&L
- Enable accurate time-weighted return (TWR) calculations
- Provide clear audit trail of external cash movements
- Distinguish investment performance from capital flows

**Dependencies**:
- ✅ Phase 0 must be complete (realized P&L tracking)
- Requires correct equity rollforward formula

**Deliverables**:
1. ✅ New `equity_changes` database table
2. ✅ 6 REST API endpoints for equity change CRUD
3. ✅ Enhanced P&L calculator with contribution/withdrawal logic
4. ✅ `ManageEquitySidePanel` UI component
5. ✅ Hero metrics integration showing capital flows
6. ✅ Tests for full equity rollforward

---

## Correct Equity Rollforward Formula

### Current (Incomplete) ❌
```python
new_equity = previous_equity + daily_pnl
```
**Problem**: Ignores realized P&L and capital flows

### After Phase 0 (Better) ⚠️
```python
new_equity = previous_equity + unrealized_pnl_change + realized_pnl
```
**Problem**: Still ignores capital flows

### After Phase 1 (Complete) ✅
```python
new_equity = (
    previous_equity           # Starting equity for the day
    + unrealized_pnl_change   # MTM change on open positions
    + realized_pnl            # P&L from closed positions
    + contributions           # Capital added to account
    - withdrawals             # Capital removed from account
)
```
**Result**: Accurate equity tracking with proper attribution

---

## Database Schema Changes

### Phase 0: Realized P&L

**Existing Fields** (no changes needed):
- `positions.realized_pnl` (already exists, needs population)
- `positions.exit_price` (already exists, needs backend support)
- `positions.exit_date` (already exists, needs backend support)

**New Fields** (migration required):
- `portfolio_snapshots.daily_realized_pnl` (Decimal 16,2)
- `portfolio_snapshots.cumulative_realized_pnl` (Decimal 16,2)

### Phase 1: Equity Changes

**New Table** (migration required):
```sql
CREATE TABLE equity_changes (
    id UUID PRIMARY KEY,
    portfolio_id UUID REFERENCES portfolios(id),
    change_date DATE NOT NULL,
    change_type VARCHAR(20) NOT NULL,  -- 'CONTRIBUTION' | 'WITHDRAWAL'
    amount NUMERIC(16,2) NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMP,
    created_by_user_id UUID REFERENCES users(id),
    -- Indexes on portfolio_id, change_date, change_type
);
```

---

## Return Calculation Implications

### Before (Incorrect)
```python
daily_return = daily_pnl / previous_equity
```
**Problem**: Capital contributions/withdrawals inflate/deflate returns

### After Phase 1 (Correct)
```python
# Adjust equity base for intraday flows
adjusted_equity = previous_equity + contributions - withdrawals

# Calculate return only on investment performance
investment_pnl = unrealized_pnl_change + realized_pnl
daily_return = investment_pnl / adjusted_equity if adjusted_equity > 0 else 0
```
**Result**: True time-weighted return (TWR) independent of capital flows

---

## Implementation Checklist

### Phase 0: Realized P&L Tracking (2-3 days)

**Backend**:
- [ ] Update `UpdatePositionRequest` schema (add `exit_price`, `exit_date`, `entry_price`)
- [ ] Add realized P&L calculation to `PositionService.update_position()`
- [ ] Create Alembic migration for snapshot fields
- [ ] Update `pnl_calculator.py` to query and aggregate realized P&L
- [ ] Add realized P&L to snapshot creation logic
- [ ] Unit tests for realized P&L calculations

**Frontend**:
- [ ] Verify `ManagePositionsSidePanel` sends exit fields (already does)
- [ ] Update position response type to include `realized_pnl`
- [ ] Display realized P&L in holdings table (optional enhancement)

**Testing**:
- [ ] Test long position close (profit scenario)
- [ ] Test long position close (loss scenario)
- [ ] Test short position close
- [ ] Test options position close
- [ ] Test partial position close
- [ ] Integration test: close position → batch run → verify snapshot

### Phase 1: Equity Changes Tracking (5-8 days)

See detailed checklist in [21-EQUITY-CHANGES-TRACKING-PLAN.md](./21-EQUITY-CHANGES-TRACKING-PLAN.md)

**High-level**:
- [ ] Phase 0 complete and tested
- [ ] Create `equity_changes` table
- [ ] Implement 6 API endpoints
- [ ] Update P&L calculator with equity change logic
- [ ] Build `ManageEquitySidePanel` component
- [ ] Integrate into Command Center
- [ ] End-to-end testing

---

## Risk Assessment

### Technical Risks

**1. Data Integrity During Migration** (High)
- **Risk**: Existing portfolios may have closed positions without realized P&L
- **Mitigation**:
  - Backfill script to calculate realized P&L for historical exits
  - Mark backfilled values with flag for audit
  - Validate calculations against known benchmarks

**2. Calculation Complexity** (Medium)
- **Risk**: Equity rollforward logic becomes complex with multiple components
- **Mitigation**:
  - Clear code comments documenting each component
  - Comprehensive unit tests for all scenarios
  - Logging at each calculation step for debugging

**3. Performance Impact** (Low)
- **Risk**: Additional queries slow down batch processing
- **Mitigation**:
  - Efficient indexing on new fields
  - Batch fetching of equity changes
  - Profile batch run before/after

### Business Risks

**1. Historical Data Gaps** (Medium)
- **Risk**: Users may not remember historical contributions/withdrawals
- **Mitigation**:
  - Allow backfilling with warning about accuracy
  - Provide CSV import for bulk historical data
  - Mark backfilled data with confidence flag

**2. User Confusion** (Medium)
- **Risk**: Users don't understand distinction between realized/unrealized P&L
- **Mitigation**:
  - Clear UI labels and tooltips
  - Help documentation with examples
  - Display total P&L (realized + unrealized) prominently

---

## Success Criteria

### Phase 0 Success Criteria

**Functional**:
- [ ] Closing a position via ManagePositionsSidePanel calculates realized P&L
- [ ] `positions.realized_pnl` is populated correctly for closed positions
- [ ] Portfolio snapshots include daily and cumulative realized P&L
- [ ] Batch calculator aggregates realized P&L from closed positions
- [ ] Equity rollforward includes realized P&L component

**Data Integrity**:
- [ ] Realized P&L matches manual calculation: `(exit_price - entry_price) × quantity`
- [ ] Long vs. short position P&L signs are correct
- [ ] Options P&L accounts for 100x multiplier
- [ ] Cumulative realized P&L equals sum of daily realized P&L

### Phase 1 Success Criteria

**Functional**:
- [ ] Users can record contributions and withdrawals via UI
- [ ] Equity changes appear in recent activity list
- [ ] Portfolio equity updates correctly with contributions/withdrawals
- [ ] Batch calculator includes equity changes in rollforward
- [ ] Returns exclude impact of capital flows (true TWR)

**User Experience**:
- [ ] UI is intuitive and matches existing patterns
- [ ] Validation prevents invalid entries
- [ ] Success/error messages are clear
- [ ] Hero metrics display capital flow information

---

## Timeline

### Week 1: Phase 0 - Realized P&L
- **Days 1-2**: Schema updates, P&L calculation logic
- **Day 3**: Snapshot fields, P&L calculator enhancement
- **Days 4-5**: Testing, backfill script, documentation

### Checkpoint: Phase 0 Review
- Validate all realized P&L calculations
- Test with demo portfolios
- Get approval before Phase 1

### Weeks 2-4: Phase 1 - Equity Changes
- **Week 2**: Backend (database, API, P&L calculator)
- **Week 3**: Frontend (service, UI, Command Center integration)
- **Week 4**: Testing, polish, deployment

**Total Duration**: 4-5 weeks

---

## Dependencies & Prerequisites

### Before Starting Phase 0
- ✅ Demo portfolios available for testing
- ✅ ManagePositionsSidePanel implemented (already done)
- ✅ Position update endpoint exists (needs enhancement)
- ✅ Batch orchestrator v3 operational

### Before Starting Phase 1
- ✅ Phase 0 fully complete and tested
- ✅ All realized P&L calculations validated
- ✅ Snapshots accurately reflect realized + unrealized P&L
- ✅ Batch processing tested end-to-end

---

## Open Questions & Decisions

### Phase 0 Decisions

1. **Historical Backfill Strategy**
   - **Question**: How to handle existing closed positions without realized P&L?
   - **Options**:
     - A: Leave null (only track going forward)
     - B: Backfill from entry_price and exit_price
     - C: Allow manual user entry
   - **Recommendation**: Option B (backfill) with audit flag

2. **Partial Position Closes**
   - **Question**: How to handle selling only part of a position?
   - **Current**: Updates quantity, no realized P&L tracking
   - **Recommendation**: Calculate realized P&L on the closed portion

### Phase 1 Decisions

See [21-EQUITY-CHANGES-TRACKING-PLAN.md](./21-EQUITY-CHANGES-TRACKING-PLAN.md) for 5 key decisions

---

## Related Documentation

### Planning Documents
- **This Document**: Master summary and overview
- **[21-EQUITY-CHANGES-TRACKING-PLAN.md](./21-EQUITY-CHANGES-TRACKING-PLAN.md)**: Detailed Phase 1 implementation plan
- **[23-REALIZED-PNL-TRACKING-PLAN.md](./23-REALIZED-PNL-TRACKING-PLAN.md)**: Detailed Phase 0 implementation plan

### Existing Documentation
- **Backend**: `backend/CLAUDE.md` - Section on batch orchestrator v3
- **Frontend**: `frontend/CLAUDE.md` - Service layer and UI patterns
- **Position Management**: `frontend/_docs/ClaudeUISuggestions/13-POSITION-MANAGEMENT-PLAN.md`
- **API Reference**: `backend/_docs/reference/API_REFERENCE_V1.4.6.md`

---

## Code References

### Key Files - Phase 0

**Backend**:
- `backend/app/models/positions.py` - Position model (lines 45-46, 61)
- `backend/app/models/snapshots.py` - PortfolioSnapshot model (need to add fields)
- `backend/app/schemas/position_schemas.py` - UpdatePositionRequest (needs exit fields)
- `backend/app/services/position_service.py` - Position CRUD logic
- `backend/app/batch/pnl_calculator.py` - P&L calculation (lines 228-249)
- `backend/app/api/v1/positions.py` - Position endpoints (line 177+)

**Frontend**:
- `frontend/src/components/portfolio/ManagePositionsSidePanel.tsx` - Position management UI (line 286-289)
- `frontend/src/services/positionManagementService.ts` - Position API calls

### Key Files - Phase 1

See [21-EQUITY-CHANGES-TRACKING-PLAN.md](./21-EQUITY-CHANGES-TRACKING-PLAN.md) for complete file list

---

## Appendix A: Example Calculations

### Realized P&L Examples

**Example 1: Long Stock Position - Profit**
```
Entry: 100 shares @ $50 = $5,000 cost basis
Exit:  100 shares @ $60 = $6,000 proceeds
Realized P&L: ($60 - $50) × 100 = $1,000 gain
```

**Example 2: Short Stock Position - Loss**
```
Entry: -100 shares @ $50 = $5,000 proceeds (credited)
Exit:  +100 shares @ $60 = $6,000 cost (to cover)
Realized P&L: ($50 - $60) × 100 = -$1,000 loss
```

**Example 3: Long Call Option - Profit**
```
Entry: 1 contract (100 shares) @ $5.00 = $500 cost
Exit:  1 contract @ $8.00 = $800 proceeds
Realized P&L: ($8.00 - $5.00) × 100 = $300 gain
```

**Example 4: Partial Close - Long Stock**
```
Original: 1,000 shares @ $50 = $50,000 cost
Sell 400:  400 shares @ $55
Realized P&L: ($55 - $50) × 400 = $2,000 gain
Remaining: 600 shares @ $50 (unrealized)
```

### Equity Rollforward Examples

**Example 1: Simple Case (No Flows)**
```
Previous Equity: $100,000
Unrealized P&L Change: +$2,000 (market movements)
Realized P&L: +$1,000 (closed position)
Contributions: $0
Withdrawals: $0

New Equity: $100,000 + $2,000 + $1,000 = $103,000
Daily Return: ($2,000 + $1,000) / $100,000 = 3.0%
```

**Example 2: With Capital Contribution**
```
Previous Equity: $100,000
Unrealized P&L Change: +$2,000
Realized P&L: +$1,000
Contributions: +$50,000 (added capital)
Withdrawals: $0

New Equity: $100,000 + $2,000 + $1,000 + $50,000 = $153,000

Adjusted Equity: $100,000 + $50,000 = $150,000
Investment P&L: $2,000 + $1,000 = $3,000
Daily Return: $3,000 / $150,000 = 2.0% (correct TWR)

Note: Without adjustment, return would be 3.0% which overstates performance
```

**Example 3: With Capital Withdrawal**
```
Previous Equity: $100,000
Unrealized P&L Change: -$1,000 (market down)
Realized P&L: +$500
Contributions: $0
Withdrawals: -$20,000 (removed capital)

New Equity: $100,000 - $1,000 + $500 - $20,000 = $79,500

Adjusted Equity: $100,000 - $20,000 = $80,000
Investment P&L: -$1,000 + $500 = -$500
Daily Return: -$500 / $80,000 = -0.625% (correct TWR)

Note: Without adjustment, return would be -0.5% which understates loss
```

---

## Appendix B: Testing Scenarios

### Phase 0 Testing Scenarios

1. **Basic Position Close - Long Stock**
   - Create position: AAPL, 100 shares @ $150
   - Close position: sell @ $160
   - Verify: realized_pnl = $1,000

2. **Basic Position Close - Short Stock**
   - Create position: TSLA, -50 shares @ $200
   - Close position: cover @ $180
   - Verify: realized_pnl = $1,000

3. **Options Position Close - Long Call**
   - Create position: SPY LC, 1 contract @ $5.00
   - Close position: sell @ $7.50
   - Verify: realized_pnl = $250 (accounts for 100x multiplier)

4. **Partial Position Close**
   - Create position: MSFT, 1000 shares @ $300
   - Sell 400 shares @ $320
   - Verify: realized_pnl = $8,000 on closed portion
   - Verify: remaining 600 shares still show unrealized P&L
   - Verify: `position_realized_events` captures quantity_closed = 400 with correct trade date

5. **Batch Integration**
   - Close position on date X
   - Run batch calculator for date X
   - Verify: snapshot.daily_realized_pnl sums `PositionRealizedEvent` rows for that date
   - Verify: snapshot.equity_balance increased by realized P&L

### Phase 1 Testing Scenarios

See [21-EQUITY-CHANGES-TRACKING-PLAN.md](./21-EQUITY-CHANGES-TRACKING-PLAN.md) Appendix B

---

## Document Maintenance

**Last Updated**: November 3, 2025

**Update Triggers**:
- After Phase 0 completion: Update success criteria, timeline estimates
- After Phase 1 completion: Mark as complete, add lessons learned
- When new issues discovered: Add to risk assessment
- When calculations change: Update formulas and examples

**Maintained By**: Development team with Claude Code assistance

---

**Next Steps**:

1. ✅ Review this summary document
2. ✅ Read [23-REALIZED-PNL-TRACKING-PLAN.md](./23-REALIZED-PNL-TRACKING-PLAN.md) for Phase 0 details
3. ✅ Make decisions on open questions
4. ✅ Approve Phase 0 implementation
5. ⏳ Begin Phase 0 development (2-3 days)
6. ⏳ Complete Phase 0 and checkpoint review
7. ⏳ Approve Phase 1 implementation
8. ⏳ Begin Phase 1 development (5-8 days)

---

*End of Master Summary Document*
