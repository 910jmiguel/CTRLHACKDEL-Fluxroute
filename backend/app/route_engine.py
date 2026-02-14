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
    DirectionStep,
    RouteMode,
    RouteOption,
    RouteSegment,
)
from app.cost_calculator import calculate_cost
from app.gtfs_parser import find_nearest_stops, haversine, find_transit_route
from app.ml_predictor import DelayPredictor
from app.otp_client import query_otp_routes, parse_otp_itinerary
from app.weather import get_current_weather

logger = logging.getLogger("fluxroute.engine")

def _get_mapbox_token() -> str:
    return os.getenv("MAPBOX_TOKEN", "")
MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox"


def _parse_steps(legs: list[dict]) -> list[dict]:
    """Extract turn-by-turn steps from Mapbox legs."""
    steps = []
    for leg in legs:
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            steps.append({
                "instruction": maneuver.get("instruction", ""),
                "distance_km": round(step.get("distance", 0) / 1000, 2),
                "duration_min": round(step.get("duration", 0) / 60, 1),
                "maneuver_type": maneuver.get("type", ""),
                "maneuver_modifier": maneuver.get("modifier", ""),
            })
    return steps


def _parse_route(route_data: dict) -> dict:
    """Parse a single Mapbox route into our format."""
    legs = route_data.get("legs", [])
    return {
        "geometry": route_data["geometry"],
        "distance_km": route_data["distance"] / 1000,
        "duration_min": route_data["duration"] / 60,
        "steps": _parse_steps(legs),
    }


async def _mapbox_directions(
    origin: Coordinate,
    destination: Coordinate,
    profile: str = "driving-traffic",
    alternatives: bool = False,
) -> Optional[dict]:
    """Call Mapbox Directions API. Returns route data or None on failure."""
    token = _get_mapbox_token()
    if not token or token == "your-mapbox-token-here":
        logger.info(
            "Mapbox token missing or placeholder — falling back to straight-line geometry. "
            "Set MAPBOX_TOKEN in backend/.env"
        )
        return None

    # Request congestion annotations for driving-traffic profile
    annotations = "&annotations=congestion" if profile == "driving-traffic" else ""
    url = (
        f"{MAPBOX_DIRECTIONS_URL}/{profile}/"
        f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"
        f"?geometries=geojson&overview=full&steps=true{annotations}&access_token={token}"
    )
    if alternatives:
        url += "&alternatives=true"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        routes = data.get("routes", [])
        if not routes:
            logger.warning(
                "Mapbox returned 200 but empty routes array for %s: "
                "origin=(%s, %s) dest=(%s, %s)",
                profile, origin.lat, origin.lng, destination.lat, destination.lng,
            )
            return None

        route = routes[0]

        # Extract congestion data if available
        congestion = None
        congestion_level = None
        if route.get("legs"):
            leg = route["legs"][0]
            annotation = leg.get("annotation", {})
            congestion = annotation.get("congestion", [])
            if congestion:
                # Compute dominant congestion level
                levels = {"low": 0, "moderate": 0, "heavy": 0, "severe": 0, "unknown": 0}
                for c in congestion:
                    levels[c] = levels.get(c, 0) + 1
                total = sum(levels.values()) or 1
                if (levels["severe"] + levels["heavy"]) / total > 0.3:
                    congestion_level = "severe" if levels["severe"] > levels["heavy"] else "heavy"
                elif (levels["moderate"] + levels["heavy"] + levels["severe"]) / total > 0.4:
                    congestion_level = "moderate"
                else:
                    congestion_level = "low"

        result = _parse_route(route)
        result["congestion"] = congestion
        result["congestion_level"] = congestion_level

        # Include alternatives if requested and available
        if alternatives and len(routes) > 1:
            result["alternatives"] = [_parse_route(r) for r in routes[1:2]]

        return result
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Mapbox API HTTP error (%s): status=%s body=%s",
            profile, e.response.status_code, e.response.text[:300],
        )
        return None
    except Exception as e:
        logger.warning(f"Mapbox API call failed ({profile}): {e}")
        return None


