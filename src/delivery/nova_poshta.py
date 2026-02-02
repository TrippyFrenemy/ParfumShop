import json
import logging

import httpx

from src.config import settings
from src.utils.redis_client import get_redis_client

logger = logging.getLogger("user_logger")

NP_API_URL = "https://api.novaposhta.ua/v2.0/json/"


async def _np_request(model_name: str, called_method: str, method_properties: dict) -> dict | None:
    """Send a request to the Nova Poshta API and return the parsed response."""
    payload = {
        "apiKey": settings.NP_API_KEY,
        "modelName": model_name,
        "calledMethod": called_method,
        "methodProperties": method_properties,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(NP_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if not data.get("success"):
            errors = data.get("errors", [])
            logger.error(f"[NP API] {model_name}.{called_method} failed: {errors}")
            return None

        return data
    except httpx.HTTPError as exc:
        logger.error(f"[NP API] HTTP error for {model_name}.{called_method}: {exc}")
        return None
    except Exception as exc:
        logger.error(f"[NP API] Unexpected error for {model_name}.{called_method}: {exc}")
        return None


async def search_cities(query: str) -> list[dict]:
    """Search cities via Nova Poshta Address.searchSettlements.

    Results are cached in Redis for 24 hours.
    """
    redis = get_redis_client()
    cache_key = f"np:cities:{query}"

    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as exc:
        logger.error(f"[NP CACHE] Redis read error for {cache_key}: {exc}")

    data = await _np_request(
        model_name="Address",
        called_method="searchSettlements",
        method_properties={"CityName": query, "Limit": 20},
    )
    if data is None:
        return []

    raw = data.get("data", [])
    # searchSettlements returns data[0]["Addresses"] list
    addresses = []
    if raw and isinstance(raw, list) and len(raw) > 0:
        addresses = raw[0].get("Addresses", [])

    result = [
        {
            "ref": item.get("DeliveryCity", "") or item.get("Ref", ""),
            "name": item.get("Present", "") or item.get("MainDescription", ""),
            "area": item.get("Area", ""),
        }
        for item in addresses
    ]

    try:
        await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=86400)
    except Exception as exc:
        logger.error(f"[NP CACHE] Redis write error for {cache_key}: {exc}")

    return result


async def get_warehouses(city_ref: str) -> list[dict]:
    """Get warehouses for a city via Nova Poshta Address.getWarehouses.

    Results are cached in Redis for 12 hours.
    """
    redis = get_redis_client()
    cache_key = f"np:wh:{city_ref}"

    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as exc:
        logger.error(f"[NP CACHE] Redis read error for {cache_key}: {exc}")

    data = await _np_request(
        model_name="Address",
        called_method="getWarehouses",
        method_properties={"CityRef": city_ref, "Limit": 500},
    )
    if data is None:
        return []

    raw = data.get("data", [])

    result = [
        {
            "ref": item.get("Ref", ""),
            "number": item.get("Number", ""),
            "description": item.get("Description", ""),
            "type": item.get("TypeOfWarehouse", ""),
        }
        for item in raw
    ]

    try:
        await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=43200)
    except Exception as exc:
        logger.error(f"[NP CACHE] Redis write error for {cache_key}: {exc}")

    return result


async def track_parcel(ttn: str) -> dict | None:
    """Track a parcel via Nova Poshta TrackingDocument.getStatusDocuments.

    Returns status dict or None if the document is not found.
    """
    data = await _np_request(
        model_name="TrackingDocument",
        called_method="getStatusDocuments",
        method_properties={
            "Documents": [{"DocumentNumber": ttn, "Phone": ""}],
        },
    )
    if data is None:
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
        "status_description": item.get("Status", ""),
        "city_recipient": item.get("CityRecipient", ""),
        "warehouse_recipient": item.get("WarehouseRecipient", ""),
        "actual_delivery_date": item.get("ActualDeliveryDate", ""),
    }
