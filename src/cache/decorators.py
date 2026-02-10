import functools
import inspect
import logging
from typing import Any, Callable, Optional

from src.cache import cache_manager
from src.config import settings

logger = logging.getLogger(__name__)


def cache_result(
    namespace: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
    skip_if: Optional[Callable] = None
):
    """
    Decorator to cache function results in Redis.

    Args:
        namespace: Cache namespace (e.g., 'products', 'categories')
        ttl: Time to live in seconds (default: CACHE_DEFAULT_TTL)
        key_builder: Function to build cache key from arguments
                     Signature: (*args, **kwargs) -> str
                     If None, uses function name
        skip_if: Function to determine if cache should be skipped
                 Signature: (*args, **kwargs) -> bool

    Example:
        @cache_result(namespace="categories", ttl=7200)
        async def get_categories(session):
            ...

        @cache_result(
            namespace="products",
            ttl=900,
            key_builder=lambda session, slug: f"detail:{slug}"
        )
        async def get_product_by_slug(session, slug):
            ...

        @cache_result(
            namespace="reports",
            ttl=900,
            skip_if=lambda filters: filters.get("custom_date")
        )
        async def get_report(filters):
            ...
    """
    if ttl is None:
        ttl = settings.CACHE_DEFAULT_TTL

    def decorator(func: Callable) -> Callable:
        # Check if function is async
        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Check skip condition
            if skip_if and skip_if(*args, **kwargs):
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                try:
                    # Call key_builder with all args/kwargs
                    cache_key = key_builder(*args, **kwargs)
                except TypeError as e:
                    logger.error(f"key_builder failed for {func.__name__}: {e}. Skipping cache.")
                    # If key_builder fails, skip caching and call function directly
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Unexpected error in key_builder for {func.__name__}: {e}. Skipping cache.")
                    return await func(*args, **kwargs)
            else:
                cache_key = func.__name__

            # Try to get from cache
            cached_value = await cache_manager.get(cache_key, namespace=namespace)
            if cached_value is not None:
                return cached_value

            # Call original function
            result = await func(*args, **kwargs)

            # Cache the result (don't wait for completion)
            if result is not None:
                await cache_manager.set(cache_key, result, ttl, namespace=namespace)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # For sync functions, we can't use cache (requires async Redis)
            # Just call the original function
            return func(*args, **kwargs)

        return async_wrapper if is_async else sync_wrapper

    return decorator
