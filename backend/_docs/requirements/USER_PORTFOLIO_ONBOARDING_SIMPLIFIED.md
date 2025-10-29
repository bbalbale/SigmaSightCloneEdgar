# Simplified MVP Design - Key Changes

**Date**: 2025-10-28
**Status**: Approved Simplifications for 50 White-Glove Users

---

## Summary of Simplifications

For an MVP serving 50 beta users with white-glove support, we're simplifying:

### ✅ **Approved Simplifications:**
1. ✂️ **Single Master Invite Code** (looks unique to user)
2. ✂️ **No Rate Limiting** (trust beta users)
3. ✂️ **No Audit Logging** (use application logs)
4. ✂️ **No `account_type` field** (all are real users)
5. ✂️ **Simplified Error Codes** (reduce from 60+ to ~35)

### ✅ **Keep for Quality:**
- ✅ Hybrid UUID strategy (deterministic for testing)
- ✅ Impersonation system
- ✅ Strict CSV validation
- ✅ Required equity_balance
- ✅ Detailed CSV validation
- ✅ Batch processing integration

---

## 1. Simplified Invite Code System

### **Original Design:**
- Database table with multiple codes
- Single-use enforcement
- Expiration tracking
- Admin endpoints for generation
- User-to-code tracking

### **Simplified Design:**

```python
# app/config.py
BETA_INVITE_CODE = "PRESCOTT-LINNAEAN-COWPERTHWAITE"  # Single master code

# app/services/invite_code_service.py (simplified)
class InviteCodeService:
    """
    Simplified invite code validation.

    Uses single master code but generates unique appearance for frontend.
    """

    def validate_invite_code(self, code: str) -> bool:
        """
        Validate invite code matches master code.

        Returns:
            True if valid, False otherwise
        """
        return code == settings.BETA_INVITE_CODE

    def generate_display_code(self, email: str) -> str:
        """
        Generate unique-looking code for user (cosmetic only).

        Uses hash of email to generate consistent but unique-looking code.
        Still validates against master code.

        Example: user@example.com → SIGMA-E8F3-A7B2
        """
        import hashlib
        hash_obj = hashlib.md5(email.encode())
        hex_dig = hash_obj.hexdigest()[:8].upper()
        return f"SIGMA-{hex_dig[:4]}-{hex_dig[4:8]}"
```

### **What This Means:**
- **No database table** - Just a config value
- **No admin endpoints** - Endpoints 3 & 4 removed
- **Looks unique** - Each user sees "their" code (cosmetic)
- **Actually same** - All codes validate against `PRESCOTT-LINNAEAN-COWPERTHWAITE`
- **White-glove friendly** - Just tell users the code in email

### **Updated Endpoints:**
- ❌ **REMOVED**: `POST /api/v1/admin/invite-codes/generate`
- ❌ **REMOVED**: `GET /api/v1/admin/invite-codes`
- **Scope reduced from 7 → 5 endpoints**

---

## 2. Remove Rate Limiting

### **Original Design (Section 9.5):**
- Registration rate limits
- CSV upload limits
- General API rate limits
- CAPTCHA for failures

### **Simplified Design:**
**NONE**. No rate limiting for MVP.

**Rationale:**
- 50 trusted beta users can't DOS the system
- White-glove support means direct contact
- Add later if abuse occurs (unlikely with invite code)

### **Implementation:**
- Remove Section 9.5 entirely
- No middleware needed
- No Redis required
- No CAPTCHA integration

---

## 3. Remove Audit Logging

### **Original Design (Section 9.2):**
```
**Audit Logging:**
- Log all impersonation events
- Log all admin endpoint access
- Include: who, when, what, target user
```

### **Simplified Design:**
Use standard application logging only.

```python
# Existing logging is sufficient
logger.info(f"User {superuser_email} impersonating {target_email}")
logger.info(f"Impersonation ended for {target_email}")
```

**Rationale:**
- 50 users = manageable with application logs
- Can grep logs if issues arise
- Add structured audit trail later for production

---

## 4. Remove `account_type` Field

### **Original Design:**
```sql
ALTER TABLE users ADD COLUMN account_type VARCHAR(20) DEFAULT 'REAL';
ALTER TABLE users ADD CONSTRAINT check_account_type
    CHECK (account_type IN ('DEMO', 'REAL'));
```

### **Simplified Design:**
**Remove entirely**. No `account_type` field.

**Logic:**
- Demo users already have `@sigmasight.com` emails (easy to identify)
- All beta users are "real users" by definition
- Can query by email pattern if needed: `email LIKE '%@sigmasight.com'`

