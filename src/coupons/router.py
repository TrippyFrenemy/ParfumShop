from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.coupons.schemas import CouponValidateRequest, CouponValidateResponse
from src.coupons.service import validate_coupon

router = APIRouter()


@router.post("/validate", response_model=CouponValidateResponse)
async def validate_coupon_endpoint(
    body: CouponValidateRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Validate a coupon code against the provided cart total.

    Accepts JSON body with ``code`` and ``cart_total``.
    Returns validity status and, when valid, the discount details.
    """
    coupon, is_valid, error_msg = await validate_coupon(
        session, body.code, body.cart_total,
    )

    if not is_valid or coupon is None:
        return CouponValidateResponse(
            valid=False,
            message=error_msg or "Купон не знайдено",
        )

    estimated_discount = coupon.calculate_discount(body.cart_total)

    return CouponValidateResponse(
        valid=True,
        message="Купон застосовано",
        discount_type=coupon.discount_type.value,
        discount_value=float(coupon.discount_value),
        estimated_discount=estimated_discount,
    )
