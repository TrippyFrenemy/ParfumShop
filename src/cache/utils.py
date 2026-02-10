import hashlib
import json
from typing import Any, Optional


def build_cache_key(*parts, **filters) -> str:
    """
    Build a cache key from parts and filters.

    Args:
        *parts: Key parts to join with ':'
        **filters: Additional filters to include in key

    Returns:
        Cache key string

    Example:
        >>> build_cache_key("list", "cat", 5, sort="newest", page=1)
        'list:cat:5:sort_newest:page_1'
    """
    key_parts = [str(p) for p in parts if p is not None]

    # Add sorted filters
    if filters:
        for k, v in sorted(filters.items()):
            if v is not None:
                key_parts.append(f"{k}_{v}")

    return ":".join(key_parts)


def hash_filters(filters: dict) -> str:
    """
    Create a short hash from filters dictionary.

    Uses MD5 hash (first 8 characters) for compact cache keys.

    Args:
        filters: Dictionary of filter parameters

    Returns:
        8-character hash string

    Example:
        >>> hash_filters({"category_id": 5, "sort": "newest", "page": 1})
        'a3f2c1d4'
    """
    # Remove None values
    clean_filters = {k: v for k, v in filters.items() if v is not None}

    # Sort for deterministic hashing
    # Use default=str to handle datetime, Decimal, etc.
    filters_str = json.dumps(clean_filters, sort_keys=True, default=str)

    # MD5 hash (first 8 chars)
    return hashlib.md5(filters_str.encode()).hexdigest()[:8]


def build_products_cache_key(
    session: Any = None,  # Ignore session parameter
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    **kwargs  # Catch any other params
) -> str:
    """
    Build cache key for product list queries.

    Creates a compact hash-based key to handle multiple filter combinations.

    Args:
        category_id: Category filter
        search: Search query
        brand: Brand filter
        min_price: Minimum price
        max_price: Maximum price
        sort: Sort option
        page: Page number
        page_size: Items per page

    Returns:
        Cache key like 'list:a3f2c1d4'
    """
    filters = {
        "cat": category_id,
        "q": search,
        "b": brand,
        "pmin": min_price,
        "pmax": max_price,
        "s": sort,
        "pg": page,
        "ps": page_size
    }

    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    # Create hash
    filter_hash = hash_filters(filters)

    return f"list:{filter_hash}"
