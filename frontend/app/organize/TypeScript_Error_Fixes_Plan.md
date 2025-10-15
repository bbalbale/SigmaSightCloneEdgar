# TypeScript Error Fixes Plan

**Created:** 2025-10-13
**Status:** Planning Phase
**Total Errors:** 28 type definition errors

---

## Executive Summary

This document outlines a phased approach to fix 28 TypeScript type definition errors in the frontend codebase. The highest priority is **Phase 1: Remove Deprecated Strategy Code**, as Strategies have been deprecated and removed from the backend.

**CRITICAL CONTEXT:**
- **Strategies ≠ Tags** - These are two completely separate concepts
- **Strategies have been DEPRECATED** - Backend no longer supports Strategy endpoints
- **Tags remain ACTIVE** - Tag functionality is fully supported and separate from Strategies

---

## Error Breakdown

### A. FactorExposure Property Name Mismatch (4 errors)
**Issue:** Code uses `factor.factor_name` but type definition has `factor.name`

**Affected Files:**
1. `src/components/portfolio/FilterBar.tsx` (lines 206, 208, 212, 221)

**Root Cause:** Type definition mismatch between component usage and API response

---

### B. StrategyListItem Missing Properties (8 errors) - **REQUIRES REMOVAL**
**Issue:** Components request Strategy data but Strategies are deprecated

**Affected Files:**
1. `src/components/organize/StrategyCard.tsx` (lines 31, 37, 46, 48, 51, 54)
2. `src/components/portfolio/StrategyList.tsx` (lines 20, 38)

**Root Cause:** These components reference deprecated Strategy functionality that no longer exists in the backend

**Action Required:** REMOVE these components entirely

---

### C. TagItem Missing usage_count Property (2 errors)
**Issue:** TagItem type doesn't include `usage_count` property

**Affected Files:**
1. `src/components/organize/TagBadge.tsx` (line 14)
2. `src/components/organize/TagList.tsx` (line 51)

**Root Cause:** TagItem type definition in `types/strategies.ts` is incomplete, or components expect a property that doesn't exist

---

### D. Tag vs TagItem Type Mismatches (5 errors)
**Issue:** Components expect `Tag` type but receive `TagItem` (or vice versa)

**Affected Files:**
1. `src/components/positions/LongPositionsList.tsx` (line 90)
2. `src/components/positions/OptionsPositionsList.tsx` (line 80)
3. `src/components/positions/PrivatePositionsList.tsx` (line 80)
4. `src/components/positions/ShortOptionsPositionsList.tsx` (line 80)
5. `src/components/positions/ShortPositionsList.tsx` (line 80)

**Root Cause:** Multiple tag type definitions exist (`Tag` in `lib/types.ts` vs `TagItem` in `types/strategies.ts`)

---

### E. Test File Errors (21 errors)
**Issue:** Missing Playwright and Jest type definitions

**Files:** Various test files

**Root Cause:** Missing dev dependencies for testing frameworks

---

### F. Other Minor Type Issues (9 errors)
**Issue:** Various type mismatches and undefined properties

**Mixed errors across multiple files**

---

## Implementation Plan

### Phase 1: Remove Deprecated Strategy Components (HIGHEST PRIORITY)

**Goal:** Remove all Strategy-related components and references since backend no longer supports Strategies

**Files to DELETE:**
1. `src/components/organize/StrategyCard.tsx` (entire file)
2. `src/components/portfolio/StrategyList.tsx` (entire file)

**Files to CHECK for Strategy References:**
1. `src/services/strategiesApi.ts` - Likely needs removal or deprecation
2. `src/hooks/useStrategies.ts` - Check if exists, remove if present
3. `app/organize/page.tsx` - Remove Strategy imports and components
4. Any imports of `StrategyCard` or `StrategyList` in other files

**Validation:**
- Search codebase for "StrategyCard" and "StrategyList" imports
- Search for "strategiesApi" usage
- Ensure no broken imports remain after deletion

**Why This is Priority 1:**
- Backend doesn't support Strategies anymore
- These components will never work
- Removing them eliminates 8 TypeScript errors immediately
- Prevents confusion between Strategies (deprecated) and Tags (active)

---

### Phase 2: Fix FactorExposure Property Names (4 errors)

**Goal:** Align component usage with type definition

**File to Modify:**
- `src/components/portfolio/FilterBar.tsx`

**Changes Required:**
Replace all occurrences of `factor.factor_name` with `factor.name`:
- Line 206: `key={factor.factor_name}` → `key={factor.name}`
- Line 208: `onFactorFilterChange?.(factor.factor_name)` → `onFactorFilterChange?.(factor.name)`
- Line 212: `selectedFactorName === factor.factor_name` → `selectedFactorName === factor.name`
- Line 221: `{factor.factor_name}` → `{factor.name}`

