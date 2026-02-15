"""Transit route suggestion engine for the custom route builder.

Provides smart suggestions of transit routes (subway lines, bus routes, streetcars)
relevant to a user's origin/destination trip. Uses OTP when available, falls back to
GTFS data analysis.
"""

import logging
import math
import uuid
from typing import Optional

import httpx

from app.models import Coordinate, TransitRouteSuggestion

logger = logging.getLogger("fluxroute.suggestions")

# Subway line colors
_LINE_COLORS = {
    "1": "#FFCC00",
    "2": "#00A651",
    "4": "#A8518A",
    "5": "#FF6600",
    "6": "#808080",
}

# Transit mode display colors (non-subway)
_MODE_COLORS = {
    "BUS": "#DA291C",
    "TRAM": "#FF6600",
    "RAIL": "#3D8B37",
}

# TTC interchange stations where passengers can transfer between lines
TTC_TRANSFER_STATIONS = [
    {"name": "Bloor-Yonge",    "lines": ["1", "2"], "stop_ids": {"1": "YU_BLRY", "2": "BD_BLRY"}, "lat": 43.6709, "lng": -79.3857},
    {"name": "St George",      "lines": ["1", "2"], "stop_ids": {"1": "YU_STGR", "2": "BD_STGR"}, "lat": 43.6683, "lng": -79.3997},
    {"name": "Spadina",        "lines": ["1", "2"], "stop_ids": {"1": "YU_SPAD", "2": "BD_SPAD"}, "lat": 43.6672, "lng": -79.4037},
    {"name": "Sheppard-Yonge", "lines": ["1", "4"], "stop_ids": {"1": "YU_SHEPY", "4": "SH_SHPY"}, "lat": 43.7615, "lng": -79.4111},
    {"name": "Cedarvale",      "lines": ["1", "5"], "stop_ids": {"1": "YU_CDRV", "5": "EC_CDVL"}, "lat": 43.6989, "lng": -79.4356},
    {"name": "Eglinton",       "lines": ["1", "5"], "stop_ids": {"1": "YU_EGLN", "5": "EC_EGLN"}, "lat": 43.7064, "lng": -79.3988},
    {"name": "Kennedy",        "lines": ["2", "5"], "stop_ids": {"2": "BD_KNDY", "5": "EC_KNDY"}, "lat": 43.7326, "lng": -79.2637},
    {"name": "Finch West",     "lines": ["1", "6"], "stop_ids": {"1": "YU_FNWT", "6": "FW_FNCH"}, "lat": 43.7649, "lng": -79.4912},
]

# Directional suffixes to strip from stop names
_DIRECTION_SUFFIXES = [
    " Eastbound Platform",
    " Westbound Platform",
    " Northbound Platform",
    " Southbound Platform",
    " - Eastbound",
    " - Westbound",
    " - Northbound",
    " - Southbound",
    " Eastbound",
    " Westbound",
    " Northbound",
    " Southbound",
    " Platform",
    " Station",
]


