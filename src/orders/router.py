import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import get_current_user
from src.cart.router import get_optional_user, _resolve_cart
from src.cart.service import get_cart, clear_cart
from src.coupons.service import validate_coupon
from src.database import get_async_session
from src.orders.service import create_order, get_order_by_number, get_user_orders
from src.utils.telegram import notify_new_order
from src.settings.models import ShopSettings
from src.users.models import User

from src.templating import templates

router = APIRouter()


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Render the checkout page with cart contents."""
    cart = await _resolve_cart(request, session, user, create=False)
    if not cart or not cart.items:
        return RedirectResponse("/cart", status_code=302)

    shop_settings = await session.get(ShopSettings, 1)

    return templates.TemplateResponse(
        "checkout.html",
        {
            "request": request,
            "user": user,
            "cart": cart,
            "shop_settings": shop_settings,
        },
    )


@router.post("/orders/create")
async def create_order_endpoint(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    email: Optional[str] = Form(None),
    delivery_method: str = Form(...),
    city: Optional[str] = Form(None),
    city_ref: Optional[str] = Form(None),
    warehouse: Optional[str] = Form(None),
    warehouse_ref: Optional[str] = Form(None),
    up_city: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    np_address: Optional[str] = Form(None),
    np_delivery_type: Optional[str] = Form("warehouse"),
    comment: Optional[str] = Form(None),
    coupon_code: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Process the checkout form and create an order."""
    cart = await _resolve_cart(request, session, user, create=False)
    if not cart or not cart.items:
        return RedirectResponse("/cart", status_code=302)

    # For Ukrposhta, use the up_city field as city and address
    if delivery_method == "ukrposhta":
        city = up_city
        city_ref = None
        warehouse = None
        warehouse_ref = None
    # For Nova Poshta address delivery, use np_address and clear warehouse fields
    elif delivery_method == "nova_poshta" and np_delivery_type == "address":
        address = np_address
        warehouse = None
        warehouse_ref = None

    checkout_data = {
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "delivery_method": delivery_method,
        "city": city,
        "city_ref": city_ref,
        "warehouse": warehouse,
        "warehouse_ref": warehouse_ref,
        "address": address,
        "comment": comment,
    }

    # Validate coupon if provided
    coupon = None
    if coupon_code:
        coupon_obj, is_valid, error_msg = await validate_coupon(
            session, coupon_code, float(cart.total_price),
        )
        if is_valid and coupon_obj:
            coupon = coupon_obj

    try:
        order = await create_order(
            session,
            checkout_data=checkout_data,
            cart=cart,
            user_id=user.id if user else None,
            coupon=coupon,
        )
    except ValueError as e:
        shop_settings = await session.get(ShopSettings, 1)
        return templates.TemplateResponse(
            "checkout.html",
            {
                "request": request,
                "user": user,
                "cart": cart,
                "shop_settings": shop_settings,
                "error": str(e),
            },
        )

    # Notify staff via Telegram (fire-and-forget, don't block checkout)
    try:
        await notify_new_order(order)
    except Exception:
        pass

    # Clear the cart after successful order
    await clear_cart(session, cart.id)

    return RedirectResponse(
        f"/orders/{order.order_number}?is_new=1",
        status_code=302,
    )


@router.get("/orders/my", response_class=HTMLResponse)
async def my_orders_page(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Render the user's order history page."""
    orders, total = await get_user_orders(session, user.id, page=page, per_page=per_page)
    total_pages = math.ceil(total / per_page) if total else 1

    return templates.TemplateResponse(
        "my_orders.html",
        {
            "request": request,
            "user": user,
            "orders": orders,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": total_pages,
            },
        },
    )


@router.get("/orders/{order_number}", response_class=HTMLResponse)
async def order_detail_page(
    request: Request,
    order_number: str,
    is_new: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Render the order detail / confirmation page."""
    order = await get_order_by_number(session, order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено")

    # Only allow the order owner or staff to view
    if order.user_id and user and order.user_id != user.id:
        if user.role.value not in ("admin", "manager", "warehouse"):
            raise HTTPException(status_code=403, detail="Доступ заборонено")

    return templates.TemplateResponse(
        "order_confirmation.html",
        {
            "request": request,
            "user": user,
            "order": order,
            "is_new": bool(is_new),
        },
    )