**Validation:**
- Run TypeScript compiler to verify errors resolved
- Test FilterBar component renders correctly
- Verify factor filtering functionality works

**Risk:** Low - Simple property name change

---

### Phase 3: Fix TagItem Type Definition (2 errors)

**Goal:** Add missing `usage_count` property to TagItem or remove its usage from components

**Option A: Add usage_count to TagItem Type**
- Modify `src/types/strategies.ts`
- Add `usage_count?: number` to TagItem interface

**Option B: Remove usage_count from Components**
- Modify `TagBadge.tsx` and `TagList.tsx`
- Remove references to `usage_count` property
- Use alternative display logic

**Recommended Approach:** Option B (Remove from Components)
- Backend likely doesn't return `usage_count` in TagItem
- Cleaner to remove unused property references
- Less risk than changing shared type definition

**Files to Modify:**
1. `src/components/organize/TagBadge.tsx` (line 14)
2. `src/components/organize/TagList.tsx` (line 51)

**Validation:**
- Verify TagBadge and TagList render correctly
- Test tag display functionality
- Run TypeScript compiler

**Risk:** Low - Remove unused property reference

---

### Phase 4: Fix Tag vs TagItem Type Mismatches (5 errors)

**Goal:** Standardize on single tag type across position components

**Root Cause Analysis:**
- `Tag` type in `lib/types.ts` includes `usage_count`
- `TagItem` type in `types/strategies.ts` is simpler
- Position components display tags but don't need full `TagItem` interface

**Recommended Solution:**
Create a simpler display-only type for position cards:

```typescript
// In lib/types.ts or types/strategies.ts
export interface TagDisplay {
  id: string
  name: string
  color: string
}
```

**Files to Modify:**
1. `src/components/positions/LongPositionsList.tsx` (line 90)
2. `src/components/positions/OptionsPositionsList.tsx` (line 80)
3. `src/components/positions/PrivatePositionsList.tsx` (line 80)
4. `src/components/positions/ShortOptionsPositionsList.tsx` (line 80)
5. `src/components/positions/ShortPositionsList.tsx` (line 80)

**Changes:**
- Update type annotations from `Tag[]` to `TagDisplay[]`
- Or cast API response to expected type

**Validation:**
- Verify tag badges display correctly in position cards
- Test tag filtering if applicable
- Run TypeScript compiler

**Risk:** Low - Display-only change, no functionality impact

---

### Phase 5: Fix Test File Errors (21 errors) - OPTIONAL

**Goal:** Install missing test dependencies

**Root Cause:** Missing Playwright and Jest type packages

**Installation Command:**
```bash
npm install --save-dev @types/jest @playwright/test
```

**Validation:**
- Run `npm run type-check` to verify errors resolved
- Run test suite to ensure tests still pass

**Priority:** Low - Tests may not be actively used
**Risk:** Low - Dev dependencies only, no production impact

---

### Phase 6: Fix Other Minor Type Issues (9 errors) - REVIEW AFTER PHASE 1-4

**Goal:** Address remaining type mismatches

**Approach:**
- Review errors after completing Phases 1-4
- Many may be resolved by upstream changes
- Address individually based on error messages

**Priority:** Low - Address after major issues resolved
**Risk:** Variable - Depends on specific errors

---

## Execution Order & Dependencies

### Week 1: Critical Removals
1. **Day 1-2:** Phase 1 - Remove Strategy components (8 errors fixed)
2. **Day 3:** Phase 2 - Fix FactorExposure names (4 errors fixed)

### Week 2: Type Consolidation
3. **Day 4-5:** Phase 3 - Fix TagItem definition (2 errors fixed)
4. **Day 6-7:** Phase 4 - Fix Tag/TagItem mismatches (5 errors fixed)

### Week 3: Optional Cleanup
5. **Day 8:** Phase 5 - Install test dependencies (21 errors fixed)
6. **Day 9-10:** Phase 6 - Review and fix remaining errors (9 errors)

**Total Expected Resolution:** 49 errors (28 type definition + 21 test errors)

---

## Risk Assessment

### High Risk
- **Phase 1:** Removing components may break imports elsewhere
  - **Mitigation:** Search entire codebase for imports before deletion
  - **Rollback:** Git commit before changes

### Medium Risk
- **Phase 4:** Changing tag types may affect data flow
  - **Mitigation:** Test thoroughly in development
  - **Rollback:** Keep original type definitions until testing complete

### Low Risk
- **Phase 2:** Simple property name changes
- **Phase 3:** Removing unused properties
- **Phase 5:** Adding dev dependencies
- **Phase 6:** Minor fixes after other phases complete

