from typing import Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.coupons.models import Coupon, DiscountType
from src.coupons.schemas import CouponCreate, CouponUpdate


async def get_coupon_by_code(session: AsyncSession, code: str) -> Optional[Coupon]:
    """Return a coupon by its unique code (case-insensitive) or None."""
    stmt = select(Coupon).where(func.lower(Coupon.code) == code.strip().lower())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def validate_coupon(
    session: AsyncSession,
    code: str,
    order_total: float,
) -> Tuple[Optional[Coupon], bool, Optional[str]]:
    """Validate a coupon code against a given order total.

    Returns (coupon | None, is_valid, error_message | None).
    """
    coupon = await get_coupon_by_code(session, code)
    if coupon is None:
        return None, False, "Купон не знайдено"

    is_valid, error_msg = coupon.is_valid(order_total)
    return coupon, is_valid, error_msg


async def get_all_coupons(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[list, int]:
    """Return a paginated list of coupons and the total count."""
    # Total count
    count_stmt = select(func.count(Coupon.id))
    total = (await session.execute(count_stmt)).scalar() or 0

    # Paginated results
    offset = (page - 1) * per_page
    stmt = (
        select(Coupon)
        .order_by(Coupon.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    coupons = result.scalars().all()

    return list(coupons), total


async def create_coupon(session: AsyncSession, data: CouponCreate) -> Coupon:
    """Create a new coupon from validated schema data."""
    coupon = Coupon(
        code=data.code.strip().upper(),
        discount_type=DiscountType(data.discount_type),
        discount_value=data.discount_value,
        min_order_amount=data.min_order_amount,
        max_uses=data.max_uses,
        is_active=data.is_active,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
    )
    session.add(coupon)
    await session.commit()
    await session.refresh(coupon)
    return coupon


async def update_coupon(
    session: AsyncSession,
    coupon_id: int,
    data: CouponUpdate,
) -> Optional[Coupon]:
    """Update an existing coupon. Returns the updated coupon or None if not found."""
    stmt = select(Coupon).where(Coupon.id == coupon_id)
    result = await session.execute(stmt)
    coupon = result.scalar_one_or_none()
    if coupon is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "discount_type" and value is not None:
            value = DiscountType(value)
        if field == "code" and value is not None:
            value = value.strip().upper()
        setattr(coupon, field, value)

    await session.commit()
    await session.refresh(coupon)
    return coupon


async def delete_coupon(session: AsyncSession, coupon_id: int) -> bool:
    """Delete a coupon by id. Returns True on success, False if not found."""
    stmt = select(Coupon).where(Coupon.id == coupon_id)
    result = await session.execute(stmt)
    coupon = result.scalar_one_or_none()
    if coupon is None:
        return False

    await session.delete(coupon)
    await session.commit()
    return True
