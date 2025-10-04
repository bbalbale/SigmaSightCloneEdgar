# Monitoring Scripts

Real-time system monitoring and health check tools.

## Key Scripts

- **monitor_chat_interface.py** ⭐ **MAIN** - Monitor chat interface with Playwright
- **simple_monitor.py** - Basic system monitoring

## Usage

### Monitor chat interface:
```bash
cd backend
uv run python scripts/monitoring/monitor_chat_interface.py
```

This script uses Playwright to:
- Monitor real-time console logs
- Capture screenshots
- Test chat interactions
- Validate SSE streaming
- Check error handling

## Features

- Real-time console log capture
- Automated screenshot capture
- Performance monitoring
- Error detection
- SSE stream validation