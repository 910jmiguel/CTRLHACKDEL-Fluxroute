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
from app.gtfs_parser import (
    find_nearest_stops, find_nearest_rapid_transit_stations, haversine,
    find_transit_route, get_active_service_ids, get_next_departures,
    get_trip_arrival_at_stop, find_transfer_stations, resolve_transfer_stop_id,
    TTC_LINE_INFO, find_bus_routes_between,
)
from app.ml_predictor import DelayPredictor
from app.models import ParkingInfo
from app.otp_client import query_otp_routes, parse_otp_itinerary, find_park_and_ride_stations
from app.parking_data import get_parking_info, find_stations_with_parking, is_station_on_suspended_line
from app.weather import get_current_weather

logger = logging.getLogger("fluxroute.engine")

def _get_mapbox_token() -> str:
    return os.getenv("MAPBOX_TOKEN", "")
MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox"

# Simple per-request cache for Mapbox directions (avoids duplicate calls within one route calculation)
_directions_cache: dict[str, Optional[dict]] = {}

def _directions_cache_key(origin: "Coordinate", destination: "Coordinate", profile: str) -> str:
    return f"{origin.lat:.5f},{origin.lng:.5f}|{destination.lat:.5f},{destination.lng:.5f}|{profile}"


async def _mapbox_directions(
    origin: Coordinate,
    destination: Coordinate,
    profile: str = "driving-traffic",
    http_client: Optional[httpx.AsyncClient] = None,
) -> Optional[dict]:
    """Call Mapbox Directions API. Returns route data or None on failure."""
    # Check cache first (avoids duplicate API calls within one route calculation)
    cache_key = _directions_cache_key(origin, destination, profile)
    if cache_key in _directions_cache:
        return _directions_cache[cache_key]

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
                async with httpx.AsyncClient(timeout=10.0, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
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

            result = {
                "geometry": route["geometry"],
                "distance_km": route["distance"] / 1000,
                "duration_min": route["duration"] / 60,
                "congestion": congestion,
                "congestion_level": congestion_level,
                "steps": steps,
            }
            _directions_cache[cache_key] = result
            return result
        except Exception as e:
            logger.warning(
                f"Mapbox API call failed ({profile}, attempt {attempt + 1}/2): "
                f"{type(e).__name__}: {e}"
            )
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            _directions_cache[cache_key] = None
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


def _bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute bearing in degrees (0-360) from point 1 to point 2."""
    import math
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlng = math.radians(lng2 - lng1)
    x = math.sin(dlng) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _bearing_diff(b1: float, b2: float) -> float:
    """Absolute angular difference between two bearings (0-180)."""
    diff = abs(b1 - b2) % 360
    return diff if diff <= 180 else 360 - diff


def _validate_hybrid_route(
    route: RouteOption,
    origin: Coordinate,
    destination: Coordinate,
    straight_line_dist: float,
) -> bool:
    """Validate a hybrid route is sensible. Returns True if valid."""
    # Rule 1: Reject if total distance > 2.5x straight-line distance
    if route.total_distance_km > straight_line_dist * 2.5:
        logger.debug(
            f"Hybrid route rejected: total {route.total_distance_km:.1f}km > "
            f"2.5x straight-line {straight_line_dist:.1f}km"
        )
        return False

    # Rule 2: Reject if driving > 60% of total route distance
    driving_dist = sum(s.distance_km for s in route.segments if s.mode == RouteMode.DRIVING)
    if route.total_distance_km > 0 and driving_dist / route.total_distance_km > 0.6:
        logger.debug(
            f"Hybrid route rejected: driving {driving_dist:.1f}km is "
            f"{driving_dist / route.total_distance_km:.0%} of total"
        )
        return False

    # Rule 3: Reject if route end is >2km from destination
    last_seg = route.segments[-1] if route.segments else None
    if last_seg and last_seg.geometry and last_seg.geometry.get("coordinates"):
        end_coord = last_seg.geometry["coordinates"][-1]  # [lng, lat]
        end_dist = haversine(end_coord[1], end_coord[0], destination.lat, destination.lng)
        if end_dist > 2.0:
            logger.debug(
                f"Hybrid route rejected: end point {end_dist:.1f}km from destination"
            )
            return False

    return True


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


async def _fetch_otp(origin, destination, now, modes, otp_available, http_client=None, app_state=None, allowed_agencies=None):
    """Query OTP if available. Returns (otp_used, otp_routes) tuple."""
    if RouteMode.TRANSIT not in modes:
        return False, []

    # Lazy recheck: if OTP was unavailable at startup, re-check periodically
    if not otp_available and app_state is not None:
        from app.otp_client import check_otp_health
        otp_available = await check_otp_health(http_client=http_client)
        if otp_available:
            app_state["otp_available"] = True
            logger.info("OTP is now available — switching to OTP for transit routing")

    if not otp_available:
        logger.info("OTP not available — skipping (using heuristic transit routing)")
        return False, []

    # Compute banned agencies (inverse of allowed)
    all_agencies = {"TTC", "GO Transit", "YRT", "MiWay", "UP Express"}
    banned_agencies = None
    if allowed_agencies is not None:
        banned = all_agencies - set(allowed_agencies)
        if banned:
            banned_agencies = list(banned)

    try:
        otp_itineraries = await query_otp_routes(
            origin, destination, now, num_itineraries=5, http_client=http_client,
            banned_agencies=banned_agencies,
        )
        # Post-filter as safety net: remove itineraries using banned agencies
        if otp_itineraries and banned_agencies:
            filtered = []
            for itin in otp_itineraries:
                legs = itin.get("legs", [])
                itin_agencies = {leg.get("agencyName", "") for leg in legs if leg.get("agencyName")}
                if not itin_agencies & set(banned_agencies):
                    filtered.append(itin)
            otp_itineraries = filtered

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
    preferences=None,
) -> list[RouteOption]:
    """Generate 3-4 route options for the given origin/destination."""
    _directions_cache.clear()  # Fresh cache per request

    if modes is None:
        modes = [RouteMode.TRANSIT, RouteMode.DRIVING, RouteMode.WALKING, RouteMode.HYBRID]

    # Extract preferences with defaults
    allowed_agencies = ["TTC", "GO Transit", "YRT", "MiWay"]
    max_drive_radius_km = 15.0
    if preferences is not None:
        allowed_agencies = preferences.allowed_agencies
        max_drive_radius_km = preferences.max_drive_radius_km

    total_distance = haversine(origin.lat, origin.lng, destination.lat, destination.lng)
    routes: list[RouteOption] = []
    now = datetime.now()

    # Get shared http client for connection pooling (falls back to per-call clients)
    http_client = (app_state or {}).get("http_client")
    otp_available = (app_state or {}).get("otp_available", False)

    # Phase 1: Fetch weather + OTP concurrently (instead of sequentially)
    weather_task = _fetch_weather_full(origin.lat, origin.lng, http_client=http_client)
    otp_task = _fetch_otp(origin, destination, now, modes, otp_available, http_client=http_client, app_state=app_state, allowed_agencies=allowed_agencies)
    weather, (otp_used, otp_itineraries) = await asyncio.gather(weather_task, otp_task)
    is_adverse = weather.get("is_adverse", False)

    # Process OTP results
    if otp_used:
        for itin in otp_itineraries[:3]:  # Take best 3 OTP results
            otp_route = parse_otp_itinerary(itin, predictor=predictor, weather=weather)
            routes.append(otp_route)
        logger.info(f"Used {min(3, len(otp_itineraries))} OTP itineraries")

    # Phase 2: Build and run route tasks in parallel
    tasks = []
    hybrid_task = None
    transit_task = None
    for mode in modes:
        if mode == RouteMode.TRANSIT and otp_used:
            continue
        if mode == RouteMode.WALKING and total_distance > 5.0:
            continue
        if mode == RouteMode.TRANSIT:
            # Transit returns a list of routes — handle like hybrid
            transit_task = _generate_transit_route(
                origin, destination, gtfs, predictor, total_distance, is_adverse, now,
                http_client=http_client,
                weather=weather,
                app_state=app_state,
                allowed_agencies=allowed_agencies,
            )
            continue
        if mode == RouteMode.HYBRID:
            # Hybrid returns a list of routes — handle separately
            hybrid_task = _generate_hybrid_routes(
                origin, destination, gtfs, predictor, total_distance, is_adverse, now,
                http_client=http_client,
                otp_available=otp_available,
                app_state=app_state,
                weather=weather,
                allowed_agencies=allowed_agencies,
                max_drive_radius_km=max_drive_radius_km,
            )
            continue
        tasks.append(_generate_single_route(
            origin, destination, mode, gtfs, predictor, total_distance, is_adverse, now,
            http_client=http_client,
            weather=weather,
            app_state=app_state,
        ))

    # Run single-mode routes + hybrid + transit in parallel
    if hybrid_task:
        tasks.append(hybrid_task)
    if transit_task:
        tasks.append(transit_task)

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

    # Log any requested modes that produced no routes
    generated_modes = {r.mode for r in routes}
    missing_modes = [m.value for m in modes if m not in generated_modes]
    if missing_modes:
        logger.warning(f"No routes generated for requested modes: {', '.join(missing_modes)}")

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
    app_state: Optional[dict] = None,
) -> Optional[RouteOption]:
    """Generate a single route option."""

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0
    delay_info = DelayInfo()
    stress_score = 0.0
    traffic_label = ""

    if mode == RouteMode.DRIVING:
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


def _enrich_transit_segment(
    seg: RouteSegment,
    gtfs: dict,
    route_id,
    origin_stop: dict,
    dest_stop: dict,
    now: datetime,
    app_state: Optional[dict] = None,
) -> None:
    """Enrich a transit segment with schedule data (departure/arrival times, next departures).

    Checks GTFS-RT trip updates first, falls back to GTFS static, then estimated.
    Mutates the segment in place.
    """
    service_ids = get_active_service_ids(gtfs)
    rid = str(route_id) if route_id else None

    departures = get_next_departures(
        gtfs, origin_stop["stop_id"], limit=5, route_id=rid, service_ids=service_ids,
    )

    if not departures:
        # Estimated fallback
        seg.schedule_source = "estimated"
        dep_minutes = now.hour * 60 + now.minute + 3  # ~3 min from now
        seg.departure_time = f"{(dep_minutes // 60) % 24:02d}:{dep_minutes % 60:02d}"
        arr_minutes = dep_minutes + round(seg.duration_min)
        seg.arrival_time = f"{(arr_minutes // 60) % 24:02d}:{arr_minutes % 60:02d}"
        return

    # Store next departures for display
    seg.next_departures = [
        {"departure_time": d["departure_time"], "minutes_until": d["minutes_until"]}
        for d in departures
    ]

    # Pick the first upcoming departure
    best = departures[0]
    trip_id = best.get("trip_id", "")
    seg.trip_id = trip_id
    seg.departure_time = best["departure_time"]
    seg.schedule_source = "gtfs-static"

    # Check GTFS-RT trip updates for real-time override
    trip_updates = (app_state or {}).get("trip_updates", {})
    rt_dep = trip_updates.get((trip_id, origin_stop["stop_id"]))
    rt_arr = trip_updates.get((trip_id, dest_stop["stop_id"]))

    if rt_dep and rt_dep.get("departure"):
        from datetime import timezone
        dep_dt = datetime.fromtimestamp(rt_dep["departure"], tz=timezone.utc)
        # Convert to local time (Toronto is UTC-5 or UTC-4)
        import time as _time
        offset = _time.timezone if _time.daylight == 0 else _time.altzone
        dep_local_minutes = dep_dt.hour * 60 + dep_dt.minute - (offset // 60)
        seg.departure_time = f"{(dep_local_minutes // 60) % 24:02d}:{dep_local_minutes % 60:02d}"
        seg.schedule_source = "gtfs-rt"

    if rt_arr and rt_arr.get("arrival"):
        from datetime import timezone
        import time as _time
        arr_dt = datetime.fromtimestamp(rt_arr["arrival"], tz=timezone.utc)
        offset = _time.timezone if _time.daylight == 0 else _time.altzone
        arr_local_minutes = arr_dt.hour * 60 + arr_dt.minute - (offset // 60)
        seg.arrival_time = f"{(arr_local_minutes // 60) % 24:02d}:{arr_local_minutes % 60:02d}"
        seg.schedule_source = "gtfs-rt"
    else:
        # Use static GTFS arrival
        arrival = get_trip_arrival_at_stop(gtfs, trip_id, dest_stop["stop_id"])
        if arrival:
            seg.arrival_time = arrival
        else:
            # Estimate from departure + duration
            dep_parts = seg.departure_time.split(":")
            dep_minutes = int(dep_parts[0]) * 60 + int(dep_parts[1])
            arr_minutes = dep_minutes + round(seg.duration_min)
            seg.arrival_time = f"{(arr_minutes // 60) % 24:02d}:{arr_minutes % 60:02d}"


async def _build_transfer_route(
    origin: Coordinate,
    destination: Coordinate,
    origin_stop: dict,
    dest_stop: dict,
    transfer_station: dict,
    gtfs: dict,
    predictor: DelayPredictor,
    is_adverse: bool,
    now: datetime,
    http_client=None,
    weather: Optional[dict] = None,
    app_state: Optional[dict] = None,
) -> Optional[RouteOption]:
    """Build a transit route with one transfer between two lines.

    Produces segments: walk/drive to origin station → transit leg 1 → transfer walk →
    transit leg 2 → walk/drive to destination.
    """
    origin_line = str(origin_stop.get("route_id") or "")
    dest_line = str(dest_stop.get("route_id") or "")
    if not origin_line or not dest_line:
        return None

    # Resolve stop IDs at the transfer station for each line
    transfer_stop_id_leg1 = resolve_transfer_stop_id(gtfs, transfer_station, origin_line)
    transfer_stop_id_leg2 = resolve_transfer_stop_id(gtfs, transfer_station, dest_line)
    if not transfer_stop_id_leg1 or not transfer_stop_id_leg2:
        return None

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0
    extra_gas_cost = 0.0

    origin_station_coord = Coordinate(lat=origin_stop["lat"], lng=origin_stop["lng"])
    dest_station_coord = Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"])
    transfer_coord = Coordinate(lat=transfer_station["lat"], lng=transfer_station["lng"])

    # --- Access TO origin station ---
    origin_access_dist = origin_stop["distance_km"]
    drive_to_origin = origin_access_dist > 2.5
    origin_profile = "driving-traffic" if drive_to_origin else "walking"

    dest_access_dist = dest_stop["distance_km"]
    drive_from_dest = dest_access_dist > 2.5
    dest_profile = "driving-traffic" if drive_from_dest else "walking"

    access_to_geo, access_from_geo = await asyncio.gather(
        _mapbox_directions(origin, origin_station_coord, origin_profile, http_client=http_client),
        _mapbox_directions(dest_station_coord, destination, dest_profile, http_client=http_client),
    )

    if drive_to_origin:
        to_dist = access_to_geo["distance_km"] if access_to_geo else origin_access_dist * 1.3
        to_dur = access_to_geo["duration_min"] if access_to_geo else _estimate_duration(to_dist, RouteMode.DRIVING)
        extra_gas_cost += to_dist * 0.12
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

    # --- Transit Leg 1: origin station → transfer station (origin's line) ---
    leg1_route = find_transit_route(gtfs, origin_stop["stop_id"], transfer_stop_id_leg1, route_id=origin_line)
    leg1_dist = leg1_route["distance_km"] if leg1_route else haversine(
        origin_stop["lat"], origin_stop["lng"], transfer_station["lat"], transfer_station["lng"]
    )
    leg1_dur = leg1_route["estimated_duration_min"] if leg1_route else _estimate_duration(leg1_dist, RouteMode.TRANSIT)
    leg1_geom = (
        leg1_route.get("geometry") if leg1_route
        else _straight_line_geometry(origin_station_coord, transfer_coord)
    )

    line1_info = TTC_LINE_INFO.get(origin_line, {})
    line1_name = line1_info.get("name", f"Line {origin_line}")
    line1_color = line1_info.get("color", "#F0CC49")

    leg1_seg = RouteSegment(
        mode=RouteMode.TRANSIT,
        geometry=leg1_geom,
        distance_km=round(leg1_dist, 2),
        duration_min=round(leg1_dur, 1),
        instructions=f"Take {line1_name} from {origin_stop['stop_name']} to {transfer_station['name']}",
        transit_line=line1_name,
        transit_route_id=origin_line,
        color=line1_color,
        board_stop_id=origin_stop["stop_id"],
        alight_stop_id=transfer_stop_id_leg1,
    )
    _enrich_transit_segment(leg1_seg, gtfs, origin_line, origin_stop,
                            {"stop_id": transfer_stop_id_leg1}, now, app_state)
    segments.append(leg1_seg)
    total_duration += leg1_dur
    total_dist += leg1_dist

    # --- Transfer walk at interchange ---
    transfer_time = transfer_station.get("time_min", 3)
    segments.append(RouteSegment(
        mode=RouteMode.WALKING,
        geometry={"type": "LineString", "coordinates": [
            [transfer_station["lng"], transfer_station["lat"]],
            [transfer_station["lng"], transfer_station["lat"]],
        ]},
        distance_km=0.1,
        duration_min=float(transfer_time),
        instructions=f"Transfer to {TTC_LINE_INFO.get(dest_line, {}).get('name', f'Line {dest_line}')} at {transfer_station['name']} ({transfer_time} min)",
        color="#10B981",
    ))
    total_duration += transfer_time
    total_dist += 0.1

    # --- Transit Leg 2: transfer station → dest station (destination's line) ---
    leg2_route = find_transit_route(gtfs, transfer_stop_id_leg2, dest_stop["stop_id"], route_id=dest_line)
    leg2_dist = leg2_route["distance_km"] if leg2_route else haversine(
        transfer_station["lat"], transfer_station["lng"], dest_stop["lat"], dest_stop["lng"]
    )
    leg2_dur = leg2_route["estimated_duration_min"] if leg2_route else _estimate_duration(leg2_dist, RouteMode.TRANSIT)
    leg2_geom = (
        leg2_route.get("geometry") if leg2_route
        else _straight_line_geometry(transfer_coord, dest_station_coord)
    )

    line2_info = TTC_LINE_INFO.get(dest_line, {})
    line2_name = line2_info.get("name", f"Line {dest_line}")
    line2_color = line2_info.get("color", "#549F4D")

    leg2_seg = RouteSegment(
        mode=RouteMode.TRANSIT,
        geometry=leg2_geom,
        distance_km=round(leg2_dist, 2),
        duration_min=round(leg2_dur, 1),
        instructions=f"Take {line2_name} from {transfer_station['name']} to {dest_stop['stop_name']}",
        transit_line=line2_name,
        transit_route_id=dest_line,
        color=line2_color,
        board_stop_id=transfer_stop_id_leg2,
        alight_stop_id=dest_stop["stop_id"],
    )
    _enrich_transit_segment(leg2_seg, gtfs, dest_line,
                            {"stop_id": transfer_stop_id_leg2}, dest_stop, now, app_state)
    segments.append(leg2_seg)
    total_duration += leg2_dur
    total_dist += leg2_dist

    # --- Access FROM destination station ---
    if drive_from_dest:
        from_dist = access_from_geo["distance_km"] if access_from_geo else dest_access_dist * 1.3
        from_dur = access_from_geo["duration_min"] if access_from_geo else _estimate_duration(from_dist, RouteMode.DRIVING)
        extra_gas_cost += from_dist * 0.12
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

    # --- Delay prediction (use worst of both lines) ---
    _w = weather or {}
    delay_info = DelayInfo()
    for line_id in [origin_line, dest_line]:
        pred_mode = "subway" if line_id in ("1", "2", "4") else "streetcar"
        prediction = predictor.predict(
            line=line_id, hour=now.hour, day_of_week=now.weekday(), month=now.month,
            temperature=_w.get("temperature"), precipitation=_w.get("precipitation"),
            snowfall=_w.get("snowfall"), wind_speed=_w.get("wind_speed"), mode=pred_mode,
        )
        if prediction["delay_probability"] > delay_info.probability:
            delay_info = DelayInfo(
                probability=prediction["delay_probability"],
                expected_minutes=prediction["expected_delay_minutes"],
                confidence=prediction["confidence"],
                factors=prediction["contributing_factors"],
            )

    # Stress: base + transfer penalty + delay
    stress_score = 0.2 + 0.1 + delay_info.probability * 0.3
    if is_adverse:
        stress_score += 0.1

    cost = calculate_cost(RouteMode.TRANSIT, leg1_dist + leg2_dist)
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
        summary=f"{line1_name} to {transfer_station['name']}, transfer to {line2_name}",
    )


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
    app_state: Optional[dict] = None,
    allowed_agencies: Optional[list[str]] = None,
) -> list[RouteOption]:
    """Generate transit route options with walking segments to/from stations."""
    # Heuristic transit routing only uses TTC GTFS data — skip if TTC not allowed
    if allowed_agencies is not None and "TTC" not in allowed_agencies:
        logger.info("TTC not in allowed agencies — skipping heuristic transit routing")
        return []

    # Find nearest rapid transit stations (subway/LRT/rail only — no bus stops)
    # Progressive radius expansion for suburban origins
    TRANSIT_RADII = [3.0, 5.0, 8.0, 15.0]
    origin_stops, dest_stops = [], []
    for radius in TRANSIT_RADII:
        if not origin_stops:
            origin_stops = find_nearest_rapid_transit_stations(gtfs, origin.lat, origin.lng, radius_km=radius, limit=5)
        if not dest_stops:
            dest_stops = find_nearest_rapid_transit_stations(gtfs, destination.lat, destination.lng, radius_km=radius, limit=5)
        if origin_stops and dest_stops:
            break

    if not origin_stops or not dest_stops:
        return []

    routes: list[RouteOption] = []
    trip_bearing = _bearing(origin.lat, origin.lng, destination.lat, destination.lng)

    # Score all origin/dest stop combinations to find the best pair.
    # ONLY consider same-line pairs (direct route) — cross-line trips need transfers
    # which we don't build yet, so they'd "teleport" between lines.
    _RAPID_LINES = {"1", "2", "4"}
    best_pair = None
    best_score = float('inf')

    # First pass: same-line pairs only
    for o_stop in origin_stops:
        for d_stop in dest_stops:
            o_rid = str(o_stop.get("route_id") or "")
            d_rid = str(d_stop.get("route_id") or "")
            if not o_rid or o_rid != d_rid:
                continue  # Skip cross-line pairs
            # Directional validation: reject if transit segment goes wrong direction
            seg_bearing = _bearing(o_stop["lat"], o_stop["lng"], d_stop["lat"], d_stop["lng"])
            if _bearing_diff(trip_bearing, seg_bearing) > 90:
                continue  # Transit segment goes in wrong direction
            score = o_stop["distance_km"] + d_stop["distance_km"]
            if o_rid in _RAPID_LINES:
                score -= 2  # Prefer subway over LRT/streetcar
            if score < best_score:
                best_score = score
                best_pair = (o_stop, d_stop)

    # Fallback: if no same-line pair, try building a transfer route
    if best_pair is None:
        logger.info("No same-line pair found — attempting transfer route")
        transfer_candidates = []
        for o_stop in origin_stops:
            for d_stop in dest_stops:
                o_rid = str(o_stop.get("route_id") or "")
                d_rid = str(d_stop.get("route_id") or "")
                if not o_rid or not d_rid or o_rid == d_rid:
                    continue
                transfers = find_transfer_stations(o_rid, d_rid)
                if not transfers:
                    continue
                for ts in transfers:
                    # Score: access distance + detour through transfer station
                    access_cost = o_stop["distance_km"] + d_stop["distance_km"]
                    detour = (
                        haversine(o_stop["lat"], o_stop["lng"], ts["lat"], ts["lng"])
                        + haversine(ts["lat"], ts["lng"], d_stop["lat"], d_stop["lng"])
                    )
                    transfer_candidates.append((access_cost + detour * 0.5, o_stop, d_stop, ts))

        if transfer_candidates:
            transfer_candidates.sort(key=lambda x: x[0])
            _, best_o, best_d, best_ts = transfer_candidates[0]
            logger.info(f"Transfer route: {best_o['stop_name']} (Line {best_o.get('route_id')}) → "
                        f"{best_ts['name']} → {best_d['stop_name']} (Line {best_d.get('route_id')})")
            transfer_route = await _build_transfer_route(
                origin, destination, best_o, best_d, best_ts,
                gtfs, predictor, is_adverse, now,
                http_client=http_client, weather=weather, app_state=app_state,
            )
            if transfer_route:
                routes.append(transfer_route)

    # Build same-line route if valid pair found
    if best_pair is not None:
        origin_stop, dest_stop = best_pair

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
        transit_route = find_transit_route(gtfs, origin_stop["stop_id"], dest_stop["stop_id"],
                                           route_id=origin_stop.get("route_id"))
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
        line_colors = {"1": "#F0CC49", "2": "#549F4D", "4": "#9C246E", "5": "#DE7731", "6": "#959595"}
        color = line_colors.get(str(route_id), "#F0CC49")

        # Build transit segment with schedule enrichment
        transit_seg = RouteSegment(
            mode=RouteMode.TRANSIT,
            geometry=transit_geometry,
            distance_km=round(transit_dist, 2),
            duration_min=round(transit_dur, 1),
            instructions=f"Take {line_name} from {origin_stop['stop_name']} to {dest_stop['stop_name']}",
            transit_line=line_name,
            transit_route_id=str(route_id) if route_id else None,
            color=color,
            board_stop_id=origin_stop["stop_id"],
            alight_stop_id=dest_stop["stop_id"],
        )

        # Enrich with schedule data
        _enrich_transit_segment(transit_seg, gtfs, route_id, origin_stop, dest_stop, now, app_state)

        segments.append(transit_seg)
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
            pred_mode = "streetcar"  # LRT treated as streetcar/surface for now
        elif len(str(route_id)) > 1 and str(route_id) not in ["1", "2", "4"]:
            rt_str = str(route_id)
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

        # Transit stress
        transfers = transit_route.get("transfers", 0) if transit_route else 0
        stress_score = 0.2 + transfers * 0.1 + prediction["delay_probability"] * 0.3

        cost = calculate_cost(RouteMode.TRANSIT, transit_dist)
        # Add gas cost if we drove to/from station
        if extra_gas_cost > 0:
            cost.gas = round(extra_gas_cost, 2)
            cost.total = round(cost.fare + cost.gas + cost.parking, 2)

        # Compute route-level departure/arrival from transit segment schedule
        route_departure = now.strftime("%H:%M")
        route_arrival = None
        transit_segs = [s for s in segments if s.mode == RouteMode.TRANSIT]
        if transit_segs and transit_segs[0].departure_time:
            first_transit_dep = transit_segs[0].departure_time
            walk_before = sum(s.duration_min for s in segments if s == segments[0] and s.mode != RouteMode.TRANSIT)
            try:
                dep_parts = first_transit_dep.split(":")
                dep_min = int(dep_parts[0]) * 60 + int(dep_parts[1])
                walk_after = sum(s.duration_min for s in segments[len(segments)-1:] if s.mode != RouteMode.TRANSIT)
                arr_min = dep_min + round(transit_dur) + round(walk_after)
                route_arrival = f"{(arr_min // 60) % 24:02d}:{arr_min % 60:02d}"
            except (ValueError, IndexError):
                pass

        routes.append(RouteOption(
            id=str(uuid.uuid4())[:8],
            label="",
            mode=RouteMode.TRANSIT,
            segments=segments,
            total_distance_km=round(total_dist, 2),
            total_duration_min=round(total_duration, 1),
            cost=cost,
            delay_info=delay_info,
            stress_score=round(min(1.0, stress_score), 2),
            departure_time=route_departure,
            arrival_time=route_arrival,
            summary=f"Transit via {origin_stop['stop_name']} → {dest_stop['stop_name']}",
        ))

    # Always try bus routes for diversity (regardless of whether rapid transit was found)
    bus_routes = find_bus_routes_between(
        gtfs, origin.lat, origin.lng, destination.lat, destination.lng,
        radius_km=1.5, limit=2,
    )
    for bus_info in bus_routes:
        bus_route = await _build_bus_route(
            origin, destination, bus_info, gtfs, predictor,
            is_adverse, now, http_client=http_client, weather=weather,
            app_state=app_state,
        )
        if bus_route:
            routes.append(bus_route)

    if not routes:
        logger.info("No valid transit route found (no rapid transit, transfer, or bus route)")

    return routes


async def _build_bus_route(
    origin: Coordinate,
    destination: Coordinate,
    bus_info: dict,
    gtfs: dict,
    predictor: DelayPredictor,
    is_adverse: bool,
    now: datetime,
    http_client=None,
    weather: Optional[dict] = None,
    app_state: Optional[dict] = None,
) -> Optional[RouteOption]:
    """Build a transit route option using a bus/streetcar route.

    bus_info comes from find_bus_routes_between() and contains:
        board_stop, alight_stop, route_id, route_name, route_type,
        distance_km, duration_min, geometry, intermediate_stops
    """
    board_stop = bus_info["board_stop"]
    alight_stop = bus_info["alight_stop"]
    route_name = bus_info["route_name"]
    route_id = bus_info["route_id"]

    segments: list[RouteSegment] = []
    total_duration = 0.0
    total_dist = 0.0

    board_coord = Coordinate(lat=board_stop["lat"], lng=board_stop["lng"])
    alight_coord = Coordinate(lat=alight_stop["lat"], lng=alight_stop["lng"])

    # Walk to boarding stop
    walk_to_geo = await _mapbox_directions(origin, board_coord, "walking", http_client=http_client)
    walk_to_dist = walk_to_geo["distance_km"] if walk_to_geo else board_stop["distance_km"]
    walk_to_dur = walk_to_geo["duration_min"] if walk_to_geo else _estimate_duration(walk_to_dist, RouteMode.WALKING)

    segments.append(RouteSegment(
        mode=RouteMode.WALKING,
        geometry=walk_to_geo["geometry"] if walk_to_geo else _straight_line_geometry(origin, board_coord),
        distance_km=round(walk_to_dist, 2),
        duration_min=round(walk_to_dur, 1),
        instructions=f"Walk to {board_stop['stop_name']}",
        color="#10B981",
        steps=_make_direction_steps(walk_to_geo.get("steps", [])) if walk_to_geo else [],
    ))
    total_duration += walk_to_dur
    total_dist += walk_to_dist

    # Bus/streetcar transit segment
    transit_dist = bus_info["distance_km"]
    transit_dur = bus_info["duration_min"]

    # Determine color
    route_type = bus_info.get("route_type", 3)
    if route_type == 0:
        color = "#DE7731"  # Streetcar/tram
    else:
        color = "#DA291C"  # Bus

    transit_seg = RouteSegment(
        mode=RouteMode.TRANSIT,
        geometry=bus_info["geometry"],
        distance_km=round(transit_dist, 2),
        duration_min=round(transit_dur, 1),
        instructions=f"Take {route_name} from {board_stop['stop_name']} to {alight_stop['stop_name']}",
        transit_line=route_name,
        transit_route_id=route_id,
        color=color,
        board_stop_id=board_stop["stop_id"],
        alight_stop_id=alight_stop["stop_id"],
        intermediate_stops=bus_info.get("intermediate_stops"),
    )

    # Enrich with schedule data
    _enrich_transit_segment(transit_seg, gtfs, route_id, board_stop, alight_stop, now, app_state)

    segments.append(transit_seg)
    total_duration += transit_dur
    total_dist += transit_dist

    # Walk from alighting stop to destination
    walk_from_geo = await _mapbox_directions(alight_coord, destination, "walking", http_client=http_client)
    walk_from_dist = walk_from_geo["distance_km"] if walk_from_geo else alight_stop["distance_km"]
    walk_from_dur = walk_from_geo["duration_min"] if walk_from_geo else _estimate_duration(walk_from_dist, RouteMode.WALKING)

    segments.append(RouteSegment(
        mode=RouteMode.WALKING,
        geometry=walk_from_geo["geometry"] if walk_from_geo else _straight_line_geometry(alight_coord, destination),
        distance_km=round(walk_from_dist, 2),
        duration_min=round(walk_from_dur, 1),
        instructions=f"Walk from {alight_stop['stop_name']} to destination",
        color="#10B981",
        steps=_make_direction_steps(walk_from_geo.get("steps", [])) if walk_from_geo else [],
    ))
    total_duration += walk_from_dur
    total_dist += walk_from_dist

    # Delay prediction
    pred_mode = "streetcar" if route_type == 0 else "bus"
    _w = weather or {}
    prediction = predictor.predict(
        line=route_id,
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

    stress_score = 0.25 + prediction["delay_probability"] * 0.3
    if is_adverse:
        stress_score += 0.15

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
        summary=f"Bus {route_name} via {board_stop['stop_name']} → {alight_stop['stop_name']}",
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

    # Bearing check: station should be roughly in the direction of the destination
    trip_bearing = _bearing(origin.lat, origin.lng, destination.lat, destination.lng)
    station_bearing = _bearing(origin.lat, origin.lng, station_lat, station_lng)
    bearing_deviation = _bearing_diff(trip_bearing, station_bearing)
    if bearing_deviation > 90:
        return -1.0  # Station is in the wrong direction
    if bearing_deviation > 60:
        base_penalty = -0.3  # Significant detour — applied below
    else:
        base_penalty = 0.0

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

    base_score = ratio_score * 0.4 + direction_score * 0.4 + base_penalty

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
    allowed_agencies: Optional[list[str]] = None,
    max_drive_radius_km: float = 15.0,
) -> list[RouteOption]:
    """Generate 1-3 hybrid (drive + transit) routes via multiple station candidates.

    Uses rapid transit stations only (no bus stops), with parking verification
    and service alert awareness.
    """
    alerts = (app_state or {}).get("alerts", [])

    # --- 1. Gather station candidates (rapid transit only) ---
    # TTC subway/LRT stations from GTFS (filtered to route_type 0/1/2)
    gtfs_stops = find_nearest_rapid_transit_stations(
        gtfs, origin.lat, origin.lng, radius_km=max_drive_radius_km, limit=15
    )
    gtfs_stops = [s for s in gtfs_stops if s["distance_km"] > 0.5]

    # GO/rail stations from OTP index (if available)
    otp_stations = []
    if otp_available and http_client:
        try:
            otp_stations = await find_park_and_ride_stations(
                origin.lat, origin.lng, radius_km=max_drive_radius_km, http_client=http_client,
            )
        except Exception as e:
            logger.warning(f"OTP station search failed: {e}")

    # Parking-only stations from hardcoded database (catches GO stations OTP might miss)
    parking_stations = find_stations_with_parking(
        origin.lat, origin.lng, radius_km=max_drive_radius_km
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

    # Filter candidates by allowed agencies
    if allowed_agencies is not None:
        candidates = [c for c in candidates if c.get("agencyName", "TTC") in allowed_agencies]

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

        # Skip departure lookup during scoring (4.2M row scan per stop is too slow).
        # Frequency bonus is minor — distance and parking matter more.
        next_dep_min = None

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

    max_candidates = min(3, len(scored))
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
            allowed_agencies=allowed_agencies,
        )
        for candidate in top_candidates
    ]

    results = await asyncio.gather(*route_tasks, return_exceptions=True)

    hybrid_routes = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Hybrid route generation failed: {result}")
        elif result:
            if _validate_hybrid_route(result, origin, destination, total_distance):
                hybrid_routes.append(result)
            else:
                logger.info(f"Hybrid route via {result.summary} rejected by validation")

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
    allowed_agencies: Optional[list[str]] = None,
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
        # Compute banned agencies for OTP transit leg
        all_agencies = {"TTC", "GO Transit", "YRT", "MiWay", "UP Express"}
        banned_for_otp = None
        if allowed_agencies is not None:
            banned = all_agencies - set(allowed_agencies)
            if banned:
                banned_for_otp = list(banned)

        try:
            otp_itineraries = await query_otp_routes(
                station_coord, destination, now, num_itineraries=3, http_client=http_client,
                banned_agencies=banned_for_otp,
            )
            if otp_itineraries:
                itin = min(otp_itineraries, key=lambda i: i.get("duration", float("inf")))
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
        # Heuristic fallback — find dest stops and prefer same-line connectivity
        dest_stops = find_nearest_stops(gtfs, destination.lat, destination.lng, radius_km=3.0, limit=5)

        # Score dest stops: strongly prefer stops on the same line as park station
        park_rid = str(park_stop.get("route_id") or "")
        dest_stop = None
        if dest_stops:
            best_dest = None
            best_dest_score = float('inf')
            for ds in dest_stops:
                ds_rid = str(ds.get("route_id") or "")
                sc = ds["distance_km"]
                if park_rid and ds_rid == park_rid:
                    sc -= 10  # Same line — strongly prefer
                if best_dest is None or sc < best_dest_score:
                    best_dest_score = sc
                    best_dest = ds
            dest_stop = best_dest

            # If no same-line connection and park station is LRT (5/6),
            # skip this hybrid — LRT lines have limited coverage
            if park_rid in ("5", "6"):
                ds_rid = str(dest_stop.get("route_id") or "")
                if ds_rid != park_rid:
                    logger.info(f"Skipping hybrid via {park_stop['stop_name']}: LRT line {park_rid} doesn't serve destination area")
                    return None

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
                color="#F0CC49",
            )]
        else:
            # Build heuristic transit + walk segments
            transit_route = find_transit_route(gtfs, park_stop["stop_id"], dest_stop["stop_id"],
                                               route_id=park_stop.get("route_id"))
            if not transit_route:
                logger.info(f"Hybrid heuristic: no transit route from {park_stop['stop_name']} to {dest_stop.get('stop_name', '?')}")
                return None
            transit_dist = transit_route["distance_km"]
            transit_dur = transit_route["estimated_duration_min"]

            transit_geometry = transit_route.get("geometry", _straight_line_geometry(
                station_coord, Coordinate(lat=dest_stop["lat"], lng=dest_stop["lng"])
            ))

            line_colors = {"1": "#F0CC49", "2": "#549F4D", "4": "#9C246E", "5": "#DE7731", "6": "#959595"}
            color = line_colors.get(str(route_id), "#F0CC49")

            hybrid_transit_seg = RouteSegment(
                mode=RouteMode.TRANSIT,
                geometry=transit_geometry,
                distance_km=round(transit_dist, 2),
                duration_min=round(transit_dur, 1),
                instructions=f"Take {transit_label} from {park_stop['stop_name']} to {dest_stop['stop_name']}",
                transit_line=transit_label,
                transit_route_id=str(route_id) if route_id else None,
                color=color,
                board_stop_id=park_stop["stop_id"],
                alight_stop_id=dest_stop["stop_id"],
            )
            _enrich_transit_segment(
                hybrid_transit_seg, gtfs, route_id, park_stop, dest_stop, now,
            )
            transit_segments.append(hybrid_transit_seg)

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
            transit_route = find_transit_route(gtfs, seg_req.start_station_id, seg_req.end_station_id,
                                               route_id=getattr(seg_req, 'route_id', None))
            t_dist = transit_route["distance_km"] if transit_route else haversine(
                start_coord.lat, start_coord.lng, end_coord.lat, end_coord.lng
            )
            t_dur = transit_route["estimated_duration_min"] if transit_route else _estimate_duration(t_dist, RouteMode.TRANSIT)
            t_geom = transit_route.get("geometry") if transit_route else _straight_line_geometry(start_coord, end_coord)

            line_info = TTC_LINE_INFO.get(seg_req.line_id, {})
            line_name = line_info.get("name", f"Line {seg_req.line_id}")
            line_color = line_info.get("color", "#F0CC49")

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
            # Extract transit lines from segments
            transit_segs = [s for s in route.segments if s.transit_line]
            if len(transit_segs) >= 2:
                # Multi-line transfer route
                line_names = []
                for ts in transit_segs:
                    name = ts.transit_line or "Transit"
                    # Shorten "Line 1 Yonge-University" to "Line 1" for label
                    if name.startswith("Line ") and len(name) > 6:
                        short = name.split()[0] + " " + name.split()[1]
                        line_names.append(short)
                    else:
                        line_names.append(name)
                route.label = f"Transit via {' → '.join(line_names)}"
            elif transit_segs:
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
                transit_route = find_transit_route(gtfs, seg_req.board_stop_id, seg_req.alight_stop_id,
                                                   route_id=getattr(seg_req, 'route_id', None))
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
