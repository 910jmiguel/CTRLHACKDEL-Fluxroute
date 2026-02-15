"""Centralized Mapbox API client for navigation services.

Covers: Directions API (full navigation params), Optimization API,
Isochrone API, and Map Matching API.
"""

import logging
import os
from typing import Optional

import httpx

from app.models import Coordinate, NavigationInstruction

logger = logging.getLogger("fluxroute.mapbox_nav")

MAPBOX_BASE = "https://api.mapbox.com"


def _get_token() -> str:
    return os.getenv("MAPBOX_TOKEN", "")


def _coords_string(coords: list[Coordinate]) -> str:
    """Convert list of Coordinates to Mapbox semicolon-separated string."""
    return ";".join(f"{c.lng},{c.lat}" for c in coords)


async def get_navigation_directions(
    origin: Coordinate,
    destination: Coordinate,
    waypoints: list[Coordinate] | None = None,
    profile: str = "driving-traffic",
    alternatives: bool = True,
    voice_instructions: bool = True,
    banner_instructions: bool = True,
    exclude: list[str] | None = None,
    depart_at: str | None = None,
    voice_locale: str = "en-US",
    http_client: Optional[httpx.AsyncClient] = None,
) -> Optional[list[dict]]:
    """Full navigation-grade Directions API call.

    Returns a list of route dicts (primary + alternatives), each containing
    geometry, distance, duration, steps with voice/banner/lane data, and
    congestion/speed/maxspeed annotations.
    """
    token = _get_token()
    if not token or token == "your-mapbox-token-here":
        logger.info("Mapbox token missing — cannot fetch navigation directions")
        return None

    all_coords = [origin] + (waypoints or []) + [destination]
    coords_str = _coords_string(all_coords)

    params: dict[str, str] = {
        "access_token": token,
        "geometries": "geojson",
        "overview": "full",
        "steps": "true",
        "alternatives": str(alternatives).lower(),
        "voice_instructions": str(voice_instructions).lower(),
        "banner_instructions": str(banner_instructions).lower(),
        "voice_units": "metric",
        "language": voice_locale[:2],
        "annotations": "congestion,speed,maxspeed,duration,distance",
    }

    if exclude:
        params["exclude"] = ",".join(exclude)
    if depart_at:
        params["depart_at"] = depart_at

    # Waypoints parameter (indices of via-points, excluding origin/destination)
    if waypoints:
        wp_indices = ";".join(str(i) for i in range(1, len(waypoints) + 1))
        params["waypoints"] = wp_indices

    url = f"{MAPBOX_BASE}/directions/v5/mapbox/{profile}/{coords_str}"

    try:
        if http_client:
            resp = await http_client.get(url, params=params, timeout=15.0)
        else:
            async with httpx.AsyncClient(timeout=15.0, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
                resp = await client.get(url, params=params)

        resp.raise_for_status()
        data = resp.json()

        routes = data.get("routes", [])
        if not routes:
            return None

        result = []
        for route in routes:
            parsed = _parse_navigation_route(route, voice_instructions, banner_instructions)
            result.append(parsed)

        return result

    except Exception as e:
        logger.warning(f"Navigation directions failed: {type(e).__name__}: {e}")
        return None


def _parse_navigation_route(
    route: dict,
    include_voice: bool = True,
    include_banner: bool = True,
) -> dict:
    """Parse a single Mapbox route into our enriched format."""
    geometry = route.get("geometry", {})
    distance_km = route.get("distance", 0) / 1000
    duration_min = route.get("duration", 0) / 60

    # Extract annotations from all legs
    congestion_all = []
    speed_all = []
    maxspeed_all = []

    steps = []
    navigation_instructions = []

    for leg in route.get("legs", []):
        annotation = leg.get("annotation", {})
        congestion_all.extend(annotation.get("congestion", []))
        speed_all.extend(annotation.get("speed", []))
        maxspeed_all.extend(annotation.get("maxspeed", []))

        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})

            step_data = {
                "instruction": maneuver.get("instruction", ""),
                "distance_km": round(step.get("distance", 0) / 1000, 2),
                "duration_min": round(step.get("duration", 0) / 60, 1),
                "maneuver_type": maneuver.get("type", ""),
                "maneuver_modifier": maneuver.get("modifier", ""),
            }
            steps.append(step_data)

            # Build NavigationInstruction
            nav_instr = {
                **step_data,
                "geometry": step.get("geometry"),
            }

            # Voice instructions (use last one in the step — closest to maneuver)
            if include_voice:
                voice_list = step.get("voiceInstructions", [])
                if voice_list:
                    last_voice = voice_list[-1]
                    nav_instr["voice_instruction"] = last_voice.get("announcement", "")

            # Banner instructions
            if include_banner:
                banner_list = step.get("bannerInstructions", [])
                if banner_list:
                    last_banner = banner_list[-1]
                    primary = last_banner.get("primary", {})
                    secondary = last_banner.get("secondary")
                    nav_instr["banner_primary"] = primary.get("text", "")
                    if secondary:
                        nav_instr["banner_secondary"] = secondary.get("text", "")

                    # Lane guidance from primary components
                    components = primary.get("components", [])
                    lanes = [c for c in components if c.get("type") == "lane"]
                    if lanes:
                        nav_instr["lane_guidance"] = lanes

            # Intersections may contain lane data
            intersections = step.get("intersections", [])
            if intersections and not nav_instr.get("lane_guidance"):
                last_intersection = intersections[-1]
                intersection_lanes = last_intersection.get("lanes", [])
                if intersection_lanes:
                    nav_instr["lane_guidance"] = intersection_lanes

            navigation_instructions.append(nav_instr)

    # Compute congestion summary
    congestion_level = None
    if congestion_all:
        levels = {"low": 0, "moderate": 0, "heavy": 0, "severe": 0, "unknown": 0}
        for c in congestion_all:
            levels[c] = levels.get(c, 0) + 1
        total = sum(levels.values()) or 1
        if (levels["severe"] + levels["heavy"]) / total > 0.3:
            congestion_level = "severe" if levels["severe"] > levels["heavy"] else "heavy"
        elif (levels["moderate"] + levels["heavy"] + levels["severe"]) / total > 0.4:
            congestion_level = "moderate"
        else:
            congestion_level = "low"

    # Extract speed limits from maxspeed annotations
    speed_limits = []
    for ms in maxspeed_all:
        if isinstance(ms, dict) and ms.get("speed"):
            speed_limits.append(ms["speed"])
        elif isinstance(ms, (int, float)):
            speed_limits.append(ms)

    return {
        "geometry": geometry,
        "distance_km": round(distance_km, 2),
        "duration_min": round(duration_min, 1),
        "congestion": congestion_all if congestion_all else None,
        "congestion_level": congestion_level,
        "speeds": speed_all if speed_all else None,
        "speed_limits": speed_limits if speed_limits else None,
        "steps": steps,
        "navigation_instructions": navigation_instructions,
    }


