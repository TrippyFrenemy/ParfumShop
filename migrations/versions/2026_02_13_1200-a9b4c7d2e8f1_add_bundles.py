"""Add bundles and bundle_items tables, extend cart_items and order_items

Revision ID: a9b4c7d2e8f1
Revises: f7a2c8b9d1e3
Create Date: 2026-02-13 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b4c7d2e8f1'
down_revision: Union[str, Sequence[str], None] = 'f7a2c8b9d1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bundles table
    op.create_table(
        'bundles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('custom_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bundles_id'), 'bundles', ['id'], unique=False)
    op.create_index(op.f('ix_bundles_slug'), 'bundles', ['slug'], unique=True)

    # Create bundle_items table
    op.create_table(
        'bundle_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bundle_items_id'), 'bundle_items', ['id'], unique=False)

    # Add bundle_id to cart_items and make product_id nullable
    op.add_column('cart_items', sa.Column('bundle_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_cart_items_bundle_id', 'cart_items', 'bundles', ['bundle_id'], ['id']
    )
    op.alter_column('cart_items', 'product_id', nullable=True)

    # Add bundle_id and bundle_name to order_items
    op.add_column('order_items', sa.Column('bundle_id', sa.Integer(), nullable=True))
    op.add_column('order_items', sa.Column('bundle_name', sa.String(255), nullable=True))
    op.create_foreign_key(
        'fk_order_items_bundle_id', 'order_items', 'bundles', ['bundle_id'], ['id']
    )


def downgrade() -> None:
    # Remove foreign keys and columns from order_items
    op.drop_constraint('fk_order_items_bundle_id', 'order_items', type_='foreignkey')
    op.drop_column('order_items', 'bundle_name')
    op.drop_column('order_items', 'bundle_id')

    # Restore product_id NOT NULL in cart_items (only if no NULLs exist)
    op.alter_column('cart_items', 'product_id', nullable=False)
    op.drop_constraint('fk_cart_items_bundle_id', 'cart_items', type_='foreignkey')
    op.drop_column('cart_items', 'bundle_id')

    # Drop bundle_items then bundles
    op.drop_index(op.f('ix_bundle_items_id'), table_name='bundle_items')
    op.drop_table('bundle_items')
    op.drop_index(op.f('ix_bundles_slug'), table_name='bundles')
    op.drop_index(op.f('ix_bundles_id'), table_name='bundles')
    op.drop_table('bundles')
