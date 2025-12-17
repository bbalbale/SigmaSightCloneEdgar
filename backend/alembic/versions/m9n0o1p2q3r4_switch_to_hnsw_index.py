"""switch_to_hnsw_index

Revision ID: m9n0o1p2q3r4
Revises: l9m0n1o2p3q4
Create Date: 2025-12-16 21:15:00.000000

Switch ai_kb_documents embedding index from IVFFlat to HNSW for better recall.

HNSW (Hierarchical Navigable Small World) provides:
- Better recall accuracy (~99% vs ~95% for IVFFlat)
- Faster query performance
- No training data required
- Better for production workloads

This migration is safe - it only changes the index structure, not the data.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm9n0o1p2q3r4'
down_revision = 'l9m0n1o2p3q4'
branch_labels = None
depends_on = None


def _check_pgvector_available(connection) -> bool:
    """Check if pgvector extension is available on this PostgreSQL instance."""
    try:
        result = connection.execute(sa.text(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        ))
        return result.scalar()
    except Exception:
        return False


def _check_index_exists(connection, index_name: str) -> bool:
    """Check if an index exists."""
    try:
        result = connection.execute(sa.text(
            f"SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}')"
        ))
        return result.scalar()
    except Exception:
        return False


def upgrade() -> None:
    connection = op.get_bind()
    pgvector_available = _check_pgvector_available(connection)

    if not pgvector_available:
        print("pgvector not available - skipping HNSW index migration")
        return

    # Check if the IVFFlat index exists
    if _check_index_exists(connection, 'ix_ai_kb_documents_embedding'):
        # Drop the existing IVFFlat index
        op.execute("DROP INDEX IF EXISTS ix_ai_kb_documents_embedding")
        print("Dropped IVFFlat index: ix_ai_kb_documents_embedding")

    # Create new HNSW index
    # m=16: max connections per node (default 16, higher = better recall, more memory)
    # ef_construction=64: build-time search width (default 64, higher = better quality, slower build)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_kb_documents_embedding "
        "ON ai_kb_documents USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    print("Created HNSW index: ix_ai_kb_documents_embedding")


def downgrade() -> None:
    connection = op.get_bind()
    pgvector_available = _check_pgvector_available(connection)

    if not pgvector_available:
        print("pgvector not available - skipping HNSW index downgrade")
        return

    # Check if the HNSW index exists
    if _check_index_exists(connection, 'ix_ai_kb_documents_embedding'):
        # Drop the HNSW index
        op.execute("DROP INDEX IF EXISTS ix_ai_kb_documents_embedding")
        print("Dropped HNSW index: ix_ai_kb_documents_embedding")

    # Recreate the IVFFlat index (original)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_kb_documents_embedding "
        "ON ai_kb_documents USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
    print("Recreated IVFFlat index: ix_ai_kb_documents_embedding")
