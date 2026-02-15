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
from app.parking_data import get_parking_info, find_stations_with_parking, is_station_on_suspended_line
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

    for attempt in range(2):
        try:
            if http_client:
                resp = await http_client.get(url, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
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
            logger.warning(
                f"Mapbox API call failed ({profile}, attempt {attempt + 1}/2): "
                f"{type(e).__name__}: {e}"
            )
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
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
                weather=weather,
            )
            continue
        tasks.append(_generate_single_route(
            origin, destination, mode, gtfs, predictor, total_distance, is_adverse, now,
            http_client=http_client,
            weather=weather,
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
    weather: Optional[dict] = None,
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
            weather=weather,
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
    weather: Optional[dict] = None,
) -> Optional[RouteOption]:
    """Generate a transit route with walking segments to/from stations."""
    # Find nearest stops — progressive radius expansion for suburban origins
    TRANSIT_RADII = [3.0, 5.0, 8.0]
    origin_stops, dest_stops = [], []
    for radius in TRANSIT_RADII:
        if not origin_stops:
            origin_stops = find_nearest_stops(gtfs, origin.lat, origin.lng, radius_km=radius, limit=3)
        if not dest_stops:
            dest_stops = find_nearest_stops(gtfs, destination.lat, destination.lng, radius_km=radius, limit=3)
        if origin_stops and dest_stops:
            break

    if not origin_stops or not dest_stops:
        return None

    origin_stop = origin_stops[0]
    dest_stop = dest_stops[0]

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0
    extra_gas_cost = 0.0  # Track gas cost if we drive to station

    # Determine access mode for each end — walk if < 2.5km, drive otherwise
    origin_access_dist = origin_stop["distance_km"]
    dest_access_dist = dest_stop["distance_km"]
    drive_to_origin_station = origin_access_dist > 2.5
    drive_from_dest_station = dest_access_dist > 2.5

    origin_station_coord = Coordinate(lat=origin_stop["lat"], lng=origin_stop["lng"])
    dest_station_coord = Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"])

    # Fetch access legs in parallel
    origin_profile = "driving-traffic" if drive_to_origin_station else "walking"
    dest_profile = "driving-traffic" if drive_from_dest_station else "walking"

    access_to_geo, access_from_geo = await asyncio.gather(
        _mapbox_directions(origin, origin_station_coord, origin_profile, http_client=http_client),
        _mapbox_directions(dest_station_coord, destination, dest_profile, http_client=http_client),
    )

    # --- Access TO origin station ---
    if drive_to_origin_station:
        to_dist = access_to_geo["distance_km"] if access_to_geo else origin_access_dist * 1.3
        to_dur = access_to_geo["duration_min"] if access_to_geo else _estimate_duration(to_dist, RouteMode.DRIVING)
        # Calculate gas cost for driving leg
        gas_per_km = 0.12  # ~$0.12/km
        extra_gas_cost += to_dist * gas_per_km
        segments.append(RouteSegment(
            mode=RouteMode.DRIVING,
            geometry=access_to_geo["geometry"] if access_to_geo else _straight_line_geometry(origin, origin_station_coord),
            distance_km=round(to_dist, 2),
            duration_min=round(to_dur, 1),
            instructions=f"Drive to {origin_stop['stop_name']} station",
            color="#3B82F6",
            steps=_make_direction_steps(access_to_geo.get("steps", [])) if access_to_geo else [],
        ))
    else:
        to_dist = access_to_geo["distance_km"] if access_to_geo else origin_access_dist
        to_dur = access_to_geo["duration_min"] if access_to_geo else _estimate_duration(to_dist, RouteMode.WALKING)
        segments.append(RouteSegment(
            mode=RouteMode.WALKING,
            geometry=access_to_geo["geometry"] if access_to_geo else _straight_line_geometry(origin, origin_station_coord),
            distance_km=round(to_dist, 2),
            duration_min=round(to_dur, 1),
            instructions=f"Walk to {origin_stop['stop_name']} station",
            color="#10B981",
            steps=_make_direction_steps(access_to_geo.get("steps", [])) if access_to_geo else [],
        ))
    total_duration += to_dur
    total_dist += to_dist

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

    # Access FROM destination station (already fetched above in parallel)
    if drive_from_dest_station:
        from_dist = access_from_geo["distance_km"] if access_from_geo else dest_access_dist * 1.3
        from_dur = access_from_geo["duration_min"] if access_from_geo else _estimate_duration(from_dist, RouteMode.DRIVING)
        gas_per_km = 0.12
        extra_gas_cost += from_dist * gas_per_km
        segments.append(RouteSegment(
            mode=RouteMode.DRIVING,
            geometry=access_from_geo["geometry"] if access_from_geo else _straight_line_geometry(dest_station_coord, destination),
            distance_km=round(from_dist, 2),
            duration_min=round(from_dur, 1),
            instructions=f"Drive from {dest_stop['stop_name']} station to destination",
            color="#3B82F6",
            steps=_make_direction_steps(access_from_geo.get("steps", [])) if access_from_geo else [],
        ))
    else:
        from_dist = access_from_geo["distance_km"] if access_from_geo else dest_access_dist
        from_dur = access_from_geo["duration_min"] if access_from_geo else _estimate_duration(from_dist, RouteMode.WALKING)
        segments.append(RouteSegment(
            mode=RouteMode.WALKING,
            geometry=access_from_geo["geometry"] if access_from_geo else _straight_line_geometry(dest_station_coord, destination),
            distance_km=round(from_dist, 2),
            duration_min=round(from_dur, 1),
            instructions=f"Walk from {dest_stop['stop_name']} station to destination",
            color="#10B981",
            steps=_make_direction_steps(access_from_geo.get("steps", [])) if access_from_geo else [],
        ))
    total_duration += from_dur
    total_dist += from_dist

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

    _w = weather or {}
    prediction = predictor.predict(
        line=line_for_pred,
        hour=now.hour,
        day_of_week=now.weekday(),
        month=now.month,
        temperature=_w.get("temperature"),
        precipitation=_w.get("precipitation"),
        snowfall=_w.get("snowfall"),
        wind_speed=_w.get("wind_speed"),
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
    # Add gas cost if we drove to/from station
    if extra_gas_cost > 0:
        cost.gas = round(extra_gas_cost, 2)
        cost.total = round(cost.fare + cost.gas + cost.parking, 2)

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
    weather: Optional[dict] = None,
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

    # Filter out stations on GO lines not currently running (e.g. Richmond Hill line on weekends/off-peak)
    candidates = [c for c in candidates if not is_station_on_suspended_line(c["stop_name"], now=now)]

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
            weather=weather,
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
    weather: Optional[dict] = None,
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
        instructions=f"Drive to {park_stop['stop_name']} (Hybrid)",
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
                otp_route = parse_otp_itinerary(itin, predictor=predictor, weather=weather)
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

    _w = weather or {}
    prediction = predictor.predict(
        line=line_for_pred,
        hour=now.hour,
        day_of_week=now.weekday(),
        month=now.month,
        temperature=_w.get("temperature"),
        precipitation=_w.get("precipitation"),
        snowfall=_w.get("snowfall"),
        wind_speed=_w.get("wind_speed"),
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
        summary=f"Hybrid via {label_prefix} — {total_dist:.1f} km, {total_duration:.0f} min{parking_note}",
        traffic_summary=hybrid_traffic,
        parking_info=parking_info_model,
    )


async def calculate_custom_route(
    request,  # CustomRouteRequest
    gtfs: dict,
    predictor: DelayPredictor,
    http_client=None,
    weather: Optional[dict] = None,
) -> RouteOption:
    """Calculate a user-defined custom route from a list of segments."""
    from app.gtfs_parser import get_line_stations, TTC_LINE_INFO

    now = datetime.now()
    segments: list[RouteSegment] = []
    total_dist = 0.0
    total_dur = 0.0
    total_fare = 0.0
    total_gas = 0.0
    delay_info = DelayInfo()
    stress_score = 0.2

    prev_end_coord: Optional[Coordinate] = None

    for i, seg_req in enumerate(request.segments):
        if seg_req.mode in (RouteMode.DRIVING, RouteMode.WALKING):
            # Driving or walking segment
            seg_origin = seg_req.origin or prev_end_coord or request.trip_origin
            seg_dest = seg_req.destination

            # If no explicit destination, look ahead to next transit segment's start
            if not seg_dest:
                if i == len(request.segments) - 1:
                    seg_dest = request.trip_destination
                else:
                    # Look ahead for the next transit segment's start station
                    for j in range(i + 1, len(request.segments)):
                        future_seg = request.segments[j]
                        if future_seg.mode == RouteMode.TRANSIT and future_seg.start_station_id:
                            future_stations = get_line_stations(gtfs, future_seg.line_id) if future_seg.line_id else []
                            future_start = next((s for s in future_stations if s["stop_id"] == future_seg.start_station_id), None)
                            if future_start:
                                seg_dest = Coordinate(lat=future_start["lat"], lng=future_start["lng"])
                            break
                    # If still no destination, use trip destination
                    if not seg_dest:
                        seg_dest = request.trip_destination

            profile = "driving-traffic" if seg_req.mode == RouteMode.DRIVING else "walking"
            mapbox = await _mapbox_directions(seg_origin, seg_dest, profile, http_client=http_client)

            if mapbox:
                dist = mapbox["distance_km"]
                dur = mapbox["duration_min"]
                geometry = mapbox["geometry"]
                steps = _make_direction_steps(mapbox.get("steps", []))
            else:
                dist = haversine(seg_origin.lat, seg_origin.lng, seg_dest.lat, seg_dest.lng) * 1.3
                dur = _estimate_duration(dist, seg_req.mode)
                geometry = _straight_line_geometry(seg_origin, seg_dest)
                steps = []

            color = "#3B82F6" if seg_req.mode == RouteMode.DRIVING else "#10B981"
            action = "Drive" if seg_req.mode == RouteMode.DRIVING else "Walk"

            segments.append(RouteSegment(
                mode=seg_req.mode,
                geometry=geometry,
                distance_km=round(dist, 2),
                duration_min=round(dur, 1),
                instructions=f"{action} segment",
                color=color,
                steps=steps,
            ))
            total_dist += dist
            total_dur += dur

            if seg_req.mode == RouteMode.DRIVING:
                total_gas += dist * 0.12

            prev_end_coord = seg_dest

        elif seg_req.mode == RouteMode.TRANSIT:
            # Transit segment — look up station coordinates
            if not seg_req.line_id or not seg_req.start_station_id or not seg_req.end_station_id:
                continue

            line_stations = get_line_stations(gtfs, seg_req.line_id)
            start_station = next((s for s in line_stations if s["stop_id"] == seg_req.start_station_id), None)
            end_station = next((s for s in line_stations if s["stop_id"] == seg_req.end_station_id), None)

            if not start_station or not end_station:
                continue

            start_coord = Coordinate(lat=start_station["lat"], lng=start_station["lng"])
            end_coord = Coordinate(lat=end_station["lat"], lng=end_station["lng"])

            # Auto-insert walking transfer from previous segment end to this start
            if prev_end_coord:
                walk_dist = haversine(prev_end_coord.lat, prev_end_coord.lng, start_coord.lat, start_coord.lng)
                if walk_dist > 0.05:  # More than 50m
                    walk_geo = await _mapbox_directions(prev_end_coord, start_coord, "walking", http_client=http_client)
                    w_dist = walk_geo["distance_km"] if walk_geo else walk_dist
                    w_dur = walk_geo["duration_min"] if walk_geo else _estimate_duration(walk_dist, RouteMode.WALKING)
                    segments.append(RouteSegment(
                        mode=RouteMode.WALKING,
                        geometry=walk_geo["geometry"] if walk_geo else _straight_line_geometry(prev_end_coord, start_coord),
                        distance_km=round(w_dist, 2),
                        duration_min=round(w_dur, 1),
                        instructions=f"Walk to {start_station['stop_name']}",
                        color="#10B981",
                    ))
                    total_dist += w_dist
                    total_dur += w_dur

            # Transit segment itself
            transit_route = find_transit_route(gtfs, seg_req.start_station_id, seg_req.end_station_id)
            t_dist = transit_route["distance_km"] if transit_route else haversine(
                start_coord.lat, start_coord.lng, end_coord.lat, end_coord.lng
            )
            t_dur = transit_route["estimated_duration_min"] if transit_route else _estimate_duration(t_dist, RouteMode.TRANSIT)
            t_geom = transit_route.get("geometry") if transit_route else _straight_line_geometry(start_coord, end_coord)

            line_info = TTC_LINE_INFO.get(seg_req.line_id, {})
            line_name = line_info.get("name", f"Line {seg_req.line_id}")
            line_color = line_info.get("color", "#FFCC00")

            segments.append(RouteSegment(
                mode=RouteMode.TRANSIT,
                geometry=t_geom,
                distance_km=round(t_dist, 2),
                duration_min=round(t_dur, 1),
                instructions=f"Take {line_name} from {start_station['stop_name']} to {end_station['stop_name']}",
                transit_line=line_name,
                transit_route_id=seg_req.line_id,
                color=line_color,
            ))
            total_dist += t_dist
            total_dur += t_dur

            # Delay prediction for this transit segment
            _w = weather or {}
            prediction = predictor.predict(
                line=seg_req.line_id,
                hour=now.hour,
                day_of_week=now.weekday(),
                month=now.month,
                temperature=_w.get("temperature"),
                precipitation=_w.get("precipitation"),
                snowfall=_w.get("snowfall"),
                wind_speed=_w.get("wind_speed"),
                mode="subway",
            )
            # Keep the worst delay info
            if prediction["delay_probability"] > delay_info.probability:
                delay_info = DelayInfo(
                    probability=prediction["delay_probability"],
                    expected_minutes=prediction["expected_delay_minutes"],
                    confidence=prediction["confidence"],
                    factors=prediction["contributing_factors"],
                )
            stress_score += prediction["delay_probability"] * 0.15

            total_fare = 3.35  # TTC flat fare

            prev_end_coord = end_coord

    # Add final walk if needed
    if prev_end_coord:
        final_dist = haversine(prev_end_coord.lat, prev_end_coord.lng, request.trip_destination.lat, request.trip_destination.lng)
        if final_dist > 0.05:
            walk_geo = await _mapbox_directions(prev_end_coord, request.trip_destination, "walking", http_client=http_client)
            w_dist = walk_geo["distance_km"] if walk_geo else final_dist
            w_dur = walk_geo["duration_min"] if walk_geo else _estimate_duration(final_dist, RouteMode.WALKING)
            segments.append(RouteSegment(
                mode=RouteMode.WALKING,
                geometry=walk_geo["geometry"] if walk_geo else _straight_line_geometry(prev_end_coord, request.trip_destination),
                distance_km=round(w_dist, 2),
                duration_min=round(w_dur, 1),
                instructions="Walk to destination",
                color="#10B981",
            ))
            total_dist += w_dist
            total_dur += w_dur

    cost = CostBreakdown(
        fare=round(total_fare, 2),
        gas=round(total_gas, 2),
        parking=0.0,
        total=round(total_fare + total_gas, 2),
    )

    return RouteOption(
        id=str(uuid.uuid4())[:8],
        label="Custom Route",
        mode=RouteMode.TRANSIT,
        segments=segments,
        total_distance_km=round(total_dist, 2),
        total_duration_min=round(total_dur, 1),
        cost=cost,
        delay_info=delay_info,
        stress_score=round(min(1.0, stress_score), 2),
        departure_time=now.strftime("%H:%M"),
        summary=f"Custom Route — {total_dist:.1f} km, {total_dur:.0f} min",
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
                route.label = f"Hybrid ({station})"
            else:
                hybrid_count += 1
                route.label = f"Hybrid {hybrid_count}" if hybrid_count > 1 else "Hybrid"
        else:
            route.label = route.mode.value.title()


async def calculate_custom_route_v2(
    request,  # CustomRouteRequestV2
    gtfs: dict,
    predictor: DelayPredictor,
    http_client=None,
    weather: Optional[dict] = None,
) -> RouteOption:
    """Calculate a user-defined custom route using V2 suggestion-based segments.

    Transit segments receive board/alight coords directly from the suggestion
    the user picked. Driving/walking segments auto-compute destinations by
    looking ahead in the chain.
    """
    now = datetime.now()
    segments: list[RouteSegment] = []
    total_dist = 0.0
    total_dur = 0.0
    total_fare = 0.0
    total_gas = 0.0
    delay_info = DelayInfo()
    stress_score = 0.2

    prev_end_coord: Optional[Coordinate] = None

    # Fix 1: Insert initial walk from origin to first transit segment's board coord
    # (if the first segment is transit, there's no explicit walk/drive before it)
    if request.segments and request.segments[0].mode == RouteMode.TRANSIT and request.segments[0].board_coord:
        first_board = request.segments[0].board_coord
        walk_dist = haversine(request.trip_origin.lat, request.trip_origin.lng, first_board.lat, first_board.lng)
        if walk_dist > 0.05:  # More than 50m gap
            walk_geo = await _mapbox_directions(request.trip_origin, first_board, "walking", http_client=http_client)
            w_dist = walk_geo["distance_km"] if walk_geo else walk_dist
            w_dur = walk_geo["duration_min"] if walk_geo else _estimate_duration(walk_dist, RouteMode.WALKING)
            segments.append(RouteSegment(
                mode=RouteMode.WALKING,
                geometry=walk_geo["geometry"] if walk_geo else _straight_line_geometry(request.trip_origin, first_board),
                distance_km=round(w_dist, 2),
                duration_min=round(w_dur, 1),
                instructions=f"Walk to {request.segments[0].board_stop_name or 'transit stop'}",
                color="#10B981",
            ))
            total_dist += w_dist
            total_dur += w_dur
            prev_end_coord = first_board

    for i, seg_req in enumerate(request.segments):
        if seg_req.mode in (RouteMode.DRIVING, RouteMode.WALKING):
            seg_origin = prev_end_coord or request.trip_origin

            # Look ahead to next transit segment's board coord
            seg_dest = None
            for j in range(i + 1, len(request.segments)):
                future_seg = request.segments[j]
                if future_seg.mode == RouteMode.TRANSIT and future_seg.board_coord:
                    seg_dest = future_seg.board_coord
                    break

            if not seg_dest:
                seg_dest = request.trip_destination

            profile = "driving-traffic" if seg_req.mode == RouteMode.DRIVING else "walking"
            mapbox = await _mapbox_directions(seg_origin, seg_dest, profile, http_client=http_client)

            if mapbox:
                dist = mapbox["distance_km"]
                dur = mapbox["duration_min"]
                geometry = mapbox["geometry"]
                steps = _make_direction_steps(mapbox.get("steps", []))
            else:
                dist = haversine(seg_origin.lat, seg_origin.lng, seg_dest.lat, seg_dest.lng) * 1.3
                dur = _estimate_duration(dist, seg_req.mode)
                geometry = _straight_line_geometry(seg_origin, seg_dest)
                steps = []

            color = "#3B82F6" if seg_req.mode == RouteMode.DRIVING else "#10B981"
            action = "Drive" if seg_req.mode == RouteMode.DRIVING else "Walk"

            segments.append(RouteSegment(
                mode=seg_req.mode,
                geometry=geometry,
                distance_km=round(dist, 2),
                duration_min=round(dur, 1),
                instructions=f"{action} segment",
                color=color,
                steps=steps,
            ))
            total_dist += dist
            total_dur += dur

            if seg_req.mode == RouteMode.DRIVING:
                total_gas += dist * 0.12

            prev_end_coord = seg_dest

        elif seg_req.mode == RouteMode.TRANSIT:
            if not seg_req.board_coord or not seg_req.alight_coord:
                continue

            board_coord = seg_req.board_coord
            alight_coord = seg_req.alight_coord

            # Auto-insert walking transfer if gap from previous segment end
            if prev_end_coord:
                walk_dist = haversine(prev_end_coord.lat, prev_end_coord.lng, board_coord.lat, board_coord.lng)
                if walk_dist > 0.05:
                    walk_geo = await _mapbox_directions(prev_end_coord, board_coord, "walking", http_client=http_client)
                    w_dist = walk_geo["distance_km"] if walk_geo else walk_dist
                    w_dur = walk_geo["duration_min"] if walk_geo else _estimate_duration(walk_dist, RouteMode.WALKING)
                    segments.append(RouteSegment(
                        mode=RouteMode.WALKING,
                        geometry=walk_geo["geometry"] if walk_geo else _straight_line_geometry(prev_end_coord, board_coord),
                        distance_km=round(w_dist, 2),
                        duration_min=round(w_dur, 1),
                        instructions=f"Walk to {seg_req.board_stop_name or 'transit stop'}",
                        color="#10B981",
                    ))
                    total_dist += w_dist
                    total_dur += w_dur

            # Fix 2: Use find_transit_route with stop_ids when available
            t_dist = None
            t_dur = None
            t_geom = None

            if seg_req.board_stop_id and seg_req.alight_stop_id:
                transit_route = find_transit_route(gtfs, seg_req.board_stop_id, seg_req.alight_stop_id)
                if transit_route:
                    t_dist = transit_route["distance_km"]
                    t_dur = transit_route["estimated_duration_min"]
                    t_geom = transit_route.get("geometry")

            # Fallback: haversine with per-mode speed and 1.4x road/track multiplier
            if t_dist is None:
                straight_dist = haversine(board_coord.lat, board_coord.lng, alight_coord.lat, alight_coord.lng)
                t_dist = straight_dist * 1.4  # Approximate real track/road distance

                # Fix 3: Per-mode speed estimates instead of generic 25 km/h
                transit_mode_str = (seg_req.transit_mode or "").upper()
                speed_map = {"SUBWAY": 35, "BUS": 20, "TRAM": 18, "RAIL": 40}
                speed = speed_map.get(transit_mode_str, 25)
                t_dur = (t_dist / speed) * 60

            if t_geom is None:
                t_geom = _straight_line_geometry(board_coord, alight_coord)
                if seg_req.route_id:
                    from app.gtfs_parser import get_route_shape
                    shape = get_route_shape(gtfs, seg_req.route_id)
                    if shape:
                        t_geom = shape

            display_name = seg_req.display_name or f"Route {seg_req.route_id or '?'}"
            line_color = seg_req.color or "#FFCC00"
            board_name = seg_req.board_stop_name or "Board"
            alight_name = seg_req.alight_stop_name or "Alight"

            segments.append(RouteSegment(
                mode=RouteMode.TRANSIT,
                geometry=t_geom,
                distance_km=round(t_dist, 2),
                duration_min=round(t_dur, 1),
                instructions=f"Take {display_name} from {board_name} to {alight_name}",
                transit_line=display_name,
                transit_route_id=seg_req.route_id,
                color=line_color,
            ))
            total_dist += t_dist
            total_dur += t_dur

            # Delay prediction
            pred_line = seg_req.route_id or "1"
            pred_mode = "subway"
            transit_mode_str = (seg_req.transit_mode or "").upper()
            if transit_mode_str == "BUS":
                pred_mode = "bus"
            elif transit_mode_str in ("TRAM", "STREETCAR"):
                pred_mode = "streetcar"

            _w = weather or {}
            prediction = predictor.predict(
                line=pred_line,
                hour=now.hour,
                day_of_week=now.weekday(),
                month=now.month,
                temperature=_w.get("temperature"),
                precipitation=_w.get("precipitation"),
                snowfall=_w.get("snowfall"),
                wind_speed=_w.get("wind_speed"),
                mode=pred_mode,
            )
            if prediction["delay_probability"] > delay_info.probability:
                delay_info = DelayInfo(
                    probability=prediction["delay_probability"],
                    expected_minutes=prediction["expected_delay_minutes"],
                    confidence=prediction["confidence"],
                    factors=prediction["contributing_factors"],
                )
            stress_score += prediction["delay_probability"] * 0.15

            total_fare = 3.35  # TTC flat fare
            prev_end_coord = alight_coord

    # Add final walk to destination if needed
    if prev_end_coord:
        final_dist = haversine(prev_end_coord.lat, prev_end_coord.lng, request.trip_destination.lat, request.trip_destination.lng)
        if final_dist > 0.05:
            walk_geo = await _mapbox_directions(prev_end_coord, request.trip_destination, "walking", http_client=http_client)
            w_dist = walk_geo["distance_km"] if walk_geo else final_dist
            w_dur = walk_geo["duration_min"] if walk_geo else _estimate_duration(final_dist, RouteMode.WALKING)
            segments.append(RouteSegment(
                mode=RouteMode.WALKING,
                geometry=walk_geo["geometry"] if walk_geo else _straight_line_geometry(prev_end_coord, request.trip_destination),
                distance_km=round(w_dist, 2),
                duration_min=round(w_dur, 1),
                instructions="Walk to destination",
                color="#10B981",
            ))
            total_dist += w_dist
            total_dur += w_dur

    cost = CostBreakdown(
        fare=round(total_fare, 2),
        gas=round(total_gas, 2),
        parking=0.0,
        total=round(total_fare + total_gas, 2),
    )

    return RouteOption(
        id=str(uuid.uuid4())[:8],
        label="Custom Route",
        mode=RouteMode.TRANSIT,
        segments=segments,
        total_distance_km=round(total_dist, 2),
        total_duration_min=round(total_dur, 1),
        cost=cost,
        delay_info=delay_info,
        stress_score=round(min(1.0, stress_score), 2),
        departure_time=now.strftime("%H:%M"),
        summary=f"Custom Route — {total_dist:.1f} km, {total_dur:.0f} min",
    )
