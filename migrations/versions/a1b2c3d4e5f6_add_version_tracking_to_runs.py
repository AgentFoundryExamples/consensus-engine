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
"""add_version_tracking_to_runs

Revision ID: a1b2c3d4e5f6
Revises: 77563d1e925b
Create Date: 2026-01-08 08:07:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '77563d1e925b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add schema_version and prompt_set_version columns to runs and step_metadata to step_progress."""
    
    # Add version tracking columns to runs table (nullable for backward compatibility)
    op.add_column('runs', sa.Column('schema_version', sa.Text(), nullable=True))
    op.add_column('runs', sa.Column('prompt_set_version', sa.Text(), nullable=True))
    
    # Add step-level metadata to step_progress table
    op.add_column('step_progress', sa.Column('step_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove version tracking columns from runs and step_metadata from step_progress."""
    
    # Drop columns from step_progress table
    op.drop_column('step_progress', 'step_metadata')
    
    # Drop columns from runs table
    op.drop_column('runs', 'prompt_set_version')
    op.drop_column('runs', 'schema_version')