def _straight_line_geometry(origin: Coordinate, destination: Coordinate) -> dict:
    """Generate straight-line GeoJSON fallback."""
    return {
        "type": "LineString",
        "coordinates": [
            [origin.lng, origin.lat],
            [destination.lng, destination.lat],
        ],
    }


def _estimate_duration(distance_km: float, mode: RouteMode) -> float:
    """Estimate duration in minutes based on mode and distance."""
    speeds = {
        RouteMode.WALKING: 5.0,
        RouteMode.CYCLING: 18.0,
        RouteMode.DRIVING: 30.0,
        RouteMode.TRANSIT: 25.0,
        RouteMode.HYBRID: 28.0,
    }
    speed = speeds.get(mode, 25.0)
    return (distance_km / speed) * 60


def _compute_congestion_summary(congestion_list: list[str]) -> tuple[str, str]:
    """Returns (dominant_level, traffic_label) from Mapbox congestion array."""
    if not congestion_list:
        return ("unknown", "Unknown Traffic")

    from collections import Counter
    counts = Counter(congestion_list)
    total = len(congestion_list)

    for level, label in [
        ("severe", "Severe Traffic"),
        ("heavy", "Heavy Traffic"),
        ("moderate", "Moderate Traffic"),
    ]:
        if counts.get(level, 0) / total > 0.3:
            return (level, label)

    return ("low", "Light Traffic")


def _congestion_stress_score(congestion_list: list[str]) -> float:
    """Convert congestion data into a stress score contribution (0.0 to 0.3)."""
    if not congestion_list:
        return 0.0

    weights = {"severe": 0.3, "heavy": 0.2, "moderate": 0.1, "low": 0.0, "unknown": 0.0}
    total = sum(weights.get(c, 0.0) for c in congestion_list)
    return total / len(congestion_list)


def _split_geometry_by_congestion(
    coordinates: list[list[float]], congestion_list: list[str]
) -> list[dict]:
    """Split a LineString into sub-segments grouped by congestion level.

    Mapbox returns one congestion value per coordinate pair (N-1 values for N coords).
    Groups consecutive coordinates with the same level into single sub-segments.
    """
    if not congestion_list or len(coordinates) < 2:
        return []

    segments = []
    current_level = congestion_list[0]
    current_coords = [coordinates[0]]

    for i, level in enumerate(congestion_list):
        current_coords.append(coordinates[i + 1])

        next_level = congestion_list[i + 1] if i + 1 < len(congestion_list) else None
        if next_level != current_level:
            segments.append({
                "geometry": {
                    "type": "LineString",
                    "coordinates": current_coords,
                },
                "congestion": current_level,
            })
            if next_level is not None:
                current_level = next_level
                current_coords = [coordinates[i + 1]]  # Overlap for continuity

    return segments


async def generate_routes(
    origin: Coordinate,
    destination: Coordinate,
    gtfs: dict,
    predictor: DelayPredictor,
    modes: Optional[list[RouteMode]] = None,
) -> list[RouteOption]:
    """Generate 3-4 route options for the given origin/destination."""
    if modes is None:
        modes = [RouteMode.TRANSIT, RouteMode.DRIVING, RouteMode.WALKING, RouteMode.HYBRID]

    total_distance = haversine(origin.lat, origin.lng, destination.lat, destination.lng)
    routes: list[RouteOption] = []

    # Get weather for delay prediction
    try:
        weather = await get_current_weather(origin.lat, origin.lng)
        is_adverse = weather.get("is_adverse", False)
    except Exception:
        is_adverse = False

    now = datetime.now()

    # Try OTP for transit routes first (multi-agency graph routing)
    otp_used = False
    if RouteMode.TRANSIT in modes:
        try:
            otp_itineraries = await query_otp_routes(origin, destination, now, num_itineraries=3)
            if otp_itineraries:
                otp_used = True
                for itin in otp_itineraries[:2]:  # Take best 2 OTP results
                    otp_route = parse_otp_itinerary(itin, predictor=predictor, is_adverse=is_adverse)
                    routes.append(otp_route)
                logger.info(f"OTP returned {len(otp_itineraries)} itineraries, used {min(2, len(otp_itineraries))}")
        except Exception as e:
            logger.warning(f"OTP query failed, falling back to heuristic: {e}")

    # Generate each mode
    for mode in modes:
        try:
            # Skip transit if OTP already handled it
            if mode == RouteMode.TRANSIT and otp_used:
                continue

            if mode == RouteMode.WALKING and total_distance > 5.0:
                continue  # Skip walking for long distances

            result = await _generate_single_route(
                origin, destination, mode, gtfs, predictor, total_distance, is_adverse, now
            )
            if result:
                if isinstance(result, list):
                    routes.extend(result)
                else:
                    routes.append(result)
        except Exception as e:
            logger.error(f"Failed to generate {mode} route: {e}")

    # Label routes
    _label_routes(routes)

    return routes