---

## Success Criteria

### Phase 1 Complete When:
- [x] StrategyCard.tsx deleted
- [x] StrategyList.tsx deleted
- [x] No imports of Strategy components remain
- [x] TypeScript compiler shows 8 fewer errors
- [x] App builds successfully without Strategy references

### Phase 2 Complete When:
- [x] All `factor.factor_name` changed to `factor.name`
- [x] TypeScript compiler shows 4 fewer errors
- [x] FilterBar component renders and functions correctly

### Phase 3 Complete When:
- [x] TagBadge and TagList no longer reference `usage_count`
- [x] TypeScript compiler shows 2 fewer errors
- [x] Tag display components render correctly

### Phase 4 Complete When:
- [x] All position components use consistent tag type
- [x] TypeScript compiler shows 5 fewer errors
- [x] Tag badges display correctly in all position lists

### Phase 5 Complete When:
- [x] Test dependencies installed
- [x] TypeScript compiler shows 21 fewer errors
- [x] Test suite runs without type errors

### Phase 6 Complete When:
- [x] All remaining type errors resolved
- [x] TypeScript compiler shows 0 errors
- [x] Full application builds and runs without errors

---

## Testing Strategy

### After Each Phase:
1. Run `npm run type-check` to verify error count reduction
2. Run `npm run build` to ensure application builds
3. Start development server and manually test affected features
4. Check browser console for runtime errors
5. Test affected components in development environment

### Specific Testing Per Phase:

**Phase 1 Testing:**
- Verify organize page loads without Strategy components
- Check that tag functionality still works independently
- Ensure no broken imports or 404 errors

**Phase 2 Testing:**
- Test factor exposure filtering in FilterBar
- Verify factor names display correctly in dropdown
- Test factor filter selection and clearing

**Phase 3 Testing:**
- Verify TagBadge renders tags correctly
- Test TagList displays all tags
- Ensure tag creation/editing still works

**Phase 4 Testing:**
- Check tag badges on ALL position types (long, short, options, private, short options)
- Verify tag colors display correctly
- Test tag filtering if applicable

**Phase 5 Testing:**
- Run test suite: `npm run test`
- Verify tests pass without type errors
- Check test coverage reports

---

## Rollback Plan

### Before Starting:
1. Create feature branch: `git checkout -b fix/typescript-errors`
2. Commit current state: `git commit -m "Pre-fix baseline"`

### After Each Phase:
1. Commit changes: `git commit -m "Phase X: [description]"`
2. Tag commit: `git tag phase-X-complete`

### If Issues Arise:
1. **Immediate rollback:** `git reset --hard HEAD~1`
2. **Phase rollback:** `git reset --hard phase-X-complete`
3. **Full rollback:** `git reset --hard origin/main`

---

## Additional Notes

### Why Strategies Were Deprecated
- Backend API no longer supports Strategy endpoints
- Strategy functionality may have been migrated to different system
- Frontend code needs to align with backend capabilities

### Strategies vs Tags - Key Differences
- **Strategies:** Complex investment strategies (DEPRECATED)
- **Tags:** Simple labels/categories for organization (ACTIVE)
- **Not interchangeable** - Removing Strategy code does NOT affect Tag functionality

### Future Considerations
- Consider adding Strategy deprecation warnings if UI references remain
- Update documentation to clarify Strategy removal
- Consider user migration path if users expected Strategy features

---

## Questions to Answer Before Implementation

1. **Strategy Removal:**
   - Are there any user-facing features that depend on Strategy components?
   - Should we display a deprecation message to users?
   - Is there user data (saved strategies) that needs migration?

2. **Tag Types:**
   - Should we consolidate `Tag` and `TagItem` into single type?
   - Does backend return `usage_count` for tags?
   - What is the authoritative source for tag type definition?

3. **Testing:**
   - Are the test files actively maintained?
   - Should we invest in fixing test errors now or defer?
   - What is the test coverage requirement?

4. **Priority:**
   - Are there other critical bugs that should take priority?
   - What is the timeline for these fixes?
   - Should we fix all at once or incrementally?

---

## Conclusion

This plan provides a structured, low-risk approach to fixing 28+ TypeScript errors with clear phases, success criteria, and rollback plans. The highest priority is removing deprecated Strategy code (Phase 1), which immediately eliminates 8 errors and prevents future confusion.

**Recommended Timeline:** 2-3 weeks for Phases 1-4 (critical fixes), with Phases 5-6 as optional cleanup.

**Expected Outcome:**
- Zero TypeScript compilation errors
- Cleaner codebase without deprecated code
- Improved type safety and developer experience
- Clear separation between Strategies (removed) and Tags (active)
