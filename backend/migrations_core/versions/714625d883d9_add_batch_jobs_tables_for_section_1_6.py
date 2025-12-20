"""Add batch_jobs tables for Section 1.6

Revision ID: 714625d883d9
Revises: 2fc0b47dcbc9
Create Date: 2025-08-06 08:41:00.632695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '714625d883d9'
down_revision: Union[str, Sequence[str], None] = '2fc0b47dcbc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if tables already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create batch_jobs table for tracking job executions
    if 'batch_jobs' not in existing_tables:
        op.create_table(
            'batch_jobs',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('job_name', sa.String(100), nullable=False),
            sa.Column('job_type', sa.String(50), nullable=True),
            sa.Column('portfolio_id', sa.UUID(), nullable=True),
            sa.Column('status', sa.Enum(
                'queued', 'running', 'completed', 'failed', 
                'cancelled', 'completed_with_warnings',
                name='jobstatus'
            ), nullable=False),
            sa.Column('scheduled_at', sa.DateTime(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('execution_time', sa.Float(), nullable=True),
            sa.Column('parameters', sa.JSON(), nullable=True),
            sa.Column('result', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('warnings', sa.JSON(), nullable=True),
            sa.Column('records_processed', sa.Float(), nullable=True),
            sa.Column('records_failed', sa.Float(), nullable=True),
            sa.Column('triggered_by', sa.String(50), nullable=True),
            sa.Column('created_by', sa.String(100), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for common queries
        op.create_index('idx_batch_jobs_status', 'batch_jobs', ['status'])
        op.create_index('idx_batch_jobs_job_name', 'batch_jobs', ['job_name'])
        op.create_index('idx_batch_jobs_portfolio_id', 'batch_jobs', ['portfolio_id'])
        op.create_index('idx_batch_jobs_started_at', 'batch_jobs', ['started_at'])
        op.create_index('idx_batch_jobs_status_started', 'batch_jobs', ['status', 'started_at'])
    
    # Create batch_job_schedules table for storing job configurations
    if 'batch_job_schedules' not in existing_tables:
        op.create_table(
            'batch_job_schedules',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('schedule_name', sa.String(100), nullable=False),
            sa.Column('job_name', sa.String(100), nullable=False),
            sa.Column('cron_expression', sa.String(100), nullable=True),
            sa.Column('timezone', sa.String(50), nullable=True),
            sa.Column('enabled', sa.String(1), nullable=True),
            sa.Column('default_parameters', sa.JSON(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('schedule_name')
        )
    
    # Create APScheduler job store table (required by APScheduler)
    if 'apscheduler_jobs' not in existing_tables:
        op.create_table(
            'apscheduler_jobs',
            sa.Column('id', sa.String(191), nullable=False),
            sa.Column('next_run_time', sa.Float(), nullable=True),
            sa.Column('job_state', sa.LargeBinary(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        
        op.create_index('ix_apscheduler_jobs_next_run_time', 'apscheduler_jobs', ['next_run_time'])


def downgrade() -> None:
    """Downgrade schema."""
    # Check if tables exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop indexes and tables only if they exist
    if 'apscheduler_jobs' in existing_tables:
        # Check if index exists before dropping
        indexes = [idx['name'] for idx in inspector.get_indexes('apscheduler_jobs')]
        if 'ix_apscheduler_jobs_next_run_time' in indexes:
            op.drop_index('ix_apscheduler_jobs_next_run_time', 'apscheduler_jobs')
        op.drop_table('apscheduler_jobs')
    
    if 'batch_jobs' in existing_tables:
        # Drop batch_jobs indexes
        indexes = [idx['name'] for idx in inspector.get_indexes('batch_jobs')]
        for idx_name in ['idx_batch_jobs_status_started', 'idx_batch_jobs_started_at', 
                        'idx_batch_jobs_portfolio_id', 'idx_batch_jobs_job_name', 
                        'idx_batch_jobs_status']:
            if idx_name in indexes:
                op.drop_index(idx_name, 'batch_jobs')
        op.drop_table('batch_jobs')
    
    if 'batch_job_schedules' in existing_tables:
        op.drop_table('batch_job_schedules')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS jobstatus')
