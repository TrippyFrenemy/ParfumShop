from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from src.auth.tokens import decode_token
from src.database import get_async_session
from src.logging_config import get_logger
from src.users.models import User

logger = get_logger(__name__)


class OAuth2PasswordBearerWithCookie(HTTPBearer):
    async def __call__(self, request: Request) -> str:
        auth_header = request.headers.get("Authorization")
        cookie_auth = request.cookies.get("Authorization")
        scheme, param = get_authorization_scheme_param(auth_header or cookie_auth)
        if scheme.lower() != "bearer":
            logger.debug("no bearer token", extra={"scheme": scheme})
            raise HTTPException(status_code=401, detail="Not authenticated")
        return param

oauth2_scheme = OAuth2PasswordBearerWithCookie()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

async def get_current_user(
    token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_async_session)
):
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise ValueError("Missing sub claim")
        user_id = int(sub)
    except (JWTError, ValueError) as exc:
        logger.debug("token decode failed", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await session.get(User, user_id)
    if not user or not user.is_active:
        logger.debug("user not found or inactive", extra={"user_id": user_id})
        raise HTTPException(status_code=403, detail="Inactive user")
    return user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> User | None:
    """Return the authenticated user or None if not authenticated/token invalid."""
    try:
        token = request.cookies.get("Authorization", "")
        if token.startswith("Bearer "):
            payload = decode_token(token[7:])
            sub = payload.get("sub")
            if sub is None:
                return None
            user_id = int(sub)
            user = await session.get(User, user_id)
            if user and user.is_active:
                return user
    except Exception as exc:
        logger.debug("get_optional_user: unauthenticated", extra={"error": str(exc)})
    return None


def require_roles(*roles: str):
    """Dependency factory: require the authenticated user to have one of the given roles."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return _check


# Convenience aliases — preserved for backwards compatibility
get_admin_user = require_roles("admin")
get_manager_or_admin = require_roles("admin", "manager")
get_warehouse_or_manager_or_admin = require_roles("admin", "manager", "warehouse")
