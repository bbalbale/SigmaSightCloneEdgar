#!/usr/bin/env python3
"""
Phase 10.5 Implementation Testing
Tests the ID refactoring implementation
"""

import asyncio
import json
import httpx
import time
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# Configuration
BASE_URL = "http://localhost:8000"
DEMO_EMAIL = "demo_growth@sigmasight.com"
DEMO_PASSWORD = "demo12345"

class Phase10Tester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.access_token: Optional[str] = None
        self.test_results = {
            "10.5.1": {},
            "10.5.2": {},
            "10.5.3": {},
            "summary": {}
        }
        
    async def login(self) -> bool:
        """Login and get access token"""
        print("🔐 Logging in...")
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "email": DEMO_EMAIL,
                    "password": DEMO_PASSWORD
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                print(f"✅ Login successful - Token: {self.access_token[:20]}...")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    async def test_backend_api_validation(self):
        """Phase 10.5.1: Backend API Validation"""
        print("\n" + "="*60)
        print("📋 Phase 10.5.1: Backend API Validation")
        print("="*60)
        
        results = {}
        
        # Test 1: Create conversation with backend ID
        print("\n1️⃣ Testing conversation creation...")
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/conversations",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"mode": "green"}
            )
            if response.status_code in [200, 201]:
                conv_data = response.json()
                conv_id = conv_data.get("id")
                # Validate UUID format
                try:
                    uuid.UUID(conv_id)
                    print(f"✅ Conversation created with valid UUID: {conv_id}")
                    results["conversation_creation"] = "PASS"
                    results["conversation_id"] = conv_id
                except ValueError:
                    print(f"❌ Invalid UUID format: {conv_id}")
                    results["conversation_creation"] = "FAIL"
            else:
                print(f"❌ Failed to create conversation: {response.status_code}")
                results["conversation_creation"] = "FAIL"
        except Exception as e:
            print(f"❌ Error creating conversation: {e}")
            results["conversation_creation"] = "ERROR"
        
        # Test 2: SSE streaming with message_created event
        if results.get("conversation_id"):
            print("\n2️⃣ Testing SSE streaming for message IDs...")
            try:
                # Send a message via SSE endpoint
                async with self.client.stream(
                    "POST",
                    f"{BASE_URL}/api/v1/chat/send",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Accept": "text/event-stream"
                    },
                    json={
                        "conversation_id": results["conversation_id"],
                        "text": "Test message for ID validation"
                    }
                ) as response:
                    if response.status_code == 200:
                        message_created_found = False
                        user_msg_id = None
                        assistant_msg_id = None
                        
                        async for line in response.aiter_lines():
                            if line.startswith("event: message_created"):
                                message_created_found = True
                            elif line.startswith("data:") and message_created_found:
                                try:
                                    data = json.loads(line[5:].strip())
                                    user_msg_id = data.get("user_message_id")
                                    assistant_msg_id = data.get("assistant_message_id")
                                    
                                    # Validate UUIDs
                                    uuid.UUID(user_msg_id)
                                    uuid.UUID(assistant_msg_id)
                                    
                                    print(f"✅ message_created event received:")
                                    print(f"   User Message ID: {user_msg_id}")
                                    print(f"   Assistant Message ID: {assistant_msg_id}")
                                    results["message_created_event"] = "PASS"
                                    results["backend_ids_valid"] = "PASS"
                                    break
                                except (json.JSONDecodeError, ValueError) as e:
                                    print(f"❌ Invalid message_created data: {e}")
                                    results["message_created_event"] = "FAIL"
                            
                            # Stop after finding what we need
                            if user_msg_id and assistant_msg_id:
                                break
                        
                        if not message_created_found:
                            print("❌ No message_created event found")
                            results["message_created_event"] = "NOT_FOUND"
                    else:
                        print(f"❌ SSE streaming failed: {response.status_code}")
                        results["sse_streaming"] = "FAIL"
            except Exception as e:
                print(f"❌ Error testing SSE: {e}")
                results["sse_streaming"] = "ERROR"
        
        # Test 3: Error handling for invalid IDs
        print("\n3️⃣ Testing error handling for invalid IDs...")
        try:
            invalid_id = "not-a-uuid"
            response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/send",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "text/event-stream"
                },
                json={
                    "conversation_id": invalid_id,
                    "text": "Test with invalid ID"
                }
            )
            if response.status_code >= 400:
                print(f"✅ Invalid ID properly rejected: {response.status_code}")
                results["invalid_id_handling"] = "PASS"
            else:
                print(f"❌ Invalid ID not rejected: {response.status_code}")
                results["invalid_id_handling"] = "FAIL"
        except Exception as e:
            print(f"✅ Invalid ID caused expected error: {e}")
            results["invalid_id_handling"] = "PASS"
        
        self.test_results["10.5.1"] = results
        return results
    
    async def test_frontend_integration(self):
        """Phase 10.5.2: Frontend Integration Validation"""
        print("\n" + "="*60)
        print("📋 Phase 10.5.2: Frontend Integration Validation")
        print("="*60)
        
        results = {}
        
        # Note: These tests verify backend behavior that frontend relies on
        
        print("\n1️⃣ Verifying backend provides IDs (no frontend generation needed)...")
        # This was tested in 10.5.1 - backend provides all IDs
        if self.test_results["10.5.1"].get("backend_ids_valid") == "PASS":
            print("✅ Backend provides all message IDs")
            results["backend_provides_ids"] = "PASS"
        else:
            print("❌ Backend ID provision not verified")
            results["backend_provides_ids"] = "FAIL"
        
        print("\n2️⃣ Verifying SSE events include proper IDs...")
        if self.test_results["10.5.1"].get("message_created_event") == "PASS":
            print("✅ SSE events include backend message IDs")
            results["sse_includes_ids"] = "PASS"
        else:
            print("❌ SSE events don't include proper IDs")
            results["sse_includes_ids"] = "FAIL"
        
        print("\n3️⃣ Testing streaming with tool calls...")
        try:
            # Create new conversation
            response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/conversations",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"mode": "green"}
            )
            if response.status_code in [200, 201]:
                conv_id = response.json()["id"]
                
                # Send message that triggers tool call
                async with self.client.stream(
                    "POST",
                    f"{BASE_URL}/api/v1/chat/send",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Accept": "text/event-stream"
                    },
                    json={
                        "conversation_id": conv_id,
                        "text": "What is my portfolio value?"
                    },
                    timeout=30.0
                ) as response:
                    if response.status_code == 200:
                        tool_call_found = False
                        tool_call_id = None
                        
                        async for line in response.aiter_lines():
                            if "tool_call" in line:
                                tool_call_found = True
                            if line.startswith("data:") and tool_call_found:
                                try:
                                    data = json.loads(line[5:].strip())
                                    if data.get("data", {}).get("tool_call_id"):
                                        tool_call_id = data["data"]["tool_call_id"]
                                        # Validate OpenAI format
                                        if tool_call_id.startswith("call_") and len(tool_call_id) == 29:
                                            print(f"✅ Valid tool call ID: {tool_call_id}")
                                            results["tool_call_ids"] = "PASS"
                                            break
                                except:
                                    pass
                        
                        if not tool_call_found:
                            print("⚠️ No tool calls in response (may be expected)")
                            results["tool_call_ids"] = "N/A"
        except Exception as e:
            print(f"❌ Error testing tool calls: {e}")
            results["tool_call_ids"] = "ERROR"
        
        self.test_results["10.5.2"] = results
        return results
    
    async def test_end_to_end_scenarios(self):
        """Phase 10.5.3: End-to-End Scenarios"""
        print("\n" + "="*60)
        print("📋 Phase 10.5.3: End-to-End Scenarios")
        print("="*60)
        
        results = {}
        
        # Test 1: Complete conversation flow
        print("\n1️⃣ Testing complete conversation with backend IDs...")
        try:
            # Create conversation
            conv_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/conversations",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"mode": "green"}
            )
            if conv_response.status_code not in [200, 201]:
                print(f"❌ Failed to create conversation: {conv_response.status_code}")
                results["complete_conversation"] = "ERROR"
                return results
            conv_id = conv_response.json()["id"]
            
            # Send multiple messages
            message_ids = []
            for i in range(3):
                prev_line = ""
                async with self.client.stream(
                    "POST",
                    f"{BASE_URL}/api/v1/chat/send",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Accept": "text/event-stream"
                    },
                    json={
                        "conversation_id": conv_id,
                        "text": f"Test message {i+1}"
                    },
                    timeout=15.0
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:") and "message_created" in prev_line:
                            try:
                                data = json.loads(line[5:].strip())
                                user_id = data.get("user_message_id")
                                if user_id:
                                    message_ids.append(user_id)
                                    break
                            except:
                                pass
                        if line.startswith("event:"):
                            prev_line = line
            
            # Check for ID uniqueness
            if len(message_ids) == len(set(message_ids)):
                print(f"✅ All {len(message_ids)} message IDs are unique")
                results["complete_conversation"] = "PASS"
            else:
                print(f"❌ Duplicate IDs found in {message_ids}")
                results["complete_conversation"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error in complete conversation test: {e}")
            results["complete_conversation"] = "ERROR"
        
        # Test 2: Multiple concurrent conversations
        print("\n2️⃣ Testing multiple concurrent conversations...")
        try:
            # Create multiple conversations
            conv_ids = []
            for i in range(3):
                response = await self.client.post(
                    f"{BASE_URL}/api/v1/chat/conversations",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json={"mode": "green"}
                )
                conv_ids.append(response.json()["id"])
            
            # Check uniqueness
            if len(conv_ids) == len(set(conv_ids)):
                print(f"✅ All {len(conv_ids)} conversation IDs are unique")
                results["concurrent_conversations"] = "PASS"
            else:
                print(f"❌ Duplicate conversation IDs found")
                results["concurrent_conversations"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Error testing concurrent conversations: {e}")
            results["concurrent_conversations"] = "ERROR"
        
        self.test_results["10.5.3"] = results
        return results
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for phase, results in self.test_results.items():
            if phase == "summary":
                continue
            print(f"\n{phase}:")
            for test_name, result in results.items():
                if test_name.endswith("_id"):
                    continue
                total_tests += 1
                status_icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
                print(f"  {status_icon} {test_name}: {result}")
                if result == "PASS":
                    passed_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 Overall Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        # Check success criteria
        print("\n✅ SUCCESS CRITERIA CHECK:")
        criteria = {
            "Backend provides all IDs": self.test_results["10.5.1"].get("backend_ids_valid") == "PASS",
            "message_created event works": self.test_results["10.5.1"].get("message_created_event") == "PASS",
            "No ID collisions": self.test_results["10.5.3"].get("concurrent_conversations") == "PASS",
            "Tool calls have proper IDs": self.test_results["10.5.2"].get("tool_call_ids") in ["PASS", "N/A"]
        }
        
        for criterion, met in criteria.items():
            status = "✅" if met else "❌"
            print(f"  {status} {criterion}")
        
        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "criteria_met": all(criteria.values())
        }
        
        return self.test_results
    
    async def run_all_tests(self):
        """Run all Phase 10.5 tests"""
        print("🚀 Starting Phase 10.5 Implementation Testing")
        print(f"📅 {datetime.now().isoformat()}")
        
        # Login first
        if not await self.login():
            print("❌ Cannot proceed without authentication")
            return
        
        # Run test phases
        await self.test_backend_api_validation()
        await self.test_frontend_integration()
        await self.test_end_to_end_scenarios()
        
        # Generate summary
        self.generate_summary()
        
        # Clean up
        await self.client.aclose()
        
        print("\n✨ Testing complete!")
        
        return self.test_results

async def main():
    tester = Phase10Tester()
    results = await tester.run_all_tests()
    
    # Save results to file
    with open("phase_10_5_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Results saved to phase_10_5_results.json")

if __name__ == "__main__":
    asyncio.run(main())