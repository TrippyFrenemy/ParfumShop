import redis.asyncio as redis

from src.config import settings



_redis_client = redis.Redis(host=settings.REDIS_HOST, port=int(settings.REDIS_PORT), decode_responses=True)

def get_redis_client() -> redis.Redis:
    return _redis_client