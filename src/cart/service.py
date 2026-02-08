from decimal import Decimal
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.cart.models import Cart, CartItem
from src.products.models import Product, ProductImage


async def get_or_create_cart(
    session: AsyncSession,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> Cart:
    """Get existing cart or create a new one for the user/guest."""
    cart = await get_cart(session, user_id=user_id, session_id=session_id)
    if cart:
        return cart

    cart = Cart(user_id=user_id, session_id=session_id)
    session.add(cart)
    await session.commit()
    await session.refresh(cart)

    # Re-fetch with eager loading so relationships are populated
    cart = await get_cart(session, user_id=user_id, session_id=session_id)
    return cart


async def get_cart(
    session: AsyncSession,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> Optional[Cart]:
    """Fetch cart with eager-loaded items -> product -> images."""
    stmt = (
        select(Cart)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.product)
            .selectinload(Product.images),
            selectinload(Cart.items)
            .selectinload(CartItem.product)
            .selectinload(Product.wholesale_tiers),
        )
        .execution_options(populate_existing=True)
    )

    if user_id is not None:
        stmt = stmt.where(Cart.user_id == user_id)
    elif session_id is not None:
        stmt = stmt.where(Cart.session_id == session_id)
    else:
        return None

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_to_cart(
    session: AsyncSession,
    cart: Cart,
    product_id: int,
    quantity: int,
) -> CartItem:
    """Add product to cart. If already present, increase quantity."""
    # Check if this product is already in the cart
    stmt = select(CartItem).where(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product_id,
    )
    result = await session.execute(stmt)
    existing_item = result.scalar_one_or_none()

    if existing_item:
        existing_item.quantity += quantity
        await session.commit()
        await session.refresh(existing_item)
        return existing_item

    item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def update_cart_item(
    session: AsyncSession,
    item_id: int,
    quantity: int,
) -> Optional[CartItem]:
    """Update item quantity. If quantity <= 0, remove the item."""
    item = await session.get(CartItem, item_id)
    if not item:
        return None

    if quantity <= 0:
        await session.delete(item)
        await session.commit()
        return None

    item.quantity = quantity
    await session.commit()
    await session.refresh(item)
    return item


async def remove_from_cart(session: AsyncSession, item_id: int) -> None:
    """Remove an item from the cart entirely."""
    item = await session.get(CartItem, item_id)
    if item:
        await session.delete(item)
        await session.commit()


async def clear_cart(session: AsyncSession, cart_id: int) -> None:
    """Remove all items from a cart."""
    stmt = delete(CartItem).where(CartItem.cart_id == cart_id)
    await session.execute(stmt)
    await session.commit()


async def merge_carts(
    session: AsyncSession,
    guest_session_id: str,
    user_id: int,
) -> Optional[Cart]:
    """
    Merge guest cart into the authenticated user's cart on login.

    For products present in both carts, quantities are summed.
    The guest cart is deleted after merging.
    """
    guest_cart = await get_cart(session, session_id=guest_session_id)
    if not guest_cart or not guest_cart.items:
        # Nothing to merge; just return the user cart if it exists
        if guest_cart:
            await session.delete(guest_cart)
            await session.commit()
        return await get_cart(session, user_id=user_id)

    user_cart = await get_or_create_cart(session, user_id=user_id)

    # Build a lookup of existing user cart items by product_id
    user_items_by_product = {
        item.product_id: item for item in user_cart.items
    }

    for guest_item in guest_cart.items:
        if guest_item.product_id in user_items_by_product:
            # Same product exists -- sum the quantities
            user_items_by_product[guest_item.product_id].quantity += guest_item.quantity
        else:
            # Move item to user cart
            new_item = CartItem(
                cart_id=user_cart.id,
                product_id=guest_item.product_id,
                quantity=guest_item.quantity,
            )
            session.add(new_item)

    # Delete the guest cart (cascade removes its items)
    await session.delete(guest_cart)
    await session.commit()

    # Re-fetch with eager loading
    return await get_cart(session, user_id=user_id)


def cart_to_dict(cart: Optional[Cart]) -> dict:
    """Serialize a Cart into a plain dict suitable for JSON responses."""
    if not cart:
        return {"items": [], "total_items": 0, "total_price": "0.00"}

    items = []
    # Sort items by ID to ensure consistent ordering
    sorted_items = sorted(cart.items, key=lambda x: x.id)
    for item in sorted_items:
        product = item.product
        price_per_unit = product.get_price_for_quantity(item.quantity) if product else Decimal("0")
        line_total = price_per_unit * item.quantity if product else Decimal("0")

        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": product.name if product else "",
            "product_slug": product.slug if product else "",
            "product_brand": product.brand if product else "",
            "product_volume_ml": product.volume_ml if product else None,
            "product_image": product.main_image if product else None,
            "price_per_unit": str(price_per_unit),
            "quantity": item.quantity,
            "line_total": str(line_total),
        })

    total_items = sum(i["quantity"] for i in items)
    total_price = sum(Decimal(i["line_total"]) for i in items)

    return {
        "items": items,
        "total_items": total_items,
        "total_price": str(total_price),
    }
