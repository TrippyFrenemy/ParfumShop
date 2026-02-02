from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.content.cache import get_cached_content, set_cached_content
from src.content.service import get_all_published, get_all_with_drafts
from src.database import async_session_maker
from src.settings.models import ShopSettings


class ContentMiddleware(BaseHTTPMiddleware):
    """Load site content into request.state for every request.

    Published content is served from Redis cache.
    Preview mode (?preview=1) loads drafts directly from DB,
    but only for authenticated admin/manager users.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip for static files and non-page requests
        path = request.url.path
        if path.startswith("/static") or path.startswith("/api/"):
            return await call_next(request)

        is_preview = request.query_params.get("preview") == "1"

        if is_preview and await self._is_staff(request):
            async with async_session_maker() as session:
                content = await get_all_with_drafts(session)
            request.state.site_content = content
            request.state.is_preview = True
        else:
            content = await get_cached_content()
            if content is None:
                async with async_session_maker() as session:
                    content = await get_all_published(session)
                await set_cached_content(content)
            request.state.site_content = content
            request.state.is_preview = False

        # Load shop settings for base template (header/footer phone, email, etc.)
        async with async_session_maker() as session:
            request.state.shop_settings = await session.get(ShopSettings, 1)

        return await call_next(request)

    @staticmethod
    async def _is_staff(request: Request) -> bool:
        """Check if the request has a valid admin/manager JWT cookie."""
        from src.auth.tokens import decode_token

        token = request.cookies.get("access_token")
        if not token:
            return False
        try:
            payload = decode_token(token)
            role = payload.get("role", "")
            return role in ("admin", "manager")
        except Exception:
            return False
