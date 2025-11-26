# Troubleshooting: Generate Button Errors

## Current Issue

You're seeing this error when clicking Generate:
```
API request failed, retrying in 2000ms (attempt 2/3)
```

## Root Cause

The backend is returning:
```json
{"detail":"Could not validate credentials"}
```

This means the **JWT token is missing or expired**.

## Quick Fix

### Option 1: Login Again (Recommended)

1. Open http://localhost:3005/login
2. Login with demo credentials:
   - Email: `demo_hnw@sigmasight.com`
   - Password: `demo12345`
3. After successful login, go to http://localhost:3005/sigmasight-ai
4. Click "Generate" button

### Option 2: Check Browser Console

1. Open browser DevTools (F12)
2. Go to Console tab
3. Run this command:
   ```javascript
   localStorage.getItem('access_token')
   ```
4. If it returns `null` or an expired token, you need to login again

### Option 3: Manual Token Check

1. Open browser DevTools (F12)
2. Go to Application tab
3. Expand "Local Storage" → http://localhost:3005
4. Check if `access_token` exists
5. If missing or looks old (check the JWT exp claim), login again

## Why This Happened

When you restart the backend server:
- The server uses a new process
- Old JWT tokens may become invalid
- User needs to re-authenticate

## How to Verify It's Fixed

After logging in again:

1. Click "Generate" button on /sigmasight-ai page
2. Check backend console logs (should show):
   ```
   INFO: Fetching analytics bundle for portfolio <uuid>
   INFO: Analytics bundle fetched: 7/7 metric categories
   INFO: Starting Claude investigation...
   ```
3. No more "Could not validate credentials" errors

## Backend Logs to Watch

The backend should show:
```
INFO:     127.0.0.1:XXXXX - "POST /api/v1/insights/generate HTTP/1.1" 200 OK
```

If you see:
```
INFO:     127.0.0.1:XXXXX - "POST /api/v1/insights/generate HTTP/1.1" 401 Unauthorized
```

Then the token is still invalid - logout and login again.

## Complete Reset (If Nothing Else Works)

```javascript
// In browser console:
localStorage.clear()
sessionStorage.clear()
location.reload(true)

// Then go to /login and login again
```

---

**Next Steps**:
1. Go to http://localhost:3005/login
2. Login with demo_hnw@sigmasight.com / demo12345
3. Navigate to /sigmasight-ai
4. Click Generate
5. Watch backend logs for Option C analytics bundle messages

**Expected Result**: Insight generates successfully in 18-22 seconds with 0 tool calls!