### **Database Changes:**
```sql
-- Remove from migration
-- DON'T ADD: account_type column
-- DON'T ADD: check_account_type constraint
-- DON'T ADD: idx_users_account_type index
```

### **API Changes:**
- Remove `account_type` from registration response
- Remove `account_type` filter from `/api/v1/admin/users`
- Simplify user data model

---

## 5. Simplify Error Codes

### **Original Design:**
60+ error codes across 6 categories:
- 5 invite errors
- 4 user errors
- 7 CSV errors
- 22 position errors
- 8 portfolio errors
- 4 batch errors
- 5 admin errors

### **Simplified Design:**
~35 essential error codes (reduce by 40%).

**Keep These Categories:**
- ✅ **User Errors** (4): Email exists, invalid email, weak password, name required
- ✅ **CSV File Errors** (5): Too large, wrong type, empty, missing headers, malformed
- ✅ **Critical Position Errors** (15): Symbol, quantity, price, date validation
- ✅ **Portfolio Errors** (6): Already has portfolio, missing fields, validation
- ✅ **Batch Errors** (3): Market data failed, timeout, database error
- ✅ **Admin Errors** (2): Not superuser, user not found

**Simplify/Remove:**
- ❌ Invite code errors → Just one: "Invalid invite code"
- ❌ Advanced position errors → Consolidate similar errors
- ❌ Duplicate position → Can be warning instead
- ❌ Options-specific → Consolidate into generic validation
- ❌ Admin-specific → Keep only critical ones

### **Updated Error Count: ~35 codes (down from 60+)**

**Example Consolidation:**
```python
# Before: 5 separate invite errors
ERR_INVITE_001, ERR_INVITE_002, ERR_INVITE_003, ERR_INVITE_004, ERR_INVITE_005

# After: 1 invite error
ERR_INVITE_001: "Invalid invite code. Please check and try again."
```

---

## 6. Updated Database Schema

### **Minimal Changes:**
```sql
-- ONLY add to users table:
ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE NOT NULL;
CREATE INDEX idx_users_is_superuser ON users(is_superuser);

-- That's it! No other changes needed for MVP.
```

### **What We're NOT Adding:**
- ❌ No `invite_codes` table
- ❌ No `account_type` column
- ❌ No `invited_by_code` column (optional - could keep for tracking)
- ❌ No `check_account_type` constraint

### **Optional Tracking:**
```sql
-- OPTIONAL: Track which code they used (for analytics)
ALTER TABLE users ADD COLUMN invited_by_code VARCHAR(50);
-- Still just one code, but confirms they had it
```

---

## 7. Revised API Scope

### **Phase 1 MVP: 5 Endpoints** (down from 7)

#### **Onboarding Endpoints (2)**
1. `POST /api/v1/onboarding/register` - User registration
2. `POST /api/v1/onboarding/create-portfolio` - Portfolio creation with CSV

#### **Admin Endpoints (3)**
3. `POST /api/v1/admin/impersonate` - Start impersonation
4. `POST /api/v1/admin/stop-impersonation` - End impersonation
5. `GET /api/v1/admin/users` - List all users

### **Removed Endpoints:**
- ❌ `POST /api/v1/admin/invite-codes/generate` (use config)
- ❌ `GET /api/v1/admin/invite-codes` (no database table)

---

## 8. Updated Implementation Timeline

### **Phase 1: Core Onboarding (Week 1-1.5)**
**Reduced from 2 weeks → 1.5 weeks**

1. Minimal database migration (just `is_superuser` column)
2. Simplified invite code validation (config-based)
3. CSV parser service (same as before)
4. Position import service (same as before)
5. Onboarding service orchestration (simplified)
6. **2 API endpoints:**
   - `POST /api/v1/onboarding/register`
   - `POST /api/v1/onboarding/create-portfolio`
7. Simplified error handling (~35 codes)
8. CSV template (static file)
9. Basic testing

### **Phase 2: Admin & Impersonation (Week 2)**
**Reduced from Week 3 → Week 2**

1. Impersonation service (same as before)
2. **3 API endpoints:**
   - `POST /api/v1/admin/impersonate`
   - `POST /api/v1/admin/stop-impersonation`
   - `GET /api/v1/admin/users`
3. Superuser authentication middleware
4. Basic application logging (no structured audit)
5. Testing with multiple test users

### **Phase 3: Testing & Polish (Week 2.5-3)**
**Simplified hardening**

