"""Hardcoded TTC and GO station parking lot database.

Contains parking capacity, daily rates, and lot type for major stations
across the TTC subway system and GO Transit network.
"""

import logging

logger = logging.getLogger("fluxroute.parking")

# Station parking database: name -> parking info
# TTC Park & Ride lots are free; GO stations typically $4/day
STATION_PARKING: dict[str, dict] = {
    # === TTC stations with parking (free Park & Ride) ===
    "Finch": {"capacity": 300, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7804, "lng": -79.4153},
    "Don Mills": {"capacity": 50, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7757, "lng": -79.3461},
    "Wilson": {"capacity": 400, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7339, "lng": -79.4502},
    "Kipling": {"capacity": 700, "daily_rate": 0.0, "type": "structure", "agency": "TTC", "lat": 43.6372, "lng": -79.5361},
    "Kennedy": {"capacity": 200, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7326, "lng": -79.2637},
    "Sheppard West": {"capacity": 300, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7494, "lng": -79.4618},
    "Downsview Park": {"capacity": 600, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7452, "lng": -79.4784},
    "VMC": {"capacity": 600, "daily_rate": 0.0, "type": "structure", "agency": "TTC", "lat": 43.7943, "lng": -79.5273},
    "Vaughan Metropolitan Centre": {"capacity": 600, "daily_rate": 0.0, "type": "structure", "agency": "TTC", "lat": 43.7943, "lng": -79.5273},
    "Highway 407": {"capacity": 1200, "daily_rate": 0.0, "type": "structure", "agency": "TTC", "lat": 43.7831, "lng": -79.5231},
    "Finch West": {"capacity": 150, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7653, "lng": -79.4910},
    "Warden": {"capacity": 100, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.6917, "lng": -79.2794},
    "Islington": {"capacity": 100, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.6386, "lng": -79.5246},
    "Yorkdale": {"capacity": 200, "daily_rate": 0.0, "type": "surface", "agency": "TTC", "lat": 43.7245, "lng": -79.4479},
    # === GO Transit stations (most lines) ===
    # Richmond Hill line
    "Richmond Hill GO": {"capacity": 700, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8721, "lng": -79.4382},
    "Langstaff GO": {"capacity": 500, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8178, "lng": -79.4240},
    "Old Cummer GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7950, "lng": -79.4078},
    "Oriole GO": {"capacity": 200, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7790, "lng": -79.3876},
    # Barrie line
    "Aurora GO": {"capacity": 500, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 44.0063, "lng": -79.4508},
    "Newmarket GO": {"capacity": 800, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 44.0575, "lng": -79.4614},
    "Maple GO": {"capacity": 600, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8533, "lng": -79.5111},
    "Rutherford GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8384, "lng": -79.4983},
    "Barrie South GO": {"capacity": 600, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 44.3599, "lng": -79.6871},
    # Stouffville line
    "Unionville GO": {"capacity": 800, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8525, "lng": -79.3145},
    "Markham GO": {"capacity": 500, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8771, "lng": -79.2616},
    "Stouffville GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.9706, "lng": -79.2502},
    "Centennial GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7891, "lng": -79.3134},
    "Agincourt GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7875, "lng": -79.2789},
    "Milliken GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8232, "lng": -79.2903},
    # Lakeshore East
    "Oshawa GO": {"capacity": 1500, "daily_rate": 4.0, "type": "structure", "agency": "GO Transit", "lat": 43.8724, "lng": -78.8719},
    "Pickering GO": {"capacity": 900, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8376, "lng": -79.0860},
    "Ajax GO": {"capacity": 700, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8503, "lng": -79.0413},
    "Whitby GO": {"capacity": 800, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.8666, "lng": -78.9419},
    "Rouge Hill GO": {"capacity": 500, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7750, "lng": -79.1330},
    "Guildwood GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7548, "lng": -79.1935},
    "Eglinton GO": {"capacity": 200, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7413, "lng": -79.2242},
    "Scarborough GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7295, "lng": -79.2527},
    "Danforth GO": {"capacity": 150, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6867, "lng": -79.2930},
    # Lakeshore West
    "Clarkson GO": {"capacity": 700, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5109, "lng": -79.6387},
    "Oakville GO": {"capacity": 1200, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.4515, "lng": -79.6818},
    "Burlington GO": {"capacity": 1000, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.3431, "lng": -79.8076},
    "Appleby GO": {"capacity": 800, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.3770, "lng": -79.7484},
    "Bronte GO": {"capacity": 500, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.4189, "lng": -79.7150},
    "Port Credit GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5550, "lng": -79.5842},
    "Long Branch GO": {"capacity": 200, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5933, "lng": -79.5425},
    "Mimico GO": {"capacity": 150, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6172, "lng": -79.4965},
    "Exhibition GO": {"capacity": 100, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6361, "lng": -79.4193},
    # Milton line
    "Milton GO": {"capacity": 600, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5180, "lng": -79.8830},
    "Lisgar GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5378, "lng": -79.8177},
    "Meadowvale GO": {"capacity": 500, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5851, "lng": -79.7543},
    "Streetsville GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5914, "lng": -79.7131},
    "Erindale GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5647, "lng": -79.6617},
    "Cooksville GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5684, "lng": -79.6169},
    "Dixie GO": {"capacity": 200, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.5812, "lng": -79.5779},
    "Kipling GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6232, "lng": -79.5280},
    # Kitchener line
    "Bramalea GO": {"capacity": 1200, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7033, "lng": -79.6887},
    "Brampton GO": {"capacity": 600, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6854, "lng": -79.7632},
    "Mount Pleasant GO": {"capacity": 500, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6912, "lng": -79.8105},
    "Georgetown GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6548, "lng": -79.9217},
    "Malton GO": {"capacity": 400, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.7098, "lng": -79.6421},
    "Etobicoke North GO": {"capacity": 300, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6837, "lng": -79.5653},
    "Weston GO": {"capacity": 200, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6987, "lng": -79.5147},
    "Bloor GO": {"capacity": 100, "daily_rate": 4.0, "type": "surface", "agency": "GO Transit", "lat": 43.6585, "lng": -79.4588},
}

