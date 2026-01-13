# Frontend Root-Level Files Documentation

This document covers all root-level configuration and setup files in `frontend/`.

---

## Configuration Files

| File | Purpose | Usage |
|------|---------|-------|
| `package.json` | Defines Node.js project metadata, dependencies (React 18, Next 16, Tailwind), dev dependencies, and npm scripts (dev on port 3005, build, lint, type-check, test). | Used by `npm install` and `npm run` commands; installed by Docker during build stage. |
| `next.config.js` | Configures Next.js 16 runtime (standalone output for Docker, Turbopack, remote image patterns, security headers, webpack rules for .md files, Windows polling for dev). | Loaded by Next.js at startup; enables Docker optimization and development features. |
| `middleware.ts` | Implements Clerk authentication middleware using `clerkMiddleware` to protect routes—allows public routes (/login, /landing), admin routes, and API routes, redirects unauthenticated users to /sign-in. | Runs on every request in Next.js App Router to enforce authentication boundaries. |
| `tsconfig.json` | Configures TypeScript compiler options (strict mode, ES5 target, path aliases like `@/`, module resolution, JSX). | Used by `npm run type-check` and IDE/build tools for TypeScript validation. |
| `tailwind.config.js` | Configures Tailwind CSS (dark mode, content paths, design tokens for cards/badges/charts, color palette, animations). | Loaded by PostCSS and referenced in components via `className` attributes for styling. |
| `postcss.config.js` | Configures PostCSS with Tailwind and Autoprefixer plugins for CSS processing. | Executed during CSS compilation to transform Tailwind directives into production CSS. |
| `.eslintrc.json` | Configures ESLint to extend Next.js core web vitals rules and ignore node_modules/.next/dist/out/coverage. | Used by `npm run lint` to validate code quality and enforce Next.js standards. |
| `components.json` | Configuration for shadcn/ui CLI tool specifying style (new-york), Tailwind config path, aliases for components/utils/ui paths. | Used by `npx shadcn-ui add` command to install UI components in correct locations. |

---

## Testing Configuration

| File | Purpose | Usage |
|------|---------|-------|
| `playwright.config.ts` | Configures Playwright E2E testing (test directory, chromium+Mobile Safari, baseURL at localhost:3005, webServer config for npm dev + Python backend). | Used by `npm run test` to run automated browser tests; supports CI with retries. |
| `playwright.equity.config.ts` | Alternative Playwright config (parallel disabled, chromium only, list reporter, used for equity-specific tests). | Manually selected when running equity test suite instead of default playwright.config. |

---

## Deployment Configuration

| File | Purpose | Usage |
|------|---------|-------|
| `railway.json` | Railway deployment configuration specifying Dockerfile path, restart policy (ON_FAILURE with 10 retries), health check endpoint (/api/health). | Read by Railway CI/CD platform to build and deploy frontend container to production. |
| `Dockerfile` | Multi-stage Docker build (deps → builder → runner) using Node 20 Alpine, installs dependencies, builds Next.js app, runs as non-root user on port 3005 with health checks. | Executed by Docker during image build; used locally (`docker build -t sigmasight-frontend .`) and in Railway deployment. |
| `docker-compose.yml` | Defines single frontend service with Dockerfile build, environment variables from .env.local, port mapping (3005:3005), health check, restart policy. | Executed by `docker-compose up -d` to build and start the frontend container locally. |

---

## Environment Configuration

| File | Purpose | Usage |
|------|---------|-------|
| `.env.example` | Template for environment variables including NEXT_PUBLIC_BACKEND_API_URL (with /api/v1), BACKEND_URL, OpenAI key, Clerk auth keys, feature flags, portfolio defaults. | Copied to `.env.local` by developers; documents all required config before running. |
| `.env.local` | Actual runtime environment configuration specifying backend URL, OpenAI API key, Clerk settings, debug flags (not committed to git). | Loaded by Next.js and Docker at startup; provides local development overrides. |
| `.gitignore` | Excludes node_modules, .next, .env files, test artifacts, IDE settings, API keys to prevent credential leaks. | Enforced by Git to prevent accidental commits of secrets and build artifacts. |

---

## TypeScript & Documentation

| File | Purpose | Usage |
|------|---------|-------|
| `next-env.d.ts` | Auto-generated TypeScript declarations for Next.js types and image globals (do not edit manually). | Included automatically in tsconfig.json to enable type checking for Next.js APIs. |
| `CLAUDE.md` | Comprehensive development guide (32KB) covering architecture, page patterns, services (11 total), state management, backend API integration, demo credentials, implementation progress. | READ FIRST before implementing features; referenced by development workflow and provides critical context. |
| `DOCKER.md` | Complete Docker deployment guide (5.4KB) with compose commands, health checks, port configuration, local vs Railway setup, troubleshooting. | Referenced when troubleshooting Docker issues or setting up new environments. |
| `RAILWAY_BACKEND_SETUP.md` | Guide for setting up Railway backend deployment. | Referenced during Railway deployment configuration. |
| `RAILWAY_DOCKER_DEPLOYMENT.md` | Guide for Docker-based Railway deployment. | Referenced during Railway deployment configuration. |

---

## Summary Statistics

- **Total Root Files**: 19 configuration/documentation files
- **Config Files**: 8 (package.json, next.config.js, tsconfig.json, tailwind, postcss, eslint, components.json, middleware)
- **Testing Configs**: 2 (playwright configs)
- **Deployment Configs**: 3 (railway.json, Dockerfile, docker-compose.yml)
- **Environment**: 3 (.env files, .gitignore)
- **Documentation**: 5 (CLAUDE.md, DOCKER.md, next-env.d.ts, Railway guides)
