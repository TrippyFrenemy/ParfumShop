"""Add applies_to_bundles to coupons

Revision ID: c2d6f9a4b3e5
Revises: a9b4c7d2e8f1
Create Date: 2026-02-13 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d6f9a4b3e5'
down_revision: Union[str, Sequence[str], None] = 'a9b4c7d2e8f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'coupons',
        sa.Column(
            'applies_to_bundles',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )


def downgrade() -> None:
    op.drop_column('coupons', 'applies_to_bundles')
