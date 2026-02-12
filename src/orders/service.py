from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import Cart
from src.coupons.models import Coupon
from src.orders.models import (
    Order, OrderItem, OrderStatus, DeliveryMethod,
    REVENUE_STATUSES,
)
from src.settings.models import ShopSettings


async def generate_order_number(session: AsyncSession) -> str:
    """Generate an order number in format PF-YYYYMMDD-XXXX."""
    today = date.today()
    date_str = today.strftime("%Y%m%d")

    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    stmt = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= start_of_day,
            Order.created_at <= end_of_day,
        )
    )
    result = await session.execute(stmt)
    count = result.scalar() or 0

    seq = str(count + 1).zfill(4)
    return f"PF-{date_str}-{seq}"


async def create_order(
    session: AsyncSession,
    checkout_data: dict,
    cart: Cart,
    user_id: Optional[int],
    coupon: Optional[Coupon],
) -> Order:
    """Create an order from the cart contents.

    Raises ValueError when business rules are violated.
    """
    # Load shop settings for minimum order validation
    settings = await session.get(ShopSettings, 1)
    min_amount = Decimal(str(settings.min_order_amount)) if settings and settings.min_order_amount else Decimal("0")

    # Calculate subtotal from cart items (snapshot prices at order time)
    subtotal = Decimal("0")
    order_items: list[OrderItem] = []
    for cart_item in cart.items:
        product = cart_item.product
        if not product:
            continue
        price = product.get_price_for_quantity(cart_item.quantity)
        line_total = Decimal(str(price)) * cart_item.quantity
        subtotal += line_total

        order_items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_image_url=product.main_image,
                price_per_unit=price,
                quantity=cart_item.quantity,
                total=line_total,
            )
        )

    if subtotal < min_amount:
        raise ValueError(
            f"Мінімальна сума замовлення: {min_amount} грн"
        )

    # Apply coupon discount
    discount_amount = Decimal("0")
    coupon_id = None
    if coupon:
        discount_amount = Decimal(str(coupon.calculate_discount(float(subtotal))))
        coupon_id = coupon.id

    total = subtotal - discount_amount
    if total < 0:
        total = Decimal("0")

    # Build payment info text from settings
    payment_info = settings.payment_info_text if settings else None

    order_number = await generate_order_number(session)

    order = Order(
        order_number=order_number,
        user_id=user_id,
        status=OrderStatus.CREATED,
        full_name=checkout_data["full_name"],
        phone=checkout_data["phone"],
        email=checkout_data.get("email"),
        delivery_method=DeliveryMethod(checkout_data["delivery_method"]),
        city=checkout_data.get("city"),
        city_ref=checkout_data.get("city_ref"),
        warehouse=checkout_data.get("warehouse"),
        warehouse_ref=checkout_data.get("warehouse_ref"),
        address=checkout_data.get("address"),
        comment=checkout_data.get("comment"),
        subtotal=subtotal,
        discount_amount=discount_amount,
        coupon_id=coupon_id,
        total=total,
        payment_info=payment_info,
        items=order_items,
    )

    session.add(order)

    # Increment coupon usage count
    if coupon:
        coupon.used_count = (coupon.used_count or 0) + 1

    await session.commit()

    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_order_by_number(
    session: AsyncSession,
    order_number: str,
) -> Optional[Order]:
    """Fetch a single order by its human-readable number with items eagerly loaded."""
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_orders(
    session: AsyncSession,
    user_id: int,
    page: int = 1,
    per_page: int = 10,
) -> tuple[list[Order], int]:
    """Return paginated orders for a specific user."""
    # Total count
    count_stmt = select(func.count(Order.id)).where(Order.user_id == user_id)
    total = (await session.execute(count_stmt)).scalar() or 0

    # Paginated results
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    orders = list(result.scalars().all())

    return orders, total


async def get_all_orders(
    session: AsyncSession,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Order], int]:
    """Return paginated orders with optional filters (admin view)."""
    conditions = []

    if status:
        conditions.append(Order.status == OrderStatus(status))

    if search:
        like_term = f"%{search}%"
        conditions.append(
            (Order.order_number.ilike(like_term))
            | (Order.full_name.ilike(like_term))
            | (Order.phone.ilike(like_term))
            | (Order.email.ilike(like_term))
        )

    if date_from:
        conditions.append(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        conditions.append(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

    where_clause = and_(*conditions) if conditions else True

    # Total count
    count_stmt = select(func.count(Order.id)).where(where_clause)
    total = (await session.execute(count_stmt)).scalar() or 0

    # Paginated results
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(where_clause)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    orders = list(result.scalars().all())

    return orders, total


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    status: OrderStatus,
) -> Optional[Order]:
    """Update the status of an order."""
    order = await session.get(Order, order_id)
    if not order:
        return None

    order.status = status
    await session.commit()

    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def update_order_ttn(
    session: AsyncSession,
    order_id: int,
    ttn: str,
) -> Optional[Order]:
    """Set the TTN (tracking number) for an order."""
    order = await session.get(Order, order_id)
    if not order:
        return None

    order.ttn = ttn
    await session.commit()

    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_order_stats(session: AsyncSession) -> dict:
    """Aggregate order statistics for the admin dashboard."""
    # Total orders
    total_orders = (
        await session.execute(select(func.count(Order.id)))
    ).scalar() or 0

    # Total revenue (sum of totals for paid/processing/shipped orders)
    revenue_stmt = select(func.sum(Order.total)).where(
        Order.status.in_(REVENUE_STATUSES)
    )
    total_revenue = (await session.execute(revenue_stmt)).scalar() or Decimal("0")

    # Orders today
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    orders_today = (
        await session.execute(
            select(func.count(Order.id)).where(Order.created_at >= start_of_day)
        )
    ).scalar() or 0

    # Pending orders (status = CREATED)
    pending_orders = (
        await session.execute(
            select(func.count(Order.id)).where(Order.status == OrderStatus.CREATED)
        )
    ).scalar() or 0

    return {
        "total_orders": total_orders,
        "total_revenue": str(total_revenue),
        "orders_today": orders_today,
        "pending_orders": pending_orders,
    }
