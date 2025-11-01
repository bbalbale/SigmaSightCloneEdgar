"""
Test Claude streaming chat endpoint

Quick test to verify /api/v1/insights/chat works
"""
import httpx
import asyncio


async def test_chat_endpoint():
    """Test the Claude chat endpoint with SSE streaming"""

    # Login to get token
    async with httpx.AsyncClient() as client:
        login_response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={
                "email": "demo_hnw@sigmasight.com",
                "password": "demo12345"
            }
        )
        token = login_response.json()["access_token"]
        print(f"[OK] Got auth token: {token[:20]}...")

        # Test chat endpoint
        print("\n[TEST] Sending message to Claude chat...")
        print("Message: 'What are the main risks in my portfolio?'")
        print("\nSSE Stream:\n" + "="*80)

        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/insights/chat",
            json={"message": "What are the main risks in my portfolio?"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=120.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(": ")[1]
                    print(f"\n[{event_type.upper()}]", end=" ")
                elif line.startswith("data:"):
                    data = line[6:]  # Remove "data: " prefix
                    print(data)

        print("\n" + "="*80)
        print("[OK] Chat endpoint test complete!")


if __name__ == "__main__":
    asyncio.run(test_chat_endpoint())
