"""order tracking fields

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-02-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('last_viewed_by', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('last_viewed_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('last_modified_by', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('last_modified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'last_modified_at')
    op.drop_column('orders', 'last_modified_by')
    op.drop_column('orders', 'last_viewed_at')
    op.drop_column('orders', 'last_viewed_by')
