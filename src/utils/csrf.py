import secrets
import logging

from src.config import settings
from src.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


async def generate_csrf_token(user_id: int) -> str:
    token = secrets.token_hex(32)
    await get_redis_client().setex(f"csrf:{user_id}:{token}", settings.CSRF_TOKEN_EXPIRY, "valid")
    return token


async def verify_csrf_token(user_id: int, token: str) -> bool:
    key = f"csrf:{user_id}:{token}"
    logger.debug("Verifying CSRF token for user_id=%s", user_id)
    r = get_redis_client()
    exists = await r.exists(key)
    if exists:
        await r.delete(key)
    return bool(exists)
