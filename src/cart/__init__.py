"""Cart domain — public API surface.

External modules should import from here, not from cart.service or cart.router directly.
"""
from src.cart.service import (
    get_cart,
    get_or_create_cart,
    add_to_cart,
    add_bundle_to_cart,
    remove_from_cart,
    update_cart_item,
    clear_cart,
    merge_carts,
    cart_to_dict,
)

__all__ = [
    "get_cart",
    "get_or_create_cart",
    "add_to_cart",
    "add_bundle_to_cart",
    "remove_from_cart",
    "update_cart_item",
    "clear_cart",
    "merge_carts",
    "cart_to_dict",
]
