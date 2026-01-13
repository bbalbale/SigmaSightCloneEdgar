# Frontend App Directory Documentation

This document covers all files in `frontend/app/` (Next.js App Router pages).

---

## Root Level Files

| File | Purpose | Usage |
|------|---------|-------|
| `layout.tsx` | Root layout wrapping entire application with Clerk provider, styling, and navigation headers. | Wraps all pages with ClerkProvider, global styles, ConditionalNavigationHeader, BottomNavigation, and Providers context. |
| `page.tsx` | Root redirect page that automatically routes to /command-center. | Serves as the main app entry point (/) for authenticated users. |
| `providers.tsx` | Central authentication provider managing Clerk JWT tokens, portfolio ID Zustand store, and theme context. | Wraps entire app in React Context for auth, Zustand store initialization, and ClerkTokenSync for token management. |
| `error.tsx` | Global error boundary displaying user-friendly error messages with error codes and troubleshooting info. | Catches errors during page rendering and displays with formatted error code, message, and retry button. |
| `loading.tsx` | Global loading fallback skeleton shown while pages load. | Displays animated spinner and "Loading SigmaSight..." text during page transitions. |

---

## Authentication Routes

| File | Purpose | Usage |
|------|---------|-------|
| `login/page.tsx` | Legacy login redirect page maintained for backward compatibility. | Redirects users from /login to /sign-in (Clerk sign-in page). |
| `sign-in/[[...sign-in]]/page.tsx` | Clerk-hosted sign-in page with dark theme and custom branding. | Displays Clerk SignIn component styled with SigmaSight branding, redirects to /command-center after login. |
| `sign-up/[[...sign-up]]/page.tsx` | Clerk-hosted sign-up page with dark theme and custom branding. | Displays Clerk SignUp component styled with SigmaSight branding, redirects to /onboarding/invite after signup. |
| `test-user-creation/page.tsx` | Legacy test user creation page maintained for backward compatibility. | Redirects users from /test-user-creation to /sign-up (Clerk sign-up page). |

---

## Landing/Marketing Pages

| File | Purpose | Usage |
|------|---------|-------|
| `landing/layout.tsx` | Wrapper layout for landing page with landing-specific container. | Provides minimal layout structure for /landing page marketing content. |
| `landing/page.tsx` | Marketing homepage with hero section, pricing tiers, and feature descriptions. | Displays product marketing, user tier selection (Basic/Standard/Professional), quick actions, and signup CTAs. |
| `landing/components/Header.tsx` | Marketing page header component. | Used in landing page layout for navigation. |

---

## Core Application Pages (Authenticated)

| File | Purpose | Usage |
|------|---------|-------|
| `command-center/page.tsx` | Main dashboard/hub page rendering CommandCenterContainer. | Thin page wrapper following container pattern; displays portfolio overview, metrics, and navigation to other features. |
| `home/page.tsx` | Home page rendering HomeContainer with core dashboard. | Thin page wrapper; provides alternative entry point to main application dashboard. |
| `risk-metrics/page.tsx` | Risk analytics page showing sector exposure, concentration, and volatility metrics. | Thin page wrapper rendering RiskMetricsContainer with advanced risk analysis visualizations. |
| `research-and-analyze/page.tsx` | Research and company analysis page. | Thin page wrapper rendering ResearchAndAnalyzeContainer with company profiling and analysis tools. |
| `sigmasight-ai/page.tsx` | AI analytical reasoning chat interface page. | Thin page wrapper rendering SigmaSightAIContainer with Claude Sonnet 4 AI chat functionality. |
| `settings/page.tsx` | User preferences and account settings page. | Thin page wrapper rendering SettingsContainer with user profile and application settings. |
| `equity-search/page.tsx` | Equity research and stock search page. | Thin page wrapper rendering EquitySearchContainer with stock/company search and research functionality. |

---

## Onboarding Flow

