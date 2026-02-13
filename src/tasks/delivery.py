import logging

import httpx
from celery import shared_task
from sqlalchemy import text

from src.config import settings
from src.delivery.service import map_np_status
from src.tasks.db import engine

logger = logging.getLogger(__name__)

NP_API_URL = "https://api.novaposhta.ua/v2.0/json/"


def _track_parcel_sync(ttn: str) -> dict | None:
    """Synchronous version of Nova Poshta tracking for use inside Celery tasks."""
    payload = {
        "apiKey": settings.NP_API_KEY,
        "modelName": "TrackingDocument",
        "calledMethod": "getStatusDocuments",
        "methodProperties": {
            "Documents": [{"DocumentNumber": ttn, "Phone": ""}],
        },
    }
    try:
        response = httpx.post(NP_API_URL, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("NP API request failed for TTN %s: %s", ttn, exc)
        return None

    if not data.get("success"):
        logger.warning("NP API error for TTN %s: %s", ttn, data.get("errors", []))
        return None

    items = data.get("data", [])
    if not items:
        return None

    item = items[0]
    status_code = item.get("StatusCode")
    if status_code is None or status_code == "":
        return None

    return {
        "status_code": int(status_code) if str(status_code).isdigit() else status_code,
        "status_name": item.get("Status", ""),
    }


@shared_task
def update_delivery_statuses() -> None:
    """Check Nova Poshta tracking for all shipped orders with a TTN and update their delivery status."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, order_number, ttn, delivery_status
                    FROM orders
                    WHERE status = 'shipped'
                      AND ttn IS NOT NULL
                      AND ttn != ''
                    """
                )
            ).fetchall()

        if not rows:
            logger.debug("No shipped orders with TTN to track")
            return

        logger.info("Tracking %d shipped orders", len(rows))
        updated = 0

        for row in rows:
            order_id = row[0]
            order_number = row[1]
            ttn = row[2]
            current_status = row[3]

            tracking = _track_parcel_sync(ttn)
            if tracking is None:
                logger.warning("Could not track TTN %s for order #%s", ttn, order_number)
                continue

            status_code = tracking.get("status_code")
            if not isinstance(status_code, int):
                logger.warning("Non-integer status_code=%r for TTN %s order #%s", status_code, ttn, order_number)
                continue

            new_status = map_np_status(status_code).value

            if new_status == current_status:
                continue

            try:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            UPDATE orders
                            SET delivery_status = :new_status,
                                updated_at = NOW()
                            WHERE id = :order_id
                            """
                        ),
                        {"new_status": new_status, "order_id": order_id},
                    )
                updated += 1
                logger.info(
                    "Order #%s TTN=%s status changed %s -> %s (NP code=%s)",
                    order_number, ttn, current_status, new_status, status_code,
                )
            except Exception as exc:
                logger.error("Failed to update order #%s: %s", order_number, exc)

        logger.info("Finished tracking: %d/%d orders updated", updated, len(rows))
    except Exception as exc:
        logger.error("Failed to run delivery status update: %s", exc)
