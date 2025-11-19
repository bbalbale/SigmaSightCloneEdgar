# Debug: Generate Button Grayed Out

**Issue**: The "Generate" button on `/sigmasight-ai` page is disabled (grayed out)

---

## Quick Diagnosis

Open browser DevTools (F12) and check these in order:

### 1. Check Console for Errors
```javascript
// Look for errors when page loads
// Common errors:
// - "Failed to load AI insights"
// - "No portfolio ID"
// - "Authentication failed"
```

### 2. Check localStorage
```javascript
// In Console tab, run:
localStorage.getItem('access_token')
localStorage.getItem('portfolio-storage')

// Expected:
// - access_token: "eyJ..." (long JWT token)
// - portfolio-storage: {"state":{"portfolioId":"2c251ae0-..."}}
```

### 3. Check React State
```javascript
// In Console tab, run:
console.log('generatingInsight:', window.__REACT_DEVTOOLS_GLOBAL_HOOK__)

// Or use React DevTools Extension:
// 1. Install React DevTools
// 2. Go to Components tab
// 3. Find SigmaSightAIContainer
// 4. Check props: generatingInsight should be false
```

### 4. Check Network Tab
```javascript
// In Network tab:
// 1. Refresh page
// 2. Look for request to /api/v1/insights?portfolio_id=...
// 3. Check if it succeeded (200) or failed (401/403/500)
```

---

## Most Common Causes & Fixes

### Cause 1: No Portfolio ID in Store

**Symptoms**:
- Button is grayed out immediately
- Console shows "No portfolio ID"

**Fix**:
```javascript
// In browser console:
// 1. Logout
localStorage.clear()

// 2. Login again at /login
// 3. Navigate to /sigmasight-ai
```

### Cause 2: `generatingInsight` State Stuck

**Symptoms**:
- Button shows "Generating..." even though nothing is happening
- React state shows `generatingInsight: true`

**Fix**:
```javascript
// Quick hack in console:
// (This is temporary - will reset on page refresh)
const store = JSON.parse(localStorage.getItem('portfolio-storage'))
// Then go to React DevTools and manually set generatingInsight to false

// OR

// Hard refresh browser
location.reload(true)
```

### Cause 3: Backend Not Connected

**Symptoms**:
- Network tab shows failed requests to localhost:8000
- Console shows "Failed to fetch"

**Fix**:
1. Check `.env.local` has:
   ```
   NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
   BACKEND_URL=http://localhost:8000
   ```
2. Restart frontend: `npm run dev`
3. Verify backend is running: http://localhost:8000/docs

### Cause 4: Authentication Failed

**Symptoms**:
- Network tab shows 401 Unauthorized
- Console shows "Authentication failed"

**Fix**:
```javascript
// Clear auth and re-login
localStorage.removeItem('access_token')
// Then go to /login and login again
```

---

## Step-by-Step Debug Process

### Step 1: Open Browser DevTools
- Press F12
- Go to Console tab

### Step 2: Check Auth Token
```javascript
localStorage.getItem('access_token')
// Should return: "eyJ..." (JWT token)
// If null: You need to login
```

### Step 3: Check Portfolio ID
```javascript
JSON.parse(localStorage.getItem('portfolio-storage'))
// Should return: {"state":{"portfolioId":"..."}}
// If null: You need to login
```

### Step 4: Check Network Requests
- Go to Network tab
- Refresh page
- Look for `/api/v1/insights?portfolio_id=...`
- Check status code (should be 200)
- If 401: Auth failed
- If 404: Portfolio not found
- If 500: Backend error

### Step 5: Check React Component State
- Install React DevTools extension
- Go to Components tab
- Find `SigmaSightAIContainer`
- Check state:
  - `generatingInsight`: should be `false`
  - `loading`: should be `false` after page loads
  - `error`: should be `null`

---

## Code References

The button is disabled when `generatingInsight` is true:

**File**: `frontend/src/containers/SigmaSightAIContainer.tsx` (line 91)
```typescript
<button
  onClick={handleGenerateInsight}
  disabled={generatingInsight}  // <-- This is the issue
  ...
>
  {generatingInsight ? "Generating..." : "Generate"}
</button>
```

**File**: `frontend/src/hooks/useAIInsights.ts` (line 20, 62-64)
```typescript
const [generatingInsight, setGeneratingInsight] = useState(false)

// In handleGenerateInsight:
if (generatingInsight) {
  console.warn('⚠️ Already generating insight, skipping')
  return  // <-- Prevents clicking while generating
}
```

---

## Manual Override (Last Resort)

If nothing else works, you can manually override the state in React DevTools:

1. Install React DevTools extension
2. Open DevTools → Components tab
3. Find `SigmaSightAIContainer`
4. Click on it
5. In right panel, find `generatingInsight` in hooks
6. Click the value and change it to `false`
7. Button should become enabled

**Note**: This is temporary and will reset on page refresh!

---

## Expected Console Logs

When the page loads correctly, you should see:

```
🔍 handleGenerateInsight called {portfolioId: "2c251ae0-...", generatingInsight: false}
✅ Starting insight generation...
📡 Calling API...
✅ Insight generated: abc-123
📝 Adding new insight to list
🏁 Finished (setting generatingInsight = false)
```

If you DON'T see these logs, the button might be disabled due to:
- No portfolio ID
- Already generating (stuck state)
- Component not mounted correctly

---

## Still Stuck?

If the button is still grayed out after trying all the above:

1. **Full Reset**:
   ```javascript
   localStorage.clear()
   sessionStorage.clear()
   location.reload(true)
   ```

2. **Check Browser Console** for errors

3. **Check Backend is Running**: http://localhost:8000/docs

4. **Try Different Browser** (Chrome/Firefox/Edge)

5. **Check .env.local** is correct:
   ```
   NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
   ```

6. **Restart Frontend**:
   ```bash
   # Kill frontend
   # Then restart
   cd frontend && npm run dev
   ```

---

**Last Updated**: December 18, 2025
