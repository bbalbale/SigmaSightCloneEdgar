#!/usr/bin/env python
"""
Test OpenAI integration without streaming (for unverified organizations).
"""
import asyncio
import json
import sys
from openai import AsyncOpenAI
from app.config import settings
from app.agent.prompts.prompt_manager import PromptManager


async def test_openai_direct():
    """Test OpenAI directly without streaming"""
    print("🚀 Testing OpenAI Direct Integration (Non-Streaming)")
    print("=" * 50)
    
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    prompt_manager = PromptManager()
    
    # Get system prompt
    system_prompt = prompt_manager.get_system_prompt("green")
    
    print(f"Model: {settings.MODEL_DEFAULT}")
    print(f"Mode: green")
    print("-" * 50)
    
    # Test messages
    test_messages = [
        "Hello! Can you introduce yourself?",
        "What are the key factors I should consider when analyzing a portfolio?"
    ]
    
    for user_msg in test_messages:
        print(f"\n🤖 User: {user_msg}")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
        
        try:
            # Non-streaming call
            response = await client.chat.completions.create(
                model=settings.MODEL_DEFAULT,
                messages=messages,
                max_completion_tokens=500,
                stream=False  # Disable streaming
            )
            
            assistant_msg = response.choices[0].message.content
            print(f"💬 Assistant: {assistant_msg[:200]}...")  # First 200 chars
            print(f"   (Total: {len(assistant_msg)} chars)")
            
            # Print usage
            if response.usage:
                print(f"   Tokens: {response.usage.total_tokens} total")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_openai_direct())