# Aliases for fuzzy matching
_STATION_ALIASES: dict[str, str] = {
    "vaughan metropolitan centre": "VMC",
    "vaughan": "VMC",
    "vmc": "VMC",
    "highway407": "Highway 407",
    "hwy 407": "Highway 407",
    "sheppard-west": "Sheppard West",
    "downsview": "Downsview Park",
    "downsview park": "Downsview Park",
    "finch station": "Finch",
    "don mills station": "Don Mills",
    "wilson station": "Wilson",
    "kipling station": "Kipling",
    "kennedy station": "Kennedy",
}


def get_parking_info(station_name: str) -> dict | None:
    """Look up parking info for a station. Tries exact match then fuzzy."""
    # Exact match
    if station_name in STATION_PARKING:
        info = STATION_PARKING[station_name].copy()
        info["station_name"] = station_name
        return info

    # Alias match
    lower = station_name.lower().strip()
    if lower in _STATION_ALIASES:
        canonical = _STATION_ALIASES[lower]
        if canonical in STATION_PARKING:
            info = STATION_PARKING[canonical].copy()
            info["station_name"] = canonical
            return info

    # Fuzzy: check if station_name is a substring of any key (or vice versa)
    for key, info in STATION_PARKING.items():
        key_lower = key.lower()
        if lower in key_lower or key_lower in lower:
            result = info.copy()
            result["station_name"] = key
            return result

    return None


def find_stations_with_parking(
    lat: float, lng: float, radius_km: float = 15.0
) -> list[dict]:
    """Return all stations with parking near a coordinate, sorted by distance."""
    from app.gtfs_parser import haversine

    results = []
    for name, info in STATION_PARKING.items():
        s_lat = info.get("lat", 0)
        s_lng = info.get("lng", 0)
        if s_lat == 0 or s_lng == 0:
            continue
        dist = haversine(lat, lng, s_lat, s_lng)
        if dist <= radius_km:
            result = info.copy()
            result["station_name"] = name
            result["distance_km"] = round(dist, 2)
            results.append(result)

    results.sort(key=lambda x: x["distance_km"])
    return results
