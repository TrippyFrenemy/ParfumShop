from src.config import settings
from src.utils.redis_client import get_redis_client


async def is_blocked(ip: str) -> bool:
    key = f"login_block:{ip}"
    attempts = await get_redis_client().get(key)
    return attempts is not None and int(attempts) >= settings.MAX_LOGIN_ATTEMPTS


async def register_failed_attempt(ip: str) -> None:
    key = f"login_block:{ip}"
    current = await get_redis_client().incr(key)
    if current == 1:
        await get_redis_client().expire(key, settings.RATE_LIMIT_BLOCK_SECONDS)


async def delete_attempt(ip: str) -> None:
    await get_redis_client().delete(f"login_block:{ip}")
