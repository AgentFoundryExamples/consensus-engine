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
"""add_versioned_run_tables

Revision ID: 453a79c83bde
Revises: 9a73090ad792
Create Date: 2026-01-07 21:58:25.102436

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '453a79c83bde'
down_revision: str | None = '9a73090ad792'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create versioned run tables with JSONB columns and indexes."""
    # Create runs table
    op.create_table(
        'runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('input_idea', sa.Text(), nullable=False),
        sa.Column('extra_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('run_type', sa.String(length=20), nullable=False),
        sa.Column('parent_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model', sa.Text(), nullable=False),
        sa.Column('temperature', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('parameters_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('overall_weighted_confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('decision_label', sa.Text(), nullable=True),
        sa.CheckConstraint(
            'temperature >= 0.0 AND temperature <= 2.0',
            name='ck_runs_temperature_range'
        ),
        sa.CheckConstraint(
            'overall_weighted_confidence >= 0.0 AND overall_weighted_confidence <= 1.0',
            name='ck_runs_confidence_range'
        ),
        sa.ForeignKeyConstraint(['parent_run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_runs_created_at', 'runs', ['created_at'], unique=False)
    op.create_index('ix_runs_parent_run_id', 'runs', ['parent_run_id'], unique=False)
    op.create_index('ix_runs_status', 'runs', ['status'], unique=False)

    # Create proposal_versions table
    op.create_table(
        'proposal_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'expanded_proposal_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column('proposal_diff_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('persona_template_version', sa.Text(), nullable=False),
        sa.Column('edit_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )

    # Create persona_reviews table
    op.create_table(
        'persona_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('persona_id', sa.String(length=100), nullable=False),
        sa.Column('persona_name', sa.Text(), nullable=False),
        sa.Column('review_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('blocking_issues_present', sa.Boolean(), nullable=False),
        sa.Column('security_concerns_present', sa.Boolean(), nullable=False),
        sa.Column(
            'prompt_parameters_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            'confidence_score >= 0.0 AND confidence_score <= 1.0',
            name='ck_persona_reviews_confidence_range'
        ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'persona_id', name='uq_persona_reviews_run_persona')
    )

    # Create decisions table
    op.create_table(
        'decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('decision_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('overall_weighted_confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('decision_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            'overall_weighted_confidence >= 0.0 AND overall_weighted_confidence <= 1.0',
            name='ck_decisions_confidence_range'
        ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )
    op.create_index(
        'ix_decisions_overall_weighted_confidence',
        'decisions',
        ['overall_weighted_confidence'],
        unique=False
    )


def downgrade() -> None:
    """Drop all versioned run tables."""
    op.drop_index('ix_decisions_overall_weighted_confidence', table_name='decisions')
    op.drop_table('decisions')
    op.drop_table('persona_reviews')
    op.drop_table('proposal_versions')
    op.drop_index('ix_runs_status', table_name='runs')
    op.drop_index('ix_runs_parent_run_id', table_name='runs')
    op.drop_index('ix_runs_created_at', table_name='runs')
    op.drop_table('runs')
