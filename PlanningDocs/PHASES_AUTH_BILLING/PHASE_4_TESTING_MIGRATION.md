# Phase 4: Testing & Migration

**Estimated Duration**: 2 days
**Dependencies**: Phases 1-3 complete
**PRD Reference**: Sections 12, 16.4, 17, 18

---

## Entry Criteria

Before starting this phase, ensure:
- [x] Phase 1 complete (Clerk configured)
- [x] Phase 2 complete (backend auth working)
- [x] Phase 3 complete (frontend auth working)
- [x] Full auth flow tested locally end-to-end
- [ ] Database backup script ready

---

## Tasks

### 4.1 Pre-Deployment Checklist

#### 4.1.1 Note Rollback Point
```bash
# Record current commit hash (rollback point)
git rev-parse HEAD
# Save this: ________________________________
```
- [ ] Record rollback commit hash

#### 4.1.2 Backup Database
```bash
# Railway production backup
railway run pg_dump -Fc > backup_pre_clerk_$(date +%Y%m%d).dump
```
- [ ] Create database backup
- [ ] Verify backup file exists and has reasonable size

#### 4.1.3 Verify Environment Variables
**Production `.env` must have:**
```bash
# Clerk (PRODUCTION keys, not test)
CLERK_SECRET_KEY=sk_live_...
CLERK_WEBHOOK_SECRET=whsec_...
CLERK_DOMAIN=clerk.sigmasight.com
CLERK_AUDIENCE=sigmasight.com

# Invite
BETA_INVITE_CODE=2026-FOUNDERS-BETA
INVITE_CODE_ENABLED=true
```
- [ ] Production Clerk keys configured (not test keys)
- [ ] Webhook secret from production Clerk instance
- [ ] Invite code configured

### 4.2 Run Migration Dry-Run ✅ COMPLETE

**File**: `backend/scripts/migrate_to_clerk_dryrun.py`

```bash
cd backend
uv run python scripts/migrate_to_clerk_dryrun.py
```

Expected output:
```
============================================================
MIGRATION DRY-RUN
============================================================
1. Checking demo accounts in database...
   ✅ demo_individual@sigmasight.com
   ✅ demo_hnw@sigmasight.com
   ✅ demo_hedgefundstyle@sigmasight.com

2. Checking required columns...
   ✅ users.clerk_user_id
   ✅ users.tier
   ✅ users.invite_validated
   ✅ users.ai_messages_used

3. Checking Clerk API...
   ✅ Clerk JWKS endpoint reachable

============================================================
✅ DRY-RUN PASSED - Ready for migration
============================================================
```

- [x] Dry-run passes all checks
- [x] Fix any issues before proceeding

### 4.3 Migrate Demo Accounts ✅ COMPLETE

**File**: `backend/scripts/migrate_to_clerk.py`

```bash
cd backend
uv run python scripts/migrate_to_clerk.py
```

This script:
1. Creates Clerk users for each demo account
2. Updates database with `clerk_user_id`
3. Sets `invite_validated=true` for demo accounts
4. Sets `tier='free'` for demo accounts

**Migration Results (2026-01-05):**
- `demo_individual@sigmasight.com` → `user_37qyX3FtBwgylQeoq8Ag4YouNBk`
- `demo_hnw@sigmasight.com` → `user_37qyX28BT2mgIsdHcykRxyfLJD2`
- `demo_hedgefundstyle@sigmasight.com` → `user_37qyX63nRcwq3PieXSdhjP79a7D`

**Note:** Password changed to `SigmaSight!Demo2025` (Clerk rejected "demo12345" as compromised)

- [x] Run migration script
- [x] Verify 3 demo accounts created in Clerk Dashboard
- [x] Verify database updated with `clerk_user_id` values

### 4.4 Deploy Backend

```bash
# Push to main (triggers Railway deploy)
git push origin main

# Or manual deploy
railway up
```

- [ ] Backend deployed to Railway
- [ ] Verify `/health` endpoint responds
- [ ] Verify `/api/v1/webhooks/clerk` endpoint exists

### 4.5 Configure Production Webhook

1. Go to Clerk Dashboard (PRODUCTION instance)
2. Webhooks → Add endpoint
3. URL: `https://sigmasight-be-production.up.railway.app/api/v1/webhooks/clerk`
4. Events: `user.created`, `user.deleted`, `subscription.created`, `subscription.cancelled`

- [ ] Production webhook endpoint configured
- [ ] Endpoint shows "Active" status
- [ ] Copy new signing secret if different from dev

### 4.6 Deploy Frontend

```bash
# Push to main (triggers Vercel/Railway deploy)
git push origin main
```

- [ ] Frontend deployed
- [ ] Verify sign-in page loads
- [ ] Verify Clerk components render

### 4.7 Post-Deployment Verification

#### 4.7.1 Demo Account Login ✅ COMPLETE (Local Testing)
Test each demo account:

| Account | Password | Expected |
|---------|----------|----------|
| demo_individual@sigmasight.com | SigmaSight!Demo2025 | Login works, sees portfolio |
| demo_hnw@sigmasight.com | SigmaSight!Demo2025 | Login works, sees portfolio |
| demo_hedgefundstyle@sigmasight.com | SigmaSight!Demo2025 | Login works, sees portfolio |

**Note:** Password updated from "demo12345" (Clerk rejected as compromised)

