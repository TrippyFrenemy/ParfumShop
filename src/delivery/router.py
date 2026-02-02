from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.delivery.nova_poshta import search_cities, get_warehouses, track_parcel
from src.delivery.service import map_np_status

router = APIRouter()


@router.get("/np/cities")
async def np_search_cities(q: str = Query(..., min_length=2, description="City name query")):
    """Search Nova Poshta cities by name. No auth required (used in guest checkout)."""
    cities = await search_cities(q)
    return JSONResponse(content=cities)


@router.get("/np/warehouses")
async def np_get_warehouses(city_ref: str = Query(..., min_length=1, description="City Ref from NP")):
    """Get Nova Poshta warehouses for a city. No auth required."""
    warehouses = await get_warehouses(city_ref)
    return JSONResponse(content=warehouses)


@router.get("/track/{ttn}")
async def np_track_parcel(ttn: str):
    """Track a Nova Poshta shipment by TTN."""
    if not ttn or len(ttn) < 10:
        raise HTTPException(status_code=400, detail="Invalid TTN format")

    tracking = await track_parcel(ttn)
    if tracking is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    status_code = tracking.get("status_code")
    if isinstance(status_code, int):
        internal_status = map_np_status(status_code)
        tracking["internal_status"] = internal_status.value

    return JSONResponse(content=tracking)
