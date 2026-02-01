from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, pwd_context
from src.users.models import User
from src.database import get_async_session
from src.utils.redis_client import get_redis_client


router = APIRouter(tags=["Users"])
redis_client = get_redis_client()
templates = Jinja2Templates(directory="src/templates")


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }

@router.post("/me/delete", response_class=RedirectResponse)
async def delete_my_account(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user),
):
    # удалить refresh_token в redis
    await redis_client.delete(f"refresh_token:{user.id}")

    # 1) пробуем hard delete
    try:
        await session.delete(user)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # 2) fallback: soft delete
        user.is_active = False
        await session.commit()

    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("Authorization", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response
