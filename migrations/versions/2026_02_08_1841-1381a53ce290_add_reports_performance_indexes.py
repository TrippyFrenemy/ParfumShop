"""add_reports_performance_indexes

Revision ID: 1381a53ce290
Revises: 3b410419aa86
Create Date: 2026-02-08 18:41:48.730087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1381a53ce290'
down_revision: Union[str, Sequence[str], None] = '3b410419aa86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add composite index on orders table for reports filtering by date and status
    op.create_index(
        'idx_orders_created_status',
        'orders',
        ['created_at', 'status'],
        unique=False
    )

    # Add index on order_items for product aggregations
    op.create_index(
        'idx_order_items_product',
        'order_items',
        ['product_id'],
        unique=False
    )

    # Add composite index on products for filtering by category and active status
    op.create_index(
        'idx_products_category_active',
        'products',
        ['category_id', 'is_active'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes in reverse order
    op.drop_index('idx_products_category_active', table_name='products')
    op.drop_index('idx_order_items_product', table_name='order_items')
    op.drop_index('idx_orders_created_status', table_name='orders')
