# Phase 1: Clerk Billing Setup

**Estimated Duration**: 1-2 days
**Dependencies**: None (can start immediately)
**PRD Reference**: Section 8 (Clerk Billing Setup), Section 11 (Local Development)

---

## Entry Criteria

Before starting this phase, ensure:
- [x] You have admin access to create Clerk account
- [x] You have access to a Stripe account (existing or new)
- [x] You have access to Railway/production environment variables

---

## Tasks

### 1.1 Create Clerk Account & Application
- [x] Create account at [clerk.com](https://clerk.com)
- [x] Create new application named "SigmaSight"
- [x] Note the **Clerk Domain**: `included-chimp-71.clerk.accounts.dev`

### 1.2 Configure Authentication Methods
- [x] Enable **Email/Password** authentication
- [x] Enable **Google OAuth** authentication
- [x] Enable **Email Verification** (required before account active)
- [x] Block email subaddresses (prevents `user+test@email.com`)

### 1.3 Enable Clerk Billing
- [x] Go to Clerk Dashboard → Billing
- [x] Click "Enable Billing"
- [x] Connect Stripe account (Clerk will guide through OAuth flow)
- [x] Verify connection shows "Connected" status

### 1.4 Create Subscription Plans
Create these plans in **Clerk Dashboard → Billing → Plans**:

| Plan | Price | Plan Key | Display Features |
|------|-------|----------|------------------|
| Free | $0/month | `free_user` | "2 portfolios, 100 AI messages/month" |
| Pro | $18/month | `pro_user` | "10 portfolios, 1,000 AI messages/month" |

- [x] Create Free plan ($0) - key: `free_user`
- [x] Create Pro plan ($18/month) - key: `pro_user`
- [x] Enable 30-day free trial for Pro
- [x] Verify both plans appear in Clerk Dashboard

### 1.5 Configure Webhook Endpoint
- [x] Go to Clerk Dashboard → Webhooks
- [x] Add endpoint: `https://sigmasight-be-production.up.railway.app/api/v1/webhooks/clerk`
- [x] Select events to receive:
  - [x] `user.created`
  - [x] `user.deleted`
  - [x] `subscription.created`
  - [x] `subscription.cancelled`
- [x] Copy the **Signing Secret** (starts with `whsec_`)

### 1.6 Collect Environment Variables
Gathered values for backend `.env`:

```bash
# From Clerk Dashboard → API Keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# From Clerk Dashboard → Webhooks → Your endpoint
CLERK_WEBHOOK_SECRET=whsec_...

# From Clerk Dashboard → Configure → Developers → Domain
CLERK_DOMAIN=included-chimp-71.clerk.accounts.dev

# Your application's audience
CLERK_AUDIENCE=sigmasight.io
```

- [x] Copy `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- [x] Copy `CLERK_SECRET_KEY`
- [x] Copy `CLERK_WEBHOOK_SECRET`
- [x] Copy `CLERK_DOMAIN`
- [x] Set `CLERK_AUDIENCE=sigmasight.io`

### 1.7 Local Development Setup
- [x] Using development instance (pk_test_/sk_test_ keys)
- [x] Added development values to local `.env`
- [x] Updated `backend/.env.example` with all Clerk variables

---

## Exit Criteria (Definition of Done)

All must pass before moving to Phase 2:

### Clerk Dashboard Verification
- [x] Can log into Clerk Dashboard
- [x] Free and Pro plans visible in Billing → Plans
- [x] Webhook endpoint configured (will show errors until backend deployed)
- [x] Google OAuth shows "Enabled"

### API Verification
```bash
# JWKS endpoint returns keys
curl https://included-chimp-71.clerk.accounts.dev/.well-known/jwks.json

# Expected: JSON with "keys" array containing RSA public keys
```
- [x] JWKS endpoint returns valid JSON with keys

### Environment Variables
- [x] All 5 env vars documented and saved securely
- [x] Development instance configured (using test keys)

---

## Rollback Plan

If issues arise:
- Clerk accounts can be deleted and recreated
- No database changes in this phase
- No code changes in this phase

---

## Notes

- **Do NOT** create Stripe products manually - Clerk creates them automatically
- **Do NOT** add Stripe API keys to your app - Clerk handles payment processing
- Development instance uses Stripe test mode automatically
