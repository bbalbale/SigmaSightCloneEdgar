#!/usr/bin/env python3
"""
Enhanced monitoring for SigmaSight Chat Testing
Monitors application endpoints AND captures browser console logs

Usage:
  python simple_monitor.py --mode automated  # Default: headless Playwright browser
  python simple_monitor.py --mode manual     # Connect to CDP-enabled manual browser
"""

import asyncio
import aiohttp
import json
import time
import argparse
import websockets
from datetime import datetime
from typing import Dict, List, Any
import os

try:
    from playwright.async_api import async_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not available - automated console logging disabled")

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️  websockets not available - manual CDP mode disabled")

class SigmaSightMonitor:
    def __init__(self, mode="automated"):
        self.mode = mode
        self.frontend_url = "http://localhost:3005"
        self.backend_url = "http://localhost:8000"
        self.cdp_url = "http://localhost:9222"
        self.monitoring_data = {
            "session_start": datetime.now().isoformat(),
            "status_checks": [],
            "errors": [],
            "chat_interactions": [],
            "console_logs": []
        }
        # Automated mode (Playwright)
        self.browser = None
        self.page = None
        # Manual mode (CDP)
        self.ws_connection = None
        self.tab_id = None
        # Shared
        self.console_buffer = []
    
    async def check_servers(self) -> Dict[str, Any]:
        """Check if both frontend and backend servers are running"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "frontend": {"status": "unknown", "response_time": 0},
            "backend": {"status": "unknown", "response_time": 0}
        }
        
        async with aiohttp.ClientSession() as session:
            # Check frontend
            try:
                start_time = time.time()
                async with session.get(self.frontend_url, timeout=5) as response:
                    status["frontend"]["status"] = "running" if response.status == 200 else f"error_{response.status}"
                    status["frontend"]["response_time"] = round((time.time() - start_time) * 1000, 2)
            except Exception as e:
                status["frontend"]["status"] = f"error: {str(e)}"
            
            # Check backend
            try:
                start_time = time.time()
                async with session.get(f"{self.backend_url}/docs", timeout=5) as response:
                    status["backend"]["status"] = "running" if response.status == 200 else f"error_{response.status}"
                    status["backend"]["response_time"] = round((time.time() - start_time) * 1000, 2)
            except Exception as e:
                status["backend"]["status"] = f"error: {str(e)}"
        
        return status
    
    async def test_auth_endpoints(self) -> Dict[str, Any]:
        """Test authentication endpoints"""
        auth_status = {
            "timestamp": datetime.now().isoformat(),
            "login_endpoint": {"status": "unknown", "response_time": 0},
            "me_endpoint": {"status": "unknown", "response_time": 0}
        }
        
        async with aiohttp.ClientSession() as session:
            # Test login endpoint availability
            try:
                start_time = time.time()
                login_data = {
                    "email": "demo_hnw@sigmasight.com",
                    "password": "demo12345"
                }
                async with session.post(
                    f"{self.backend_url}/api/v1/auth/login",
                    json=login_data,
                    timeout=10
                ) as response:
                    auth_status["login_endpoint"]["status"] = response.status
                    auth_status["login_endpoint"]["response_time"] = round((time.time() - start_time) * 1000, 2)
                    
                    if response.status == 200:
                        result = await response.json()
                        auth_status["login_endpoint"]["has_token"] = "access_token" in result
                        
                        # Test authenticated endpoint
                        if "access_token" in result:
                            headers = {"Authorization": f"Bearer {result['access_token']}"}
                            start_time = time.time()
                            async with session.get(
                                f"{self.backend_url}/api/v1/auth/me",
                                headers=headers,
                                timeout=5
                            ) as me_response:
                                auth_status["me_endpoint"]["status"] = me_response.status
                                auth_status["me_endpoint"]["response_time"] = round((time.time() - start_time) * 1000, 2)
            except Exception as e:
                auth_status["login_endpoint"]["error"] = str(e)
        
        return auth_status
    
    async def setup_cdp_monitoring(self) -> bool:
        """Setup CDP connection to manually running Chrome browser"""
        if not WEBSOCKETS_AVAILABLE:
            print("❌ websockets library required for CDP mode")
            return False
            
        try:
            # Get available tabs from CDP
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.cdp_url}/json") as response:
                    if response.status != 200:
                        print(f"❌ CDP not accessible at {self.cdp_url}")
                        print("   Start Chrome with: --remote-debugging-port=9222")
                        return False
                        
                    tabs = await response.json()
                    
            # Find active tab (or use first available)
            active_tab = None
            for tab in tabs:
                if tab.get('type') == 'page' and not tab.get('url', '').startswith('devtools://'):
                    active_tab = tab
                    break
                    
            if not active_tab:
                print("❌ No active browser tabs found")
                return False
                
            self.tab_id = active_tab['id']
            ws_url = active_tab['webSocketDebuggerUrl']
            
            # Connect to WebSocket
            self.ws_connection = await websockets.connect(ws_url)
            
            # Enable Console domain
            await self.ws_connection.send(json.dumps({
                "id": 1,
                "method": "Console.enable",
                "params": {}
            }))
            
            # Enable Runtime domain for console API calls
            await self.ws_connection.send(json.dumps({
                "id": 2, 
                "method": "Runtime.enable",
                "params": {}
            }))
            
            print(f"🔗 Connected to Chrome tab: {active_tab.get('title', 'Unknown')[:50]}...")
            print(f"   URL: {active_tab.get('url', 'Unknown')[:80]}...")
            
            # Start listening for console messages
            asyncio.create_task(self.listen_cdp_messages())
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup CDP monitoring: {e}")
            return False
    
    async def listen_cdp_messages(self):
        """Listen for CDP console messages via WebSocket"""
        try:
            async for message in self.ws_connection:
                data = json.loads(message)
                
                # Handle console API calls (console.log, etc.)
                if data.get('method') == 'Runtime.consoleAPICalled':
                    params = data.get('params', {})
                    self.handle_cdp_console_message(params)
                    
                # Handle JavaScript exceptions
                elif data.get('method') == 'Runtime.exceptionThrown':
                    params = data.get('params', {})
                    self.handle_cdp_exception(params)
                    
        except websockets.exceptions.ConnectionClosed:
            print("⚠️  CDP connection closed")
        except Exception as e:
            print(f"❌ CDP message listening error: {e}")
    
    def handle_cdp_console_message(self, params: Dict[str, Any]):
        """Process console API calls from CDP"""
        level = params.get('type', 'log')
        args = params.get('args', [])
        
        # Construct message from arguments
        message_parts = []
        for arg in args:
            if arg.get('type') == 'string':
                message_parts.append(arg.get('value', ''))
            else:
                # For objects, numbers, etc.
                message_parts.append(str(arg.get('value', arg.get('description', 'Object'))))
        
        message = ' '.join(message_parts)
        
        # Get stack trace for location
        stack_trace = params.get('stackTrace', {})
        call_frames = stack_trace.get('callFrames', [])
        location = ''
        if call_frames:
            frame = call_frames[0]
            url = frame.get('url', '')
            line = frame.get('lineNumber', 0)
            location = f"{url.split('/')[-1]}:{line}" if url else ''
        
        self.console_buffer.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "location": location,
            "source": "cdp_manual"
        })
    
    def handle_cdp_exception(self, params: Dict[str, Any]):
        """Process JavaScript exceptions from CDP"""
        exception_details = params.get('exceptionDetails', {})
        text = exception_details.get('text', 'JavaScript Error')
        
        # Get location from exception
        location = ''
        if 'url' in exception_details:
            url = exception_details['url']
            line = exception_details.get('lineNumber', 0)
            location = f"{url.split('/')[-1]}:{line}" if url else ''
        
        self.console_buffer.append({
            "timestamp": datetime.now().isoformat(),
            "level": "error",
            "message": text,
            "location": location,
            "source": "cdp_manual"
        })
    
    async def setup_browser_monitoring(self) -> bool:
        """Setup Playwright browser for console monitoring"""
        if not PLAYWRIGHT_AVAILABLE:
            return False
            
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,  # Run in background
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            self.page = await context.new_page()
            
            # Listen for console messages
            def handle_console_msg(msg):
                self.console_buffer.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": msg.type,
                    "message": msg.text,
                    "location": msg.location.get('url', '') if msg.location else '',
                    "source": "browser"
                })
            
            # Listen for page errors
            def handle_page_error(error):
                self.console_buffer.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "error",
                    "message": str(error),
                    "location": "page",
                    "source": "browser"
                })
            
            self.page.on("console", handle_console_msg)
            self.page.on("pageerror", handle_page_error)
            
            print("🌐 Browser console monitoring enabled")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup browser monitoring: {e}")
            return False
    
    async def navigate_to_app(self):
        """Navigate browser to application and perform basic setup"""
        if not self.page:
            return
            
        try:
            # Navigate to the application
            await self.page.goto(self.frontend_url, wait_until='networkidle')
            await asyncio.sleep(2)  # Allow React app to initialize
            
            print("🔗 Browser navigated to application")
            
        except Exception as e:
            self.console_buffer.append({
                "timestamp": datetime.now().isoformat(),
                "level": "error",
                "message": f"Navigation failed: {str(e)}",
                "location": self.frontend_url,
                "source": "browser"
            })
    
    def categorize_console_message(self, msg: Dict[str, Any]) -> str:
        """Categorize console messages for better analysis"""
        message = msg.get("message", "").lower()
        location = msg.get("location", "").lower()
        
        if any(term in message for term in ["chat", "sse", "stream", "websocket"]):
            return "chat"
        elif any(term in message for term in ["auth", "login", "token", "jwt"]):
            return "auth"
        elif any(term in message for term in ["fetch", "xhr", "api", "network"]):
            return "network"
        elif any(term in message for term in ["react", "component", "render"]):
            return "ui"
        elif msg.get("level") == "error":
            return "error"
        else:
            return "general"
    
    def process_console_buffer(self):
        """Process accumulated console messages and add to monitoring data"""
        if not self.console_buffer:
            return
            
        # Add categories and move to monitoring data
        for msg in self.console_buffer:
            msg["category"] = self.categorize_console_message(msg)
            self.monitoring_data["console_logs"].append(msg)
        
        # Keep only last 200 console messages to prevent bloat
        if len(self.monitoring_data["console_logs"]) > 200:
            self.monitoring_data["console_logs"] = self.monitoring_data["console_logs"][-200:]
        
        self.console_buffer.clear()
    
    async def cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.mode == "automated":
                if self.page:
                    await self.page.close()
                if self.browser:
                    await self.browser.close()
            elif self.mode == "manual":
                if self.ws_connection:
                    await self.ws_connection.close()
        except Exception as e:
            print(f"⚠️  Browser cleanup warning: {e}")
    
    async def test_chat_endpoints(self, auth_token: str = None) -> Dict[str, Any]:
        """Test chat endpoints availability"""
        chat_status = {
            "timestamp": datetime.now().isoformat(),
            "send_endpoint": {"status": "unknown"},
            "stream_endpoint": {"status": "unknown"}
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            # Test chat send endpoint
            try:
                chat_data = {
                    "text": "Hello, this is a monitoring test",
                    "conversation_id": None
                }
                async with session.post(
                    f"{self.backend_url}/api/v1/chat/send",
                    json=chat_data,
                    headers=headers,
                    timeout=5
                ) as response:
                    chat_status["send_endpoint"]["status"] = response.status
                    if response.status != 200:
                        chat_status["send_endpoint"]["error"] = await response.text()
            except Exception as e:
                chat_status["send_endpoint"]["error"] = str(e)
        
        return chat_status
    
    def print_status(self, status_data: Dict[str, Any]):
        """Print formatted status update"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] 📊 SigmaSight Monitoring Status")
        print("=" * 50)
        
        if "frontend" in status_data:
            frontend = status_data["frontend"]
            print(f"Frontend (localhost:3005): {frontend['status']} ({frontend.get('response_time', 0)}ms)")
        
        if "backend" in status_data:
            backend = status_data["backend"]
            print(f"Backend (localhost:8000):  {backend['status']} ({backend.get('response_time', 0)}ms)")
        
        if "login_endpoint" in status_data:
            login = status_data["login_endpoint"]
            print(f"Auth Login:              {login['status']} ({login.get('response_time', 0)}ms)")
            if "has_token" in login:
                print(f"Token Generated:         {'✅ Yes' if login['has_token'] else '❌ No'}")
        
        if "me_endpoint" in status_data:
            me = status_data["me_endpoint"]
            print(f"Auth Me:                 {me['status']} ({me.get('response_time', 0)}ms)")
        
        if "send_endpoint" in status_data:
            send = status_data["send_endpoint"]
            print(f"Chat Send:               {send['status']}")
            
        # Show console log summary
        console_count = len(self.console_buffer)
        if console_count > 0:
            error_count = len([msg for msg in self.console_buffer if msg.get('level') == 'error'])
            warn_count = len([msg for msg in self.console_buffer if msg.get('level') == 'warn'])
            print(f"Console Logs:            {console_count} new ({error_count} errors, {warn_count} warnings)")
    
    def save_monitoring_data(self):
        """Save monitoring data to file"""
        with open('/Users/elliottng/CascadeProjects/SigmaSight-BE/backend/chat_monitoring_report.json', 'w') as f:
            json.dump(self.monitoring_data, f, indent=2)
    
    async def run_continuous_monitoring(self):
        """Run continuous monitoring session with console capture"""
        print("🚀 Starting Enhanced SigmaSight Chat Monitoring")
        print("=" * 55)
        print("📊 Monitoring Capabilities:")
        print("  - Server availability (frontend & backend)")
        print("  - Authentication endpoints")
        print("  - Chat endpoint availability")
        print("  - Browser console logs & errors")
        print("  - Response times and error rates")
        print()
        print(f"🔧 Mode: {self.mode.upper()}")
        
        # Setup console monitoring based on mode
        browser_enabled = False
        if self.mode == "automated":
            browser_enabled = await self.setup_browser_monitoring()
            if browser_enabled:
                print("🌐 Automated browser console monitoring: ENABLED (Playwright)")
                await self.navigate_to_app()
            else:
                print("🌐 Automated browser console monitoring: DISABLED (Playwright not available)")
        elif self.mode == "manual":
            browser_enabled = await self.setup_cdp_monitoring()
            if browser_enabled:
                print("🌐 Manual browser console monitoring: ENABLED (CDP connection)")
            else:
                print("🌐 Manual browser console monitoring: DISABLED (CDP not available)")
        
        print()
        if self.mode == "manual":
            print("🎯 Manual testing workflow:")
            print("  1. Start Chrome with: --remote-debugging-port=9222")
            print("  2. Navigate to: http://localhost:3005")
            print("  3. Login with: demo_hnw@sigmasight.com / demo12345")
            print("  4. Test chat - all console logs will be captured automatically")
        else:
            print("🎯 Automated monitoring active:")
            print("  - Background browser monitors basic functionality")
            print("  - For chat testing, use manual mode for better coverage")
        
        print()
        print("📈 Live monitoring updates every 30 seconds...")
        print("--- MONITORING STARTED ---")
        
        cycle_count = 0
        auth_token = None
        
        try:
            while True:
                try:
                    cycle_count += 1
                    
                    # Process any accumulated console logs
                    if browser_enabled:
                        self.process_console_buffer()
                    
                    # Check server status
                    server_status = await self.check_servers()
                    self.monitoring_data["status_checks"].append(server_status)
                    
                    # Test authentication every 5th cycle or if we don't have a token
                    if cycle_count % 5 == 1 or not auth_token:
                        auth_status = await self.test_auth_endpoints()
                        self.monitoring_data["status_checks"].append(auth_status)
                        
                        # Extract token for chat testing
                        if auth_status.get("login_endpoint", {}).get("has_token"):
                            # We'd need to make another call to get the actual token
                            # For now, just mark that auth is working
                            pass
                        
                        self.print_status({**server_status, **auth_status})
                    else:
                        self.print_status(server_status)
                    
                    # Save data
                    self.save_monitoring_data()
                    
                    # Keep only last 100 entries to prevent memory bloat
                    if len(self.monitoring_data["status_checks"]) > 100:
                        self.monitoring_data["status_checks"] = self.monitoring_data["status_checks"][-100:]
                    
                    await asyncio.sleep(30)  # Wait 30 seconds
                    
                except KeyboardInterrupt:
                    print("\n🛑 Monitoring stopped by user")
                    break
                except Exception as e:
                    error_data = {
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e)
                    }
                    self.monitoring_data["errors"].append(error_data)
                    print(f"❌ Monitoring error: {e}")
                    await asyncio.sleep(5)
                    
        finally:
            # Cleanup browser resources
            if browser_enabled:
                print("🧹 Cleaning up browser resources...")
                await self.cleanup_browser()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SigmaSight Enhanced Chat Monitoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python simple_monitor.py --mode automated    # Headless browser monitoring (default)
  python simple_monitor.py --mode manual       # Connect to your manual Chrome browser

Manual Mode Setup:
  1. Start Chrome with remote debugging:
     # macOS: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
     # Linux: google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug  
     # Windows: "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome-debug
  2. Navigate to your testing page
  3. Run monitoring script - it will capture your console logs in real-time
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["automated", "manual"], 
        default="automated",
        help="Monitoring mode: 'automated' for headless browser, 'manual' for CDP connection"
    )
    
    args = parser.parse_args()
    
    monitor = SigmaSightMonitor(mode=args.mode)
    asyncio.run(monitor.run_continuous_monitoring())