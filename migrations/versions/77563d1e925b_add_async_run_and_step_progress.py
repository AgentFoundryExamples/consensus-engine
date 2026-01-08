# Copyright 2025 John Brosnihan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""add_async_run_and_step_progress

Revision ID: 77563d1e925b
Revises: 1be7b272f496
Create Date: 2026-01-08 03:24:30.045725

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '77563d1e925b'
down_revision: str | None = '1be7b272f496'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add async-ready fields to runs table and create step_progress table."""
    
    # Add new status value 'queued' to existing status enum
    # Note: PostgreSQL doesn't allow direct modification of enums, so we need to handle carefully
    # For string-based enum storage (native_enum=False), we just need to ensure the column accepts it
    
    # Add new columns to runs table
    op.add_column('runs', sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('runs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('runs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('runs', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('runs', sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'))
    
    # Create indexes for new timestamp columns
    op.create_index('ix_runs_queued_at', 'runs', ['queued_at'], unique=False)
    op.create_index('ix_runs_started_at', 'runs', ['started_at'], unique=False)
    op.create_index('ix_runs_completed_at', 'runs', ['completed_at'], unique=False)
    op.create_index('ix_runs_priority', 'runs', ['priority'], unique=False)
    
    # Add check constraint for retry_count
    op.create_check_constraint(
        'ck_runs_retry_count_non_negative',
        'runs',
        'retry_count >= 0'
    )
    
    # Create step_progress table
    op.create_table(
        'step_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(length=100), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.CheckConstraint(
            'step_order >= 0',
            name='ck_step_progress_order_non_negative'
        ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'step_name', name='uq_step_progress_run_step')
    )
    
    # Create indexes for step_progress table
    op.create_index('ix_step_progress_run_id', 'step_progress', ['run_id'], unique=False)
    op.create_index('ix_step_progress_status', 'step_progress', ['status'], unique=False)


def downgrade() -> None:
    """Remove async-ready fields from runs table and drop step_progress table."""
    
    # Drop step_progress table and its indexes
    op.drop_index('ix_step_progress_status', table_name='step_progress')
    op.drop_index('ix_step_progress_run_id', table_name='step_progress')
    op.drop_table('step_progress')
    
    # Drop check constraint
    op.drop_constraint('ck_runs_retry_count_non_negative', 'runs', type_='check')
    
    # Drop indexes from runs table
    op.drop_index('ix_runs_priority', table_name='runs')
    op.drop_index('ix_runs_completed_at', table_name='runs')
    op.drop_index('ix_runs_started_at', table_name='runs')
    op.drop_index('ix_runs_queued_at', table_name='runs')
    
    # Drop columns from runs table
    op.drop_column('runs', 'priority')
    op.drop_column('runs', 'retry_count')
    op.drop_column('runs', 'completed_at')
    op.drop_column('runs', 'started_at')
    op.drop_column('runs', 'queued_at')

