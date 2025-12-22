"""
Run the fix migration for missing AI learning tables on Railway.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"


async def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = await conn.execute(text(
        f"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        f"WHERE table_schema = 'public' AND table_name = '{table_name}')"
    ))
    return result.scalar()


async def pgvector_available(conn) -> bool:
    """Check if pgvector extension is available."""
    try:
        result = await conn.execute(text(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        ))
        return result.scalar()
    except Exception:
        return False


async def run_migration():
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        has_pgvector = await pgvector_available(conn)
        print(f"pgvector available: {has_pgvector}")

        # Create ai_kb_documents table if it doesn't exist
        if not await table_exists(conn, 'ai_kb_documents'):
            print("Creating ai_kb_documents table...")
            await conn.execute(text("""
                CREATE TABLE ai_kb_documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    scope VARCHAR(100) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                )
            """))

            if has_pgvector:
                await conn.execute(text("ALTER TABLE ai_kb_documents ADD COLUMN embedding vector(1536)"))
                await conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_ai_kb_documents_embedding "
                    "ON ai_kb_documents USING hnsw (embedding vector_cosine_ops) "
                    "WITH (m = 16, ef_construction = 64)"
                ))

            await conn.execute(text("CREATE INDEX ix_ai_kb_documents_scope ON ai_kb_documents(scope)"))
            print("Created ai_kb_documents table")
        else:
            print("ai_kb_documents table already exists")

        # Create ai_memories table if it doesn't exist
        if not await table_exists(conn, 'ai_memories'):
            print("Creating ai_memories table...")
            await conn.execute(text("""
                CREATE TABLE ai_memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id UUID,
                    scope VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                )
            """))
            await conn.execute(text("CREATE INDEX ix_ai_memories_scope ON ai_memories(scope)"))
            await conn.execute(text("CREATE INDEX ix_ai_memories_user_id ON ai_memories(user_id)"))
            await conn.execute(text("CREATE INDEX ix_ai_memories_tenant_id ON ai_memories(tenant_id)"))
            print("Created ai_memories table")
        else:
            print("ai_memories table already exists")

        # Create ai_feedback table if it doesn't exist
        if not await table_exists(conn, 'ai_feedback'):
            print("Creating ai_feedback table...")
            await conn.execute(text("""
                CREATE TABLE ai_feedback (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    message_id UUID NOT NULL,
                    rating VARCHAR(10) NOT NULL,
                    edited_text TEXT,
                    comment TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                )
            """))
            await conn.execute(text("CREATE INDEX ix_ai_feedback_message_id ON ai_feedback(message_id)"))
            await conn.execute(text("CREATE INDEX ix_ai_feedback_rating ON ai_feedback(rating)"))
            print("Created ai_feedback table")
        else:
            print("ai_feedback table already exists")

        # Update alembic_version to include the new migration
        await conn.execute(text(
            "UPDATE alembic_version SET version_num = 'o1p2q3r4s5t6'"
        ))
        print("Updated alembic_version to o1p2q3r4s5t6")

        print("\nMigration complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())
