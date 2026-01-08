"""add_analytics_index_for_decision_and_date

Revision ID: 1be7b272f496
Revises: 453a79c83bde
Create Date: 2026-01-08 00:20:36.732568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1be7b272f496'
down_revision: Union[str, None] = '453a79c83bde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite index on (decision_label, created_at) for analytics queries.
    
    This index accelerates queries filtering by decision outcome and date range,
    which are common in analytics dashboards and reporting tools.
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