def _make_direction_steps(raw_steps: list[dict]) -> list[DirectionStep]:
    """Convert raw step dicts to DirectionStep models."""
    return [DirectionStep(**s) for s in raw_steps]


async def _generate_single_route(
    origin: Coordinate,
    destination: Coordinate,
    mode: RouteMode,
    gtfs: dict,
    predictor: DelayPredictor,
    total_distance: float,
    is_adverse: bool,
    now: datetime,
) -> Optional[RouteOption | list[RouteOption]]:
    """Generate route option(s). Driving may return a list with alternatives."""

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0
    delay_info = DelayInfo()
    stress_score = 0.0
    traffic_label = ""

    if mode == RouteMode.TRANSIT:
        return await _generate_transit_route(
            origin, destination, gtfs, predictor, total_distance, is_adverse, now
        )

    elif mode == RouteMode.DRIVING:
        mapbox = await _mapbox_directions(origin, destination, "driving-traffic", alternatives=True)

        if mapbox:
            geometry = mapbox["geometry"]
            total_dist = mapbox["distance_km"]
            total_duration = mapbox["duration_min"]
            steps = _make_direction_steps(mapbox.get("steps", []))
        else:
            geometry = _straight_line_geometry(origin, destination)
            total_dist = total_distance * 1.3
            total_duration = _estimate_duration(total_dist, RouteMode.DRIVING)
            steps = []

        # Extract raw congestion array and compute summary
        congestion_data = mapbox.get("congestion") if mapbox else None
        if congestion_data:
            congestion_level, traffic_label_text = _compute_congestion_summary(congestion_data)
            traffic_label = f" ({traffic_label_text})"
            # Split geometry into multi-colored sub-segments
            coords = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
            congestion_segments = _split_geometry_by_congestion(coords, congestion_data)
        else:
            congestion_level = None
            traffic_label = ""
            congestion_segments = None

        segments.append(RouteSegment(
            mode=RouteMode.DRIVING,
            geometry=geometry,
            distance_km=round(total_dist, 2),
            duration_min=round(total_duration, 1),
            instructions=f"Drive to destination{traffic_label}",
            color="#3B82F6",
            steps=steps,
            congestion_level=congestion_level,
            congestion_segments=congestion_segments,
        ))

        # Driving stress: use real congestion data if available, else rush-hour heuristic
        stress_score = 0.3
        if congestion_data:
            stress_score += _congestion_stress_score(congestion_data)
        elif 7 <= now.hour <= 9 or 17 <= now.hour <= 19:
            stress_score += 0.2
        if is_adverse:
            stress_score += 0.1

        cost = calculate_cost(RouteMode.DRIVING, total_dist, destination.lat, destination.lng)

        primary = RouteOption(
            id=str(uuid.uuid4())[:8],
            label="",
            mode=mode,
            segments=segments,
            total_distance_km=round(total_dist, 2),
            total_duration_min=round(total_duration, 1),
            cost=cost,
            delay_info=delay_info,
            stress_score=round(min(1.0, stress_score), 2),
            departure_time=now.strftime("%H:%M"),
            summary=f"Driving — {total_dist:.1f} km, {total_duration:.0f} min",
        )

        results: list[RouteOption] = [primary]

        # Build alternative driving routes if available
        if mapbox and mapbox.get("alternatives"):
            for alt in mapbox["alternatives"]:
                alt_dist = alt["distance_km"]
                alt_dur = alt["duration_min"]
                alt_steps = _make_direction_steps(alt.get("steps", []))
                alt_cost = calculate_cost(RouteMode.DRIVING, alt_dist, destination.lat, destination.lng)

                alt_option = RouteOption(
                    id=str(uuid.uuid4())[:8],
                    label="",
                    mode=RouteMode.DRIVING,
                    segments=[RouteSegment(
                        mode=RouteMode.DRIVING,
                        geometry=alt["geometry"],
                        distance_km=round(alt_dist, 2),
                        duration_min=round(alt_dur, 1),
                        instructions="Alternative driving route",
                        color="#60A5FA",
                        steps=alt_steps,
                    )],
                    total_distance_km=round(alt_dist, 2),
                    total_duration_min=round(alt_dur, 1),
                    cost=alt_cost,
                    delay_info=DelayInfo(),
                    stress_score=round(min(1.0, stress_score), 2),
                    departure_time=now.strftime("%H:%M"),
                    summary=f"Driving (alt) — {alt_dist:.1f} km, {alt_dur:.0f} min",
                )
                results.append(alt_option)

        return results

    elif mode == RouteMode.WALKING:
        mapbox = await _mapbox_directions(origin, destination, "walking")

        if mapbox:
            geometry = mapbox["geometry"]
            total_dist = mapbox["distance_km"]
            total_duration = mapbox["duration_min"]
            steps = _make_direction_steps(mapbox.get("steps", []))
        else:
            geometry = _straight_line_geometry(origin, destination)
            total_dist = total_distance * 1.2
            total_duration = _estimate_duration(total_dist, RouteMode.WALKING)
            steps = []

        segments.append(RouteSegment(
            mode=RouteMode.WALKING,
            geometry=geometry,
            distance_km=round(total_dist, 2),
            duration_min=round(total_duration, 1),
            instructions="Walk to destination",
            color="#10B981",
            steps=steps,
        ))

        stress_score = 0.1
        if is_adverse:
            stress_score += 0.3

        cost = calculate_cost(RouteMode.WALKING, total_dist)

    elif mode == RouteMode.HYBRID:
        return await _generate_hybrid_route(
            origin, destination, gtfs, predictor, total_distance, is_adverse, now
        )
    else:
        return None

    if mode not in (RouteMode.TRANSIT, RouteMode.HYBRID):
        # Generate traffic_summary for driving routes
        traffic_summary_text = ""
        if mode == RouteMode.DRIVING and congestion_data:
            _, traffic_summary_text = _compute_congestion_summary(congestion_data)

        return RouteOption(
            id=str(uuid.uuid4())[:8],
            label="",
            mode=mode,
            segments=segments,
            total_distance_km=round(total_dist, 2),
            total_duration_min=round(total_duration, 1),
            cost=cost,
            delay_info=delay_info,
            stress_score=round(min(1.0, stress_score), 2),
            departure_time=now.strftime("%H:%M"),
            summary=f"{mode.value.title()} — {total_dist:.1f} km, {total_duration:.0f} min{traffic_label if mode == RouteMode.DRIVING else ''}",
            traffic_summary=traffic_summary_text,
        )

    return None


