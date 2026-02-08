"""replace stock_quantity with in_stock

Revision ID: 3b410419aa86
Revises: b2c3d4e5f6a8
Create Date: 2026-02-08 03:22:25.734569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b410419aa86'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Replace stock_quantity with in_stock."""
    # Normalize brands: apply title case to prevent duplicates
    # (e.g., "CHANEL", "chanel", "Chanel" → all become "Chanel")
    op.execute("""
        UPDATE products
        SET brand = INITCAP(TRIM(brand))
        WHERE brand IS NOT NULL
    """)

    # Normalize product names: trim whitespace but preserve casing
    op.execute("""
        UPDATE products
        SET name = TRIM(name)
        WHERE name IS NOT NULL
    """)

    # Add new in_stock field
    op.add_column('products', sa.Column('in_stock', sa.Boolean(),
                  nullable=False, server_default='1'))

    # Migrate data: convert stock_quantity to boolean
    # Products with stock_quantity > 0 are in stock, otherwise out of stock
    op.execute("UPDATE products SET in_stock = CASE WHEN stock_quantity > 0 THEN TRUE ELSE FALSE END")

    # Drop old stock_quantity column
    op.drop_column('products', 'stock_quantity')


def downgrade() -> None:
    """Downgrade schema: Restore stock_quantity from in_stock."""
    # Add back stock_quantity column with default 0
    op.add_column('products', sa.Column('stock_quantity', sa.Integer(),
                  nullable=False, server_default='0'))

    # Reverse migration: convert boolean back to quantity
    # in_stock=True → 1, in_stock=False → 0
    op.execute("UPDATE products SET stock_quantity = CASE WHEN in_stock = TRUE THEN 1 ELSE 0 END")

    # Drop in_stock column
    op.drop_column('products', 'in_stock')
