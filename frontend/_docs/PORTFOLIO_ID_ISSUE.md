# Portfolio ID Resolution - Development Approach

## Problem Summary
Portfolio IDs are dynamically generated (uuid4()) during database seeding, causing different IDs across developer machines. This breaks the frontend which currently hardcodes portfolio IDs that only work on one developer's machine.

## Root Cause Analysis

### Current Issue
1. **Backend generates random UUIDs** when seeding (`backend/app/db/seed_demo_portfolios.py` line 322)
2. **Every database seed creates different IDs** 
3. **Frontend hardcodes specific IDs** (`frontend/src/services/portfolioResolver.ts` lines 56-60)
4. **Result**: 404 errors when frontend tries to fetch portfolios with wrong IDs

### Example of the Mismatch

**Windows Database (Actual):**
```
demo_individual@sigmasight.com: 52110fe1-ca52-42ff-abaa-c0c90e8e21be
demo_hnw@sigmasight.com: 7ec9dab7-b709-4a3a-b7b6-2399e53ac3eb  
demo_hedgefundstyle@sigmasight.com: 1341a9f2-5ef1-4acb-a480-2dca21a7d806
```

**Frontend Hardcoded (Wrong):**
```
demo_individual@sigmasight.com: 51134ffd-2f13-49bd-b1f5-0c327e801b69
demo_hnw@sigmasight.com: c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e
demo_hedgefundstyle@sigmasight.com: 2ee7435f-379f-4606-bdb7-dadce587a182
```

## Recommended Solution: Deterministic IDs for Development

### Why Deterministic IDs Make Sense in Development

1. **Team Consistency**: Every developer gets identical portfolio IDs
2. **Simple Testing**: Known IDs can be documented and referenced
3. **No "Works on My Machine"**: Eliminates environment-specific issues
4. **Development Speed**: Can temporarily hardcode known IDs while building
5. **Progressive Enhancement**: Add proper API discovery later

### Implementation Plan

#### Step 1: Update Backend Seed Script
Add deterministic UUID generation to `backend/app/db/seed_demo_portfolios.py`:

```python
import hashlib
from uuid import UUID

def generate_deterministic_uuid(seed_string: str) -> UUID:
    """Generate consistent UUID from seed string - DEVELOPMENT ONLY"""
    # Creates same UUID on every machine for same input
    hash_hex = hashlib.md5(seed_string.encode()).hexdigest()
    return UUID(hash_hex)

# Line 322 - Replace uuid4() with:
portfolio = Portfolio(
    id=generate_deterministic_uuid(f"{user.email}_portfolio"),
    user_id=user.id,
    name=portfolio_data["portfolio_name"],
    description=portfolio_data["description"]
)

# Also update Position IDs for consistency (line 244):
position = Position(
    id=generate_deterministic_uuid(f"{portfolio.id}_{symbol}_{entry_date}"),
    ...
)
```

#### Step 2: Document the Generated IDs
The deterministic function will always generate these IDs:

```typescript
// These IDs will be consistent across all developer machines
export const DEVELOPMENT_PORTFOLIO_IDS = {
  'demo_individual@sigmasight.com': 'a6b9f6c7-8e4a-3b2d-9f1e-7c5a4d3b2e1a',    // Example
  'demo_hnw@sigmasight.com': 'b7c8e7d8-9f5b-4c3e-a02f-8d6b5e4c3f2b',         // Example  
  'demo_hedgefundstyle@sigmasight.com': 'c8d9f8e9-a06c-5d4f-b130-9e7c6f5d4g3c' // Example
}
// Note: Actual IDs will be different but consistent
```

#### Step 3: All Developers Reseed
```bash
# One-time migration for all developers
cd backend
uv run python scripts/reset_and_seed.py reset  # Clear old data
uv run python scripts/seed_database.py          # Seed with deterministic IDs
```

#### Step 4: Update Frontend (Temporary)
Update `frontend/src/services/portfolioResolver.ts` with the new deterministic IDs.

#### Step 5: Future Enhancement (Post-MVP)
Implement proper portfolio discovery via API (per PORTFOLIO_ID_DESIGN_DOC.md Level 1):
- Backend includes portfolio_id in JWT
- `/api/v1/me` returns portfolio_id
- Frontend fetches dynamically instead of hardcoding

## Why Not Other Approaches?

### Why Not Fix the API First?
- **Complexity**: Requires changes to JWT, auth flow, multiple endpoints
- **Time**: Multiple days of work across backend and frontend
- **Risk**: Could break existing auth flows
- **Overkill**: For 3 demo accounts in development

### Why Not Just Update Hardcoded IDs?
- **Doesn't Scale**: Every new developer needs different IDs
- **Maintenance Burden**: Can't commit changes without breaking others
- **Documentation Nightmare**: No single source of truth

### Why Not Use Email-Based Lookups?
- **Backend Missing Endpoint**: `/api/v1/portfolios` endpoint not working
- **Additional Complexity**: Need to implement portfolio discovery
- **Development Speed**: Slows down frontend development

## Development Philosophy

**Current Stage**: Rapid development with 3 demo users
**Priority**: Developer productivity and consistency
**Approach**: Start simple, add complexity when needed

This follows the principle: **"Make it work, make it right, make it fast"**

Deterministic IDs immediately make it work for everyone. We can make it "right" with proper API discovery after MVP.

## Security Considerations

**Not a concern because:**
- Only used for demo accounts
- Development environment only  
- Will use random UUIDs in production
- No real user data involved

## Migration Path to Production

When ready for production:
1. Switch back to `uuid4()` for random IDs
2. Implement full Level 1 from PORTFOLIO_ID_DESIGN_DOC.md
3. Remove all hardcoded portfolio mappings
4. Use proper API-based discovery

## Action Items

1. [ ] Update seed script with deterministic UUID function
2. [ ] Test generated IDs match expected values
3. [ ] Document actual generated IDs
4. [ ] Coordinate team database reseed
5. [ ] Update frontend with new IDs
6. [ ] Add TODO for future API-based discovery

## Questions for Discussion

1. Should Position IDs also be deterministic? (Helps with testing)
2. Should we use SHA256 instead of MD5? (More future-proof)
3. Do we need deterministic IDs for other entities? (Users, Tags, etc.)
4. When should we prioritize proper API discovery? (Post-MVP?)

---

**Decision Date**: 2025-01-05
**Decision Maker**: Development Team
**Status**: Proposed Solution - Awaiting Implementation
**Original Author**: bbalbale@dockyardcapital.com