1. **UUID Strategy:** Keep hybrid (deterministic for testing)
2. **No rate limiting** (skip entirely)
3. **No monitoring** (use existing logs)
4. **Security review:**
   - Auth bypass testing
   - User isolation testing
   - File upload security
5. **Documentation:**
   - API docs (Swagger)
   - User CSV guide
   - Simple admin guide

### **Total Timeline: ~3 weeks** (down from 4 weeks)

---

## 9. White Glove Support Model

### **What White Glove Means:**
1. **Direct Support:**
   - Email/Slack for CSV issues
   - Personal onboarding calls
   - Manual database fixes if needed

2. **Invite Code Distribution:**
   - Send `PRESCOTT-LINNAEAN-COWPERTHWAITE` in welcome email
   - Tell users "your exclusive code is..."
   - They enter it, feels personalized

3. **CSV Help:**
   - Walk users through template
   - Help fix validation errors over call
   - Can manually create positions if needed

4. **Trust Model:**
   - No rate limits (we trust them)
   - No strict expiration (code works until we change it)
   - Direct contact if issues

---

## 10. Migration Path to Production

### **When to Add Back Complexity:**

**After 50 users successfully onboarded:**
1. **Rate Limiting:** Add if abuse occurs (unlikely)
2. **Multiple Invite Codes:** If need cohort tracking
3. **Audit Logging:** If compliance requires it
4. **Account Types:** If need to distinguish user tiers
5. **Random UUIDs:** Migrate from hybrid to random

### **Keep Simple:**
- Error codes (35 is plenty)
- Single invite code (works for hundreds of users)
- Application logging (sufficient for small scale)

---

## 11. Updated Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **User Creation** | Self-service with single invite code | Simple, secure enough for 50 users |
| **Portfolio Limit** | 1 portfolio per user | Existing constraint |
| **Invite Codes** | Single master code (config) | Simplest, no database needed |
| **UUID Strategy** | Hybrid (deterministic → random) | Test thoroughly first |
| **Superuser Access** | Database flag + impersonation | Testing value |
| **Rate Limiting** | None | Trust beta users |
| **Audit Logging** | Application logs only | Sufficient for 50 users |
| **Account Types** | None (identify by email) | Unnecessary complexity |
| **Error Codes** | ~35 (down from 60+) | Balanced detail |
| **Batch Processing** | Synchronous (30-60s) | Same as before |
| **CSV Validation** | Strict (all-or-nothing) | Data quality |
| **Equity Balance** | Required field | Handle leverage |

---

## 12. Key Simplification Benefits

### **Time Savings:**
- **Week 1:** -0.5 weeks (simpler invite system, no rate limiting)
- **Week 2:** -1 week (fewer endpoints, no audit logging)
- **Week 3:** -0.5 weeks (skip rate limiting, simpler monitoring)
- **Total:** ~3 weeks instead of 4-5 weeks

### **Code Reduction:**
- No `invite_codes` table → No model, no migrations for that table
- No rate limiting → No middleware, no Redis
- No audit logging → No structured logs, no audit table
- No account_type → Simpler user model
- **Estimated:** ~30% less code

### **Maintenance Savings:**
- Fewer database tables to manage
- Fewer endpoints to maintain
- Simpler error handling
- Less documentation needed

---

## 13. Risk Mitigation

### **Risks of Simplification:**

1. **Single Invite Code:**
   - **Risk:** Code could leak to non-beta users
   - **Mitigation:** Change code if leaked (30 second fix)
   - **White-glove:** Personal emails reduce leak risk

2. **No Rate Limiting:**
   - **Risk:** User could spam API
   - **Mitigation:** 50 users we trust + can add later
   - **Worst case:** Manual intervention (call the user)

3. **No Audit Logging:**
   - **Risk:** Can't track admin actions formally
   - **Mitigation:** Application logs capture everything
   - **White-glove:** Small team, direct communication

4. **No Account Types:**
   - **Risk:** Can't distinguish user tiers
   - **Mitigation:** Email patterns sufficient
   - **Future:** Add field if needed

### **All risks acceptable for 50-user MVP with white-glove support.**

---

## Summary

**Simplifications reduce complexity by ~40% while maintaining quality:**
- ✅ Still secure (invite code required)
- ✅ Still robust (error handling, validation)
- ✅ Still testable (hybrid UUIDs, impersonation)
- ✅ Much faster to implement (3 weeks vs 4-5 weeks)
- ✅ Easier to maintain (less code, fewer tables)
- ✅ Perfect for white-glove MVP (50 trusted users)

**Next step:** Update main design document with these simplifications.
