from src.config import settings
from src.utils.redis_client import get_redis_client


async def is_blocked(ip: str) -> bool:
    key = f"login_block:{ip}"
    attempts = await get_redis_client().get(key)
    return attempts is not None and int(attempts) >= settings.MAX_LOGIN_ATTEMPTS


async def register_failed_attempt(ip: str) -> None:
    key = f"login_block:{ip}"
    client = get_redis_client()
    async with client.pipeline(transaction=True) as pipe:
        await pipe.incr(key)
        await pipe.expire(key, settings.RATE_LIMIT_BLOCK_SECONDS)
        await pipe.execute()


async def delete_attempt(ip: str) -> None:
    await get_redis_client().delete(f"login_block:{ip}")
