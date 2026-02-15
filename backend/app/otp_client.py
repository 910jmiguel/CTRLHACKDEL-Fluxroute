"""OpenTripPlanner client for multi-agency transit routing."""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import httpx

from app.models import (
    Coordinate,
    CostBreakdown,
    DelayInfo,
    RouteMode,
    RouteOption,
    RouteSegment,
)

logger = logging.getLogger("fluxroute.otp")

OTP_BASE_URL = None


def _get_otp_url() -> str:
    global OTP_BASE_URL
    if OTP_BASE_URL is None:
        OTP_BASE_URL = os.getenv("OTP_BASE_URL", "http://localhost:8080")
    return OTP_BASE_URL


# OTP mode string → our RouteMode
_OTP_MODE_MAP = {
    "WALK": RouteMode.WALKING,
    "BUS": RouteMode.TRANSIT,
    "SUBWAY": RouteMode.TRANSIT,
    "RAIL": RouteMode.TRANSIT,
    "TRAM": RouteMode.TRANSIT,
    "FERRY": RouteMode.TRANSIT,
    "CABLE_CAR": RouteMode.TRANSIT,
    "GONDOLA": RouteMode.TRANSIT,
    "FUNICULAR": RouteMode.TRANSIT,
    "CAR": RouteMode.DRIVING,
    "BICYCLE": RouteMode.CYCLING,
}

# Agency colors for route segments
_AGENCY_COLORS = {
    "TTC": "#DA291C",
    "GO Transit": "#3D8B37",
    "YRT": "#0072CE",
    "MiWay": "#F7941D",
    "Brampton Transit": "#E31937",
}

_TRANSIT_MODE_COLORS = {
    "SUBWAY": "#F0CC49",
    "RAIL": "#3D8B37",
    "BUS": "#DA291C",
    "TRAM": "#DE7731",
}


_RAPID_TRANSIT_MODES = {"SUBWAY", "RAIL"}


async def find_park_and_ride_stations(
    lat: float,
    lng: float,
    radius_km: float = 15.0,
    http_client: Optional[httpx.AsyncClient] = None,
) -> list[dict]:
    """Find subway/rail stations near a point using the OTP index API.

    Returns a list of dicts with stop_id, name, lat, lng, mode, agencyName.
    """
    base = _get_otp_url()
    # OTP index API uses bounding box — convert radius to approx degrees
    delta_lat = radius_km / 111.0
    delta_lng = radius_km / (111.0 * 0.7)  # cos(~43.7°) ≈ 0.72

    params = {
        "minLat": str(lat - delta_lat),
        "maxLat": str(lat + delta_lat),
        "minLon": str(lng - delta_lng),
        "maxLon": str(lng + delta_lng),
    }

    try:
        url = f"{base}/otp/routers/default/index/stops"
        if http_client:
            resp = await http_client.get(url, params=params, timeout=5.0)
        else:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
        resp.raise_for_status()
        stops = resp.json()
    except Exception as e:
        logger.warning(f"OTP stop search failed: {e}")
        return []

    results = []
    for stop in stops:
        # Filter to stops that serve rapid transit routes
        modes = stop.get("modes", [])
        if not any(m in _RAPID_TRANSIT_MODES for m in modes):
            # Check routes if modes not directly available
            routes = stop.get("routes", [])
            if routes:
                has_rapid = any(
                    r.get("mode") in _RAPID_TRANSIT_MODES for r in routes
                )
                if not has_rapid:
                    continue
            else:
                continue

        stop_lat = stop.get("lat", 0)
        stop_lng = stop.get("lon", 0)

        # Determine mode
        mode = "SUBWAY"
        agency = ""
        if stop.get("routes"):
            for r in stop["routes"]:
                if r.get("mode") in _RAPID_TRANSIT_MODES:
                    mode = r["mode"]
                    agency = r.get("agencyName", "")
                    break
        elif "RAIL" in modes:
            mode = "RAIL"

        results.append({
            "stop_id": stop.get("id", ""),
            "stop_name": stop.get("name", ""),
            "lat": stop_lat,
            "lng": stop_lng,
            "mode": mode,
            "agencyName": agency,
        })

    logger.info(f"Found {len(results)} park-and-ride station candidates near ({lat:.4f}, {lng:.4f})")
    return results


