#!/usr/bin/env python3
"""
Manual test script for ID refactoring implementation
Tests the complete flow with backend-first ID generation
"""

import asyncio
import json
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("🧪 MANUAL ID SYSTEM TEST")
        print("=" * 60)
        
        # 1. Login
        print("\n1️⃣ Logging in...")
        login_resp = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code}")
            return
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✅ Login successful")
        
        # 2. Create conversation
        print("\n2️⃣ Creating conversation...")
        conv_resp = await client.post(
            f"{BASE_URL}/api/v1/chat/conversations",
            headers=headers,
            json={"mode": "green"}
        )
        if conv_resp.status_code not in [200, 201]:
            print(f"❌ Failed to create conversation: {conv_resp.status_code}")
            return
        
        conv_data = conv_resp.json()
        conv_id = conv_data["id"]
        print(f"✅ Conversation created with ID: {conv_id}")
        
        # 3. Send message and stream response
        print("\n3️⃣ Sending test message...")
        print("📤 Message: 'What are my top 3 holdings?'")
        
        message_created_found = False
        user_msg_id = None
        assistant_msg_id = None
        tool_calls_found = []
        tokens_received = 0
        
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/v1/chat/send",
            headers={**headers, "Accept": "text/event-stream"},
            json={
                "conversation_id": conv_id,
                "text": "What are my top 3 holdings?"
            }
        ) as response:
            if response.status_code != 200:
                print(f"❌ Streaming failed: {response.status_code}")
                return
            
            print("\n📡 SSE Stream Events:")
            print("-" * 40)
            
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    
                    if event_type == "message_created":
                        message_created_found = True
                        print(f"✅ Event: message_created")
                    elif event_type == "token":
                        tokens_received += 1
                        if tokens_received == 1:
                            print(f"✅ Event: token (streaming started)")
                    elif event_type == "tool_call":
                        print(f"✅ Event: tool_call")
                    elif event_type == "done":
                        print(f"✅ Event: done")
                
                elif line.startswith("data:") and line.strip() != "data:":
                    try:
                        data = json.loads(line[5:].strip())
                        
                        # Check for message_created data
                        if message_created_found and not user_msg_id:
                            user_msg_id = data.get("user_message_id")
                            assistant_msg_id = data.get("assistant_message_id")
                            if user_msg_id and assistant_msg_id:
                                print(f"\n📋 Message IDs Received:")
                                print(f"   User Message ID: {user_msg_id}")
                                print(f"   Assistant Message ID: {assistant_msg_id}")
                                message_created_found = False
                        
                        # Check for tool calls
                        if "tool_call_id" in data.get("data", {}):
                            tool_id = data["data"]["tool_call_id"]
                            tool_name = data["data"].get("tool_name", "unknown")
                            if tool_id and tool_id not in tool_calls_found:
                                tool_calls_found.append(tool_id)
                                print(f"   Tool Call: {tool_name} (ID: {tool_id})")
                            elif not tool_id:
                                print(f"   ⚠️  Tool Call: {tool_name} (ID: None - BUG!)")
                    except json.JSONDecodeError:
                        pass
        
        # 4. Validate results
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        
        results = {
            "conversation_id_valid": len(conv_id) == 36,  # UUID format
            "user_message_id_valid": user_msg_id and len(user_msg_id) == 36,
            "assistant_message_id_valid": assistant_msg_id and len(assistant_msg_id) == 36,
            "message_ids_different": user_msg_id != assistant_msg_id,
            "tokens_received": tokens_received > 0,
            "tool_calls_valid": len(tool_calls_found) == 0 or all(tc.startswith("call_") and len(tc) == 29 for tc in tool_calls_found)
        }
        
        all_passed = all(results.values())
        
        for test, passed in results.items():
            status = "✅" if passed else "❌"
            print(f"{status} {test}: {passed}")
        
        if tool_calls_found:
            print(f"\n🔧 Tool Calls Found: {len(tool_calls_found)}")
            for tc in tool_calls_found:
                print(f"   - {tc}")
        
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ ALL TESTS PASSED - ID System Working Correctly!")
        else:
            print("❌ Some tests failed - check implementation")
        print("=" * 60)

if __name__ == "__main__":
    print("Starting manual test...")
    print("Make sure backend is running on localhost:8000")
    print("")
    asyncio.run(main())