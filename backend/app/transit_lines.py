"""Build transit line geometries and station positions for map overlay.

Primary source: GTFS shapes.txt (TTC) — reliable, complete geometry.
Secondary: OTP index API for GO/regional rail lines not in local GTFS.
Fallback: hardcoded TTC subway stations if GTFS unavailable.
"""

import logging
from typing import Optional

import httpx
import pandas as pd

from app.otp_client import _decode_polyline, _get_otp_url
from app.gtfs_parser import TTC_SUBWAY_STATIONS

logger = logging.getLogger("fluxroute.transit_lines")

# Rapid transit route_type values from GTFS spec
_RAPID_ROUTE_TYPES = {0, 1, 2}  # 0=Tram/LRT, 1=Subway, 2=Rail

# Map GTFS route_type to display mode
_ROUTE_TYPE_MODE = {
    0: "TRAM",
    1: "SUBWAY",
    2: "RAIL",
}

# Fallback colors for TTC lines
_TTC_LINE_COLORS = {
    "1": "#FFCC00",  # Line 1 Yonge-University
    "2": "#00A651",  # Line 2 Bloor-Danforth
    "4": "#A8518A",  # Line 4 Sheppard
    "5": "#FF6600",  # Line 5 Eglinton Crosstown
    "6": "#8B4513",  # Line 6 Finch West
}

_TTC_MODE_MAP = {
    "1": "SUBWAY",
    "2": "SUBWAY",
    "4": "SUBWAY",
    "5": "TRAM",
    "6": "TRAM",
}


def build_transit_overlay_from_gtfs(gtfs: dict) -> dict:
    """Build transit overlay from GTFS shapes.txt — most reliable source for TTC lines.

    Filters routes to rapid transit (route_type 0/1/2), then joins through
    trips to get shape geometry from shapes.txt. Also collects station points
    from stop_times for those routes.

    Returns {lines: FeatureCollection, stations: FeatureCollection}.
    """
    routes_df = gtfs.get("routes", pd.DataFrame())
    trips_df = gtfs.get("trips", pd.DataFrame())
    shapes_df = gtfs.get("shapes", pd.DataFrame())
    stops_df = gtfs.get("stops", pd.DataFrame())
    stop_times_df = gtfs.get("stop_times", pd.DataFrame())

    if routes_df.empty or trips_df.empty or shapes_df.empty:
        logger.warning("GTFS data incomplete for transit overlay — using fallback")
        return get_fallback_transit_lines()

    # Check if route_type column exists
    if "route_type" not in routes_df.columns:
        logger.warning("No route_type column in GTFS routes — using fallback")
        return get_fallback_transit_lines()

    # Filter to rapid transit routes
    rapid_routes = routes_df[routes_df["route_type"].isin(_RAPID_ROUTE_TYPES)]
    if rapid_routes.empty:
        logger.warning("No rapid transit routes found in GTFS — using fallback")
        return get_fallback_transit_lines()

    logger.info(f"GTFS: {len(rapid_routes)} rapid transit routes found")

    lines_features = []
    station_features = []
    seen_stations = set()

    for _, route_row in rapid_routes.iterrows():
        route_id = route_row["route_id"]
        route_type = int(route_row["route_type"])
        short_name = str(route_row.get("route_short_name", "")) if pd.notna(route_row.get("route_short_name")) else ""
        long_name = str(route_row.get("route_long_name", "")) if pd.notna(route_row.get("route_long_name")) else ""
        mode = _ROUTE_TYPE_MODE.get(route_type, "SUBWAY")

        # Get color from GTFS or fallback
        raw_color = route_row.get("route_color")
        if pd.notna(raw_color) and raw_color:
            color = str(raw_color)
            if not color.startswith("#"):
                color = f"#{color}"
        else:
            color = _TTC_LINE_COLORS.get(short_name, "#3B82F6")

        # Find trips for this route and pick the one with the longest shape
        route_trips = trips_df[trips_df["route_id"] == route_id]
        if route_trips.empty:
            continue

        # Pick the trip with the most shape points (longest geometry)
        if "shape_id" not in route_trips.columns:
            continue

        valid_trips = route_trips.dropna(subset=["shape_id"])
        if valid_trips.empty:
            continue

        # Count shape points per shape_id and pick the longest
        shape_ids = valid_trips["shape_id"].unique()
        best_shape_id = None
        best_count = 0

        for sid in shape_ids:
            count = len(shapes_df[shapes_df["shape_id"] == sid])
            if count > best_count:
                best_count = count
                best_shape_id = sid

        if best_shape_id is None or best_count < 2:
            continue

        # Get shape coordinates
        shape_points = shapes_df[shapes_df["shape_id"] == best_shape_id].sort_values("shape_pt_sequence")
        coordinates = [
            [float(row["shape_pt_lon"]), float(row["shape_pt_lat"])]
            for _, row in shape_points.iterrows()
        ]

        if len(coordinates) < 2:
            continue

        lines_features.append({
            "type": "Feature",
            "properties": {
                "id": str(route_id),
                "shortName": short_name,
                "longName": long_name,
                "mode": mode,
                "color": color,
                "agencyName": "TTC",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
        })

        # Collect stations served by this route
        if not stop_times_df.empty and not stops_df.empty:
            # Get all trips for this route
            trip_ids = route_trips["trip_id"].unique()
            # Get stop_ids from stop_times for these trips
            route_stop_times = stop_times_df[stop_times_df["trip_id"].isin(trip_ids)]
            station_stop_ids = route_stop_times["stop_id"].unique()
            # Get stop details
            route_stops = stops_df[stops_df["stop_id"].isin(station_stop_ids)]

            for _, stop_row in route_stops.iterrows():
                lat_col = "stop_lat" if "stop_lat" in stops_df.columns else "latitude"
                lng_col = "stop_lon" if "stop_lon" in stops_df.columns else "longitude"
                lat = float(stop_row[lat_col])
                lng = float(stop_row[lng_col])
                key = (round(lat, 4), round(lng, 4))
                if key in seen_stations:
                    continue
                seen_stations.add(key)

                station_features.append({
                    "type": "Feature",
                    "properties": {
                        "name": str(stop_row.get("stop_name", "")),
                        "stopId": str(stop_row["stop_id"]),
                        "mode": mode,
                        "color": color,
                        "agencyName": "TTC",
                        "routeName": short_name or long_name,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lng, lat],
                    },
                })

    logger.info(f"GTFS transit overlay: {len(lines_features)} lines, {len(station_features)} stations")

    if not lines_features:
        logger.warning("No lines built from GTFS shapes — using fallback")
        return get_fallback_transit_lines()

    return {
        "lines": {
            "type": "FeatureCollection",
            "features": lines_features,
        },
        "stations": {
            "type": "FeatureCollection",
            "features": station_features,
        },
    }


