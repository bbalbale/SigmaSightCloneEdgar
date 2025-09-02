#!/usr/bin/env python3
"""
Quick status checker for monitoring session
"""
import json
import os
from pathlib import Path

def check_monitoring_status():
    """Check current status of monitoring session"""
    print("🔍 Checking monitoring session status...")
    
    # Check for screenshots
    screenshots_dir = Path("monitoring_screenshots")
    if screenshots_dir.exists():
        screenshots = list(screenshots_dir.glob("*.png"))
        print(f"📸 Screenshots found: {len(screenshots)}")
        for screenshot in sorted(screenshots):
            print(f"  - {screenshot.name}")
    else:
        print("📸 No screenshots directory found yet")
        
    # Check for report file
    report_file = Path("chat_monitoring_report.json")
    if report_file.exists():
        try:
            with open(report_file, 'r') as f:
                report = json.load(f)
            print(f"📄 Monitoring report found:")
            print(f"  - Total logs: {report['summary']['total_logs']}")
            print(f"  - Errors: {report['summary']['errors']}")
            print(f"  - Warnings: {report['summary']['warnings']}")
            print(f"  - Info logs: {report['summary']['info_logs']}")
            print(f"  - Screenshots: {report['summary']['screenshots_taken']}")
        except Exception as e:
            print(f"❌ Error reading report: {e}")
    else:
        print("📄 No monitoring report found yet")
        
    # Check if browser processes are running
    try:
        import psutil
        browser_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower():
                    browser_processes.append(proc.info)
            except:
                pass
        print(f"🌐 Browser processes: {len(browser_processes)}")
    except ImportError:
        print("🌐 Browser process check requires psutil")

if __name__ == "__main__":
    check_monitoring_status()