def _clean_stop_name(name: str) -> str:
    """Strip directional suffixes and 'Station' from OTP stop names."""
    cleaned = name.strip()
    for suffix in _DIRECTION_SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute bearing in degrees from point 1 to point 2."""
    dlng = math.radians(lng2 - lng1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    x = math.sin(dlng) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlng)
    bearing_deg = math.degrees(math.atan2(x, y))
    return (bearing_deg + 360) % 360


def _bearing_to_direction(bearing: float) -> str:
    """Convert bearing to cardinal direction string."""
    if bearing < 45 or bearing >= 315:
        return "Northbound"
    elif bearing < 135:
        return "Eastbound"
    elif bearing < 225:
        return "Southbound"
    else:
        return "Westbound"


def _bearing_diff(b1: float, b2: float) -> float:
    """Absolute angular difference between two bearings (0-180)."""
    diff = abs(b1 - b2) % 360
    return min(diff, 360 - diff)


async def get_transit_suggestions(
    origin: Coordinate,
    destination: Coordinate,
    gtfs: dict,
    http_client: Optional[httpx.AsyncClient] = None,
    otp_available: bool = False,
) -> tuple[list[TransitRouteSuggestion], str]:
    """Get transit route suggestions for a trip.

    Returns (suggestions, source) where source is "otp", "gtfs", or "otp+gemini".
    """
    suggestions: list[TransitRouteSuggestion] = []
    source = "gtfs"

    # Try OTP first
    if otp_available and http_client:
        otp_suggestions = await _suggestions_from_otp(origin, destination, http_client)
        if otp_suggestions:
            suggestions = otp_suggestions
            source = "otp"
            logger.info(f"Got {len(suggestions)} suggestions from OTP")

    # GTFS fallback (or supplement OTP results)
    gtfs_suggestions = _suggestions_from_gtfs(origin, destination, gtfs)
    if gtfs_suggestions:
        if not suggestions:
            suggestions = gtfs_suggestions
            source = "gtfs"
        else:
            # Merge: add GTFS suggestions not already covered by OTP
            existing_routes = {s.route_id for s in suggestions}
            for gs in gtfs_suggestions:
                if gs.route_id not in existing_routes:
                    suggestions.append(gs)

    # Add transfer-based suggestions (multi-line with interchange)
    transfer_sug = _transfer_suggestions(origin, destination)
    if transfer_sug:
        suggestions.extend(transfer_sug)

    # Deduplicate by route_id (keep first occurrence), but skip transfer group suggestions
    seen = set()
    deduped = []
    for s in suggestions:
        if s.transfer_group_id:
            # Always keep transfer pair suggestions (dedup handled by group_id)
            deduped.append(s)
        elif s.route_id not in seen:
            seen.add(s.route_id)
            deduped.append(s)
    suggestions = deduped

    # Sort: subway first, then by estimated duration; keep transfer pairs together
    mode_order = {"SUBWAY": 0, "TRAM": 1, "BUS": 2, "RAIL": 0}
    suggestions.sort(key=lambda s: (
        mode_order.get(s.transit_mode, 3),
        s.transfer_sequence or 0,
        s.estimated_duration_min,
    ))

    # Limit to 20 suggestions
    suggestions = suggestions[:20]

    logger.info(f"Returning {len(suggestions)} transit suggestions (source={source})")
    return suggestions, source


async def _suggestions_from_otp(
    origin: Coordinate,
    destination: Coordinate,
    http_client: httpx.AsyncClient,
) -> list[TransitRouteSuggestion]:
    """Extract transit route suggestions from OTP itineraries."""
    import os
    from datetime import datetime

    base = os.getenv("OTP_BASE_URL", "http://localhost:8080")
    now = datetime.now()

    params = {
        "fromPlace": f"{origin.lat},{origin.lng}",
        "toPlace": f"{destination.lat},{destination.lng}",
        "mode": "TRANSIT,WALK",
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "numItineraries": "5",
        "walkReluctance": "2",
        "maxWalkDistance": "2000",
        "arriveBy": "false",
    }

    try:
        resp = await http_client.get(
            f"{base}/otp/routers/default/plan", params=params, timeout=5.0
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"OTP suggestion query failed: {e}")
        return []

    plan = data.get("plan")
    if not plan:
        return []

    itineraries = plan.get("itineraries", [])
    suggestions = []
    seen_routes = set()

    for itin in itineraries:
        for leg in itin.get("legs", []):
            mode = leg.get("mode", "WALK")
            if mode in ("WALK", "CAR", "BICYCLE"):
                continue

            route_short = leg.get("routeShortName", "")
            route_long = leg.get("routeLongName", "")
            route_id_raw = leg.get("routeId", "")
            agency = leg.get("agencyName", "")

            # Build a unique key
            key = f"{agency}:{route_short or route_long}"
            if key in seen_routes:
                continue
            seen_routes.add(key)

            # Extract board/alight info
            from_stop = leg.get("from", {})
            to_stop = leg.get("to", {})
            board_name = _clean_stop_name(from_stop.get("name", ""))
            alight_name = _clean_stop_name(to_stop.get("name", ""))
            board_coord = Coordinate(lat=from_stop.get("lat", 0), lng=from_stop.get("lon", 0))
            alight_coord = Coordinate(lat=to_stop.get("lat", 0), lng=to_stop.get("lon", 0))
            board_stop_id = from_stop.get("stopId") or from_stop.get("stop_id")
            alight_stop_id = to_stop.get("stopId") or to_stop.get("stop_id")

            # Determine transit mode
            transit_mode = "BUS"
            if mode == "SUBWAY":
                transit_mode = "SUBWAY"
            elif mode == "TRAM":
                transit_mode = "TRAM"
            elif mode == "RAIL":
                transit_mode = "RAIL"

            # Display name
            if route_short and route_long:
                display_name = f"{route_short} {route_long}"
            elif route_short:
                display_name = route_short
            elif route_long:
                display_name = route_long
            else:
                display_name = f"{agency} {mode}"

            # Color
            route_color = leg.get("routeColor")
            if route_color:
                color = f"#{route_color}" if not route_color.startswith("#") else route_color
            elif transit_mode == "SUBWAY":
                # Try to match to TTC line by route short name
                color = _LINE_COLORS.get(route_short, "#FFCC00")
            else:
                color = _MODE_COLORS.get(transit_mode, "#DA291C")

            # Direction
            leg_bearing = _bearing(board_coord.lat, board_coord.lng, alight_coord.lat, alight_coord.lng)
            direction = _bearing_to_direction(leg_bearing)

            # Duration/distance
            duration = leg.get("duration", 0) / 60
            distance = leg.get("distance", 0) / 1000

            suggestions.append(TransitRouteSuggestion(
                suggestion_id=str(uuid.uuid4())[:8],
                route_id=route_id_raw or route_short,
                display_name=display_name,
                transit_mode=transit_mode,
                color=color,
                board_stop_name=board_name,
                board_coord=board_coord,
                board_stop_id=str(board_stop_id) if board_stop_id else None,
                alight_stop_name=alight_name,
                alight_coord=alight_coord,
                alight_stop_id=str(alight_stop_id) if alight_stop_id else None,
                direction_hint=direction,
                relevance_reason=f"Used in OTP itinerary ({agency})" if agency else "OTP suggested route",
                estimated_duration_min=round(duration, 1),
                estimated_distance_km=round(distance, 2),
            ))

    return suggestions


def _suggestions_from_gtfs(
    origin: Coordinate,
    destination: Coordinate,
    gtfs: dict,
) -> list[TransitRouteSuggestion]:
    """Generate transit suggestions from loaded GTFS data.

    Finds routes that serve stops near both origin and destination,
    filtered by direction compatibility.
    """
    import pandas as pd
    from app.gtfs_parser import find_nearest_stops

    suggestions = []
    trip_bearing = _bearing(origin.lat, origin.lng, destination.lat, destination.lng)
    trip_distance = _haversine(origin.lat, origin.lng, destination.lat, destination.lng)

    # Find stops near origin and destination
    origin_radius = min(3.0, max(1.0, trip_distance * 0.3))
    dest_radius = min(3.0, max(1.0, trip_distance * 0.3))

    origin_stops = find_nearest_stops(gtfs, origin.lat, origin.lng, radius_km=origin_radius, limit=20)
    dest_stops = find_nearest_stops(gtfs, destination.lat, destination.lng, radius_km=dest_radius, limit=20)

    if not origin_stops or not dest_stops:
        # Widen search
        origin_stops = find_nearest_stops(gtfs, origin.lat, origin.lng, radius_km=5.0, limit=30)
        dest_stops = find_nearest_stops(gtfs, destination.lat, destination.lng, radius_km=5.0, limit=30)

    if not origin_stops or not dest_stops:
        return _subway_line_fallback(origin, destination)

    origin_stop_ids = {s["stop_id"] for s in origin_stops}
    dest_stop_ids = {s["stop_id"] for s in dest_stops}

    # Look up routes serving these stops via stop_times + trips
    stop_times_df = gtfs.get("stop_times")
    trips_df = gtfs.get("trips")
    routes_df = gtfs.get("routes")

    if stop_times_df is None or trips_df is None or routes_df is None:
        return _subway_line_fallback(origin, destination)

    # Find trip_ids that visit origin stops
    origin_trips = stop_times_df[stop_times_df["stop_id"].isin(origin_stop_ids)][["trip_id", "stop_id", "stop_sequence"]].copy()
    if origin_trips.empty:
        return _subway_line_fallback(origin, destination)

    # Find trip_ids that also visit destination stops
    dest_trips = stop_times_df[stop_times_df["stop_id"].isin(dest_stop_ids)][["trip_id", "stop_id", "stop_sequence"]].copy()
    if dest_trips.empty:
        return _subway_line_fallback(origin, destination)

    # Find trips that serve BOTH origin and destination areas
    common_trip_ids = set(origin_trips["trip_id"]) & set(dest_trips["trip_id"])
    if not common_trip_ids:
        return _subway_line_fallback(origin, destination)

    # Filter to trips where origin stop comes before destination stop
    origin_trips = origin_trips[origin_trips["trip_id"].isin(common_trip_ids)]
    dest_trips = dest_trips[dest_trips["trip_id"].isin(common_trip_ids)]

    # Merge to find valid (trip, origin_stop, dest_stop) combos
    merged = origin_trips.merge(dest_trips, on="trip_id", suffixes=("_origin", "_dest"))
    merged = merged[merged["stop_sequence_origin"] < merged["stop_sequence_dest"]]

    if merged.empty:
        return _subway_line_fallback(origin, destination)

    # Get route_ids for these trips
    trip_route_map = trips_df.set_index("trip_id")["route_id"].to_dict()
    merged["route_id"] = merged["trip_id"].map(trip_route_map)
    merged = merged.dropna(subset=["route_id"])

    # Group by route_id — pick the best origin/dest stop pair per route
    origin_stop_map = {s["stop_id"]: s for s in origin_stops}
    dest_stop_map = {s["stop_id"]: s for s in dest_stops}

    route_info = {}
    if routes_df is not None and not routes_df.empty:
        for _, row in routes_df.iterrows():
            rid = str(row.get("route_id", ""))
            route_info[rid] = {
                "route_short_name": str(row.get("route_short_name", "")),
                "route_long_name": str(row.get("route_long_name", "")),
                "route_type": int(row.get("route_type", 3)),
                "route_color": str(row.get("route_color", "")) if pd.notna(row.get("route_color")) else "",
            }

    seen_routes = set()
    for route_id_val in merged["route_id"].unique():
        route_id_str = str(route_id_val)
        if route_id_str in seen_routes:
            continue
        seen_routes.add(route_id_str)

        route_rows = merged[merged["route_id"] == route_id_val]
        # Pick the pair with closest origin stop
        best_row = None
        best_origin_dist = float("inf")
        for _, row in route_rows.iterrows():
            o_stop = origin_stop_map.get(row["stop_id_origin"])
            if o_stop and o_stop["distance_km"] < best_origin_dist:
                best_origin_dist = o_stop["distance_km"]
                best_row = row

        if best_row is None:
            continue

        o_stop = origin_stop_map.get(best_row["stop_id_origin"])
        d_stop = dest_stop_map.get(best_row["stop_id_dest"])
        if not o_stop or not d_stop:
            continue

        # Direction check: bearing from board to alight should roughly match trip bearing
        seg_bearing = _bearing(o_stop["lat"], o_stop["lng"], d_stop["lat"], d_stop["lng"])
        if _bearing_diff(seg_bearing, trip_bearing) > 90:
            continue

        # Build suggestion
        rinfo = route_info.get(route_id_str, {})
        short_name = rinfo.get("route_short_name", "")
        long_name = rinfo.get("route_long_name", "")
        route_type = rinfo.get("route_type", 3)

        # Determine transit mode from GTFS route_type
        # 0 = Tram/Streetcar/LRT, 1 = Subway/Metro, 2 = Rail, 3 = Bus
        if route_type == 1:
            transit_mode = "SUBWAY"
        elif route_type == 0:
            transit_mode = "TRAM"
        elif route_type == 2:
            transit_mode = "RAIL"
        else:
            transit_mode = "BUS"

        # Display name
        if short_name and long_name:
            display_name = f"{short_name} {long_name}"
        elif short_name:
            display_name = short_name
        elif long_name:
            display_name = long_name
        else:
            display_name = f"Route {route_id_str}"

        # Color
        route_color = rinfo.get("route_color", "")
        if route_color:
            color = f"#{route_color}" if not route_color.startswith("#") else route_color
        elif transit_mode == "SUBWAY":
            color = _LINE_COLORS.get(short_name, "#FFCC00")
        else:
            color = _MODE_COLORS.get(transit_mode, "#DA291C")

        direction = _bearing_to_direction(seg_bearing)
        est_dist = _haversine(o_stop["lat"], o_stop["lng"], d_stop["lat"], d_stop["lng"])
        # Speed estimates: subway 35km/h, bus 20km/h, tram 18km/h
        speed = {"SUBWAY": 35, "RAIL": 40, "TRAM": 18, "BUS": 20}.get(transit_mode, 20)
        est_dur = (est_dist / speed) * 60

        board_name = _clean_stop_name(o_stop.get("stop_name", ""))
        alight_name = _clean_stop_name(d_stop.get("stop_name", ""))

        # Get intermediate stops for accurate distance
        from app.gtfs_parser import get_intermediate_stops
        board_sid = str(o_stop.get("stop_id", ""))
        alight_sid = str(d_stop.get("stop_id", ""))
        intermediate = get_intermediate_stops(gtfs, route_id_str, board_sid, alight_sid)

        # If we have intermediate stops, compute more accurate distance
        if len(intermediate) >= 2:
            est_dist = 0.0
            for k in range(len(intermediate) - 1):
                est_dist += _haversine(
                    intermediate[k]["lat"], intermediate[k]["lng"],
                    intermediate[k + 1]["lat"], intermediate[k + 1]["lng"],
                )
            est_dur = (est_dist / speed) * 60

        suggestions.append(TransitRouteSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            route_id=route_id_str,
            display_name=display_name,
            transit_mode=transit_mode,
            color=color,
            board_stop_name=board_name,
            board_coord=Coordinate(lat=o_stop["lat"], lng=o_stop["lng"]),
            board_stop_id=board_sid,
            alight_stop_name=alight_name,
            alight_coord=Coordinate(lat=d_stop["lat"], lng=d_stop["lng"]),
            alight_stop_id=alight_sid,
            direction_hint=direction,
            relevance_reason=f"Serves stops near your origin and destination",
            estimated_duration_min=round(est_dur, 1),
            estimated_distance_km=round(est_dist, 2),
            intermediate_stops=intermediate,
        ))

    # Always include relevant subway lines from fallback if not already present
    fallback = _subway_line_fallback(origin, destination)
    existing_names = {s.display_name for s in suggestions}
    for fb in fallback:
        if fb.display_name not in existing_names:
            suggestions.append(fb)

    return suggestions


def _subway_line_fallback(
    origin: Coordinate,
    destination: Coordinate,
) -> list[TransitRouteSuggestion]:
    """Hardcoded subway line suggestions as ultimate fallback.

    Determines which subway lines are relevant based on origin/destination geography.
    """
    from app.gtfs_parser import TTC_SUBWAY_STATIONS

    suggestions = []
    trip_bearing = _bearing(origin.lat, origin.lng, destination.lat, destination.lng)

    # Line definitions with key stations and rough corridors
    lines = [
        {
            "id": "1", "name": "Line 1 Yonge-University", "color": "#FFCC00",
            "corridor": "north-south", "mode": "SUBWAY",
            "lat_range": (43.6, 43.81), "lng_range": (-79.46, -79.37),
        },
        {
            "id": "2", "name": "Line 2 Bloor-Danforth", "color": "#00A651",
            "corridor": "east-west", "mode": "SUBWAY",
            "lat_range": (43.63, 43.67), "lng_range": (-79.54, -79.29),
        },
        {
            "id": "4", "name": "Line 4 Sheppard", "color": "#A8518A",
            "corridor": "east-west", "mode": "SUBWAY",
            "lat_range": (43.76, 43.78), "lng_range": (-79.42, -79.33),
        },
        {
            "id": "5", "name": "Line 5 Eglinton", "color": "#FF6600",
            "corridor": "east-west", "mode": "TRAM",
            "lat_range": (43.68, 43.74), "lng_range": (-79.50, -79.26),
        },
        {
            "id": "6", "name": "Line 6 Finch West", "color": "#808080",
            "corridor": "east-west", "mode": "TRAM",
            "lat_range": (43.72, 43.77), "lng_range": (-79.61, -79.49),
        },
    ]

    for line in lines:
        lat_min, lat_max = line["lat_range"]
        lng_min, lng_max = line["lng_range"]

        # Check if origin or destination is near this line's corridor
        origin_near = (lat_min - 0.03 <= origin.lat <= lat_max + 0.03 and
                       lng_min - 0.03 <= origin.lng <= lng_max + 0.03)
        dest_near = (lat_min - 0.03 <= destination.lat <= lat_max + 0.03 and
                     lng_min - 0.03 <= destination.lng <= lng_max + 0.03)

        if not (origin_near or dest_near):
            continue

        # Find stations on this line (TTC_SUBWAY_STATIONS is a flat list, filter by route_id)
        line_stations = [s for s in TTC_SUBWAY_STATIONS if str(s.get("route_id")) == line["id"]]
        if not line_stations:
            continue

        # Find closest station to origin and destination
        # Note: TTC_SUBWAY_STATIONS uses stop_lat/stop_lon fields
        board_station = min(line_stations, key=lambda s: _haversine(origin.lat, origin.lng, s["stop_lat"], s["stop_lon"]))
        alight_station = min(line_stations, key=lambda s: _haversine(destination.lat, destination.lng, s["stop_lat"], s["stop_lon"]))

        if board_station["stop_id"] == alight_station["stop_id"]:
            continue

        # Check direction makes sense
        seg_bearing = _bearing(board_station["stop_lat"], board_station["stop_lon"], alight_station["stop_lat"], alight_station["stop_lon"])
        if _bearing_diff(seg_bearing, trip_bearing) > 120:
            continue

        direction = _bearing_to_direction(seg_bearing)

        # Get intermediate stops for accurate distance
        board_sid = board_station["stop_id"]
        alight_sid = alight_station["stop_id"]
        # Build intermediate stops from TTC_SUBWAY_STATIONS
        board_idx = next((idx for idx, s in enumerate(line_stations) if s["stop_id"] == board_sid), None)
        alight_idx = next((idx for idx, s in enumerate(line_stations) if s["stop_id"] == alight_sid), None)
        intermediate: list[dict] = []
        if board_idx is not None and alight_idx is not None:
            lo, hi = min(board_idx, alight_idx), max(board_idx, alight_idx)
            subset = line_stations[lo:hi + 1]
            if board_idx > alight_idx:
                subset = list(reversed(subset))
            intermediate = [
                {"stop_id": s["stop_id"], "stop_name": s["stop_name"],
                 "lat": s["stop_lat"], "lng": s["stop_lon"]}
                for s in subset
            ]

        # Compute distance through intermediate stops if available
        if len(intermediate) >= 2:
            est_dist = 0.0
            for k in range(len(intermediate) - 1):
                est_dist += _haversine(
                    intermediate[k]["lat"], intermediate[k]["lng"],
                    intermediate[k + 1]["lat"], intermediate[k + 1]["lng"],
                )
        else:
            est_dist = _haversine(board_station["stop_lat"], board_station["stop_lon"], alight_station["stop_lat"], alight_station["stop_lon"])

        speed = {"SUBWAY": 35, "TRAM": 18}.get(line["mode"], 35)
        est_dur = (est_dist / speed) * 60

        suggestions.append(TransitRouteSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            route_id=line["id"],
            display_name=line["name"],
            transit_mode=line["mode"],
            color=line["color"],
            board_stop_name=board_station["stop_name"],
            board_coord=Coordinate(lat=board_station["stop_lat"], lng=board_station["stop_lon"]),
            board_stop_id=board_sid,
            alight_stop_name=alight_station["stop_name"],
            alight_coord=Coordinate(lat=alight_station["stop_lat"], lng=alight_station["stop_lon"]),
            alight_stop_id=alight_sid,
            direction_hint=direction,
            relevance_reason="TTC subway line serving your corridor",
            estimated_duration_min=round(est_dur, 1),
            estimated_distance_km=round(est_dist, 2),
            intermediate_stops=intermediate,
        ))

    return suggestions


def _transfer_suggestions(
    origin: Coordinate,
    destination: Coordinate,
) -> list[TransitRouteSuggestion]:
    """Generate transfer-based suggestions across TTC interchange stations.

    For each transfer station that connects two lines, checks if it makes sense
    to ride Line A to the transfer station and then Line B to the destination
    (or vice versa). Returns paired suggestions linked by transfer_group_id.
    """
    from app.gtfs_parser import TTC_SUBWAY_STATIONS

    suggestions = []

    line_info = {
        "1": {"name": "Line 1 Yonge-University", "color": "#FFCC00", "mode": "SUBWAY"},
        "2": {"name": "Line 2 Bloor-Danforth", "color": "#00A651", "mode": "SUBWAY"},
        "4": {"name": "Line 4 Sheppard", "color": "#A8518A", "mode": "SUBWAY"},
        "5": {"name": "Line 5 Eglinton", "color": "#FF6600", "mode": "TRAM"},
        "6": {"name": "Line 6 Finch West", "color": "#808080", "mode": "TRAM"},
    }

    trip_bearing = _bearing(origin.lat, origin.lng, destination.lat, destination.lng)

    # Pre-index stations by line
    stations_by_line: dict[str, list[dict]] = {}
    for s in TTC_SUBWAY_STATIONS:
        lid = str(s.get("route_id", ""))
        stations_by_line.setdefault(lid, []).append(s)

    for xfer in TTC_TRANSFER_STATIONS:
        line_a, line_b = xfer["lines"][0], xfer["lines"][1]

        for first_line, second_line in [(line_a, line_b), (line_b, line_a)]:
            first_stations = stations_by_line.get(first_line, [])
            second_stations = stations_by_line.get(second_line, [])
            if not first_stations or not second_stations:
                continue

            # Find nearest station on first_line to origin
            board_station = min(
                first_stations,
                key=lambda s: _haversine(origin.lat, origin.lng, s["stop_lat"], s["stop_lon"]),
            )
            # Find nearest station on second_line to destination
            alight_station = min(
                second_stations,
                key=lambda s: _haversine(destination.lat, destination.lng, s["stop_lat"], s["stop_lon"]),
            )

            # Transfer station stop IDs on each line
            xfer_stop_first = xfer["stop_ids"].get(first_line)
            xfer_stop_second = xfer["stop_ids"].get(second_line)
            if not xfer_stop_first or not xfer_stop_second:
                continue

            # Viability checks
            board_sid = board_station["stop_id"]
            alight_sid = alight_station["stop_id"]

            # Don't suggest if boarding/alighting at the transfer station itself
            if board_sid == xfer_stop_first or alight_sid == xfer_stop_second:
                continue

            # Walking distance checks (origin to board, destination to alight)
            walk_to_board = _haversine(origin.lat, origin.lng, board_station["stop_lat"], board_station["stop_lon"])
            walk_from_alight = _haversine(destination.lat, destination.lng, alight_station["stop_lat"], alight_station["stop_lon"])
            if walk_to_board > 5.0 or walk_from_alight > 5.0:
                continue

            # Direction check: overall trip from board to alight via transfer should roughly match trip bearing
            overall_bearing = _bearing(board_station["stop_lat"], board_station["stop_lon"],
                                       alight_station["stop_lat"], alight_station["stop_lon"])
            if _bearing_diff(overall_bearing, trip_bearing) > 135:
                continue

            # Build intermediate stops for leg 1 (board → transfer)
            board_idx = next((i for i, s in enumerate(first_stations) if s["stop_id"] == board_sid), None)
            xfer_first_idx = next((i for i, s in enumerate(first_stations) if s["stop_id"] == xfer_stop_first), None)

            intermediate_1: list[dict] = []
            est_dist_1 = 0.0
            if board_idx is not None and xfer_first_idx is not None:
                lo, hi = min(board_idx, xfer_first_idx), max(board_idx, xfer_first_idx)
                subset = first_stations[lo:hi + 1]
                if board_idx > xfer_first_idx:
                    subset = list(reversed(subset))
                intermediate_1 = [
                    {"stop_id": s["stop_id"], "stop_name": s["stop_name"],
                     "lat": s["stop_lat"], "lng": s["stop_lon"]}
                    for s in subset
                ]
                for k in range(len(intermediate_1) - 1):
                    est_dist_1 += _haversine(
                        intermediate_1[k]["lat"], intermediate_1[k]["lng"],
                        intermediate_1[k + 1]["lat"], intermediate_1[k + 1]["lng"],
                    )
            if est_dist_1 == 0:
                est_dist_1 = _haversine(board_station["stop_lat"], board_station["stop_lon"], xfer["lat"], xfer["lng"])

            # Build intermediate stops for leg 2 (transfer → alight)
            xfer_second_idx = next((i for i, s in enumerate(second_stations) if s["stop_id"] == xfer_stop_second), None)
            alight_idx = next((i for i, s in enumerate(second_stations) if s["stop_id"] == alight_sid), None)

            intermediate_2: list[dict] = []
            est_dist_2 = 0.0
            if xfer_second_idx is not None and alight_idx is not None:
                lo, hi = min(xfer_second_idx, alight_idx), max(xfer_second_idx, alight_idx)
                subset = second_stations[lo:hi + 1]
                if xfer_second_idx > alight_idx:
                    subset = list(reversed(subset))
                intermediate_2 = [
                    {"stop_id": s["stop_id"], "stop_name": s["stop_name"],
                     "lat": s["stop_lat"], "lng": s["stop_lon"]}
                    for s in subset
                ]
                for k in range(len(intermediate_2) - 1):
                    est_dist_2 += _haversine(
                        intermediate_2[k]["lat"], intermediate_2[k]["lng"],
                        intermediate_2[k + 1]["lat"], intermediate_2[k + 1]["lng"],
                    )
            if est_dist_2 == 0:
                est_dist_2 = _haversine(xfer["lat"], xfer["lng"], alight_station["stop_lat"], alight_station["stop_lon"])

            # Compute durations
            first_info_d = line_info.get(first_line, {"name": first_line, "color": "#999", "mode": "SUBWAY"})
            second_info_d = line_info.get(second_line, {"name": second_line, "color": "#999", "mode": "SUBWAY"})
            speed_1 = {"SUBWAY": 35, "TRAM": 18}.get(first_info_d["mode"], 35)
            speed_2 = {"SUBWAY": 35, "TRAM": 18}.get(second_info_d["mode"], 35)
            est_dur_1 = (est_dist_1 / speed_1) * 60
            est_dur_2 = (est_dist_2 / speed_2) * 60

            # Direction hints per leg
            dir_1 = _bearing_to_direction(_bearing(
                board_station["stop_lat"], board_station["stop_lon"], xfer["lat"], xfer["lng"]
            ))
            dir_2 = _bearing_to_direction(_bearing(
                xfer["lat"], xfer["lng"], alight_station["stop_lat"], alight_station["stop_lon"]
            ))

            # Get the transfer station objects on each line
            xfer_station_first = next(
                (s for s in first_stations if s["stop_id"] == xfer_stop_first), None
            )
            xfer_station_second = next(
                (s for s in second_stations if s["stop_id"] == xfer_stop_second), None
            )
            if not xfer_station_first or not xfer_station_second:
                continue

            group_id = str(uuid.uuid4())[:8]

            # Leg 1: origin line → transfer station
            suggestions.append(TransitRouteSuggestion(
                suggestion_id=str(uuid.uuid4())[:8],
                route_id=first_line,
                display_name=first_info_d["name"],
                transit_mode=first_info_d["mode"],
                color=first_info_d["color"],
                board_stop_name=board_station["stop_name"],
                board_coord=Coordinate(lat=board_station["stop_lat"], lng=board_station["stop_lon"]),
                board_stop_id=board_sid,
                alight_stop_name=xfer_station_first["stop_name"],
                alight_coord=Coordinate(lat=xfer_station_first["stop_lat"], lng=xfer_station_first["stop_lon"]),
                alight_stop_id=xfer_stop_first,
                direction_hint=dir_1,
                relevance_reason=f"Transfer at {xfer['name']} to {second_info_d['name']}",
                estimated_duration_min=round(est_dur_1, 1),
                estimated_distance_km=round(est_dist_1, 2),
                intermediate_stops=intermediate_1,
                transfer_group_id=group_id,
                transfer_sequence=1,
                transfer_station_name=xfer["name"],
            ))

            # Leg 2: transfer station → destination line
            suggestions.append(TransitRouteSuggestion(
                suggestion_id=str(uuid.uuid4())[:8],
                route_id=second_line,
                display_name=second_info_d["name"],
                transit_mode=second_info_d["mode"],
                color=second_info_d["color"],
                board_stop_name=xfer_station_second["stop_name"],
                board_coord=Coordinate(lat=xfer_station_second["stop_lat"], lng=xfer_station_second["stop_lon"]),
                board_stop_id=xfer_stop_second,
                alight_stop_name=alight_station["stop_name"],
                alight_coord=Coordinate(lat=alight_station["stop_lat"], lng=alight_station["stop_lon"]),
                alight_stop_id=alight_sid,
                direction_hint=dir_2,
                relevance_reason=f"Transfer from {first_info_d['name']} at {xfer['name']}",
                estimated_duration_min=round(est_dur_2, 1),
                estimated_distance_km=round(est_dist_2, 2),
                intermediate_stops=intermediate_2,
                transfer_group_id=group_id,
                transfer_sequence=2,
                transfer_station_name=xfer["name"],
            ))

    return suggestions