async def get_optimized_route(
    coordinates: list[Coordinate],
    profile: str = "driving",
    roundtrip: bool = False,
    source: str = "first",
    destination: str = "last",
    http_client: Optional[httpx.AsyncClient] = None,
) -> Optional[dict]:
    """Call Mapbox Optimization API for multi-stop route ordering.

    Returns optimized waypoint order and route geometry.
    """
    token = _get_token()
    if not token or token == "your-mapbox-token-here":
        return None

    if len(coordinates) < 2 or len(coordinates) > 12:
        logger.warning(f"Optimization requires 2-12 coordinates, got {len(coordinates)}")
        return None

    coords_str = _coords_string(coordinates)
    url = f"{MAPBOX_BASE}/optimized-trips/v1/mapbox/{profile}/{coords_str}"

    params = {
        "access_token": token,
        "geometries": "geojson",
        "overview": "full",
        "steps": "true",
        "roundtrip": str(roundtrip).lower(),
        "source": source,
        "destination": destination,
        "annotations": "duration,distance",
    }

    try:
        if http_client:
            resp = await http_client.get(url, params=params, timeout=15.0)
        else:
            async with httpx.AsyncClient(timeout=15.0, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
                resp = await client.get(url, params=params)

        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "Ok":
            logger.warning(f"Optimization API returned: {data.get('code')}")
            return None

        trips = data.get("trips", [])
        waypoints = data.get("waypoints", [])

        if not trips:
            return None

        trip = trips[0]
        waypoint_order = [wp.get("waypoint_index", i) for i, wp in enumerate(waypoints)]

        return {
            "geometry": trip.get("geometry", {}),
            "distance_km": round(trip.get("distance", 0) / 1000, 2),
            "duration_min": round(trip.get("duration", 0) / 60, 1),
            "waypoint_order": waypoint_order,
            "legs": trip.get("legs", []),
        }

    except Exception as e:
        logger.warning(f"Optimization API failed: {type(e).__name__}: {e}")
        return None


async def get_isochrone(
    center: Coordinate,
    profile: str = "driving",
    contours_minutes: list[int] | None = None,
    polygons: bool = True,
    http_client: Optional[httpx.AsyncClient] = None,
) -> Optional[dict]:
    """Call Mapbox Isochrone API for reachability polygons.

    Returns GeoJSON FeatureCollection of isochrone polygons/lines.
    """
    token = _get_token()
    if not token or token == "your-mapbox-token-here":
        return None

    if contours_minutes is None:
        contours_minutes = [10, 20, 30]

    url = f"{MAPBOX_BASE}/isochrone/v1/mapbox/{profile}/{center.lng},{center.lat}"

    params = {
        "access_token": token,
        "contours_minutes": ",".join(str(m) for m in contours_minutes),
        "polygons": str(polygons).lower(),
        "generalize": "500",  # Simplify geometry (meters)
    }

    try:
        if http_client:
            resp = await http_client.get(url, params=params, timeout=15.0)
        else:
            async with httpx.AsyncClient(timeout=15.0, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
                resp = await client.get(url, params=params)

        resp.raise_for_status()
        data = resp.json()

        if data.get("type") != "FeatureCollection":
            logger.warning(f"Isochrone API returned unexpected format: {data.get('type')}")
            return None

        return data

    except Exception as e:
        logger.warning(f"Isochrone API failed: {type(e).__name__}: {e}")
        return None


async def map_match(
    coordinates: list[Coordinate],
    profile: str = "driving",
    http_client: Optional[httpx.AsyncClient] = None,
) -> Optional[dict]:
    """Snap GPS trace to road network via Map Matching API.

    Useful for correcting noisy GPS positions during navigation.
    """
    token = _get_token()
    if not token or token == "your-mapbox-token-here":
        return None

    if len(coordinates) < 2 or len(coordinates) > 100:
        logger.warning(f"Map matching requires 2-100 coordinates, got {len(coordinates)}")
        return None

    coords_str = _coords_string(coordinates)
    url = f"{MAPBOX_BASE}/matching/v5/mapbox/{profile}/{coords_str}"

    params = {
        "access_token": token,
        "geometries": "geojson",
        "overview": "full",
        "steps": "true",
        "annotations": "speed,duration",
    }

    try:
        if http_client:
            resp = await http_client.get(url, params=params, timeout=15.0)
        else:
            async with httpx.AsyncClient(timeout=15.0, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
                resp = await client.get(url, params=params)

        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "Ok":
            logger.warning(f"Map Matching returned: {data.get('code')}")
            return None

        matchings = data.get("matchings", [])
        if not matchings:
            return None

        match = matchings[0]
        return {
            "geometry": match.get("geometry", {}),
            "distance_km": round(match.get("distance", 0) / 1000, 2),
            "duration_min": round(match.get("duration", 0) / 60, 1),
            "confidence": match.get("confidence", 0),
            "legs": match.get("legs", []),
        }

    except Exception as e:
        logger.warning(f"Map Matching failed: {type(e).__name__}: {e}")
        return None
