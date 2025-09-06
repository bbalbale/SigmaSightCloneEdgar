# Docker Diagnostic & Fix Plan

## Current Issues
1. Login page: "Unexpected token '<', "<!DOCTYPE"..." error (404 returning HTML)
2. Chat streaming: Not working (was working before Docker)

## Root Cause
The Docker image was built with old code before the chatAuthService fix. The production build uses `NODE_ENV` to determine the baseUrl, which fails in Docker.

## Immediate Fix Plan

### Step 1: Verify Current State
```bash
# Check what the dev server is using
curl -X POST http://localhost:3005/api/proxy/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'

# Check what the Docker container has
docker exec frontend cat .next/BUILD_ID
```

### Step 2: Fix Service Configuration
The issue is that services are checking `NODE_ENV` at runtime, but in production builds, this needs to be determined at build time or use runtime environment variables.

**Option A: Runtime Configuration (Recommended)**
- Use `NEXT_PUBLIC_USE_PROXY` environment variable
- Services check this instead of NODE_ENV
- Can be changed without rebuilding

**Option B: Build-time Configuration**
- Use `NEXT_PUBLIC_API_BASE_URL` at build time
- Bake the correct URL into the build
- Requires rebuild for changes

### Step 3: Implementation

#### Fix 1: Update Service Files
```typescript
// chatAuthService.ts
constructor() {
  // Use environment variable or default to proxy
  this.baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/proxy';
}
```

#### Fix 2: Update Dockerfile
```dockerfile
# Add build args for public variables
ARG NEXT_PUBLIC_API_BASE_URL=/api/proxy
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
```

#### Fix 3: Rebuild and Test
```bash
# Rebuild with correct configuration
cd frontend
docker build -t sigmasight-frontend \
  --build-arg NEXT_PUBLIC_API_BASE_URL=/api/proxy .

# Run with verification
docker run -d -p 3006:3005 --name frontend sigmasight-frontend

# Test endpoints
curl http://localhost:3006/api/proxy/api/v1/auth/login # Should work
# Browser login should also work
```

## Long-term Solution

### Align with Docker Implementation Plan
The plan (lines 508-520) suggests:
```javascript
const API_URL = process.env.DOCKER_ENV 
  ? 'http://backend:8000' 
  : 'http://localhost:8000';
```

But we need to consider:
1. **Standalone mode**: Container runs alone (use host.docker.internal)
2. **Compose mode**: Container in network (use backend service name)
3. **Production mode**: Real deployment (use actual URLs)

### Recommended Architecture
```
Environment Detection:
├── Development (npm run dev) → localhost:8000
├── Docker Standalone → host.docker.internal:8000  
├── Docker Compose → backend:8000
└── Production → $NEXT_PUBLIC_BACKEND_URL
```

## Testing Checklist
- [ ] Login page loads without errors
- [ ] Login succeeds and redirects to portfolio
- [ ] Portfolio data loads from backend
- [ ] Chat interface opens
- [ ] Chat messages stream properly
- [ ] All API calls go through proxy
- [ ] No CORS errors
- [ ] No 404 errors on API calls

## Rollback Plan
If issues persist:
1. Stop Docker container
2. Use npm run dev (known working)
3. Debug with browser DevTools
4. Check network tab for actual requests
5. Compare dev vs Docker behavior

## Prevention
1. Always rebuild Docker after service changes
2. Use environment variables for configuration
3. Test both dev and Docker before declaring success
4. Add automated tests for critical paths