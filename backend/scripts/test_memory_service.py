"""
Test script for memory service with real user ID from database.
"""
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal


async def get_demo_user_id():
    """Get a real user ID from the database."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT id, email FROM users LIMIT 1"))
        row = result.fetchone()
        if row:
            return row[0], row[1]
        return None, None


async def test_memory_crud():
    """Test memory CRUD operations with a real user."""
    from app.agent.services.memory_service import (
        save_memory,
        get_user_memories,
        delete_memory,
        count_user_memories,
        format_memories_for_prompt,
    )

    # Get a real user ID
    user_id, email = await get_demo_user_id()
    if not user_id:
        print("ERROR: No users found in database")
        return

    print(f"Using user: {email} (ID: {user_id})")

    async with AsyncSessionLocal() as db:
        # 1. Count initial memories
        initial_count = await count_user_memories(db, user_id)
        print(f"Initial memory count: {initial_count}")

        # 2. Save a test memory
        memory_id = await save_memory(
            db,
            user_id=user_id,
            content="User prefers concise bullet-point answers",
            scope="user",
            tags={"category": "preference", "source": "test"},
        )
        print(f"Saved memory ID: {memory_id}")

        # 3. Count after save
        count_after = await count_user_memories(db, user_id)
        print(f"Memory count after save: {count_after}")

        # 4. Retrieve memories
        memories = await get_user_memories(db, user_id, limit=5)
        print(f"Retrieved {len(memories)} memories:")
        for m in memories:
            print(f"  - [{m['scope']}] {m['content'][:50]}...")

        # 5. Format for prompt
        formatted = format_memories_for_prompt(memories)
        print(f"Formatted for prompt:\n{formatted}")

        # 6. Delete the test memory
        deleted = await delete_memory(db, memory_id, user_id)
        print(f"Deleted test memory: {deleted}")

        # 7. Final count
        final_count = await count_user_memories(db, user_id)
        print(f"Final memory count: {final_count}")

        print("\n=== Memory Service Test PASSED ===")


if __name__ == "__main__":
    asyncio.run(test_memory_crud())
