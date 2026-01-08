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
"""add_analytics_index_for_decision_and_date

Revision ID: 1be7b272f496
Revises: 453a79c83bde
Create Date: 2026-01-08 00:20:36.732568

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1be7b272f496'
down_revision: str | None = '453a79c83bde'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite index on (decision_label, created_at) for analytics queries.

    This index accelerates queries filtering by decision outcome and date range,
    which are common in analytics dashboards and reporting tools.

    Index Design:
    - Column order (decision_label, created_at) is optimized for queries that filter
      by decision label first, then by date range. Example:
      SELECT * FROM runs WHERE decision_label = 'approve' AND created_at >= '2024-01-01'

    - If your application primarily filters by date range first and then by decision,
      consider creating an additional index with reversed column order:
      CREATE INDEX ix_runs_created_at_decision_label ON runs(created_at, decision_label)

    - The existing ix_runs_created_at index on created_at alone remains useful for
      queries that only filter by date without decision filtering.

    Performance Notes:
    - For small result sets, the index is highly effective
    - For queries returning large result sets, ensure proper LIMIT/OFFSET pagination
    - Monitor query performance and adjust index strategy based on actual usage patterns
    """
    # Create composite index for decision_label + created_at
    # This supports queries like: WHERE decision_label = 'approve' AND created_at >= '2024-01-01'
    op.create_index(
        'ix_runs_decision_label_created_at',
        'runs',
        ['decision_label', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    """Remove the analytics index."""
    op.drop_index('ix_runs_decision_label_created_at', table_name='runs')
