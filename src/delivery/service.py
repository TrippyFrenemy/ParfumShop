import logging

from src.delivery.models import DeliveryStatus
from src.delivery.nova_poshta import track_parcel

logger = logging.getLogger("user_logger")

# Nova Poshta status code -> internal DeliveryStatus mapping
_NP_STATUS_MAP: dict[int, DeliveryStatus] = {
    1: DeliveryStatus.PENDING,
    2: DeliveryStatus.PENDING,
    3: DeliveryStatus.PENDING,
    4: DeliveryStatus.PENDING,
    5: DeliveryStatus.PENDING,
    6: DeliveryStatus.PENDING,
    7: DeliveryStatus.IN_TRANSIT,
    8: DeliveryStatus.IN_TRANSIT,
    9: DeliveryStatus.DELIVERED,
    10: DeliveryStatus.RECEIVED,
    11: DeliveryStatus.RETURNED,
    101: DeliveryStatus.IN_TRANSIT,
    102: DeliveryStatus.RETURNED,
    103: DeliveryStatus.RETURNED,
    104: DeliveryStatus.RETURNED,
    105: DeliveryStatus.RETURNED,
    106: DeliveryStatus.RETURNED,
}


def map_np_status(status_code: int) -> DeliveryStatus:
    """Map a Nova Poshta numeric status code to an internal DeliveryStatus."""
    return _NP_STATUS_MAP.get(status_code, DeliveryStatus.PENDING)


async def update_order_delivery_status(session, order) -> bool:
    """Check the TTN on Nova Poshta and update the order's delivery_status.

    Returns True if the status was updated, False otherwise.
    """
    if not order.ttn:
        logger.debug(f"[DELIVERY] Order #{order.order_number} has no TTN, skipping")
        return False

    tracking = await track_parcel(order.ttn)
    if tracking is None:
        logger.warning(
            f"[DELIVERY] Could not track TTN {order.ttn} for order #{order.order_number}"
        )
        return False

    status_code = tracking.get("status_code")
    if not isinstance(status_code, int):
        logger.warning(
            f"[DELIVERY] Non-integer status_code={status_code!r} for TTN {order.ttn}"
        )
        return False

    new_status = map_np_status(status_code)

    if order.delivery_status == new_status:
        return False

    old_status = order.delivery_status
    order.delivery_status = new_status
    await session.commit()

    logger.info(
        f"[DELIVERY] Order #{order.order_number} TTN={order.ttn} "
        f"status changed {old_status.value} -> {new_status.value} (NP code={status_code})"
    )
    return True
