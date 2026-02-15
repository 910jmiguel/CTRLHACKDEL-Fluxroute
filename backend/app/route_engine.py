import asyncio
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
from app.cost_calculator import calculate_cost, calculate_hybrid_cost
from app.gtfs_parser import find_nearest_stops, find_nearest_rapid_transit_stations, haversine, find_transit_route
from app.ml_predictor import DelayPredictor
from app.models import ParkingInfo
from app.otp_client import query_otp_routes, parse_otp_itinerary, find_park_and_ride_stations
from app.parking_data import get_parking_info, find_stations_with_parking
from app.weather import get_current_weather

logger = logging.getLogger("fluxroute.engine")

def _get_mapbox_token() -> str:
    return os.getenv("MAPBOX_TOKEN", "")
MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox"


async def _mapbox_directions(
    origin: Coordinate,
    destination: Coordinate,
    profile: str = "driving-traffic",
    http_client: Optional[httpx.AsyncClient] = None,
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

    try:
        if http_client:
            resp = await http_client.get(url, timeout=8.0)
            resp.raise_for_status()
            data = resp.json()
        else:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

        routes = data.get("routes", [])
        if not routes:
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

        # Extract turn-by-turn steps
        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                maneuver = step.get("maneuver", {})
                steps.append({
                    "instruction": maneuver.get("instruction", ""),
                    "distance_km": round(step.get("distance", 0) / 1000, 2),
                    "duration_min": round(step.get("duration", 0) / 60, 1),
                    "maneuver_type": maneuver.get("type", ""),
                    "maneuver_modifier": maneuver.get("modifier", ""),
                })

        return {
            "geometry": route["geometry"],
            "distance_km": route["distance"] / 1000,
            "duration_min": route["duration"] / 60,
            "congestion": congestion,
            "congestion_level": congestion_level,
            "steps": steps,
        }
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


def _make_direction_steps(raw_steps: list[dict]) -> list[DirectionStep]:
    """Convert raw step dicts to DirectionStep models."""
    return [DirectionStep(**s) for s in raw_steps]


async def _fetch_weather_full(lat: float, lng: float, http_client=None) -> dict:
    """Fetch full weather data. Returns defaults on failure."""
    try:
        weather = await get_current_weather(lat, lng, http_client=http_client)
        return weather
    except Exception:
        return {
            "temperature": 5.0, "precipitation": 0.0, "snowfall": 0.0,
            "wind_speed": 15.0, "is_adverse": False,
        }


async def _fetch_otp(origin, destination, now, modes, otp_available, http_client=None):
    """Query OTP if available. Returns (otp_used, otp_routes) tuple."""
    if RouteMode.TRANSIT not in modes or not otp_available:
        if RouteMode.TRANSIT in modes and not otp_available:
            logger.info("OTP not available — skipping (using heuristic transit routing)")
        return False, []

    try:
        otp_itineraries = await query_otp_routes(
            origin, destination, now, num_itineraries=3, http_client=http_client
        )
        if otp_itineraries:
            logger.info(f"OTP returned {len(otp_itineraries)} itineraries")
            return True, otp_itineraries
    except Exception as e:
        logger.warning(f"OTP query failed, falling back to heuristic: {e}")

    return False, []


async def generate_routes(
    origin: Coordinate,
    destination: Coordinate,
    gtfs: dict,
    predictor: DelayPredictor,
    modes: Optional[list[RouteMode]] = None,
    app_state: Optional[dict] = None,
) -> list[RouteOption]:
    """Generate 3-4 route options for the given origin/destination."""
    if modes is None:
        modes = [RouteMode.TRANSIT, RouteMode.DRIVING, RouteMode.WALKING, RouteMode.HYBRID]

    total_distance = haversine(origin.lat, origin.lng, destination.lat, destination.lng)
    routes: list[RouteOption] = []
    now = datetime.now()

    # Get shared http client for connection pooling (falls back to per-call clients)
    http_client = (app_state or {}).get("http_client")
    otp_available = (app_state or {}).get("otp_available", False)

    # Phase 1: Fetch weather + OTP concurrently (instead of sequentially)
    weather_task = _fetch_weather_full(origin.lat, origin.lng, http_client=http_client)
    otp_task = _fetch_otp(origin, destination, now, modes, otp_available, http_client=http_client)
    weather, (otp_used, otp_itineraries) = await asyncio.gather(weather_task, otp_task)
    is_adverse = weather.get("is_adverse", False)

    # Process OTP results
    if otp_used:
        for itin in otp_itineraries[:2]:  # Take best 2 OTP results
            otp_route = parse_otp_itinerary(itin, predictor=predictor, weather=weather)
            routes.append(otp_route)
        logger.info(f"Used {min(2, len(otp_itineraries))} OTP itineraries")

    # Phase 2: Build and run route tasks in parallel
    tasks = []
    hybrid_task = None
    for mode in modes:
        if mode == RouteMode.TRANSIT and otp_used:
            continue
        if mode == RouteMode.WALKING and total_distance > 5.0:
            continue
        if mode == RouteMode.HYBRID:
            # Hybrid returns a list of routes — handle separately
            hybrid_task = _generate_hybrid_routes(
                origin, destination, gtfs, predictor, total_distance, is_adverse, now,
                http_client=http_client,
                otp_available=otp_available,
                app_state=app_state,
            )
            continue
        tasks.append(_generate_single_route(
            origin, destination, mode, gtfs, predictor, total_distance, is_adverse, now,
            http_client=http_client,
        ))

    # Run single-mode routes + hybrid in parallel
    if hybrid_task:
        tasks.append(hybrid_task)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            import traceback
            logger.error(f"Route generation failed: {result}\n{''.join(traceback.format_exception(type(result), result, result.__traceback__))}")
        elif isinstance(result, list):
            # Hybrid routes return a list
            routes.extend(result)
        elif result:
            routes.append(result)

    # Label routes
    _label_routes(routes)

    return routes


async def _generate_single_route(
    origin: Coordinate,
    destination: Coordinate,
    mode: RouteMode,
    gtfs: dict,
    predictor: DelayPredictor,
    total_distance: float,
    is_adverse: bool,
    now: datetime,
    http_client=None,
) -> Optional[RouteOption]:
    """Generate a single route option."""

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0
    delay_info = DelayInfo()
    stress_score = 0.0
    traffic_label = ""

    if mode == RouteMode.TRANSIT:
        return await _generate_transit_route(
            origin, destination, gtfs, predictor, total_distance, is_adverse, now,
            http_client=http_client,
        )

    elif mode == RouteMode.DRIVING:
        mapbox = await _mapbox_directions(origin, destination, "driving-traffic", http_client=http_client)

        if mapbox:
            geometry = mapbox["geometry"]
            total_dist = mapbox["distance_km"]
            total_duration = mapbox["duration_min"]
            steps = _make_direction_steps(mapbox.get("steps", []))
        else:
            geometry = _straight_line_geometry(origin, destination)
            total_dist = total_distance * 1.3  # Roads are ~30% longer than straight line
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

    elif mode == RouteMode.WALKING:
        mapbox = await _mapbox_directions(origin, destination, "walking", http_client=http_client)

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
        # Hybrid is handled by _generate_hybrid_routes() in the main pipeline
        return None
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
    http_client=None,
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

    # Walk to station + walk from station — run in PARALLEL
    walk_to_dist = origin_stop["distance_km"]
    walk_to_dur = _estimate_duration(walk_to_dist, RouteMode.WALKING)
    walk_from_dist = dest_stop["distance_km"]
    walk_from_dur = _estimate_duration(walk_from_dist, RouteMode.WALKING)

    walk_to_geo, walk_from_geo = await asyncio.gather(
        _mapbox_directions(
            origin,
            Coordinate(lat=origin_stop["lat"], lng=origin_stop["lng"]),
            "walking",
            http_client=http_client,
        ),
        _mapbox_directions(
            Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]),
            destination,
            "walking",
            http_client=http_client,
        ),
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

    # Walk from station (already fetched above in parallel)
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

    # ML delay prediction with granular weather
    line_for_pred = str(route_id) if route_id else "1"
    
    # Determine mode string for predictor
    pred_mode = "subway"
    if str(route_id) in ["5", "6"]:
        pred_mode = "streetcar" # LRT treated as streetcar/surface for now
    elif len(str(route_id)) > 1 and str(route_id) not in ["1", "2", "4"]:
        # Heuristic: 3-digit routes are bus/streetcar. 
        # But we need to distinguish bus vs streetcar if possible.
        # For now, default to bus for non-subway, unless it's a known streetcar line.
        # Streetcars: 501, 503, 504, 505, 506, 509, 510, 511, 512, 301, 304, etc.
        rt_str = str(route_id)
        if rt_str.startswith("5") and len(rt_str) == 3:
             pred_mode = "streetcar"
        elif rt_str.startswith("3") and len(rt_str) == 3 and int(rt_str) < 320:
             # Night streetcars usually low 300s
             pred_mode = "streetcar"
        else:
             pred_mode = "bus"

    prediction = predictor.predict(
        line=line_for_pred,
        hour=now.hour,
        day_of_week=now.weekday(),
        month=now.month,
        is_adverse_weather=is_adverse,
        mode=pred_mode,
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


def _check_line_disruption(alerts: list, line_name: str) -> tuple[bool, str]:
    """Check if a transit line has active disruptions.

    Returns (is_disrupted, reason).
    Alerts can be ServiceAlert Pydantic models or plain dicts.
    """
    if not alerts or not line_name:
        return False, ""

    line_lower = line_name.lower()
    # Build search terms from line name
    search_terms = [line_lower]
    parts = line_lower.split()
    for p in parts:
        if len(p) > 2:
            search_terms.append(p)

    for alert in alerts:
        # Support both Pydantic models and dicts
        if hasattr(alert, "active"):
            active = alert.active
            title = (alert.title or "").lower()
            desc = (alert.description or "").lower()
            severity = alert.severity or "info"
            title_raw = alert.title or "Service disruption"
        else:
            active = alert.get("active", True)
            title = (alert.get("title", "") or "").lower()
            desc = (alert.get("description", "") or "").lower()
            severity = alert.get("severity", "info")
            title_raw = alert.get("title", "Service disruption")

        if not active:
            continue

        # Only consider warnings and errors as disruptions
        if severity not in ("warning", "error"):
            continue

        text = f"{title} {desc}"
        for term in search_terms:
            if term in text:
                return True, title_raw

    return False, ""


def _score_park_and_ride_candidate(
    origin: Coordinate,
    destination: Coordinate,
    station_lat: float,
    station_lng: float,
    total_distance: float,
    has_parking: bool = False,
    is_disrupted: bool = False,
    next_departure_min: int | None = None,
    is_go: bool = False,
    now: Optional[datetime] = None,
) -> float:
    """Score a park-and-ride station candidate by strategic value.

    Higher score = better candidate. Considers:
    - Station is between origin and destination (reduces backtracking)
    - Drive ratio ~20-40% of total distance (sweet spot)
    - Parking availability bonus
    - Service disruption penalty
    - Frequent service bonus
    - TTC priority over GO (subway runs all day, GO is limited)
    - Weekend/off-hours GO penalty (many GO lines don't run)
    """
    drive_dist = haversine(origin.lat, origin.lng, station_lat, station_lng)
    transit_dist = haversine(station_lat, station_lng, destination.lat, destination.lng)

    # Penalize if station too close (< 0.5km — pointless to drive)
    if drive_dist < 0.5:
        return -1.0

    # Penalize if station is farther from destination than origin is
    if transit_dist > total_distance * 1.1:
        return -0.5

    # Drive ratio (ideal: 20-40% of total distance)
    drive_ratio = drive_dist / max(total_distance, 0.1)
    if 0.15 <= drive_ratio <= 0.5:
        ratio_score = 1.0
    elif drive_ratio < 0.15:
        ratio_score = drive_ratio / 0.15  # Too close
    else:
        ratio_score = max(0, 1.0 - (drive_ratio - 0.5))  # Too far

    # Direction score: is station between origin and destination?
    total_via = drive_dist + transit_dist
    detour_ratio = total_via / max(total_distance, 0.1)
    direction_score = max(0, 2.0 - detour_ratio)  # Best when ~1.0

    base_score = ratio_score * 0.4 + direction_score * 0.4

    # Parking bonus
    if has_parking:
        base_score += 0.3

    # TTC subway priority: runs frequently all day, every day
    if not is_go:
        base_score += 0.15  # TTC bonus

    # GO Transit: check weekend/off-hours — most GO lines have limited service
    if is_go and now:
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
        hour = now.hour
        # GO trains typically run: weekday peak 6-10am, 3-8pm
        # Weekend service is very limited (some lines don't run at all)
        if is_weekend:
            base_score -= 0.4  # Strong weekend penalty
        elif hour < 6 or hour > 22:
            base_score -= 0.3  # Late night — no GO service
        elif 10 <= hour <= 15:
            base_score -= 0.1  # Midday — reduced GO frequency

    # Service disruption penalty
    if is_disrupted:
        base_score -= 0.5

    # Frequent service bonus
    if next_departure_min is not None:
        if next_departure_min <= 10:
            base_score += 0.2
        elif next_departure_min <= 20:
            base_score += 0.1
        elif next_departure_min > 45:
            base_score -= 0.3  # Very infrequent — penalize

    return base_score


async def _generate_hybrid_routes(
    origin: Coordinate,
    destination: Coordinate,
    gtfs: dict,
    predictor: DelayPredictor,
    total_distance: float,
    is_adverse: bool,
    now: datetime,
    http_client=None,
    otp_available: bool = False,
    app_state: Optional[dict] = None,
) -> list[RouteOption]:
    """Generate 1-3 hybrid (drive + transit) routes via multiple station candidates.

    Uses rapid transit stations only (no bus stops), with parking verification
    and service alert awareness.
    """
    alerts = (app_state or {}).get("alerts", [])

    # --- 1. Gather station candidates (rapid transit only) ---
    # TTC subway/LRT stations from GTFS (filtered to route_type 0/1/2)
    # Use 25km radius to cover suburban origins (e.g. Richmond Hill → Finch is 11km)
    gtfs_stops = find_nearest_rapid_transit_stations(
        gtfs, origin.lat, origin.lng, radius_km=25.0, limit=15
    )
    gtfs_stops = [s for s in gtfs_stops if s["distance_km"] > 0.5]

    # GO/rail stations from OTP index (if available) — wider radius
    otp_stations = []
    if otp_available and http_client:
        try:
            otp_stations = await find_park_and_ride_stations(
                origin.lat, origin.lng, radius_km=20.0, http_client=http_client,
            )
        except Exception as e:
            logger.warning(f"OTP station search failed: {e}")

    # Parking-only stations from hardcoded database (catches GO stations OTP might miss)
    parking_stations = find_stations_with_parking(
        origin.lat, origin.lng, radius_km=20.0
    )

    # Merge candidates — normalize format
    candidates = []
    seen_names = set()

    for stop in gtfs_stops:
        name = stop["stop_name"]
        if name in seen_names:
            continue
        seen_names.add(name)

        parking = get_parking_info(name)
        candidates.append({
            "stop_id": stop["stop_id"],
            "stop_name": name,
            "lat": stop["lat"],
            "lng": stop["lng"],
            "route_id": stop.get("route_id"),
            "line": stop.get("line", "TTC Subway"),
            "agencyName": "TTC",
            "is_go": False,
            "parking": parking,
        })

    for stop in otp_stations:
        name = stop["stop_name"]
        if name in seen_names:
            continue
        seen_names.add(name)

        parking = get_parking_info(name)
        is_go = stop.get("mode") == "RAIL" and stop.get("agencyName", "").startswith("GO")
        candidates.append({
            "stop_id": stop["stop_id"],
            "stop_name": name,
            "lat": stop["lat"],
            "lng": stop["lng"],
            "route_id": None,
            "line": f"{stop.get('agencyName', 'GO')} {stop.get('mode', 'Rail')}",
            "agencyName": stop.get("agencyName", "GO Transit"),
            "is_go": is_go,
            "parking": parking,
        })

    # Add parking-database stations not already covered
    for ps in parking_stations:
        name = ps["station_name"]
        if name in seen_names:
            continue
        seen_names.add(name)

        is_go = ps.get("agency", "") == "GO Transit"
        candidates.append({
            "stop_id": f"parking_{name.replace(' ', '_')}",
            "stop_name": name,
            "lat": ps["lat"],
            "lng": ps["lng"],
            "route_id": None,
            "line": "GO Transit Rail" if is_go else "TTC Subway",
            "agencyName": ps.get("agency", "TTC"),
            "is_go": is_go,
            "parking": ps,
        })

    if not candidates:
        logger.info("No hybrid station candidates found")
        return []

    # --- 2. Score and rank candidates ---
    from app.gtfs_parser import get_next_departures

    scored = []
    for c in candidates:
        has_parking = c.get("parking") is not None
        line_name = c.get("line", "")
        is_disrupted, _ = _check_line_disruption(alerts, line_name)

        # Check next departure for service frequency
        next_dep_min = None
        departures = get_next_departures(gtfs, c["stop_id"], limit=1)
        if departures:
            next_dep_min = departures[0].get("minutes_until")

        score = _score_park_and_ride_candidate(
            origin, destination, c["lat"], c["lng"], total_distance,
            has_parking=has_parking,
            is_disrupted=is_disrupted,
            next_departure_min=next_dep_min,
            is_go=c.get("is_go", False),
            now=now,
        )
        if score > 0:
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Ensure diversity: at least 1 TTC and 1 GO (if available)
    ttc_picks = [c for _, c in scored if not c["is_go"]]
    go_picks = [c for _, c in scored if c["is_go"]]

    max_candidates = min(5, len(scored))
    top_candidates = []
    # Take best overall
    for _, c in scored:
        if len(top_candidates) >= max_candidates:
            break
        top_candidates.append(c)

    # Ensure at least 1 TTC if available and not already included
    if ttc_picks and not any(not c["is_go"] for c in top_candidates):
        top_candidates[-1] = ttc_picks[0]

    # Ensure at least 1 GO if available and not already included
    if go_picks and not any(c["is_go"] for c in top_candidates):
        if len(top_candidates) >= 2:
            top_candidates[-1] = go_picks[0]
        else:
            top_candidates.append(go_picks[0])

    if not top_candidates:
        logger.info("No viable hybrid station candidates after scoring")
        return []

    logger.info(f"Hybrid routing: {len(top_candidates)} candidates — {[c['stop_name'] for c in top_candidates]}")

    # --- 3. Generate routes for top candidates in parallel ---
    route_tasks = [
        _build_single_hybrid_route(
            origin, destination, candidate, gtfs, predictor,
            is_adverse, now, http_client, otp_available,
        )
        for candidate in top_candidates
    ]

    results = await asyncio.gather(*route_tasks, return_exceptions=True)

    hybrid_routes = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Hybrid route generation failed: {result}")
        elif result:
            hybrid_routes.append(result)

    return hybrid_routes


async def _build_single_hybrid_route(
    origin: Coordinate,
    destination: Coordinate,
    park_stop: dict,
    gtfs: dict,
    predictor: DelayPredictor,
    is_adverse: bool,
    now: datetime,
    http_client=None,
    otp_available: bool = False,
) -> Optional[RouteOption]:
    """Build a single hybrid route via a specific park-and-ride station."""

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0

    station_coord = Coordinate(lat=park_stop["lat"], lng=park_stop["lng"])

    # --- Drive to station (Mapbox driving-traffic) ---
    drive_geo = await _mapbox_directions(
        origin, station_coord, "driving-traffic", http_client=http_client,
    )

    drive_dist = drive_geo["distance_km"] if drive_geo else haversine(origin.lat, origin.lng, park_stop["lat"], park_stop["lng"]) * 1.3
    drive_dur = drive_geo["duration_min"] if drive_geo else _estimate_duration(drive_dist, RouteMode.DRIVING)
    drive_congestion_data = drive_geo.get("congestion") if drive_geo else None
    drive_congestion = None
    drive_congestion_segments = None

    if drive_congestion_data:
        drive_congestion, _ = _compute_congestion_summary(drive_congestion_data)
        drive_geom = drive_geo["geometry"] if drive_geo else None
        if drive_geom:
            coords = drive_geom.get("coordinates", [])
            drive_congestion_segments = _split_geometry_by_congestion(coords, drive_congestion_data)

    segments.append(RouteSegment(
        mode=RouteMode.DRIVING,
        geometry=drive_geo["geometry"] if drive_geo else _straight_line_geometry(origin, station_coord),
        distance_km=round(drive_dist, 2),
        duration_min=round(drive_dur, 1),
        instructions=f"Drive to {park_stop['stop_name']} (Park & Ride)",
        color="#3B82F6",
        steps=_make_direction_steps(drive_geo.get("steps", [])) if drive_geo else [],
        congestion_level=drive_congestion,
        congestion_segments=drive_congestion_segments,
    ))
    total_duration += drive_dur
    total_dist += drive_dist

    # --- Transit leg: use OTP if available, else heuristic ---
    transit_segments = []
    transit_dist = 0.0
    transit_dur = 0.0
    transit_label = park_stop.get("line", "Transit")
    route_id = park_stop.get("route_id")
    includes_go = park_stop.get("is_go", False)

    if otp_available and http_client:
        try:
            otp_itineraries = await query_otp_routes(
                station_coord, destination, now, num_itineraries=1, http_client=http_client,
            )
            if otp_itineraries:
                itin = otp_itineraries[0]
                otp_route = parse_otp_itinerary(itin, predictor=predictor, is_adverse=is_adverse)
                # Use OTP segments directly (includes walking + transit)
                transit_segments = otp_route.segments
                transit_dist = otp_route.total_distance_km
                transit_dur = otp_route.total_duration_min
                # Extract label from OTP route
                transit_label = otp_route.summary
                logger.debug(f"Hybrid OTP transit leg: {transit_label}")
        except Exception as e:
            logger.warning(f"OTP transit leg failed for hybrid via {park_stop['stop_name']}: {e}")

    if not transit_segments:
        # Heuristic fallback
        dest_stops = find_nearest_stops(gtfs, destination.lat, destination.lng, radius_km=3.0, limit=3)
        dest_stop = dest_stops[0] if dest_stops else None

        if not dest_stop:
            # Can't build transit leg — straight-line fallback
            transit_dist = haversine(park_stop["lat"], park_stop["lng"], destination.lat, destination.lng)
            transit_dur = _estimate_duration(transit_dist, RouteMode.TRANSIT)
            transit_segments = [RouteSegment(
                mode=RouteMode.TRANSIT,
                geometry=_straight_line_geometry(station_coord, destination),
                distance_km=round(transit_dist, 2),
                duration_min=round(transit_dur, 1),
                instructions=f"Take transit to destination",
                transit_line=transit_label,
                color="#FFCC00",
            )]
        else:
            # Build heuristic transit + walk segments
            transit_route = find_transit_route(gtfs, park_stop["stop_id"], dest_stop["stop_id"])
            transit_dist = transit_route["distance_km"] if transit_route else haversine(
                park_stop["lat"], park_stop["lng"], dest_stop["lat"], dest_stop["lng"]
            )
            transit_dur = transit_route["estimated_duration_min"] if transit_route else _estimate_duration(transit_dist, RouteMode.TRANSIT)

            transit_geometry = (
                transit_route.get("geometry") if transit_route
                else _straight_line_geometry(station_coord, Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]))
            )

            line_colors = {"1": "#FFCC00", "2": "#00A651", "4": "#A8518A", "5": "#FF6600", "6": "#8B4513"}
            color = line_colors.get(str(route_id), "#FFCC00")

            transit_segments.append(RouteSegment(
                mode=RouteMode.TRANSIT,
                geometry=transit_geometry,
                distance_km=round(transit_dist, 2),
                duration_min=round(transit_dur, 1),
                instructions=f"Take {transit_label} from {park_stop['stop_name']} to {dest_stop['stop_name']}",
                transit_line=transit_label,
                transit_route_id=str(route_id) if route_id else None,
                color=color,
            ))

            # Walk from final station
            walk_dist = dest_stop["distance_km"]
            walk_dur = _estimate_duration(walk_dist, RouteMode.WALKING)
            walk_geo = await _mapbox_directions(
                Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"]),
                destination, "walking", http_client=http_client,
            )
            transit_segments.append(RouteSegment(
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
            transit_dist += walk_geo["distance_km"] if walk_geo else walk_dist
            transit_dur += walk_geo["duration_min"] if walk_geo else walk_dur

    segments.extend(transit_segments)
    total_duration += transit_dur
    total_dist += transit_dist

    # --- Delay prediction ---
    line_for_pred = str(route_id) if route_id else "1"
    
    # Determine mode string for predictor (Hybrid uses the transit part's mode)
    pred_mode = "subway"
    rt_str = str(route_id) if route_id else ""
    if rt_str in ["5", "6"]:
        pred_mode = "streetcar"
    elif len(rt_str) > 1 and rt_str not in ["1", "2", "4"]:
        if rt_str.startswith("5") and len(rt_str) == 3:
             pred_mode = "streetcar"
        elif rt_str.startswith("3") and len(rt_str) == 3 and int(rt_str) < 320:
             pred_mode = "streetcar"
        else:
             pred_mode = "bus"

    prediction = predictor.predict(
        line=line_for_pred,
        hour=now.hour,
        day_of_week=now.weekday(),
        month=now.month,
        is_adverse_weather=is_adverse,
        mode=pred_mode,
    )

    delay_info = DelayInfo(
        probability=prediction["delay_probability"],
        expected_minutes=prediction["expected_delay_minutes"],
        confidence=prediction["confidence"],
        factors=prediction["contributing_factors"],
    )

    # --- Stress score ---
    stress_score = 0.25 + prediction["delay_probability"] * 0.2
    if drive_congestion_data:
        stress_score += _congestion_stress_score(drive_congestion_data)
    elif 7 <= now.hour <= 9 or 17 <= now.hour <= 19:
        stress_score += 0.1

    # --- Parking info ---
    parking = park_stop.get("parking")
    parking_rate = None
    parking_info_model = None
    if parking:
        parking_rate = parking.get("daily_rate", 0.0)
        parking_info_model = ParkingInfo(
            station_name=parking.get("station_name", park_stop["stop_name"]),
            daily_rate=parking_rate,
            capacity=parking.get("capacity", 0),
            parking_type=parking.get("type", ""),
            agency=parking.get("agency", park_stop.get("agencyName", "")),
        )

    # --- Cost (using actual distances + real parking rate) ---
    cost = calculate_hybrid_cost(
        drive_distance_km=drive_dist,
        transit_distance_km=transit_dist,
        includes_go=includes_go,
        parking_type="station",
        parking_rate=parking_rate,
    )

    # Traffic summary
    hybrid_traffic = ""
    if drive_congestion_data:
        _, hybrid_traffic = _compute_congestion_summary(drive_congestion_data)

    station_name = park_stop["stop_name"]
    label_prefix = f"GO {station_name}" if includes_go else station_name

    # Build parking note for summary
    parking_note = ""
    if parking_info_model:
        rate_str = "Free" if parking_info_model.daily_rate == 0 else f"${parking_info_model.daily_rate:.0f}/day"
        parking_note = f" ({rate_str} parking)"

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
        summary=f"Park & Ride via {label_prefix} — {total_dist:.1f} km, {total_duration:.0f} min{parking_note}",
        traffic_summary=hybrid_traffic,
        parking_info=parking_info_model,
    )


def _label_routes(routes: list[RouteOption]) -> None:
    """Label routes by mode with descriptive names."""
    if not routes:
        return

    hybrid_count = 0
    for route in routes:
        if route.label:
            continue

        if route.mode == RouteMode.DRIVING:
            route.label = "Direct Drive"
        elif route.mode == RouteMode.WALKING:
            route.label = "Walk"
        elif route.mode == RouteMode.TRANSIT:
            # Extract main transit line from segments
            transit_segs = [s for s in route.segments if s.transit_line]
            if transit_segs:
                main_line = transit_segs[0].transit_line or "Transit"
                route.label = f"Transit via {main_line}"
            else:
                route.label = "Transit"
        elif route.mode == RouteMode.HYBRID:
            summary = route.summary or ""
            if "via " in summary:
                station = summary.split("via ")[1].split(" —")[0].strip()
                route.label = f"Park & Ride ({station})"
            else:
                hybrid_count += 1
                route.label = f"Park & Ride {hybrid_count}" if hybrid_count > 1 else "Park & Ride"
        else:
            route.label = route.mode.value.title()
