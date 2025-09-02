#!/usr/bin/env python3
"""
SigmaSight Chat Interface Monitor
Automated browser testing with real-time console monitoring
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext, ConsoleMessage

class ChatInterfaceMonitor:
    def __init__(self):
        self.console_logs = []
        self.screenshots_dir = Path("monitoring_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        
    async def setup_console_monitoring(self, page: Page):
        """Set up real-time console monitoring"""
        def on_console(msg: ConsoleMessage):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_entry = {
                "timestamp": timestamp,
                "type": msg.type,
                "text": msg.text,
                "location": f"{msg.location.get('url', 'unknown')}:{msg.location.get('lineNumber', 0)}"
            }
            self.console_logs.append(log_entry)
            
            # Color-coded console output
            color_map = {
                "error": "\033[91m",     # Red
                "warning": "\033[93m",   # Yellow
                "log": "\033[94m",       # Blue
                "info": "\033[96m",      # Cyan
                "debug": "\033[90m"      # Gray
            }
            reset_color = "\033[0m"
            color = color_map.get(msg.type, "")
            
            print(f"{color}[{timestamp}] {msg.type.upper()}: {msg.text}{reset_color}")
            if msg.location.get('url') and 'localhost:3005' in msg.location.get('url', ''):
                print(f"  Location: {log_entry['location']}")
        
        page.on("console", on_console)
        
        # Also monitor page errors
        page.on("pageerror", lambda error: print(f"\033[91m[PAGE ERROR]: {error}\033[0m"))
        
    async def take_screenshot(self, page: Page, name: str):
        """Take and save screenshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.screenshots_dir / f"{timestamp}_{name}.png"
        await page.screenshot(path=str(filename), full_page=True)
        print(f"📸 Screenshot saved: {filename}")
        return filename
        
    async def wait_for_element_safe(self, page: Page, selector: str, timeout: int = 10000):
        """Wait for element with error handling"""
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            print(f"⚠️  Element not found: {selector} - {e}")
            return False
            
    async def login_flow(self, page: Page):
        """Execute login flow with monitoring"""
        print("\n🔐 Starting login flow...")
        
        # Navigate to login page
        await page.goto("http://localhost:3005/login")
        await self.take_screenshot(page, "01_login_page")
        
        # Wait for login form
        if not await self.wait_for_element_safe(page, 'input[type="email"]'):
            print("❌ Login form not found")
            return False
            
        # Fill credentials
        await page.fill('input[type="email"]', 'demo_hnw@sigmasight.com')
        await page.fill('input[type="password"]', 'demo12345')
        await self.take_screenshot(page, "02_credentials_filled")
        
        # Submit login
        await page.click('button[type="submit"]')
        print("🔄 Login submitted, waiting for redirect...")
        
        # Wait for successful login (dashboard or portfolio page)
        await page.wait_for_timeout(3000)  # Allow time for redirect
        await self.take_screenshot(page, "03_post_login")
        
        current_url = page.url
        print(f"📍 Current URL after login: {current_url}")
        
        if "login" in current_url:
            print("❌ Login failed - still on login page")
            return False
            
        print("✅ Login successful!")
        return True
        
    async def navigate_to_portfolio(self, page: Page):
        """Navigate to portfolio page"""
        print("\n📊 Navigating to portfolio...")
        
        # Check if already on portfolio page
        if "portfolio" in page.url:
            print("✅ Already on portfolio page")
            return True
            
        # Look for portfolio navigation
        portfolio_selectors = [
            'a[href*="portfolio"]',
            'button:has-text("Portfolio")',
            'nav a:has-text("Portfolio")',
            '.portfolio-link'
        ]
        
        for selector in portfolio_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.click()
                    await page.wait_for_timeout(2000)
                    await self.take_screenshot(page, "04_portfolio_page")
                    print("✅ Navigated to portfolio page")
                    return True
            except:
                continue
                
        # Try direct navigation to portfolio
        portfolio_id = "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e"
        portfolio_url = f"http://localhost:3005/portfolio/{portfolio_id}"
        await page.goto(portfolio_url)
        await page.wait_for_timeout(2000)
        await self.take_screenshot(page, "05_direct_portfolio_nav")
        print(f"📍 Direct navigation to: {portfolio_url}")
        return True
        
    async def locate_chat_interface(self, page: Page):
        """Locate and test the chat interface"""
        print("\n💬 Locating chat interface...")
        
        # Common chat interface selectors
        chat_selectors = [
            '.chat-container',
            '.chat-interface',
            '.chat-widget',
            'div[data-testid*="chat"]',
            'button:has-text("Chat")',
            '.ai-chat',
            '#chat',
            'textarea[placeholder*="chat" i]',
            'input[placeholder*="message" i]'
        ]
        
        found_elements = []
        
        for selector in chat_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    found_elements.append((selector, len(elements)))
                    print(f"✅ Found {len(elements)} element(s) with selector: {selector}")
            except Exception as e:
                continue
                
        if not found_elements:
            print("❌ No chat interface elements found with common selectors")
            print("🔍 Searching for any interactive elements...")
            
            # Search for any text input or button that might be chat-related
            all_inputs = await page.query_selector_all('input, textarea, button')
            print(f"📝 Found {len(all_inputs)} interactive elements total")
            
            # Check for any element with chat-related text
            chat_related = []
            for element in all_inputs:
                try:
                    text_content = await element.text_content() or ""
                    placeholder = await element.get_attribute("placeholder") or ""
                    aria_label = await element.get_attribute("aria-label") or ""
                    
                    combined_text = f"{text_content} {placeholder} {aria_label}".lower()
                    if any(keyword in combined_text for keyword in ['chat', 'message', 'ask', 'ai', 'assistant']):
                        chat_related.append((element, combined_text))
                except:
                    continue
                    
            if chat_related:
                print(f"🎯 Found {len(chat_related)} potentially chat-related elements")
                for i, (element, text) in enumerate(chat_related):
                    print(f"  {i+1}. {text.strip()}")
            else:
                print("❌ No chat-related elements found")
                
        await self.take_screenshot(page, "06_chat_interface_search")
        return found_elements
        
    async def test_chat_interactions(self, page: Page, chat_elements):
        """Test chat interface interactions"""
        print("\n🧪 Testing chat interactions...")
        
        if not chat_elements:
            print("❌ No chat elements to test")
            return
            
        # Try to interact with found elements
        for selector, count in chat_elements:
            print(f"\n🔬 Testing selector: {selector}")
            
            try:
                # Get first element matching selector
                element = await page.query_selector(selector)
                if not element:
                    continue
                    
                # Check if it's an input element
                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                
                if tag_name in ['input', 'textarea']:
                    # Try typing in input
                    test_message = "Hello, this is a test message from automated monitoring"
                    await element.fill(test_message)
                    print(f"✅ Successfully typed test message in {tag_name}")
                    
                    await self.take_screenshot(page, f"07_chat_input_{tag_name}")
                    
                    # Look for submit button nearby
                    submit_selectors = [
                        'button[type="submit"]',
                        'button:has-text("Send")',
                        'button:has-text("Submit")',
                        '.send-button',
                        '.chat-send'
                    ]
                    
                    for submit_selector in submit_selectors:
                        try:
                            submit_btn = await page.query_selector(submit_selector)
                            if submit_btn:
                                print(f"🔄 Found submit button: {submit_selector}")
                                await submit_btn.click()
                                await page.wait_for_timeout(2000)
                                await self.take_screenshot(page, "08_chat_message_sent")
                                print("✅ Chat message submitted")
                                break
                        except:
                            continue
                            
                elif tag_name == 'button':
                    # Try clicking button
                    button_text = await element.text_content()
                    print(f"🖱️  Clicking button: {button_text}")
                    await element.click()
                    await page.wait_for_timeout(2000)
                    await self.take_screenshot(page, "09_chat_button_clicked")
                    
            except Exception as e:
                print(f"❌ Error testing {selector}: {e}")
                
    async def monitor_console_during_interaction(self, page: Page, duration: int = 30):
        """Monitor console logs during interaction period"""
        print(f"\n👀 Monitoring console logs for {duration} seconds...")
        print("📝 Console output will appear in real-time above")
        print("💡 Try manually interacting with the chat interface if needed")
        
        start_time = datetime.now()
        await asyncio.sleep(duration)
        
        print(f"\n📊 Console monitoring complete. Captured {len(self.console_logs)} log entries")
        return self.console_logs
        
    async def save_monitoring_report(self):
        """Save detailed monitoring report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "console_logs": self.console_logs,
            "screenshots_taken": len(list(self.screenshots_dir.glob("*.png"))),
            "summary": {
                "total_logs": len(self.console_logs),
                "errors": len([log for log in self.console_logs if log["type"] == "error"]),
                "warnings": len([log for log in self.console_logs if log["type"] == "warning"]),
                "info_logs": len([log for log in self.console_logs if log["type"] in ["log", "info"]])
            }
        }
        
        report_file = Path("chat_monitoring_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"📄 Monitoring report saved: {report_file}")
        return report
        
    async def run_monitoring_session(self):
        """Main monitoring session"""
        print("🚀 Starting SigmaSight Chat Interface Monitoring")
        print("=" * 60)
        
        async with async_playwright() as p:
            # Launch browser with dev tools for debugging
            browser = await p.chromium.launch(
                headless=False,  # Keep browser visible
                devtools=False,  # Don't auto-open devtools
                args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
            )
            
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            
            page = await context.new_page()
            
            # Set up console monitoring
            await self.setup_console_monitoring(page)
            
            try:
                # Execute monitoring workflow
                if await self.login_flow(page):
                    await self.navigate_to_portfolio(page)
                    chat_elements = await self.locate_chat_interface(page)
                    await self.test_chat_interactions(page, chat_elements)
                    
                    # Keep monitoring for additional time
                    await self.monitor_console_during_interaction(page, 30)
                else:
                    print("❌ Login failed, cannot proceed with chat testing")
                    
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                await self.take_screenshot(page, "error_state")
                
            finally:
                # Save report and cleanup
                await self.save_monitoring_report()
                print("\n🏁 Monitoring session complete")
                print(f"📁 Screenshots saved in: {self.screenshots_dir}")
                
                # Keep browser open for manual inspection
                print("\n⏳ Browser will remain open for 60 seconds for manual inspection...")
                await asyncio.sleep(60)
                
                await browser.close()

async def main():
    """Entry point"""
    monitor = ChatInterfaceMonitor()
    await monitor.run_monitoring_session()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Monitoring interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)