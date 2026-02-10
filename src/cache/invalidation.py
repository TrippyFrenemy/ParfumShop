"""
Cache invalidation functions for different data types.

These functions should be called after CRUD operations to keep cache in sync.
"""
import logging
from typing import Optional

from src.cache import cache_manager

logger = logging.getLogger(__name__)


async def invalidate_categories_cache():
    """
    Invalidate all categories cache.

    Should be called after:
    - Creating a new category
    - Updating category details
    - Deleting a category
    - Changing category hierarchy
    """
    count = await cache_manager.invalidate_namespace("categories")
    logger.info(f"Invalidated categories cache ({count} keys)")


async def invalidate_brands_cache():
    """
    Invalidate brands cache.

    Should be called after:
    - Creating a product with new brand
    - Updating product brand
    - Deleting last product of a brand
    """
    count = await cache_manager.invalidate_namespace("brands")
    logger.info(f"Invalidated brands cache ({count} keys)")


async def invalidate_products_cache(
    product_id: Optional[int] = None,
    slug: Optional[str] = None
):
    """
    Invalidate products cache.

    Args:
        product_id: If specified, invalidate only this product
        slug: Product slug for specific invalidation

    Should be called after:
    - Creating a new product
    - Updating product details
    - Deleting a product
    - Changing product price/availability
    """
    # Always invalidate product lists (they depend on all products)
    count = await cache_manager.delete_pattern("list:*", namespace="products")

    # Invalidate specific product detail if slug provided
    if slug:
        await cache_manager.delete(f"detail:slug_{slug}", namespace="products")
        count += 1

    logger.info(f"Invalidated products cache ({count} keys)")


async def invalidate_settings_cache():
    """
    Invalidate shop settings cache.

    Should be called after:
    - Updating shop settings
    """
    count = await cache_manager.invalidate_namespace("settings")
    logger.info(f"Invalidated settings cache ({count} keys)")


async def invalidate_reports_cache():
    """
    Invalidate reports cache.

    Should be called after:
    - Order status changes
    - New orders created
    - Manual cache refresh
    """
    count = await cache_manager.invalidate_namespace("reports")
    logger.info(f"Invalidated reports cache ({count} keys)")


async def invalidate_all_cache():
    """
    Invalidate ALL application cache.

    Use with caution - this clears everything.
    """
    namespaces = ["categories", "brands", "products", "settings", "reports"]
    total = 0

    for namespace in namespaces:
        count = await cache_manager.invalidate_namespace(namespace)
        total += count

    logger.warning(f"Invalidated ALL cache ({total} keys)")
    return total
