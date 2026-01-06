# Phase 3: Frontend Auth Migration

**Estimated Duration**: 2-3 days
**Dependencies**: Phase 2 complete (backend auth working)
**PRD Reference**: Sections 6, 13, 14

---

## Entry Criteria

Before starting this phase, ensure:
- [x] Phase 2 complete (all exit criteria passed)
- [x] Backend webhook handler working (tested with Clerk)
- [x] Can verify JWT tokens via backend `/api/v1/auth/me`
- [x] Frontend running locally (`npm run dev` or Docker)

---

## Tasks

### 3.1 Install Clerk SDK

**File**: `frontend/package.json`

```bash
cd frontend
npm install @clerk/nextjs @clerk/themes
```

- [x] Install `@clerk/nextjs`
- [x] Install `@clerk/themes` (optional, for styling)
- [x] Verify packages in `package.json`

### 3.2 Environment Variables

**File**: `frontend/.env.local`

```bash
# Clerk (from Clerk Dashboard → API Keys)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Clerk URLs
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/settings
```

- [x] Add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- [x] Add `CLERK_SECRET_KEY`
- [x] Configure redirect URLs

### 3.3 ClerkProvider Setup

**File**: `frontend/app/layout.tsx`

Wrap app with ClerkProvider:

```tsx
import { ClerkProvider } from '@clerk/nextjs'

export default function RootLayout({ children }) {
  return (
    <ClerkProvider>
      <html>
        <body>{children}</body>
      </html>
    </ClerkProvider>
  )
}
```

- [x] Import `ClerkProvider`
- [x] Wrap root layout with provider

### 3.4 Middleware Configuration

**File**: `frontend/middleware.ts`

Implement route protection (PRD Sections 9.3.1, 13.2):

```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isAdminRoute = createRouteMatcher(['/admin(.*)'])
const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)', '/landing(.*)'])
const isSettingsRoute = createRouteMatcher(['/settings(.*)', '/invite(.*)'])

export default clerkMiddleware(async (auth, req) => {
  // Admin routes bypass Clerk
  if (isAdminRoute(req)) return

  // Public routes don't require auth
  if (isPublicRoute(req)) return

  // Require auth for everything else
  const { userId } = auth()
  if (!userId) return auth().protect()

  // Settings allowed without invite (to enter code)
  if (isSettingsRoute(req)) return

  // Check invite status for other pages
  const user = await fetchCurrentUser(userId)
  if (!user.invite_validated) {
    return Response.redirect(new URL('/settings?invite_required=true', req.url))
  }
})
```

- [x] Create `middleware.ts`
- [x] Exclude admin routes from Clerk
- [x] Allow settings without invite validation
- [x] Redirect non-invited users to settings (handled at component level)

### 3.5 Sign-In Page

**File**: `frontend/app/sign-in/[[...sign-in]]/page.tsx`

```tsx
import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignIn />
    </div>
  )
}
```

- [x] Create sign-in page with Clerk component
- [x] Style to match app design

### 3.6 Sign-Up Page

**File**: `frontend/app/sign-up/[[...sign-up]]/page.tsx`

```tsx
import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignUp />
    </div>
  )
}
```

- [x] Create sign-up page with Clerk component
- [x] Style to match app design

### 3.7 API Client Hook

**File**: `frontend/src/hooks/useApiClient.ts`

Create hook for authenticated API calls (PRD Section 6.2):

```typescript
import { useAuth } from '@clerk/nextjs'

export function useApiClient() {
  const { getToken } = useAuth()

  return {
    fetch: async (url: string, options?: RequestInit) => {
      const token = await getToken()
      return fetch(url, {
        ...options,
        headers: {
          ...options?.headers,
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    },
    getAuthHeaders: async () => {
      const token = await getToken()
      return { Authorization: `Bearer ${token}` }
    },
  }
}
```

- [x] Create `useApiClient` hook
- [x] Ensure it works with SSE connections

### 3.8 Update Service Layer

Update existing services to accept token as parameter:

**File**: `frontend/src/services/portfolioService.ts` (example)

```typescript
// Before: Used authManager internally
// After: Accept token as parameter

export async function getPortfolios(token: string) {
  return fetch('/api/v1/portfolios', {
    headers: { Authorization: `Bearer ${token}` },
  })
}
```

- [x] Update `portfolioService.ts` (via ClerkTokenSync + apiClient interceptor)
- [x] Update `chatService.ts` (SSE) (via ClerkTokenSync)
- [x] Update other services as needed (via global token store)
- [x] Remove old `authManager` usage from components (kept for backward compat)

### 3.9 Settings Page Updates

**File**: `frontend/app/settings/page.tsx`

