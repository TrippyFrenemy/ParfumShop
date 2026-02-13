import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.cart.schemas import AddToCartRequest, CartOut, UpdateCartItemRequest
from src.cart.service import (
    add_to_cart,
    cart_to_dict,
    get_cart,
    get_or_create_cart,
    remove_from_cart,
    update_cart_item,
)
from src.database import get_async_session
from src.users.models import User

from src.templating import templates

router = APIRouter()


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    """Try to get current user, return None if not authenticated."""
    try:
        token = request.cookies.get("Authorization", "")
        if token.startswith("Bearer "):
            from src.auth.tokens import decode_token

            payload = decode_token(token[7:])
            user_id = int(payload.get("sub"))
            user = await session.get(User, user_id)
            if user and user.is_active:
                return user
    except Exception as exc:
        logger.debug("get_optional_user failed (unauthenticated): %s", exc)
    return None


def _get_session_id(request: Request) -> Optional[str]:
    """Read the guest cart session id from cookies."""
    return request.cookies.get("cart_session_id")


def _ensure_session_id(request: Request) -> str:
    """Return the existing cart_session_id cookie or generate a new one."""
    existing = request.cookies.get("cart_session_id")
    if existing:
        return existing
    return str(uuid.uuid4())


async def _resolve_cart(
    request: Request,
    session: AsyncSession,
    user: Optional[User],
    create: bool = True,
):
    """
    Resolve the current cart for the request.

    If the user is authenticated, use user_id.
    Otherwise fall back to the guest cart_session_id cookie.
    When create=True a new cart is created if none exists.
    """
    if user:
        if create:
            return await get_or_create_cart(session, user_id=user.id)
        return await get_cart(session, user_id=user.id)

    session_id = _get_session_id(request)
    if not session_id and not create:
        return None

    if not session_id:
        session_id = _ensure_session_id(request)

    if create:
        return await get_or_create_cart(session, session_id=session_id)
    return await get_cart(session, session_id=session_id)


def _set_session_cookie_if_guest(
    response: JSONResponse,
    request: Request,
    user: Optional[User],
) -> None:
    """Set the cart_session_id cookie for guest users if not already present."""
    if user:
        return
    existing = request.cookies.get("cart_session_id")
    if not existing:
        response.set_cookie(
            key="cart_session_id",
            value=_ensure_session_id(request),
            httponly=True,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,  # 30 days
            path="/",
        )


# ---------------------------------------------------------------------------
# JSON API endpoints
# ---------------------------------------------------------------------------

@router.get("/api/cart")
async def api_get_cart(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Return the current cart as JSON."""
    cart = await _resolve_cart(request, session, user, create=False)
    data = cart_to_dict(cart)
    return JSONResponse(content=data)


@router.post("/api/cart/add")
async def api_add_to_cart(
    request: Request,
    body: AddToCartRequest,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Add an item to the cart. Returns the updated cart."""
    # For guest users we need to ensure session_id is available before
    # creating the cart, so we read/generate it early.
    session_id = _ensure_session_id(request) if not user else None
    # Save user_id before expire_all() to avoid lazy-load on expired async object
    user_id = user.id if user else None

    if user_id:
        cart = await get_or_create_cart(session, user_id=user_id)
    else:
        cart = await get_or_create_cart(session, session_id=session_id)

    await add_to_cart(session, cart, body.product_id, body.quantity)

    # Expire cached objects so re-fetch returns fresh data
    # (expire_on_commit is False in the session factory)
    session.expire_all()

    # Re-fetch to get fully loaded relationships
    if user_id:
        cart = await get_cart(session, user_id=user_id)
    else:
        cart = await get_cart(session, session_id=session_id)

    data = cart_to_dict(cart)
    response = JSONResponse(content=data)

    # Set session cookie for guests
    if not user and not request.cookies.get("cart_session_id"):
        response.set_cookie(
            key="cart_session_id",
            value=session_id,
            httponly=True,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,
            path="/",
        )

    return response


@router.patch("/api/cart/update/{item_id}")
async def api_update_cart_item(
    item_id: int,
    request: Request,
    body: UpdateCartItemRequest,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Update the quantity of a cart item. Returns the updated cart."""
    user_id = user.id if user else None
    await update_cart_item(session, item_id, body.quantity)
    session.expire_all()

    if user_id:
        cart = await get_cart(session, user_id=user_id)
    else:
        session_id = _get_session_id(request)
        cart = await get_cart(session, session_id=session_id) if session_id else None
    data = cart_to_dict(cart)
    return JSONResponse(content=data)


@router.delete("/api/cart/remove/{item_id}")
async def api_remove_cart_item(
    item_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Remove an item from the cart. Returns the updated cart."""
    user_id = user.id if user else None
    await remove_from_cart(session, item_id)
    session.expire_all()

    if user_id:
        cart = await get_cart(session, user_id=user_id)
    else:
        session_id = _get_session_id(request)
        cart = await get_cart(session, session_id=session_id) if session_id else None
    data = cart_to_dict(cart)
    return JSONResponse(content=data)


# ---------------------------------------------------------------------------
# HTML page endpoint
# ---------------------------------------------------------------------------

@router.get("/cart")
async def cart_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Render the cart HTML page."""
    cart = await _resolve_cart(request, session, user, create=False)
    data = cart_to_dict(cart)
    return templates.TemplateResponse(
        "cart.html",
        {"request": request, "cart": data, "user": user},
    )
