"""Enrich TTC delay CSV with historical weather data from Open-Meteo Archive API.

Uses date-range queries to fetch an entire year of daily weather in a single request,
making the process ~365x faster than per-date fetching.
"""

import logging
import os
import time

import httpx
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fluxroute.ml.enrich")

ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
TORONTO_LAT = 43.6532
TORONTO_LNG = -79.3832

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
INPUT_PATH = os.path.join(DATA_DIR, "ttc-all-delay-data.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "ttc-all-delay-data-enriched.csv")


def _fetch_weather_range(start_date: str, end_date: str) -> dict[str, dict]:
    """Fetch daily weather for a date range from Open-Meteo Archive API.

    Returns a dict mapping date strings (YYYY-MM-DD) to weather dicts.
    """
    url = (
        f"{ARCHIVE_API}"
        f"?latitude={TORONTO_LAT}&longitude={TORONTO_LNG}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min"
        f",precipitation_sum,snowfall_sum,wind_speed_10m_max"
        f"&timezone=America/Toronto"
    )

    try:
        resp = httpx.get(url, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})

        dates = daily.get("time", [])
        result = {}

        for i, date_str in enumerate(dates):
            result[date_str] = {
                "temperature_mean": _safe_float(daily.get("temperature_2m_mean", [None] * len(dates))[i], 5.0),
                "temperature_max": _safe_float(daily.get("temperature_2m_max", [None] * len(dates))[i], 10.0),
                "temperature_min": _safe_float(daily.get("temperature_2m_min", [None] * len(dates))[i], 0.0),
                "precipitation_sum": _safe_float(daily.get("precipitation_sum", [None] * len(dates))[i], 0.0),
                "snowfall_sum": _safe_float(daily.get("snowfall_sum", [None] * len(dates))[i], 0.0),
                "wind_speed_max": _safe_float(daily.get("wind_speed_10m_max", [None] * len(dates))[i], 15.0),
            }

        return result

    except Exception as e:
        logger.warning(f"Weather fetch failed for {start_date} to {end_date}: {e}")
        return {}


def _safe_float(val, default: float) -> float:
    """Safely convert to float with a default."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _default_weather() -> dict:
    """Return neutral default weather values."""
    return {
        "temperature_mean": 5.0,
        "temperature_max": 10.0,
        "temperature_min": 0.0,
        "precipitation_sum": 0.0,
        "snowfall_sum": 0.0,
        "wind_speed_max": 15.0,
    }


def enrich():
    """Main enrichment: add weather columns to delay CSV.

    Fetches weather in year-sized chunks (4 API calls for 2022-2025)
    instead of per-date (1,460+ calls).
    """
    logger.info(f"Loading delay data from {INPUT_PATH}")
    df = pd.read_csv(INPUT_PATH)
    logger.info(f"Loaded {len(df)} rows")

    date_col = "date" if "date" in df.columns else "Date"
    unique_dates = df[date_col].dropna().unique()
    logger.info(f"Total unique dates in data: {len(unique_dates)}")

    # Determine year range
    parsed = pd.to_datetime(pd.Series(unique_dates), errors="coerce").dropna()
    min_year = parsed.dt.year.min()
    max_year = parsed.dt.year.max()
    logger.info(f"Date range: {min_year} to {max_year}")

    # Fetch weather by year (one API call per year)
    weather_cache: dict[str, dict] = {}

    for year in range(min_year, max_year + 1):
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        logger.info(f"  Fetching weather for {year} ({start} to {end})...")

        year_weather = _fetch_weather_range(start, end)
        weather_cache.update(year_weather)
        logger.info(f"    Got {len(year_weather)} days of weather data")
        time.sleep(1.0)  # Be respectful to the API

    logger.info(f"Total weather entries cached: {len(weather_cache)}")

    # Check coverage
    covered = sum(1 for d in unique_dates if str(d) in weather_cache)
    logger.info(f"Weather coverage: {covered}/{len(unique_dates)} dates ({covered/len(unique_dates):.1%})")

    # Map weather to each row
    weather_rows = []
    for _, row in df.iterrows():
        weather = weather_cache.get(str(row[date_col]), _default_weather())
        weather_rows.append(weather)

    weather_df = pd.DataFrame(weather_rows)
    enriched_df = pd.concat([df.reset_index(drop=True), weather_df.reset_index(drop=True)], axis=1)

    enriched_df.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"Enriched CSV saved to {OUTPUT_PATH}")
    logger.info(f"Columns: {list(enriched_df.columns)}")
    logger.info(f"Shape: {enriched_df.shape}")


if __name__ == "__main__":
    enrich()