**Clerk Dashboard Fix:** Disabled "Client Trust" setting to prevent new device verification prompts

- [x] demo_individual login works
- [x] demo_hnw login works (verified: cookie:__session auth)
- [x] demo_hedgefundstyle login works (verified: bearer token auth)

#### 4.7.2 New User Signup
1. Create new account via `/sign-up`
2. Verify email
3. Redirected to `/settings`
4. Enter invite code: `2026-FOUNDERS-BETA`
5. Verify can access dashboard

- [ ] New signup works
- [ ] Email verification works
- [ ] Invite code validation works
- [ ] Can access dashboard after invite

#### 4.7.3 Billing Flow
1. As free user, click "Upgrade" on settings
2. Redirected to Clerk billing portal
3. Enter test card: `4242 4242 4242 4242`
4. Complete checkout
5. Verify tier changes to "paid"

- [ ] Upgrade flow works
- [ ] Webhook updates tier to "paid"
- [ ] User sees higher limits

#### 4.7.4 AI Chat
1. Login as validated user
2. Send AI message
3. Verify response streams
4. Check AI message counter incremented

- [ ] Chat works with Clerk auth
- [ ] SSE streaming works
- [ ] Counter increments

#### 4.7.5 Admin System
1. Login at `/admin/login` with admin credentials
2. Access admin dashboard
3. Verify admin functions work
4. Confirm no interference with Clerk

- [ ] Admin login works
- [ ] Admin dashboard accessible
- [ ] Admin auth independent of Clerk

### 4.8 Monitor First 24 Hours

**Check logs for:**
```bash
# Webhook errors
railway logs | grep "webhook"

# Auth errors
railway logs | grep "401\|403\|auth"

# Signup events
railway logs | grep "EVENT: user_signup"
```

- [ ] No webhook signature errors
- [ ] No unexpected 401/403 errors
- [ ] Signups logging correctly

**Check Clerk Dashboard:**
- [ ] Webhook deliveries showing success
- [ ] No failed deliveries
- [ ] User count matches expectations

---

## Exit Criteria (Definition of Done)

### All Tests Pass
- [ ] Demo accounts can login
- [ ] New signup flow complete
- [ ] Invite code validation works
- [ ] Upgrade to paid works
- [ ] AI chat works
- [ ] Admin system unaffected

### Monitoring Configured
- [ ] Can view webhook delivery status in Clerk
- [ ] Can grep logs for auth events
- [ ] Know how to check tier mismatches

### Documentation Updated
- [ ] PROGRESS_AUTH_BILLING.md updated with completion status
- [ ] Any issues encountered documented

---

## Rollback Plan

**If critical issues within first hour:**

```bash
# 1. Revert to pre-Clerk commit
git revert --no-commit HEAD~N..HEAD  # N = number of commits
git commit -m "Rollback: Revert Clerk auth migration"
git push origin main

# 2. Railway/Vercel auto-deploys (~3-5 minutes)

# 3. Users can login with old auth immediately
```

**Rollback time**: ~5 minutes

**Data safety**:
- `clerk_user_id` column ignored by old auth
- Portfolio data uses internal UUIDs (unaffected)
- Database columns are additive (no data loss)

---

## VIP User Migration (If Applicable)

If there are existing alpha testers beyond demo accounts:

### Option A: User Re-registers (Default)
Send email:
```
Subject: SigmaSight Login Update

We've upgraded our login system. Please:
1. Create a new account at sigmasight.com/sign-up
2. Use invite code: 2026-FOUNDERS-BETA
3. Re-import your portfolio CSV

Reply if you need help!
```

### Option B: Manual VIP Migration
For important early adopters:

```python
# 1. Create Clerk user via API
clerk_user = clerk.users.create(
    email_address=["vip@example.com"],
    skip_password_requirement=True,  # They'll reset via email
)

# 2. Link to existing data
UPDATE users
SET clerk_user_id = 'user_xxx',
    invite_validated = true
WHERE email = 'vip@example.com';

# 3. Send password reset email via Clerk
```

- [ ] Identify any VIP users needing migration
- [ ] Choose migration option for each
- [ ] Execute and verify

---

## Success Criteria (PRD Section 18)

| Metric | Target | Status |
|--------|--------|--------|
| Demo accounts work | 3/3 login and see data | [ ] |
| New user signup | Complete in <60 seconds | [ ] |
| Invite validation | Blocks until validated | [ ] |
| First payment | $18 processed successfully | [ ] |
| Portfolio limit (Free) | Hard block at 2 | [ ] |
| Portfolio limit (Paid) | Hard block at 10 | [ ] |
| AI message limit (Free) | Hard block at 100/month | [ ] |
| AI message limit (Paid) | Hard block at 1,000/month | [ ] |
| Upgrade flow | Immediate higher limits | [ ] |
| SSE chat | Works with Clerk token | [ ] |
| Logging | Key events in logs | [ ] |

---

## Post-Migration Cleanup (Week 2)

After 1 week of stable operation:

- [ ] Remove old `/api/v1/auth/login` endpoint (or mark deprecated)
- [ ] Remove old `/api/v1/auth/register` endpoint
- [ ] Remove `authManager.ts` from frontend
- [ ] Clean up any dual-auth code paths
- [ ] Update documentation to reflect Clerk-only auth