async def _generate_transit_route(
    origin: Coordinate,
    destination: Coordinate,
    gtfs: dict,
    predictor: DelayPredictor,
    total_distance: float,
    is_adverse: bool,
    now: datetime,
) -> Optional[RouteOption]:
    """Generate a transit route with walking segments to/from stations."""
    # Find nearest stops to origin and destination
    origin_stops = find_nearest_stops(gtfs, origin.lat, origin.lng, radius_km=3.0, limit=3)
    dest_stops = find_nearest_stops(gtfs, destination.lat, destination.lng, radius_km=3.0, limit=3)

    if not origin_stops or not dest_stops:
        return None

    origin_stop = origin_stops[0]
    dest_stop = dest_stops[0]

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0

    # Walk to station
    walk_to_dist = origin_stop["distance_km"]
    walk_to_dur = _estimate_duration(walk_to_dist, RouteMode.WALKING)
    walk_to_geo = await _mapbox_directions(
        origin,
        Coordinate(lat=origin_stop["lat"], lng=origin_stop["lng"]),
        "walking"
    )

    segments.append(RouteSegment(
        mode=RouteMode.WALKING,
        geometry=walk_to_geo["geometry"] if walk_to_geo else _straight_line_geometry(
            origin, Coordinate(lat=origin_stop["lat"], lng=origin_stop["lng"])
        ),
        distance_km=round(walk_to_geo["distance_km"] if walk_to_geo else walk_to_dist, 2),
        duration_min=round(walk_to_geo["duration_min"] if walk_to_geo else walk_to_dur, 1),
        instructions=f"Walk to {origin_stop['stop_name']} station",
        color="#10B981",
        steps=_make_direction_steps(walk_to_geo.get("steps", [])) if walk_to_geo else [],
    ))
    total_duration += walk_to_geo["duration_min"] if walk_to_geo else walk_to_dur
    total_dist += walk_to_geo["distance_km"] if walk_to_geo else walk_to_dist

    # Transit segment
    transit_route = find_transit_route(gtfs, origin_stop["stop_id"], dest_stop["stop_id"])
    transit_dist = transit_route["distance_km"] if transit_route else haversine(
        origin_stop["lat"], origin_stop["lng"], dest_stop["lat"], dest_stop["lng"]
    )
    transit_dur = transit_route["estimated_duration_min"] if transit_route else _estimate_duration(transit_dist, RouteMode.TRANSIT)

    transit_geometry = (
        transit_route.get("geometry") if transit_route
        else _straight_line_geometry(
            Coordinate(lat=origin_stop["lat"], lng=origin_stop["lng"]),
            Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]),
        )
    )

    line_name = origin_stop.get("line") or (transit_route.get("line", "TTC Subway") if transit_route else "TTC Subway")
    route_id = origin_stop.get("route_id") or (transit_route.get("route_id") if transit_route else None)

    # Determine transit line color
    line_colors = {"1": "#FFCC00", "2": "#00A651", "4": "#A8518A", "5": "#FF6600", "6": "#8B4513"}
    color = line_colors.get(str(route_id), "#FFCC00")

    segments.append(RouteSegment(
        mode=RouteMode.TRANSIT,
        geometry=transit_geometry,
        distance_km=round(transit_dist, 2),
        duration_min=round(transit_dur, 1),
        instructions=f"Take {line_name} from {origin_stop['stop_name']} to {dest_stop['stop_name']}",
        transit_line=line_name,
        transit_route_id=str(route_id) if route_id else None,
        color=color,
    ))
    total_duration += transit_dur
    total_dist += transit_dist

    # Walk from station
    walk_from_dist = dest_stop["distance_km"]
    walk_from_dur = _estimate_duration(walk_from_dist, RouteMode.WALKING)
    walk_from_geo = await _mapbox_directions(
        Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]),
        destination,
        "walking"
    )

    segments.append(RouteSegment(
        mode=RouteMode.WALKING,
        geometry=walk_from_geo["geometry"] if walk_from_geo else _straight_line_geometry(
            Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]), destination
        ),
        distance_km=round(walk_from_geo["distance_km"] if walk_from_geo else walk_from_dist, 2),
        duration_min=round(walk_from_geo["duration_min"] if walk_from_geo else walk_from_dur, 1),
        instructions=f"Walk from {dest_stop['stop_name']} station to destination",
        color="#10B981",
        steps=_make_direction_steps(walk_from_geo.get("steps", [])) if walk_from_geo else [],
    ))
    total_duration += walk_from_geo["duration_min"] if walk_from_geo else walk_from_dur
    total_dist += walk_from_geo["distance_km"] if walk_from_geo else walk_from_dist

    # ML delay prediction
    line_for_pred = str(route_id) if route_id else "1"
    prediction = predictor.predict(
        line=line_for_pred,
        hour=now.hour,
        day_of_week=now.weekday(),
        month=now.month,
        is_adverse_weather=is_adverse,
    )

    delay_info = DelayInfo(
        probability=prediction["delay_probability"],
        expected_minutes=prediction["expected_delay_minutes"],
        confidence=prediction["confidence"],
        factors=prediction["contributing_factors"],
    )

    # Transit stress
    transfers = transit_route.get("transfers", 0) if transit_route else 0
    stress_score = 0.2 + transfers * 0.1 + prediction["delay_probability"] * 0.3

    cost = calculate_cost(RouteMode.TRANSIT, transit_dist)

    return RouteOption(
        id=str(uuid.uuid4())[:8],
        label="",
        mode=RouteMode.TRANSIT,
        segments=segments,
        total_distance_km=round(total_dist, 2),
        total_duration_min=round(total_duration, 1),
        cost=cost,
        delay_info=delay_info,
        stress_score=round(min(1.0, stress_score), 2),
        departure_time=now.strftime("%H:%M"),
        summary=f"Transit via {origin_stop['stop_name']} → {dest_stop['stop_name']}",
    )


