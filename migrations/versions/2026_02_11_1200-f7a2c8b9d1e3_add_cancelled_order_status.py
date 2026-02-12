"""Add cancelled order status

Revision ID: f7a2c8b9d1e3
Revises: 1381a53ce290
Create Date: 2026-02-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a2c8b9d1e3'
down_revision: Union[str, Sequence[str], None] = '1381a53ce290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cancelled to OrderStatus enum.

    This adds a new value to the existing PostgreSQL enum type 'orderstatus'.
    Cancelled orders will be excluded from revenue calculations and reports.
    """
    # PostgreSQL: ALTER TYPE can only ADD values, not remove them
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    """Cannot remove enum values in PostgreSQL.

    WARNING: This migration is not reversible without recreating the entire enum
    and updating all columns that use it, which is risky in production.

    Manual intervention required if downgrade is absolutely necessary:
    1. Create new enum without 'cancelled'
    2. Alter column to use new enum
    3. Drop old enum
    4. Rename new enum
    """
    pass