async def check_otp_health(http_client: Optional[httpx.AsyncClient] = None) -> bool:
    """Check if OTP server is available."""
    base = _get_otp_url()
    try:
        if http_client:
            resp = await http_client.get(f"{base}/otp/routers/default/", timeout=3.0)
            return resp.status_code == 200
        else:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{base}/otp/routers/default/")
                return resp.status_code == 200
    except Exception:
        return False


async def query_otp_routes(
    origin: Coordinate,
    destination: Coordinate,
    departure_time: Optional[datetime] = None,
    num_itineraries: int = 3,
    http_client: Optional[httpx.AsyncClient] = None,
) -> list[dict]:
    """Query OTP for transit itineraries.

    Returns a list of raw OTP itinerary dicts, or empty list on failure.
    """
    base = _get_otp_url()
    now = departure_time or datetime.now()

    params = {
        "fromPlace": f"{origin.lat},{origin.lng}",
        "toPlace": f"{destination.lat},{destination.lng}",
        "mode": "TRANSIT,WALK",
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "numItineraries": str(num_itineraries),
        "walkReluctance": "2",
        "maxWalkDistance": "2000",
        "arriveBy": "false",
    }

    url = f"{base}/otp/routers/default/plan"

    try:
        if http_client:
            resp = await http_client.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
        else:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

        plan = data.get("plan")
        if not plan:
            error = data.get("error", {})
            logger.warning(f"OTP returned no plan: {error.get('message', 'unknown')}")
            return []

        return plan.get("itineraries", [])

    except httpx.TimeoutException:
        logger.warning("OTP request timed out")
        return []
    except Exception as e:
        logger.warning(f"OTP query failed: {e}")
        return []


def _decode_polyline(encoded: str) -> list[list[float]]:
    """Decode a Google-style encoded polyline to [lng, lat] coords."""
    coords = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        # Latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat += (~(result >> 1) if (result & 1) else (result >> 1))

        # Longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lng += (~(result >> 1) if (result & 1) else (result >> 1))

        coords.append([lng / 1e5, lat / 1e5])

    return coords


def _leg_to_segment(leg: dict) -> RouteSegment:
    """Convert an OTP leg dict to our RouteSegment model."""
    otp_mode = leg.get("mode", "WALK")
    mode = _OTP_MODE_MAP.get(otp_mode, RouteMode.WALKING)

    # Decode geometry
    encoded = leg.get("legGeometry", {}).get("points", "")
    if encoded:
        coordinates = _decode_polyline(encoded)
    else:
        coordinates = [
            [leg["from"]["lon"], leg["from"]["lat"]],
            [leg["to"]["lon"], leg["to"]["lat"]],
        ]

    geometry = {"type": "LineString", "coordinates": coordinates}

    distance_km = leg.get("distance", 0) / 1000
    duration_min = leg.get("duration", 0) / 60

    # Transit-specific info
    transit_line = None
    transit_route_id = None
    color = None

    if mode == RouteMode.TRANSIT:
        route_info = leg.get("route", "")
        agency_name = leg.get("agencyName", "")
        transit_line = f"{agency_name} {route_info}".strip() if agency_name else route_info
        transit_route_id = leg.get("routeId", None)

        # Determine color
        route_color = leg.get("routeColor")
        if route_color:
            color = f"#{route_color}" if not route_color.startswith("#") else route_color
        else:
            color = _AGENCY_COLORS.get(agency_name, _TRANSIT_MODE_COLORS.get(otp_mode, "#3b82f6"))

        instructions = f"Take {transit_line} from {leg['from'].get('name', '')} to {leg['to'].get('name', '')}"
    elif mode == RouteMode.WALKING:
        color = "#10B981"
        from_name = leg["from"].get("name", "")
        to_name = leg["to"].get("name", "")
        instructions = f"Walk from {from_name} to {to_name}" if from_name else "Walk"
    else:
        color = "#3B82F6"
        instructions = f"{otp_mode.title()} segment"

    return RouteSegment(
        mode=mode,
        geometry=geometry,
        distance_km=round(distance_km, 2),
        duration_min=round(duration_min, 1),
        instructions=instructions,
        transit_line=transit_line,
        transit_route_id=transit_route_id,
        color=color,
    )


