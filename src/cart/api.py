"""Cart public API for cross-module use.

Other modules (orders, auth) should call these functions instead of importing
cart.service internals directly. This is the boundary layer that will become
an HTTP/gRPC call when Cart is extracted to its own microservice.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.cart.models import Cart
from src.cart.service import cart_to_dict, clear_cart, get_cart, merge_carts


async def get_cart_for_checkout(
    session: AsyncSession,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> Optional[Cart]:
    """Return the cart for the checkout flow.

    Resolves the correct cart by user_id (authenticated) or session_id (guest).
    Returns None if no cart is found or it is empty.
    """
    cart = await get_cart(session, user_id=user_id, session_id=session_id)
    if not cart or not cart.items:
        return None
    return cart


async def clear_cart_after_order(session: AsyncSession, cart: Cart) -> None:
    """Clear the cart contents after a successful order is placed."""
    await clear_cart(session, cart.id)


async def merge_guest_cart(
    session: AsyncSession,
    guest_session_id: str,
    user_id: int,
) -> None:
    """Merge a guest cart into the authenticated user's cart.

    Called by auth module on login/register/oauth to preserve cart items.
    """
    await merge_carts(session, guest_session_id=guest_session_id, user_id=user_id)


def serialize_cart(cart: Optional[Cart]) -> dict:
    """Serialize a Cart ORM object to a plain dict for use in templates/responses."""
    return cart_to_dict(cart)