| File | Purpose | Usage |
|------|---------|-------|
| `onboarding/invite/page.tsx` | Invite code validation page during signup flow. | Renders InviteCodeForm; user enters invite code to proceed to portfolio upload. |
| `onboarding/upload/page.tsx` | Portfolio upload page accepting CSV file with positions. | Handles portfolio CSV file upload with validation, displays errors, uploading state, and error handling. |
| `onboarding/progress/page.tsx` | Real-time batch processing status monitor during portfolio setup. | Polls batch status endpoint and displays phase-by-phase progress with activity logs and completion states. |

---

## Admin Dashboard

| File | Purpose | Usage |
|------|---------|-------|
| `admin/layout.tsx` | Admin area layout with authentication check and access control. | Wraps admin routes with auth verification; redirects unauthenticated users to /admin/login. |
| `admin/page.tsx` | Admin dashboard home with overview metrics and section navigation. | Displays AI metrics (requests, latency, errors), batch status, and links to admin sections (onboarding, AI metrics, batch processing). |
| `admin/login/page.tsx` | Admin login page for admin-only access. | Renders AdminLoginForm for admin authentication with admin-specific credentials. |
| `admin/onboarding/page.tsx` | Onboarding analytics dashboard showing funnel and error tracking. | Displays user funnel progression, error breakdown, daily activity trends with period filtering. |
| `admin/batch/page.tsx` | Batch processing history and job monitoring page. | Shows batch run history, status breakdown, performance metrics, phase durations, and downloadable logs. |
| `admin/ai/page.tsx` | AI performance metrics dashboard with latency, tokens, and errors. | Displays AI request metrics, latency percentiles, token usage, tool usage breakdown, model usage, and error analysis. |

---

## API Routes

| File | Purpose | Usage |
|------|---------|-------|
| `api/health/route.ts` | Health check endpoint for container monitoring and uptime verification. | Returns JSON with status, timestamp, version, and environment; used by Docker health checks. |
| `api/proxy/[...path]/route.ts` | Universal proxy to FastAPI backend handling CORS, auth, and streaming. | Forwards GET/POST/PUT/PATCH/DELETE/OPTIONS requests to backend at BACKEND_URL with cookie/header forwarding and SSE streaming support. |

---

## Development/Testing

| File | Purpose | Usage |
|------|---------|-------|
| `dev/api-test/page.tsx` | Development API testing page for debugging backend endpoints. | Provides comprehensive API testing interface with portfolio detection, analytics calls, target price management, strategy/tag testing, and full request/response logging. |

---

## Summary Statistics

- **Total Pages**: 28 main files
- **Authenticated Pages**: 7 (command-center, home, risk-metrics, research-and-analyze, sigmasight-ai, settings, equity-search)
- **Onboarding Pages**: 3 (invite, upload, progress)
- **Admin Pages**: 6 (dashboard, login, onboarding, batch, ai, + layout)
- **API Routes**: 2 (health, proxy)
- **Marketing**: 2 (landing page + layout)
- **Auth Routes**: 4 (login, sign-in, sign-up, test-user-creation)
- **Root/System**: 5 (layout, page, providers, error, loading)
- **Development**: 1 (api-test)

---

## Architectural Patterns

1. **Thin Page Files** (5-15 lines) - Most authenticated pages follow container pattern
2. **Container Pattern** - Business logic in containers, pages just import and render
3. **Admin Layout Pattern** - Nested layout with auth checking for protected admin routes
4. **API Proxy Pattern** - Single proxy route handling all backend communication
5. **Clerk Authentication** - Sign-in/sign-up pages use Clerk hosted components with dark theme

---

## Key User Flows

- **Authentication**: /sign-in → /command-center → All app pages
- **New User**: /sign-up → /onboarding/invite → /onboarding/upload → /onboarding/progress → /command-center
- **Admin**: /admin/login → /admin (dashboard) → Sub-sections (onboarding, batch, ai)
- **Dev Testing**: /dev/api-test (requires authentication)