async def _generate_hybrid_route(
    origin: Coordinate,
    destination: Coordinate,
    gtfs: dict,
    predictor: DelayPredictor,
    total_distance: float,
    is_adverse: bool,
    now: datetime,
) -> Optional[RouteOption]:
    """Generate a drive-to-station then transit route."""
    # Find stops near the destination
    dest_stops = find_nearest_stops(gtfs, destination.lat, destination.lng, radius_km=3.0, limit=3)
    if not dest_stops:
        return None

    dest_stop = dest_stops[0]

    # Find a strategic mid-point station (closer to origin for park & ride)
    origin_stops = find_nearest_stops(gtfs, origin.lat, origin.lng, radius_km=5.0, limit=5)
    if not origin_stops:
        return None

    # Pick a station that's not too close (want some driving)
    park_stop = None
    for stop in origin_stops:
        if stop["distance_km"] > 0.5:
            park_stop = stop
            break
    if not park_stop:
        park_stop = origin_stops[0]

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0

    # Drive to station
    drive_geo = await _mapbox_directions(
        origin,
        Coordinate(lat=park_stop["lat"], lng=park_stop["lng"]),
        "driving-traffic"
    )

    drive_dist = drive_geo["distance_km"] if drive_geo else haversine(origin.lat, origin.lng, park_stop["lat"], park_stop["lng"]) * 1.3
    drive_dur = drive_geo["duration_min"] if drive_geo else _estimate_duration(drive_dist, RouteMode.DRIVING)
    drive_congestion_data = drive_geo.get("congestion") if drive_geo else None
    drive_congestion = drive_geo.get("congestion_level") if drive_geo else None
    drive_congestion_segments = None

    if drive_congestion_data:
        drive_congestion, _ = _compute_congestion_summary(drive_congestion_data)
        drive_geom = drive_geo["geometry"] if drive_geo else None
        if drive_geom:
            coords = drive_geom.get("coordinates", [])
            drive_congestion_segments = _split_geometry_by_congestion(coords, drive_congestion_data)

    segments.append(RouteSegment(
        mode=RouteMode.DRIVING,
        geometry=drive_geo["geometry"] if drive_geo else _straight_line_geometry(
            origin, Coordinate(lat=park_stop["lat"], lng=park_stop["lng"])
        ),
        distance_km=round(drive_dist, 2),
        duration_min=round(drive_dur, 1),
        instructions=f"Drive to {park_stop['stop_name']} station (Park & Ride)",
        color="#3B82F6",
        steps=_make_direction_steps(drive_geo.get("steps", [])) if drive_geo else [],
        congestion_level=drive_congestion,
        congestion_segments=drive_congestion_segments,
    ))
    total_duration += drive_dur
    total_dist += drive_dist

    # Transit segment
    transit_route = find_transit_route(gtfs, park_stop["stop_id"], dest_stop["stop_id"])
    transit_dist = transit_route["distance_km"] if transit_route else haversine(
        park_stop["lat"], park_stop["lng"], dest_stop["lat"], dest_stop["lng"]
    )
    transit_dur = transit_route["estimated_duration_min"] if transit_route else _estimate_duration(transit_dist, RouteMode.TRANSIT)

    transit_geometry = (
        transit_route.get("geometry") if transit_route
        else _straight_line_geometry(
            Coordinate(lat=park_stop["lat"], lng=park_stop["lng"]),
            Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]),
        )
    )

    route_id = park_stop.get("route_id")
    line_colors = {"1": "#FFCC00", "2": "#00A651", "4": "#A8518A", "5": "#FF6600", "6": "#8B4513"}
    color = line_colors.get(str(route_id), "#FFCC00")

    segments.append(RouteSegment(
        mode=RouteMode.TRANSIT,
        geometry=transit_geometry,
        distance_km=round(transit_dist, 2),
        duration_min=round(transit_dur, 1),
        instructions=f"Take transit from {park_stop['stop_name']} to {dest_stop['stop_name']}",
        transit_line=park_stop.get("line", "TTC Subway"),
        transit_route_id=str(route_id) if route_id else None,
        color=color,
    ))
    total_duration += transit_dur
    total_dist += transit_dist

    # Walk from final station
    walk_dist = dest_stop["distance_km"]
    walk_dur = _estimate_duration(walk_dist, RouteMode.WALKING)
    walk_geo = await _mapbox_directions(
        Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]),
        destination,
        "walking"
    )

    segments.append(RouteSegment(
        mode=RouteMode.WALKING,
        geometry=walk_geo["geometry"] if walk_geo else _straight_line_geometry(
            Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]), destination
        ),
        distance_km=round(walk_geo["distance_km"] if walk_geo else walk_dist, 2),
        duration_min=round(walk_geo["duration_min"] if walk_geo else walk_dur, 1),
        instructions=f"Walk from {dest_stop['stop_name']} to destination",
        color="#10B981",
        steps=_make_direction_steps(walk_geo.get("steps", [])) if walk_geo else [],
    ))
    total_duration += walk_geo["duration_min"] if walk_geo else walk_dur
    total_dist += walk_geo["distance_km"] if walk_geo else walk_dist

    # Delay prediction
    line_for_pred = str(route_id) if route_id else "1"
    prediction = predictor.predict(
        line=line_for_pred,
        hour=now.hour,
        day_of_week=now.weekday(),
        month=now.month,
        is_adverse_weather=is_adverse,
    )

    delay_info = DelayInfo(
        probability=prediction["delay_probability"],
        expected_minutes=prediction["expected_delay_minutes"],
        confidence=prediction["confidence"],
        factors=prediction["contributing_factors"],
    )

    # Use real congestion for stress if available, else rush-hour heuristic
    stress_score = 0.25 + prediction["delay_probability"] * 0.2
    if drive_congestion_data:
        stress_score += _congestion_stress_score(drive_congestion_data)
    elif 7 <= now.hour <= 9 or 17 <= now.hour <= 19:
        stress_score += 0.1

    cost = calculate_cost(RouteMode.HYBRID, total_dist, destination.lat, destination.lng)

    # Traffic summary for hybrid driving segment
    hybrid_traffic = ""
    if drive_congestion_data:
        _, hybrid_traffic = _compute_congestion_summary(drive_congestion_data)

    return RouteOption(
        id=str(uuid.uuid4())[:8],
        label="",
        mode=RouteMode.HYBRID,
        segments=segments,
        total_distance_km=round(total_dist, 2),
        total_duration_min=round(total_duration, 1),
        cost=cost,
        delay_info=delay_info,
        stress_score=round(min(1.0, stress_score), 2),
        departure_time=now.strftime("%H:%M"),
        summary=f"Drive to {park_stop['stop_name']} → Transit to {dest_stop['stop_name']}",
        traffic_summary=hybrid_traffic,
    )


def _label_routes(routes: list[RouteOption]) -> None:
    """Label routes as Fastest, Cheapest, Zen based on their attributes."""
    if not routes:
        return

    fastest = min(routes, key=lambda r: r.total_duration_min)
    cheapest = min(routes, key=lambda r: r.cost.total)
    zen = min(routes, key=lambda r: r.stress_score)

    fastest.label = "Fastest"
    cheapest.label = "Thrifty" if cheapest.label != "Fastest" else cheapest.label
    zen.label = "Zen" if zen.label == "" else zen.label

    # Ensure all routes have a label
    for route in routes:
        if not route.label:
            if route.mode == RouteMode.HYBRID:
                route.label = "Balanced"
            elif route.mode == RouteMode.TRANSIT:
                route.label = "Transit"
            elif route.mode == RouteMode.DRIVING:
                route.label = "Drive"
            elif route.mode == RouteMode.WALKING:
                route.label = "Walk"
            else:
                route.label = route.mode.value.title()
