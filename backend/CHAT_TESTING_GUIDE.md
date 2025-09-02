# SigmaSight Chat Testing Guide

## 🚀 Live Monitoring Session - ACTIVE

The monitoring infrastructure is now running and ready for testing.

### ✅ Current Status

**Servers Running:**
- ✅ Frontend: http://localhost:3005 (39ms response time)
- ✅ Backend: http://localhost:8000 (3ms response time)
- ✅ Authentication: Working (JWT + HttpOnly cookies)
- ✅ Monitoring: Active (updates every 30 seconds)

**Background Processes:**
- Frontend Dev Server (bash_5) - Running Next.js on localhost:3005
- Backend Server (bash_3) - Running FastAPI on localhost:8000  
- Monitoring Script (bash_10) - Logging to `chat_monitoring_report.json`

### 🎯 Manual Testing Steps

#### 1. Open Browser and Navigate
```
URL: http://localhost:3005
```
The application will automatically redirect to `/portfolio`

#### 2. Login with Demo Credentials
```
Email: demo_hnw@sigmasight.com
Password: demo12345
```

#### 3. Navigate to Chat Interface
- Look for chat button/trigger on the portfolio page
- The chat interface should be integrated into the portfolio view

#### 4. Test Chat Functionality
- Send a test message: "What is my portfolio performance?"
- Monitor for:
  - Real-time streaming responses
  - Console errors (F12 Developer Tools)
  - Network requests to `/api/v1/chat/*`
  - Authentication persistence

### 📊 Real-Time Monitoring

The monitoring system tracks:

**Console Monitoring:**
- All console messages (info, warn, error)
- JavaScript errors and stack traces
- Authentication flows

**Network Monitoring:**  
- All HTTP requests (focus on `/api/v1/chat/`)
- Response status codes and timing
- SSE streaming connections

**Error Tracking:**
- Request failures
- Authentication errors  
- Streaming connection issues

### 📈 Monitoring Data Location

Live monitoring data is saved to:
```
/Users/elliottng/CascadeProjects/SigmaSight-BE/backend/chat_monitoring_report.json
```

This file updates every 60 seconds with:
- Console messages (last 100)
- Network requests (last 50) 
- Error summaries
- Performance metrics

### 🔍 Key Areas to Monitor

#### Authentication Flow
- JWT token generation and validation
- HttpOnly cookie handling  
- Session persistence across refreshes
- Logout cleanup

#### SSE Streaming
- Connection establishment to streaming endpoints
- Message delivery and formatting
- Error handling and reconnection
- Abort/cancel functionality

#### Responsive Design
- Mobile viewport behavior
- Touch interactions
- Layout shifts
- iOS Safari compatibility

#### Error Handling
- RATE_LIMITED errors (30s retry)
- AUTH_EXPIRED redirects  
- NETWORK_ERROR retries
- SERVER_ERROR displays

### 📋 Testing Checklist

- [ ] Login flow works with demo credentials
- [ ] Chat interface is accessible
- [ ] Test message sends successfully  
- [ ] Streaming responses arrive in real-time
- [ ] Console shows no JavaScript errors
- [ ] Network requests complete successfully
- [ ] Authentication persists across page refresh
- [ ] Mobile responsive design works
- [ ] Error states display appropriately

### 🛠 Troubleshooting

If issues arise:

1. **Check Server Status:**
   ```bash
   curl http://localhost:3005  # Should return 200
   curl http://localhost:8000/docs  # Should return 200
   ```

2. **View Live Monitoring:**
   ```bash
   tail -f /Users/elliottng/CascadeProjects/SigmaSight-BE/backend/chat_monitoring_report.json
   ```

3. **Check Background Processes:**
   ```bash
   # Check frontend logs
   # Check backend logs  
   # Check monitoring script
   ```

4. **Restart if Needed:**
   ```bash
   # Frontend: Ctrl+C and npm run dev
   # Backend: Ctrl+C and uv run python run.py
   # Monitoring: Ctrl+C and uv run python simple_monitor.py
   ```

### 📊 Performance Targets

- **TTFB (Time to First Byte):** < 3000ms
- **Total Response Time:** < 10s  
- **Memory Usage:** Monitor for leaks
- **Error Rate:** < 1%

---

**Session Status:** ✅ READY FOR TESTING
**Next Step:** Open browser to http://localhost:3005 and begin manual testing