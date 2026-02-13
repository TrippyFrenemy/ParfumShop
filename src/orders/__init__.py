"""Orders domain — public API surface.

External modules should import from here, not from orders.service or orders.models directly.
"""
from src.orders.service import (
    create_order,
    get_order_by_number,
    get_user_orders,
    get_all_orders,
    get_order_stats,
    update_order_status,
    update_order_ttn,
    generate_order_number,
)

__all__ = [
    "create_order",
    "get_order_by_number",
    "get_user_orders",
    "get_all_orders",
    "get_order_stats",
    "update_order_status",
    "update_order_ttn",
    "generate_order_number",
]
