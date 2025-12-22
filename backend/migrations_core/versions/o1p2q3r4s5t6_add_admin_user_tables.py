"""add_admin_user_tables

Revision ID: o1p2q3r4s5t6
Revises: n0o1p2q3r4s5
Create Date: 2025-12-22 14:00:00.000000

Admin Dashboard Phase 1: Admin Authentication Tables

Creates two tables for admin authentication system:
1. admin_users - Separate admin user accounts (not linked to regular users)
2. admin_sessions - Token invalidation and session tracking

This enables:
- Completely separate admin authentication from regular users
- Session tracking for token invalidation on logout
- IP/User-Agent logging for security audit
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'o1p2q3r4s5t6'
down_revision = 'n0o1p2q3r4s5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='admin'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Index for admin_users email lookup
    op.create_index('ix_admin_users_email', 'admin_users', ['email'])

    print("Created table: admin_users")

    # 2. Create admin_sessions table
    op.create_table(
        'admin_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('admin_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Indexes for admin_sessions
    op.create_index('ix_admin_sessions_admin_user_id', 'admin_sessions', ['admin_user_id'])
    op.create_index('ix_admin_sessions_expires_at', 'admin_sessions', ['expires_at'])
    op.create_index('ix_admin_sessions_token_hash', 'admin_sessions', ['token_hash'])

    print("Created table: admin_sessions")
    print("\nAdmin authentication tables created successfully!")


def downgrade() -> None:
    # Drop tables in reverse order (due to foreign key dependencies)
    op.drop_table('admin_sessions')
    print("Dropped table: admin_sessions")

    op.drop_table('admin_users')
    print("Dropped table: admin_users")

    print("\nAdmin authentication tables dropped successfully!")
