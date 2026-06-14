import redis.asyncio as redis

from src.config import settings



_redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=int(settings.REDIS_PORT),
    decode_responses=True,
    socket_keepalive=True,
    socket_connect_timeout=5,
    retry_on_timeout=True,
)
_cache_redis_client = None

def get_redis_client() -> redis.Redis:
    return _redis_client

def get_cache_redis_client() -> redis.Redis:
    """Get Redis client for application cache (DB 2)"""
    global _cache_redis_client
    if _cache_redis_client is None:
        _cache_redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            db=settings.REDIS_CACHE_DB,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
    return _cache_redis_client