"""Products domain — public API surface."""
from src.products.service import (
    get_products,
    get_products_cached,
    get_product_by_slug,
    get_categories,
    get_category_tree_cached,
    get_featured_products,
    create_product,
    update_product,
    delete_product,
)

__all__ = [
    "get_products",
    "get_products_cached",
    "get_product_by_slug",
    "get_categories",
    "get_category_tree_cached",
    "get_featured_products",
    "create_product",
    "update_product",
    "delete_product",
]
