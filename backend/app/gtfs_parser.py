import math
import os
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger("fluxroute.gtfs")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gtfs")

# Hardcoded TTC subway stations as fallback
TTC_SUBWAY_STATIONS = [
    # Line 1 Yonge-University (YU)
    {"stop_id": "YU_FINCH", "stop_name": "Finch", "stop_lat": 43.7804, "stop_lon": -79.4153, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_NYCTR", "stop_name": "North York Centre", "stop_lat": 43.7676, "stop_lon": -79.4131, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SHEPY", "stop_name": "Sheppard-Yonge", "stop_lat": 43.7615, "stop_lon": -79.4111, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_YORK", "stop_name": "York Mills", "stop_lat": 43.7440, "stop_lon": -79.4066, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_LAWR", "stop_name": "Lawrence", "stop_lat": 43.7251, "stop_lon": -79.4024, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_EGLN", "stop_name": "Eglinton", "stop_lat": 43.7057, "stop_lon": -79.3983, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DAVS", "stop_name": "Davisville", "stop_lat": 43.6975, "stop_lon": -79.3971, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STCL", "stop_name": "St Clair", "stop_lat": 43.6880, "stop_lon": -79.3934, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SUMM", "stop_name": "Summerhill", "stop_lat": 43.6822, "stop_lon": -79.3910, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_ROSE", "stop_name": "Rosedale", "stop_lat": 43.6767, "stop_lon": -79.3887, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_BLRY", "stop_name": "Bloor-Yonge", "stop_lat": 43.6709, "stop_lon": -79.3857, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_WELL", "stop_name": "Wellesley", "stop_lat": 43.6655, "stop_lon": -79.3839, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_COLL", "stop_name": "College", "stop_lat": 43.6613, "stop_lon": -79.3827, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DUND", "stop_name": "Dundas", "stop_lat": 43.6561, "stop_lon": -79.3803, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_QUEN", "stop_name": "Queen", "stop_lat": 43.6523, "stop_lon": -79.3793, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_KING", "stop_name": "King", "stop_lat": 43.6490, "stop_lon": -79.3782, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_UNON", "stop_name": "Union", "stop_lat": 43.6453, "stop_lon": -79.3806, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STAN", "stop_name": "St Andrew", "stop_lat": 43.6476, "stop_lon": -79.3846, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_OSGO", "stop_name": "Osgoode", "stop_lat": 43.6507, "stop_lon": -79.3872, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STPA", "stop_name": "St Patrick", "stop_lat": 43.6548, "stop_lon": -79.3885, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_QNPK", "stop_name": "Queen's Park", "stop_lat": 43.6600, "stop_lon": -79.3909, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_MUSM", "stop_name": "Museum", "stop_lat": 43.6670, "stop_lon": -79.3935, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STGR", "stop_name": "St George", "stop_lat": 43.6683, "stop_lon": -79.3997, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SPAD", "stop_name": "Spadina", "stop_lat": 43.6672, "stop_lon": -79.4037, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DUPO", "stop_name": "Dupont", "stop_lat": 43.6748, "stop_lon": -79.4069, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STCW", "stop_name": "St Clair West", "stop_lat": 43.6841, "stop_lon": -79.4150, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_GLNC", "stop_name": "Glencairn", "stop_lat": 43.7089, "stop_lon": -79.4412, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_LWST", "stop_name": "Lawrence West", "stop_lat": 43.7158, "stop_lon": -79.4440, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_YKDL", "stop_name": "Yorkdale", "stop_lat": 43.7245, "stop_lon": -79.4479, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_WLSN", "stop_name": "Wilson", "stop_lat": 43.7339, "stop_lon": -79.4502, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DWPK", "stop_name": "Downsview Park", "stop_lat": 43.7452, "stop_lon": -79.4784, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SHPW", "stop_name": "Sheppard West", "stop_lat": 43.7494, "stop_lon": -79.4618, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_FNWT", "stop_name": "Finch West", "stop_lat": 43.7653, "stop_lon": -79.4910, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_HW407", "stop_name": "Highway 407", "stop_lat": 43.7831, "stop_lon": -79.5231, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_VMC", "stop_name": "Vaughan Metropolitan Centre", "stop_lat": 43.7943, "stop_lon": -79.5273, "route_id": "1", "line": "Line 1 Yonge-University"},
    # Line 2 Bloor-Danforth (BD)
    {"stop_id": "BD_KPLG", "stop_name": "Kipling", "stop_lat": 43.6372, "stop_lon": -79.5361, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_ISLN", "stop_name": "Islington", "stop_lat": 43.6386, "stop_lon": -79.5246, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_RYLK", "stop_name": "Royal York", "stop_lat": 43.6384, "stop_lon": -79.5113, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_OLDM", "stop_name": "Old Mill", "stop_lat": 43.6502, "stop_lon": -79.4952, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_JANE", "stop_name": "Jane", "stop_lat": 43.6502, "stop_lon": -79.4838, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_RUNM", "stop_name": "Runnymede", "stop_lat": 43.6512, "stop_lon": -79.4754, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_HGPK", "stop_name": "High Park", "stop_lat": 43.6540, "stop_lon": -79.4668, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_KEEL", "stop_name": "Keele", "stop_lat": 43.6557, "stop_lon": -79.4597, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_DDWT", "stop_name": "Dundas West", "stop_lat": 43.6567, "stop_lon": -79.4526, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_LNSD", "stop_name": "Lansdowne", "stop_lat": 43.6595, "stop_lon": -79.4426, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_DFFR", "stop_name": "Dufferin", "stop_lat": 43.6601, "stop_lon": -79.4356, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_OSSN", "stop_name": "Ossington", "stop_lat": 43.6624, "stop_lon": -79.4267, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CHRS", "stop_name": "Christie", "stop_lat": 43.6643, "stop_lon": -79.4185, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BATH", "stop_name": "Bathurst", "stop_lat": 43.6660, "stop_lon": -79.4110, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_SPAD", "stop_name": "Spadina", "stop_lat": 43.6672, "stop_lon": -79.4037, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_STGR", "stop_name": "St George", "stop_lat": 43.6683, "stop_lon": -79.3997, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BAY", "stop_name": "Bay", "stop_lat": 43.6700, "stop_lon": -79.3901, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BLRY", "stop_name": "Bloor-Yonge", "stop_lat": 43.6709, "stop_lon": -79.3857, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_SHRB", "stop_name": "Sherbourne", "stop_lat": 43.6722, "stop_lon": -79.3764, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CSTL", "stop_name": "Castle Frank", "stop_lat": 43.6741, "stop_lon": -79.3686, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BRDV", "stop_name": "Broadview", "stop_lat": 43.6770, "stop_lon": -79.3584, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CHST", "stop_name": "Chester", "stop_lat": 43.6783, "stop_lon": -79.3521, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_PAPE", "stop_name": "Pape", "stop_lat": 43.6799, "stop_lon": -79.3451, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_DNLD", "stop_name": "Donlands", "stop_lat": 43.6812, "stop_lon": -79.3375, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_GRWD", "stop_name": "Greenwood", "stop_lat": 43.6831, "stop_lon": -79.3302, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CXWL", "stop_name": "Coxwell", "stop_lat": 43.6842, "stop_lon": -79.3228, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_WDBN", "stop_name": "Woodbine", "stop_lat": 43.6865, "stop_lon": -79.3126, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_MAIN", "stop_name": "Main Street", "stop_lat": 43.6890, "stop_lon": -79.3012, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_VCPK", "stop_name": "Victoria Park", "stop_lat": 43.6903, "stop_lon": -79.2930, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_WARD", "stop_name": "Warden", "stop_lat": 43.6917, "stop_lon": -79.2794, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_KNDY", "stop_name": "Kennedy", "stop_lat": 43.7326, "stop_lon": -79.2637, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    # Line 3 Scarborough RT
    {"stop_id": "SRT_SCBC", "stop_name": "Scarborough Centre", "stop_lat": 43.7747, "stop_lon": -79.2577, "route_id": "3", "line": "Line 3 Scarborough"},
    {"stop_id": "SRT_MCCW", "stop_name": "McCowan", "stop_lat": 43.7750, "stop_lon": -79.2498, "route_id": "3", "line": "Line 3 Scarborough"},
    {"stop_id": "SRT_LWRE", "stop_name": "Lawrence East", "stop_lat": 43.7482, "stop_lon": -79.2706, "route_id": "3", "line": "Line 3 Scarborough"},
    {"stop_id": "SRT_ELLM", "stop_name": "Ellesmere", "stop_lat": 43.7668, "stop_lon": -79.2612, "route_id": "3", "line": "Line 3 Scarborough"},
    {"stop_id": "SRT_MIDL", "stop_name": "Midland", "stop_lat": 43.7706, "stop_lon": -79.2725, "route_id": "3", "line": "Line 3 Scarborough"},
    # Line 4 Sheppard
    {"stop_id": "SH_SHPY", "stop_name": "Sheppard-Yonge", "stop_lat": 43.7615, "stop_lon": -79.4111, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_BAYV", "stop_name": "Bayview", "stop_lat": 43.7670, "stop_lon": -79.3868, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_BESS", "stop_name": "Bessarion", "stop_lat": 43.7693, "stop_lon": -79.3763, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_LESL", "stop_name": "Leslie", "stop_lat": 43.7710, "stop_lon": -79.3659, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_DNML", "stop_name": "Don Mills", "stop_lat": 43.7757, "stop_lon": -79.3461, "route_id": "4", "line": "Line 4 Sheppard"},
]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_gtfs_data() -> dict:
    """Load GTFS static data from files, falling back to hardcoded stations."""
    data = {"stops": pd.DataFrame(), "routes": pd.DataFrame(), "shapes": pd.DataFrame(),
            "trips": pd.DataFrame(), "stop_times": pd.DataFrame(), "using_fallback": False}

    files = {
        "stops": "stops.txt",
        "routes": "routes.txt",
        "shapes": "shapes.txt",
        "trips": "trips.txt",
        "stop_times": "stop_times.txt",
    }

    try:
        for key, fname in files.items():
            fpath = os.path.join(DATA_DIR, fname)
            if os.path.exists(fpath):
                data[key] = pd.read_csv(fpath, low_memory=False)
                logger.info(f"Loaded {key}: {len(data[key])} rows")
            else:
                logger.warning(f"GTFS file not found: {fpath}")
    except Exception as e:
        logger.error(f"Error loading GTFS files: {e}")

    # If stops are empty, use fallback
    if data["stops"].empty:
        logger.warning("Using hardcoded TTC subway station fallback")
        data["stops"] = pd.DataFrame(TTC_SUBWAY_STATIONS)
        data["using_fallback"] = True

    return data


def find_nearest_stops(gtfs: dict, lat: float, lng: float, radius_km: float = 2.0, limit: int = 5) -> list[dict]:
    """Find nearest stops using vectorized distance calculation."""
    stops = gtfs["stops"]
    if stops.empty:
        return []

    lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"

    # Vectorized haversine
    lat_r = math.radians(lat)
    stops_lat_r = stops[lat_col].apply(math.radians)
    stops_lng_r = stops[lng_col].apply(math.radians)
    lng_r = math.radians(lng)

    dlat = stops_lat_r - lat_r
    dlng = stops_lng_r - lng_r

    a = (dlat / 2).apply(math.sin) ** 2 + math.cos(lat_r) * stops_lat_r.apply(math.cos) * (dlng / 2).apply(math.sin) ** 2
    a = a.clip(upper=1.0)  # Clamp to prevent math domain error from float precision
    distances = 6371.0 * 2 * (a.apply(math.sqrt).apply(lambda x: math.atan2(x, math.sqrt(1 - x))))

    stops_with_dist = stops.copy()
    stops_with_dist["distance_km"] = distances

    nearby = stops_with_dist[stops_with_dist["distance_km"] <= radius_km].nsmallest(limit, "distance_km")

    results = []
    for _, row in nearby.iterrows():
        stop_id = row.get("stop_id", "")
        stop_name = row.get("stop_name", "Unknown")
        results.append({
            "stop_id": str(stop_id),
            "stop_name": stop_name,
            "lat": row[lat_col],
            "lng": row[lng_col],
            "distance_km": round(row["distance_km"], 3),
            "route_id": row.get("route_id", None),
            "line": row.get("line", None),
        })

    return results


def get_route_shape(gtfs: dict, route_id: str) -> Optional[dict]:
    """Get GeoJSON LineString for a route from shapes.txt."""
    shapes = gtfs.get("shapes", pd.DataFrame())
    trips = gtfs.get("trips", pd.DataFrame())

    if shapes.empty or trips.empty:
        return _get_fallback_shape(gtfs, route_id)

    # Find a shape_id for this route
    route_trips = trips[trips["route_id"].astype(str) == str(route_id)]
    if route_trips.empty:
        return _get_fallback_shape(gtfs, route_id)

    shape_id = route_trips.iloc[0].get("shape_id")
    if pd.isna(shape_id):
        return _get_fallback_shape(gtfs, route_id)

    shape_points = shapes[shapes["shape_id"] == shape_id].sort_values("shape_pt_sequence")
    if shape_points.empty:
        return _get_fallback_shape(gtfs, route_id)

    coordinates = [[row["shape_pt_lon"], row["shape_pt_lat"]] for _, row in shape_points.iterrows()]

    return {"type": "LineString", "coordinates": coordinates}


def _get_fallback_shape(gtfs: dict, route_id: str) -> Optional[dict]:
    """Generate shape from station coordinates for fallback data."""
    stops = gtfs["stops"]
    if "route_id" not in stops.columns:
        return None

    route_stops = stops[stops["route_id"].astype(str) == str(route_id)]
    if route_stops.empty:
        return None

    lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"

    coordinates = [[row[lng_col], row[lat_col]] for _, row in route_stops.iterrows()]
    return {"type": "LineString", "coordinates": coordinates}


def get_next_departures(gtfs: dict, stop_id: str, limit: int = 5) -> list[dict]:
    """Get next departures from a stop, handling GTFS 25:00:00 time format."""
    stop_times = gtfs.get("stop_times", pd.DataFrame())
    if stop_times.empty:
        return _generate_mock_departures(stop_id, limit)

    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    stop_deps = stop_times[stop_times["stop_id"].astype(str) == str(stop_id)].copy()
    if stop_deps.empty:
        return _generate_mock_departures(stop_id, limit)

    def parse_gtfs_time(t: str) -> int:
        """Parse GTFS time like '25:30:00' to minutes since midnight."""
        try:
            parts = str(t).split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0

    stop_deps["dep_minutes"] = stop_deps["departure_time"].apply(parse_gtfs_time)
    upcoming = stop_deps[stop_deps["dep_minutes"] >= current_minutes].nsmallest(limit, "dep_minutes")

    results = []
    for _, row in upcoming.iterrows():
        mins = row["dep_minutes"]
        h, m = divmod(mins % 1440, 60)
        results.append({
            "stop_id": str(stop_id),
            "trip_id": str(row.get("trip_id", "")),
            "departure_time": f"{h:02d}:{m:02d}",
            "minutes_until": mins - current_minutes,
        })

    return results if results else _generate_mock_departures(stop_id, limit)


def _generate_mock_departures(stop_id: str, limit: int) -> list[dict]:
    """Generate realistic mock departure times."""
    now = datetime.now()
    results = []
    for i in range(limit):
        wait = 3 + i * 5  # Every ~5 minutes
        dep_time = now.hour * 60 + now.minute + wait
        h, m = divmod(dep_time % 1440, 60)
        results.append({
            "stop_id": stop_id,
            "trip_id": f"mock_{i}",
            "departure_time": f"{h:02d}:{m:02d}",
            "minutes_until": wait,
        })
    return results


def find_transit_route(gtfs: dict, origin_stop_id: str, dest_stop_id: str) -> Optional[dict]:
    """Find a transit route connecting two stops."""
    stops = gtfs["stops"]
    stop_times = gtfs.get("stop_times", pd.DataFrame())

    # Get stop coordinates
    lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"

    origin_stop = stops[stops["stop_id"].astype(str) == str(origin_stop_id)]
    dest_stop = stops[stops["stop_id"].astype(str) == str(dest_stop_id)]

    if origin_stop.empty or dest_stop.empty:
        return None

    origin_row = origin_stop.iloc[0]
    dest_row = dest_stop.iloc[0]

    distance = haversine(origin_row[lat_col], origin_row[lng_col], dest_row[lat_col], dest_row[lng_col])

    # Check if same line (for fallback data)
    same_line = (origin_row.get("route_id") is not None and
                 origin_row.get("route_id") == dest_row.get("route_id"))

    # Build route info
    route_info = {
        "origin_stop": origin_stop_id,
        "dest_stop": dest_stop_id,
        "origin_name": origin_row.get("stop_name", "Unknown"),
        "dest_name": dest_row.get("stop_name", "Unknown"),
        "distance_km": round(distance, 2),
        "estimated_duration_min": round(distance / 0.5, 1),  # ~30 km/h average subway speed
        "line": origin_row.get("line", "Unknown"),
        "route_id": str(origin_row.get("route_id", "")),
        "transfers": 0 if same_line else 1,
    }

    # Try to get geometry
    shape = get_route_shape(gtfs, str(origin_row.get("route_id", "")))
    if shape:
        route_info["geometry"] = shape
    else:
        # Straight line fallback
        route_info["geometry"] = {
            "type": "LineString",
            "coordinates": [
                [origin_row[lng_col], origin_row[lat_col]],
                [dest_row[lng_col], dest_row[lat_col]],
            ]
        }

    return route_info
