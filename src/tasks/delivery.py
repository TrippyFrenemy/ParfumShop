import httpx
from celery import shared_task
from sqlalchemy import create_engine, text

from src.config import settings

SYNC_DB_URL = (
    f"postgresql://{settings.DB_USER}:{settings.DB_PASS}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)
engine = create_engine(SYNC_DB_URL)

NP_API_URL = "https://api.novaposhta.ua/v2.0/json/"

# Nova Poshta status code -> internal DeliveryStatus mapping
# Mirrors src/delivery/service.py _NP_STATUS_MAP
_NP_STATUS_MAP: dict[int, str] = {
    1: "pending",
    2: "pending",
    3: "pending",
    4: "pending",
    5: "pending",
    6: "pending",
    7: "in_transit",
    8: "in_transit",
    9: "delivered",
    10: "received",
    11: "returned",
    101: "in_transit",
    102: "returned",
    103: "returned",
    104: "returned",
    105: "returned",
    106: "returned",
}


def _map_np_status(status_code: int) -> str:
    """Map a Nova Poshta numeric status code to a delivery_status string."""
    return _NP_STATUS_MAP.get(status_code, "pending")


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
        print(f"[DELIVERY] NP API request failed for TTN {ttn}: {exc}")
        return None

    if not data.get("success"):
        print(f"[DELIVERY] NP API error for TTN {ttn}: {data.get('errors', [])}")
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
            print("[DELIVERY] No shipped orders with TTN to track")
            return

        print(f"[DELIVERY] Tracking {len(rows)} shipped orders")
        updated = 0

        for row in rows:
            order_id = row[0]
            order_number = row[1]
            ttn = row[2]
            current_status = row[3]

            tracking = _track_parcel_sync(ttn)
            if tracking is None:
                print(f"[DELIVERY] Could not track TTN {ttn} for order #{order_number}")
                continue

            status_code = tracking.get("status_code")
            if not isinstance(status_code, int):
                print(
                    f"[DELIVERY] Non-integer status_code={status_code!r} "
                    f"for TTN {ttn} order #{order_number}"
                )
                continue

            new_status = _map_np_status(status_code)

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
                print(
                    f"[DELIVERY] Order #{order_number} TTN={ttn} "
                    f"status changed {current_status} -> {new_status} (NP code={status_code})"
                )
            except Exception as exc:
                print(f"[DELIVERY] Failed to update order #{order_number}: {exc}")

        print(f"[DELIVERY] Finished tracking: {updated}/{len(rows)} orders updated")
    except Exception as exc:
        print(f"[DELIVERY] Failed to run delivery status update: {exc}")