Add:
1. Invite code entry form (if not validated)
2. Billing link (to Clerk portal)
3. Usage display (portfolio count, AI messages)

```tsx
// Invite code form (show if !invite_validated)
<form onSubmit={handleInviteSubmit}>
  <input name="invite_code" placeholder="Enter invite code" />
  <button type="submit">Validate</button>
</form>

// Billing link
<a href={`https://accounts.${CLERK_DOMAIN}/user/billing`}>
  Manage Subscription
</a>
```

- [x] Add invite code entry form
- [x] Add billing portal link
- [x] Show usage stats from `/api/v1/auth/me`
- [x] Show upgrade prompt for free users

### 3.10 Upgrade Prompts

Add upgrade prompts when limits are reached:

**Portfolio limit reached:**
```tsx
{portfolioCount >= portfolioLimit && (
  <div className="alert">
    You've reached your limit of {portfolioLimit} portfolios.
    <a href="/settings">Upgrade to Pro</a>
  </div>
)}
```

**AI message limit reached:**
```tsx
{aiMessagesUsed >= aiMessagesLimit && (
  <div className="alert">
    You've used all {aiMessagesLimit} AI messages this month.
    <a href="/settings">Upgrade for more</a>
  </div>
)}
```

- [x] Add portfolio limit prompt to portfolio creation UI (UpgradePrompt component)
- [x] Add AI message limit prompt to chat UI (UpgradePrompt component)

### 3.11 Remove Old Auth Components

- [x] Remove or redirect `/login` page to `/sign-in`
- [x] Remove or redirect `/signup` page to `/sign-up`
- [x] Remove `authManager.ts` (or mark deprecated) - kept for backward compat
- [x] Update navigation to use Clerk's `<UserButton />`

### 3.12 User Button in Navigation

**File**: `frontend/src/components/navigation/NavigationDropdown.tsx`

Replace custom user menu with Clerk's UserButton:

```tsx
import { UserButton } from '@clerk/nextjs'

// In navigation component
<UserButton afterSignOutUrl="/sign-in" />
```

- [x] Import and use `<UserButton />`
- [x] Configure sign-out redirect

---

## Exit Criteria (Definition of Done)

### Visual Verification
- [x] Sign-in page renders Clerk component
- [x] Sign-up page renders Clerk component
- [x] Settings page shows invite code form (for non-validated users)
- [x] Settings page shows billing link
- [x] UserButton appears in navigation

### Auth Flow Tests (Deferred to Phase 4)

> **Note**: These tests require a running frontend + backend with real Clerk credentials.
> They are tracked in Phase 4: Testing & Migration.

**Test 1: New user signup**
1. Go to `/sign-up`
2. Create account with email/password
3. Verify email (Clerk sends verification)
4. Redirected to `/settings`
5. See invite code form
- [ ] Signup flow works end-to-end

**Test 2: Invite code entry**
1. On settings page, enter `2026-FOUNDERS-BETA`
2. Submit form
3. Verify success message
4. Can now access dashboard
- [ ] Invite code validation works

**Test 3: Google OAuth**
1. Go to `/sign-in`
2. Click "Continue with Google"
3. Complete OAuth flow
4. Redirected to app
- [ ] Google OAuth works

**Test 4: Protected route redirect**
1. As user with `invite_validated=false`
2. Try to access `/dashboard`
3. Redirected to `/settings?invite_required=true`
- [ ] Non-invited users redirected

**Test 5: API calls with Clerk token**
1. Login via Clerk
2. Navigate to dashboard
3. Verify portfolio data loads
4. Check Network tab: Authorization header present
- [ ] API calls include Clerk JWT

**Test 6: Admin routes still work**
1. Login as admin at `/admin/login`
2. Access admin dashboard
3. Verify admin functions work
- [ ] Admin auth unaffected by Clerk migration

---

## Code Review Fixes (2026-01-05)

After initial implementation, code review identified blocking issues. All fixed:

- [x] **authManager token bridge**: `getAccessToken()` now checks `clerkTokenStore` first
- [x] **useUserEntitlements response shape**: Fixed to use nested `limits` object
- [x] **providers.tsx Clerk integration**: Uses Clerk hooks instead of legacy authManager
- [x] **Legacy page redirects**: `/login` and `/test-user-creation` redirect to Clerk pages

---

## Rollback Plan

If issues arise:
1. Remove Clerk packages: `npm uninstall @clerk/nextjs @clerk/themes`
2. Remove `ClerkProvider` from layout
3. Delete middleware.ts (or restore original)
4. Restore old login/signup pages
5. Restore authManager usage in services

---

## Notes

- Keep old auth pages temporarily (redirect to new ones)
- Test with Clerk Development instance
- Admin routes are completely separate from Clerk
- SSE connections need token at connection time (see PRD Section 6.3)
