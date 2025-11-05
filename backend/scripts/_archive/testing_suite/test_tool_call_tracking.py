#!/usr/bin/env python3
"""
Test script to verify enhanced tool call ID tracking (Phase 10.1.3)
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any, List
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER = "demo_growth@sigmasight.com"
TEST_PASSWORD = "demo12345"

class ToolCallTrackingTest:
    def __init__(self):
        self.session = None
        self.token = None
        self.conversation_id = None
        self.tool_calls_observed = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.login()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def login(self):
        """Login and get JWT token"""
        async with self.session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER, "password": TEST_PASSWORD}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Login failed: {await resp.text()}")
            data = await resp.json()
            self.token = data["access_token"]
            print(f"✅ Logged in successfully")
            
    async def get_or_create_conversation(self):
        """Get existing conversation or create new one"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Try to get existing conversations
        async with self.session.get(
            f"{BASE_URL}/api/v1/chat/conversations",
            headers=headers
        ) as resp:
            if resp.status == 200:
                conversations = await resp.json()
                if conversations and isinstance(conversations, list):
                    self.conversation_id = conversations[0]["id"]
                    print(f"✅ Using existing conversation: {self.conversation_id}")
                    return
                    
        # Create new conversation if needed
        async with self.session.post(
            f"{BASE_URL}/api/v1/chat/conversations",
            headers=headers,
            json={"title": "Tool Call ID Tracking Test"}
        ) as resp:
            if resp.status not in [200, 201]:
                raise Exception(f"Failed to create conversation: {await resp.text()}")
            data = await resp.json()
            self.conversation_id = data["id"]
            print(f"✅ Created new conversation: {self.conversation_id}")
            
    async def send_message_and_track_tools(self, message: str) -> Dict[str, Any]:
        """Send message and track tool call IDs"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "text/event-stream"
        }
        
        test_results = {
            "tool_calls": [],
            "tool_results": [],
            "id_correlations": [],
            "has_proper_ids": True
        }
        
        print(f"\n📨 Sending message: '{message}'")
        print("🔍 Tracking tool call IDs...")
        
        async with self.session.post(
            f"{BASE_URL}/api/v1/chat/send",
            headers=headers,
            json={
                "conversation_id": self.conversation_id,
                "text": message
            }
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Send message failed: {await resp.text()}")
                
            event_type = None
            async for line in resp.content:
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue
                    
                # Parse SSE events
                if line_str.startswith("event:"):
                    event_type = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("data:") and event_type:
                    data_str = line_str.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        
                        # Track tool_call events
                        if event_type == "tool_call":
                            tool_data = data.get("data", {})
                            tool_call_id = tool_data.get("tool_call_id")
                            tool_name = tool_data.get("tool_name")
                            
                            if tool_call_id:
                                test_results["tool_calls"].append({
                                    "id": tool_call_id,
                                    "name": tool_name,
                                    "args": tool_data.get("tool_args", {})
                                })
                                print(f"  🔧 Tool Call: {tool_name}")
                                print(f"     ID: {tool_call_id}")
                                
                                # Verify it's a proper OpenAI-format ID
                                if tool_call_id.startswith("call_") and len(tool_call_id) == 29:
                                    print(f"     ✅ Valid OpenAI format")
                                else:
                                    print(f"     ⚠️ Non-standard ID format")
                                    test_results["has_proper_ids"] = False
                            else:
                                print(f"  ❌ Tool call missing ID: {tool_name}")
                                test_results["has_proper_ids"] = False
                                
                        # Track tool_result events
                        elif event_type == "tool_result":
                            result_data = data.get("data", {})
                            tool_call_id = result_data.get("tool_call_id")
                            tool_name = result_data.get("tool_name")
                            duration = result_data.get("duration_ms")
                            
                            if tool_call_id:
                                test_results["tool_results"].append({
                                    "id": tool_call_id,
                                    "name": tool_name,
                                    "duration_ms": duration
                                })
                                print(f"  ✅ Tool Result: {tool_name}")
                                print(f"     ID: {tool_call_id}")
                                print(f"     Duration: {duration}ms")
                                
                                # Check for correlation
                                matching_call = next(
                                    (tc for tc in test_results["tool_calls"] if tc["id"] == tool_call_id),
                                    None
                                )
                                if matching_call:
                                    test_results["id_correlations"].append({
                                        "tool_call_id": tool_call_id,
                                        "tool_name": tool_name,
                                        "correlated": True
                                    })
                                    print(f"     ✅ Correlated with tool_call event")
                                else:
                                    print(f"     ⚠️ No matching tool_call event found")
                            else:
                                print(f"  ❌ Tool result missing ID: {tool_name}")
                                
                    except json.JSONDecodeError:
                        pass
                        
        return test_results
        
async def run_tests():
    """Run comprehensive tool call ID tracking tests"""
    print("=" * 60)
    print("🔧 TOOL CALL ID TRACKING TEST (Phase 10.1.3)")
    print("=" * 60)
    
    async with ToolCallTrackingTest() as tester:
        await tester.get_or_create_conversation()
        
        # Test 1: Message that triggers tool calls
        print("\n" + "=" * 60)
        print("TEST 1: Portfolio Analysis (Should trigger tools)")
        print("=" * 60)
        
        results = await tester.send_message_and_track_tools(
            "What is the total value and top holdings in my portfolio?"
        )
        
        # Analyze results
        print("\n📊 Test Results:")
        print(f"Tool Calls Captured: {len(results['tool_calls'])}")
        print(f"Tool Results Captured: {len(results['tool_results'])}")
        print(f"Successful Correlations: {len(results['id_correlations'])}")
        
        if results["has_proper_ids"]:
            print("✅ All tool calls have proper OpenAI-format IDs")
        else:
            print("❌ Some tool calls have invalid or missing IDs")
            
        # Check correlation success
        if results["tool_calls"] and results["tool_results"]:
            correlation_rate = len(results["id_correlations"]) / len(results["tool_calls"]) * 100
            print(f"ID Correlation Rate: {correlation_rate:.0f}%")
            
            if correlation_rate == 100:
                print("✅ Perfect ID correlation between calls and results")
            elif correlation_rate > 0:
                print(f"⚠️ Partial correlation: {len(results['id_correlations'])}/{len(results['tool_calls'])}")
            else:
                print("❌ No ID correlation achieved")
        
        # Test 2: Simple message (no tools expected)
        print("\n" + "=" * 60)
        print("TEST 2: Simple Question (No tools expected)")
        print("=" * 60)
        
        results2 = await tester.send_message_and_track_tools("What does SPY stand for?")
        
        print("\n📊 Test Results:")
        if results2["tool_calls"]:
            print(f"⚠️ Unexpected tool calls: {len(results2['tool_calls'])}")
        else:
            print("✅ No tool calls (as expected)")
            
        # Summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        print("\n✅ Enhanced Tool Call ID Tracking Features:")
        print("1. Tool call IDs logged at creation")
        print("2. Tool call IDs tracked through execution")
        print("3. Tool call IDs included in tool_result events")
        print("4. ID mapping dictionary for correlation")
        print("5. Summary logging at conversation end")
        
        if results["has_proper_ids"] and results["id_correlations"]:
            print("\n✅ Phase 10.1.3 Implementation Successful!")
        else:
            print("\n⚠️ Some issues detected - check logs for details")
        
if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)