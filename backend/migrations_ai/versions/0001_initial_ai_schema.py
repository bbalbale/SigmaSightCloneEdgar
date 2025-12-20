"""Initial AI database schema with pgvector

Revision ID: 0001
Revises:
Create Date: 2025-12-19

Creates the AI database tables:
- ai_kb_documents: RAG knowledge base with HNSW vector index
- ai_memories: User/tenant preferences and rules
- ai_feedback: User feedback on AI responses
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI tables and vector index."""

    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create ai_kb_documents table
    op.create_table(
        'ai_kb_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('scope', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('embedding', sa.Column('embedding', sa.Text).type, nullable=True),  # Placeholder
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Add vector column using raw SQL (SQLAlchemy doesn't fully support pgvector types in DDL)
    op.execute("ALTER TABLE ai_kb_documents DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE ai_kb_documents ADD COLUMN embedding vector(1536)")

    # Create indexes for ai_kb_documents
    op.create_index('ix_ai_kb_documents_scope', 'ai_kb_documents', ['scope'])
    op.create_index('ix_ai_kb_documents_created', 'ai_kb_documents', ['created_at'])

    # Create HNSW index for vector similarity search
    op.execute("""
        CREATE INDEX ix_ai_kb_documents_embedding_hnsw
        ON ai_kb_documents
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Create ai_memories table
    op.create_table(
        'ai_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scope', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for ai_memories
    op.create_index('ix_ai_memories_scope', 'ai_memories', ['scope'])
    op.create_index('ix_ai_memories_user_id', 'ai_memories', ['user_id'])
    op.create_index('ix_ai_memories_tenant_id', 'ai_memories', ['tenant_id'])

    # Create ai_feedback table
    op.create_table(
        'ai_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.String(10), nullable=False),
        sa.Column('edited_text', sa.Text, nullable=True),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for ai_feedback
    op.create_index('ix_ai_feedback_message_id', 'ai_feedback', ['message_id'])
    op.create_index('ix_ai_feedback_rating', 'ai_feedback', ['rating'])


def downgrade() -> None:
    """Drop AI tables."""
    op.drop_table('ai_feedback')
    op.drop_table('ai_memories')
    op.drop_table('ai_kb_documents')