async def _fetch_otp_regional_lines(http_client: httpx.AsyncClient) -> dict:
    """Fetch GO/regional rail lines from OTP index API.

    Only fetches RAIL mode routes (not SUBWAY/TRAM which are covered by GTFS).
    Returns {lines: [...], stations: [...]}.
    """
    base = _get_otp_url()
    lines = []
    stations = []
    seen_stations = set()

    async def _get(url: str):
        try:
            resp = await http_client.get(url, timeout=8.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"OTP index request failed ({url}): {e}")
            return None

    routes = await _get(f"{base}/otp/routers/default/index/routes")
    if not routes:
        return {"lines": [], "stations": []}

    # Only RAIL routes (GO Transit, etc.) — SUBWAY and TRAM covered by GTFS
    rail_routes = [r for r in routes if r.get("mode") == "RAIL"]
    logger.info(f"OTP: {len(rail_routes)} regional rail routes")

    for route in rail_routes:
        route_id = route.get("id", "")
        short_name = route.get("shortName", "")
        long_name = route.get("longName", "")
        agency_name = route.get("agencyName", "")
        color = route.get("color")
        if color and not color.startswith("#"):
            color = f"#{color}"
        elif not color:
            color = "#3D8B37"  # GO green

        patterns = await _get(f"{base}/otp/routers/default/index/routes/{route_id}/patterns")
        if not patterns:
            continue

        best_pattern = max(patterns, key=lambda p: p.get("numStops", 0), default=None)
        if not best_pattern:
            continue

        pattern_id = best_pattern.get("id", "")
        geom_data = await _get(f"{base}/otp/routers/default/index/patterns/{pattern_id}/geometry")
        if not geom_data:
            continue

        encoded = None
        coordinates = None
        if isinstance(geom_data, dict):
            encoded = geom_data.get("points")
            if not encoded and geom_data.get("type") == "LineString":
                coordinates = geom_data.get("coordinates", [])
        elif isinstance(geom_data, str):
            encoded = geom_data

        if encoded:
            coordinates = _decode_polyline(encoded)

        if not coordinates or len(coordinates) < 2:
            continue

        lines.append({
            "type": "Feature",
            "properties": {
                "id": route_id,
                "shortName": short_name,
                "longName": long_name,
                "mode": "RAIL",
                "color": color,
                "agencyName": agency_name,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
        })

        stops_data = await _get(f"{base}/otp/routers/default/index/patterns/{pattern_id}/stops")
        if stops_data:
            for stop in stops_data:
                lat = stop.get("lat", 0)
                lon = stop.get("lon", 0)
                key = (round(lat, 4), round(lon, 4))
                if key in seen_stations:
                    continue
                seen_stations.add(key)
                stations.append({
                    "type": "Feature",
                    "properties": {
                        "name": stop.get("name", ""),
                        "stopId": stop.get("id", ""),
                        "mode": "RAIL",
                        "color": color,
                        "agencyName": agency_name,
                        "routeName": short_name or long_name,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    },
                })

    return {"lines": lines, "stations": stations}


async def fetch_transit_lines(
    gtfs: dict,
    http_client: Optional[httpx.AsyncClient] = None,
) -> dict:
    """Build transit overlay: TTC from GTFS shapes, GO from OTP.

    1. TTC lines from GTFS shapes.txt (always reliable, complete geometry)
    2. If OTP available, add GO/regional rail lines from OTP index
    """
    # Primary: TTC from GTFS shapes
    result = build_transit_overlay_from_gtfs(gtfs)

    # Secondary: GO/regional rail from OTP (only RAIL mode, not SUBWAY/TRAM)
    if http_client:
        try:
            go_data = await _fetch_otp_regional_lines(http_client)
            go_lines = go_data.get("lines", [])
            go_stations = go_data.get("stations", [])
            if go_lines:
                result["lines"]["features"].extend(go_lines)
                result["stations"]["features"].extend(go_stations)
                logger.info(f"Added {len(go_lines)} GO/regional rail lines from OTP")
        except Exception as e:
            logger.warning(f"Failed to fetch GO lines from OTP: {e}")

    return result


def get_fallback_transit_lines() -> dict:
    """Build transit overlay from hardcoded TTC subway/LRT stations.

    Groups stations by route_id and connects them as LineStrings.
    Also returns station points for markers.
    """
    from collections import defaultdict

    routes: dict[str, list] = defaultdict(list)
    station_features = []

    for station in TTC_SUBWAY_STATIONS:
        rid = str(station.get("route_id", ""))
        routes[rid].append(station)

        mode = _TTC_MODE_MAP.get(rid, "SUBWAY")
        color = _TTC_LINE_COLORS.get(rid, "#FFCC00")

        station_features.append({
            "type": "Feature",
            "properties": {
                "name": station["stop_name"],
                "stopId": station["stop_id"],
                "mode": mode,
                "color": color,
                "agencyName": "TTC",
                "routeName": station.get("line", ""),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [station["stop_lon"], station["stop_lat"]],
            },
        })

    lines_features = []
    for rid, stations in routes.items():
        coordinates = [[s["stop_lon"], s["stop_lat"]] for s in stations]
        if len(coordinates) < 2:
            continue

        color = _TTC_LINE_COLORS.get(rid, "#FFCC00")
        mode = _TTC_MODE_MAP.get(rid, "SUBWAY")
        line_name = stations[0].get("line", f"Line {rid}")

        lines_features.append({
            "type": "Feature",
            "properties": {
                "id": rid,
                "shortName": f"Line {rid}",
                "longName": line_name,
                "mode": mode,
                "color": color,
                "agencyName": "TTC",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
        })

    logger.info(f"Fallback transit overlay: {len(lines_features)} lines, {len(station_features)} stations (TTC only)")

    return {
        "lines": {
            "type": "FeatureCollection",
            "features": lines_features,
        },
        "stations": {
            "type": "FeatureCollection",
            "features": station_features,
        },
    }
