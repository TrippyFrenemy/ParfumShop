"""show_out_of_stock setting

Revision ID: a1b2c3d4e5f7
Revises: c3a1b2d4e5f6
Create Date: 2026-02-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'c3a1b2d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shop_settings', sa.Column('show_out_of_stock', sa.Boolean(), server_default='0', nullable=True))


def downgrade() -> None:
    op.drop_column('shop_settings', 'show_out_of_stock')