def parse_otp_itinerary(
    itinerary: dict,
    predictor=None,
    weather: Optional[dict] = None,
    is_adverse: bool = False,
) -> RouteOption:
    """Convert an OTP itinerary into our RouteOption model.

    Adds delay prediction and cost calculation on top of OTP data.
    Accepts either a weather dict (preferred) or is_adverse bool (backward compat).
    """
    from app.cost_calculator import calculate_cost

    legs = itinerary.get("legs", [])
    segments = [_leg_to_segment(leg) for leg in legs]

    total_distance_km = sum(s.distance_km for s in segments)
    total_duration_min = itinerary.get("duration", 0) / 60

    # Count transfers
    transit_legs = [l for l in legs if _OTP_MODE_MAP.get(l.get("mode", ""), RouteMode.WALKING) == RouteMode.TRANSIT]
    transfers = max(0, len(transit_legs) - 1)

    # Determine dominant transit mode/agency for labeling
    agencies = set()
    transit_modes = set()
    for leg in legs:
        if leg.get("agencyName"):
            agencies.add(leg["agencyName"])
        if _OTP_MODE_MAP.get(leg.get("mode", "")) == RouteMode.TRANSIT:
            transit_modes.add(leg.get("mode", ""))

    # Resolve weather params
    if weather is None:
        weather = {}
    _is_adverse = weather.get("is_adverse", is_adverse)

    # Delay prediction (use first transit leg's line)
    delay_info = DelayInfo()
    now = datetime.now()
    if predictor and transit_legs:
        first_transit = transit_legs[0]
        line_for_pred = first_transit.get("routeShortName", "1")
        try:
            prediction = predictor.predict(
                line=line_for_pred,
                hour=now.hour,
                day_of_week=now.weekday(),
                month=now.month,
                temperature=weather.get("temperature"),
                precipitation=weather.get("precipitation"),
                snowfall=weather.get("snowfall"),
                wind_speed=weather.get("wind_speed"),
                is_adverse_weather=_is_adverse if not weather else None,
                mode=first_transit.get("mode", "SUBWAY").lower(), # Pass OTP mode (BUS, SUBWAY, TRAM)
            )
            delay_info = DelayInfo(
                probability=prediction["delay_probability"],
                expected_minutes=prediction["expected_delay_minutes"],
                confidence=prediction["confidence"],
                factors=prediction["contributing_factors"],
            )
        except Exception as e:
            logger.debug(f"Delay prediction failed for OTP route: {e}")

    # Stress score
    stress_score = 0.2 + transfers * 0.1 + delay_info.probability * 0.3
    if _is_adverse:
        stress_score += 0.1
    stress_score = min(1.0, stress_score)

    # Cost
    transit_dist = sum(s.distance_km for s in segments if s.mode == RouteMode.TRANSIT)
    cost = calculate_cost(RouteMode.TRANSIT, transit_dist)

    # Multi-agency cost adjustment (extra fare for cross-agency)
    if len(agencies) > 1:
        cost.fare = round(cost.fare + 3.35 * (len(agencies) - 1), 2)
        cost.total = round(cost.fare + cost.gas + cost.parking, 2)

    # Departure/arrival times
    start_time = itinerary.get("startTime")
    end_time = itinerary.get("endTime")
    dep_str = datetime.fromtimestamp(start_time / 1000).strftime("%H:%M") if start_time else now.strftime("%H:%M")
    arr_str = datetime.fromtimestamp(end_time / 1000).strftime("%H:%M") if end_time else None

    # Summary
    agency_str = " + ".join(sorted(agencies)) if agencies else "Transit"
    transfer_str = f", {transfers} transfer{'s' if transfers != 1 else ''}" if transfers > 0 else ""
    summary = f"{agency_str} — {total_distance_km:.1f} km, {total_duration_min:.0f} min{transfer_str}"

    return RouteOption(
        id=str(uuid.uuid4())[:8],
        label="",
        mode=RouteMode.TRANSIT,
        segments=segments,
        total_distance_km=round(total_distance_km, 2),
        total_duration_min=round(total_duration_min, 1),
        cost=cost,
        delay_info=delay_info,
        stress_score=round(stress_score, 2),
        departure_time=dep_str,
        arrival_time=arr_str,
        summary=summary,
    )
