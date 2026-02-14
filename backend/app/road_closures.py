import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger("fluxroute.road_closures")

# City of Toronto Open Data - Road Restrictions/Closures (ArcGIS FeatureServer)
# Query: 1=1 (all records), outFields=* (all fields), f=geojson
ROAD_CLOSURES_URL = (
    "https://services.arcgis.com/S9gh4fPZq4aJ5B5K/arcgis/rest/services/"
    "RoadClosures_Public/FeatureServer/0/query"
)

# Cache configuration
_cache: Dict[str, Any] = {
    "data": None,
    "expires_at": 0
}
CACHE_DURATION_SECONDS = 300  # 5 minutes

async def fetch_road_closures() -> Dict[str, Any]:
    """
    Fetch active road closures/restrictions from Toronto Open Data.
    Returns GeoJSON FeatureCollection.
    """
    global _cache
    now = time.time()

    # Return cached data if valid
    if _cache["data"] and now < _cache["expires_at"]:
        return _cache["data"]

    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "geojson",
        "outSR": "4326"  # Ensure WGS84 coordinates
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(ROAD_CLOSURES_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Basic validation
        if "features" in data:
            count = len(data["features"])
            logger.info(f"Fetched {count} road closures from Toronto Open Data")
            
            # Simple filtering for active closures if API returns expired ones
            # (Though ArcGIS usually returns current snapshot)
            _cache["data"] = data
            _cache["expires_at"] = now + CACHE_DURATION_SECONDS
            return data
        else:
            logger.warning("No features found in road closure response")
            return {"type": "FeatureCollection", "features": []}

    except Exception as e:
        logger.error(f"Failed to fetch road closures: {e}")
        # Return empty collection or stale cache if available
        if _cache["data"]:
            logger.info("Serving stale road closure data due to error")
            return _cache["data"]
        return {"type": "FeatureCollection", "features": []}
