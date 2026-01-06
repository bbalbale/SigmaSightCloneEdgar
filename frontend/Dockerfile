# Multi-stage build for production
# Updated 2025-10-09 - Node 20 LTS, improved caching, all dependencies

# Stage 1: Dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat python3 make g++
WORKDIR /app

# Copy package files for better layer caching
COPY package.json package-lock.json* ./

# Install dependencies with better caching
# Using --legacy-peer-deps to handle React 18.x compatibility
RUN npm ci --prefer-offline --no-audit --legacy-peer-deps && \
    npm cache clean --force

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy application source
COPY . .

# Build-time environment variables (configurable via --build-arg)
ARG NEXT_PUBLIC_BACKEND_API_URL
ARG NEXT_PUBLIC_DEBUG
ARG NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID
ARG NEXT_PUBLIC_MARKET_DATA_REFRESH_INTERVAL
ARG NEXT_PUBLIC_ENABLE_REALTIME_DATA
ARG NEXT_PUBLIC_ENABLE_HISTORICAL_CHARTS
ARG OPENAI_API_KEY

# Clerk Authentication (Phase 3 - required at build time for static pages)
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_CLERK_SIGN_IN_URL
ARG NEXT_PUBLIC_CLERK_SIGN_UP_URL
ARG NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL
ARG NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL
ARG NEXT_PUBLIC_CLERK_DOMAIN

# Set environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ENV NEXT_PUBLIC_BACKEND_API_URL=$NEXT_PUBLIC_BACKEND_API_URL
ENV NEXT_PUBLIC_DEBUG=$NEXT_PUBLIC_DEBUG
ENV NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID=$NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID
ENV NEXT_PUBLIC_MARKET_DATA_REFRESH_INTERVAL=$NEXT_PUBLIC_MARKET_DATA_REFRESH_INTERVAL
ENV NEXT_PUBLIC_ENABLE_REALTIME_DATA=$NEXT_PUBLIC_ENABLE_REALTIME_DATA
ENV NEXT_PUBLIC_ENABLE_HISTORICAL_CHARTS=$NEXT_PUBLIC_ENABLE_HISTORICAL_CHARTS
ENV OPENAI_API_KEY=$OPENAI_API_KEY

# Clerk Authentication environment variables
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_CLERK_SIGN_IN_URL=$NEXT_PUBLIC_CLERK_SIGN_IN_URL
ENV NEXT_PUBLIC_CLERK_SIGN_UP_URL=$NEXT_PUBLIC_CLERK_SIGN_UP_URL
ENV NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=$NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL
ENV NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=$NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL
ENV NEXT_PUBLIC_CLERK_DOMAIN=$NEXT_PUBLIC_CLERK_DOMAIN

# Build the application
RUN npm run build

# Stage 3: Production Runner
FROM node:20-alpine AS runner
WORKDIR /app

# Production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3005
ENV HOSTNAME="0.0.0.0"

# Backend URL configured via environment variables (no hardcoded defaults)
# Set these via docker run -e or docker-compose.yml
# ENV BACKEND_URL=
# ENV NEXT_PUBLIC_BACKEND_API_URL=

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone build output
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose application port
EXPOSE 3005

# Health check using the /api/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3005/api/health', (r) => {r.statusCode === 200 ? process.exit(0) : process.exit(1)})" || exit 1

# Start the application
CMD ["node", "server.js"]