#!/usr/bin/env python
"""Test authentication dependency issue"""

import asyncio
from app.database import AsyncSessionLocal
from fastapi import HTTPException
import jwt
from uuid import UUID

async def test_auth_dependency():
    """Test the authentication dependency directly"""
    
    # The token we're using
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZGFjZmIwZi0yMTIzLTdhOTQtZGViYy0wZjk4MmI5MGQ4NDUiLCJlbWFpbCI6ImRlbW9faG53QHNpZ21hc2lnaHQuY29tIiwicG9ydGZvbGlvX2lkIjoiZTIzYWI5MzEtYTAzMy1lZGZlLWVkNGYtOWQwMjQ3NDc4MGI0IiwiZXhwIjoxNzU4MzE3ODI4fQ.4eVJgZTQqS9iuDK0cNdPY12Fojo4rHXa8KzN3fUtSjc"
    
    print("🔍 Testing JWT token decode...")
    try:
        # Decode token without verification first
        payload = jwt.decode(token, options={"verify_signature": False})
        print(f"   ✅ Token payload: {payload}")
        user_id = payload.get('sub')
        print(f"   📊 User ID from token: {user_id}")
    except Exception as e:
        print(f"   ❌ Token decode failed: {e}")
        return
        
    print("\n🔐 Testing auth dependency logic...")
    async with AsyncSessionLocal() as db:
        try:
            # Test the same logic as get_current_user
            from app.models.users import User
            from sqlalchemy import select
            
            user_uuid = UUID(user_id)
            result = await db.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()
            
            if not user:
                print("   ❌ User not found in database")
                return
            else:
                print(f"   ✅ User found: {user.email}")
                print(f"   📊 User active: {user.is_active}")
                
                if not user.is_active:
                    print("   ❌ User is not active")
                    return
                else:
                    print("   ✅ User is active")
                    
        except Exception as e:
            print(f"   ❌ Auth dependency failed: {e}")
            import traceback
            traceback.print_exc()
            return
            
    print("\n🎉 Authentication dependency should work!")
    print("The issue might be elsewhere in the API endpoint.")

if __name__ == "__main__":
    asyncio.run(test_auth_dependency())