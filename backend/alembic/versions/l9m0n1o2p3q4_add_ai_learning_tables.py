"""add_ai_learning_tables

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2025-12-11 10:00:00.000000

Phase 3.1: AI Learning Tables for RAG and Feedback
- Enables pgvector extension for embedding storage
- Creates ai_kb_documents table for RAG knowledge base
- Creates ai_memories table for persistent rules/preferences
- Creates ai_feedback table for user feedback on AI responses
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'l9m0n1o2p3q4'
down_revision = 'k8l9m0n1o2p3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension for embedding storage
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create ai_kb_documents table for RAG knowledge base
    op.create_table(
        'ai_kb_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('scope', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Add embedding column using raw SQL (SQLAlchemy doesn't natively support pgvector)
    op.execute("ALTER TABLE ai_kb_documents ADD COLUMN embedding vector(1536)")

    # Create indexes for ai_kb_documents
    op.create_index('ix_ai_kb_documents_scope', 'ai_kb_documents', ['scope'])

    # Create IVFFlat index for vector similarity search
    # Note: lists=100 is a good default for datasets < 100k rows
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_kb_documents_embedding "
        "ON ai_kb_documents USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # Create ai_memories table for persistent rules/preferences
    op.create_table(
        'ai_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scope', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for ai_memories
    op.create_index('ix_ai_memories_scope', 'ai_memories', ['scope'])
    op.create_index('ix_ai_memories_user_id', 'ai_memories', ['user_id'])
    op.create_index('ix_ai_memories_tenant_id', 'ai_memories', ['tenant_id'])

    # Create ai_feedback table for user feedback on AI responses
    op.create_table(
        'ai_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.String(10), nullable=False),
        sa.Column('edited_text', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for ai_feedback
    op.create_index('ix_ai_feedback_message_id', 'ai_feedback', ['message_id'])
    op.create_index('ix_ai_feedback_rating', 'ai_feedback', ['rating'])


def downgrade() -> None:
    # Drop ai_feedback table and indexes
    op.drop_index('ix_ai_feedback_rating', table_name='ai_feedback')
    op.drop_index('ix_ai_feedback_message_id', table_name='ai_feedback')
    op.drop_table('ai_feedback')

    # Drop ai_memories table and indexes
    op.drop_index('ix_ai_memories_tenant_id', table_name='ai_memories')
    op.drop_index('ix_ai_memories_user_id', table_name='ai_memories')
    op.drop_index('ix_ai_memories_scope', table_name='ai_memories')
    op.drop_table('ai_memories')

    # Drop ai_kb_documents table and indexes
    op.execute("DROP INDEX IF EXISTS ix_ai_kb_documents_embedding")
    op.drop_index('ix_ai_kb_documents_scope', table_name='ai_kb_documents')
    op.drop_table('ai_kb_documents')

    # Note: We do NOT drop the vector extension in downgrade()
    # because other tables may depend on it
