import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional

import redis.asyncio as redis

from src.config import settings
from src.utils.redis_client import get_cache_redis_client

logger = logging.getLogger(__name__)


def json_serializer(obj):
    """
    Custom JSON serializer for special types.

    Handles datetime, date, Decimal - common types in the application.
    Raises TypeError for SQLAlchemy models to prevent silent bugs.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, '__tablename__'):
        # This looks like a SQLAlchemy model - ERROR!
        raise TypeError(
            f"Cannot serialize SQLAlchemy model: {type(obj).__name__}. "
            f"Convert to dictionary first before caching."
        )
    # Fallback to string for other types
    return str(obj)


class CacheManager:
    """
    Centralized cache manager for application caching.

    Uses Redis DB 2 for all application cache with namespace isolation.
    Provides automatic JSON serialization/deserialization and graceful degradation.
    """

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._enabled = settings.CACHE_ENABLED
        self._hit_count = 0
        self._miss_count = 0

    def _get_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if self._client is None:
            self._client = get_cache_redis_client()
        return self._client

    def _build_key(self, key: str, namespace: str = "") -> str:
        """Build full cache key with namespace prefix"""
        if namespace:
            return f"{namespace}:{key}"
        return key

    async def get(self, key: str, namespace: str = "") -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            namespace: Namespace prefix (e.g., 'products', 'categories')

        Returns:
            Cached value or None if not found/error
        """
        if not self._enabled:
            return None

        try:
            client = self._get_client()
            full_key = self._build_key(key, namespace)
            value = await client.get(full_key)

            if value is None:
                self._miss_count += 1
                logger.debug(f"Cache MISS: {full_key}")
                return None

            self._hit_count += 1
            logger.debug(f"Cache HIT: {full_key}")

            # Deserialize JSON
            return json.loads(value)

        except redis.RedisError as e:
            logger.error(f"Redis error on get({full_key}): {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key {full_key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int,
        namespace: str = ""
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            namespace: Namespace prefix

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False

        try:
            client = self._get_client()
            full_key = self._build_key(key, namespace)

            # Serialize to JSON with custom serializer
            serialized = json.dumps(value, ensure_ascii=False, default=json_serializer)

            # Set with TTL
            await client.setex(full_key, ttl, serialized)
            logger.debug(f"Cache SET: {full_key} (TTL: {ttl}s)")
            return True

        except redis.RedisError as e:
            logger.error(f"Redis error on set({full_key}): {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error for key {full_key}: {e}")
            return False

    async def delete(self, key: str, namespace: str = "") -> bool:
        """
        Delete a single key from cache.

        Args:
            key: Cache key
            namespace: Namespace prefix

        Returns:
            True if deleted, False otherwise
        """
        if not self._enabled:
            return False

        try:
            client = self._get_client()
            full_key = self._build_key(key, namespace)
            result = await client.delete(full_key)
            logger.debug(f"Cache DELETE: {full_key}")
            return result > 0

        except redis.RedisError as e:
            logger.error(f"Redis error on delete({full_key}): {e}")
            return False

    async def delete_pattern(self, pattern: str, namespace: str = "") -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., 'list:*')
            namespace: Namespace prefix

        Returns:
            Number of keys deleted
        """
        if not self._enabled:
            return 0

        try:
            client = self._get_client()
            full_pattern = self._build_key(pattern, namespace)

            # Find all matching keys
            keys = []
            async for key in client.scan_iter(match=full_pattern):
                keys.append(key)

            if not keys:
                return 0

            # Delete all at once
            result = await client.delete(*keys)
            logger.info(f"Cache DELETE PATTERN: {full_pattern} ({result} keys)")
            return result

        except redis.RedisError as e:
            logger.error(f"Redis error on delete_pattern({full_pattern}): {e}")
            return 0

    async def invalidate_namespace(self, namespace: str) -> int:
        """
        Clear all keys in a namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            Number of keys deleted
        """
        return await self.delete_pattern("*", namespace=namespace)

    def get_stats(self) -> dict:
        """
        Get cache hit/miss statistics.

        Returns:
            Dictionary with hit_count, miss_count, hit_rate
        """
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total * 100) if total > 0 else 0

        return {
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "total_requests": total,
            "hit_rate": round(hit_rate, 2),
            "enabled": self._enabled
        }

    def reset_stats(self):
        """Reset hit/miss counters"""
        self._hit_count = 0
        self._miss_count = 0
