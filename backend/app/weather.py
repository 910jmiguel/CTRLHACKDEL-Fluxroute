import logging
from typing import Optional

import httpx

logger = logging.getLogger("fluxroute.weather")

# Toronto default coordinates
DEFAULT_LAT = 43.6532
DEFAULT_LNG = -79.3832


async def get_current_weather(lat: Optional[float] = None, lng: Optional[float] = None) -> dict:
    """Fetch current weather from Open-Meteo API (no API key needed)."""
    lat = lat or DEFAULT_LAT
    lng = lng or DEFAULT_LNG

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lng}"
            f"&current=temperature_2m,precipitation,snowfall,wind_speed_10m,weather_code"
            f"&timezone=America/Toronto"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})

        temperature = current.get("temperature_2m", 5.0)
        precipitation = current.get("precipitation", 0.0)
        snowfall = current.get("snowfall", 0.0)
        wind_speed = current.get("wind_speed_10m", 10.0)
        weather_code = current.get("weather_code", 0)

        # Determine if adverse conditions
        is_adverse = (
            precipitation > 2.0 or
            snowfall > 0.5 or
            wind_speed > 40.0 or
            temperature < -15.0 or
            weather_code >= 65  # Heavy rain/snow codes
        )

        return {
            "temperature": temperature,
            "precipitation": precipitation,
            "snowfall": snowfall,
            "wind_speed": wind_speed,
            "weather_code": weather_code,
            "weather_description": _weather_code_to_text(weather_code),
            "is_adverse": is_adverse,
            "location": {"lat": lat, "lng": lng},
        }

    except Exception as e:
        logger.warning(f"Weather API failed, using defaults: {e}")
        return {
            "temperature": 2.0,
            "precipitation": 0.0,
            "snowfall": 0.0,
            "wind_speed": 15.0,
            "weather_code": 3,
            "weather_description": "Overcast",
            "is_adverse": False,
            "location": {"lat": lat, "lng": lng},
        }


def _weather_code_to_text(code: int) -> str:
    """Convert WMO weather code to human-readable text."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return codes.get(code, "Unknown")
