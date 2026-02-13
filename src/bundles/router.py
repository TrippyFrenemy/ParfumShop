import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_optional_user
from src.bundles.schemas import AddBundleToCartRequest
from src.bundles.service import get_bundle_by_id, get_bundle_by_slug, get_bundles_cached
from src.cart.service import add_bundle_to_cart, cart_to_dict, get_cart, get_or_create_cart
from src.database import get_async_session
from src.templating import templates
from src.users.models import User

router = APIRouter()


@router.get("/bundles")
async def bundles_list_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Public bundle listing page — only shows available bundles."""
    from src.settings.models import ShopSettings
    shop_settings = await ShopSettings.get_settings(session)
    show_oos = bool(shop_settings and shop_settings.show_out_of_stock)
    bundles = await get_bundles_cached(session, show_out_of_stock=show_oos)
    return templates.TemplateResponse(
        "bundles/list.html",
        {"request": request, "user": user, "bundles": bundles},
    )


@router.get("/bundles/{slug}")
async def bundle_detail_page(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Public bundle detail page."""
    bundle = await get_bundle_by_slug(session, slug)
    if not bundle or not bundle.is_available:
        raise HTTPException(status_code=404, detail="Набір не знайдено")
    return templates.TemplateResponse(
        "bundles/detail.html",
        {"request": request, "user": user, "bundle": bundle},
    )


@router.post("/api/cart/add-bundle")
async def api_add_bundle_to_cart(
    request: Request,
    body: AddBundleToCartRequest,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Add a bundle to the cart. Returns updated cart."""
    bundle = await get_bundle_by_id(session, body.bundle_id)
    if not bundle or not bundle.is_available:
        raise HTTPException(status_code=400, detail="Набір більше недоступний")

    user_id = user.id if user else None
    session_id = request.cookies.get("cart_session_id") if not user else None

    if not session_id and not user_id:
        session_id = str(uuid.uuid4())

    if user_id:
        cart = await get_or_create_cart(session, user_id=user_id)
    else:
        cart = await get_or_create_cart(session, session_id=session_id)

    await add_bundle_to_cart(session, cart, body.bundle_id, body.quantity)
    session.expire_all()

    if user_id:
        cart = await get_cart(session, user_id=user_id)
    else:
        cart = await get_cart(session, session_id=session_id)

    data = cart_to_dict(cart)
    response = JSONResponse(content=data)

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
