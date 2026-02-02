import json
from typing import Optional

from src.utils.redis_client import get_redis_client

CACHE_KEY = "site_content:published"
CACHE_TTL = 300  # 5 minutes


async def get_cached_content() -> Optional[dict[str, str]]:
    r = get_redis_client()
    raw = await r.get(CACHE_KEY)
    if raw:
        return json.loads(raw)
    return None


async def set_cached_content(content: dict[str, str]) -> None:
    r = get_redis_client()
    await r.set(CACHE_KEY, json.dumps(content, ensure_ascii=False), ex=CACHE_TTL)


async def invalidate_content_cache() -> None:
    r = get_redis_client()
    await r.delete(CACHE_KEY)
