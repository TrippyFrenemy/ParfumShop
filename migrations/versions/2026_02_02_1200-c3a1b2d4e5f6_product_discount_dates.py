"""product_discount_dates

Revision ID: c3a1b2d4e5f6
Revises: fd191d9c09e7
Create Date: 2026-02-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a1b2d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fd191d9c09e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('discount_start', sa.DateTime(), nullable=True))
    op.add_column('products', sa.Column('discount_end', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'discount_end')
    op.drop_column('products', 'discount_start')
