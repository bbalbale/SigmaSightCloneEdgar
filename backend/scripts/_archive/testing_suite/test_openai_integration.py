#!/usr/bin/env python
"""
Test OpenAI integration with the chat endpoints.
"""
import asyncio
import json
import aiohttp
import sys
from typing import AsyncGenerator


async def login_and_get_token() -> str:
    """Login with demo user and get JWT token"""
    async with aiohttp.ClientSession() as session:
        login_data = {
            "email": "demo_growth@sigmasight.com",
            "password": "demo12345"
        }
        async with session.post(
            "http://localhost:8000/api/v1/auth/login",
            json=login_data
        ) as resp:
            if resp.status != 200:
                print(f"Login failed: {await resp.text()}")
                sys.exit(1)
            data = await resp.json()
            return data["access_token"]


async def create_conversation(token: str, mode: str = "green") -> str:
    """Create a new conversation"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {token}"}
        conv_data = {"mode": mode}
        async with session.post(
            "http://localhost:8000/api/v1/chat/conversations",
            headers=headers,
            json=conv_data
        ) as resp:
            if resp.status != 201:
                print(f"Create conversation failed: {await resp.text()}")
                sys.exit(1)
            data = await resp.json()
            return data["conversation_id"]


async def stream_message(token: str, conversation_id: str, message: str) -> None:
    """Send a message and stream the response"""
    print(f"\n🤖 Sending: {message}")
    print("-" * 50)
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream"
        }
        message_data = {
            "conversation_id": conversation_id,
            "text": message
        }
        
        async with session.post(
            "http://localhost:8000/api/v1/chat/send",
            headers=headers,
            json=message_data
        ) as resp:
            if resp.status != 200:
                print(f"Send message failed: {await resp.text()}")
                return
            
            # Parse SSE stream
            async for line in resp.content:
                line_text = line.decode('utf-8').strip()
                if line_text.startswith('event:'):
                    event_type = line_text.split(':', 1)[1].strip()
                elif line_text.startswith('data:'):
                    data_text = line_text.split(':', 1)[1].strip()
                    if data_text:
                        try:
                            data = json.loads(data_text)
                            
                            # Handle different event types
                            if event_type == 'start':
                                print(f"📍 Mode: {data['mode']}, Model: {data['model']}")
                            elif event_type == 'message':
                                print(data['delta'], end='', flush=True)
                            elif event_type == 'tool_started':
                                print(f"\n🔧 Tool: {data['tool_name']}({json.dumps(data['arguments'])})")
                            elif event_type == 'tool_finished':
                                print(f"   ✅ Result: {data.get('result', 'success')}")
                            elif event_type == 'done':
                                print(f"\n✨ Done - Tool calls: {data['tool_calls_count']}, Latency: {data.get('latency_ms', 0)}ms")
                            elif event_type == 'error':
                                print(f"\n❌ Error: {data['message']}")
                        except json.JSONDecodeError:
                            pass


async def main():
    """Run the test"""
    print("🚀 Testing OpenAI Integration")
    print("=" * 50)
    
    # Get auth token
    print("1. Logging in...")
    token = await login_and_get_token()
    print("   ✅ Authenticated")
    
    # Create conversation
    print("2. Creating conversation...")
    conversation_id = await create_conversation(token, "green")
    print(f"   ✅ Conversation ID: {conversation_id}")
    
    # Test messages
    test_messages = [
        "Hello! Can you introduce yourself?",
        "What portfolio analysis capabilities do you have?",
        # Note: Tool calls won't work without actual portfolio context
        # "Can you show me the current market quotes for AAPL and MSFT?"
    ]
    
    for msg in test_messages:
        await stream_message(token, conversation_id, msg)
        await asyncio.sleep(2)  # Pause between messages
    
    print("\n" + "=" * 50)
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())