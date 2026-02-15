"""Download and combine TTC delay data from Toronto Open Data.

Combines subway, streetcar, and bus delay data from 2022-2025 into a single
unified CSV for ML training.

Columns in output:
  date, time, day, mode, line, station_or_location, code, min_delay, min_gap,
  bound, vehicle

Data source: City of Toronto Open Data Portal
  - https://open.toronto.ca/dataset/ttc-subway-delay-data/
  - https://open.toronto.ca/dataset/ttc-streetcar-delay-data/
  - https://open.toronto.ca/dataset/ttc-bus-delay-data/
"""

import logging
import os

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fluxroute.ml.combine")

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_downloads")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ttc-all-delay-data.csv")


def _load_subway_xlsx(path: str) -> pd.DataFrame:
    """Load subway XLSX (2022-2024 format)."""
    df = pd.read_excel(path)
    # Columns: Date, Time, Day, Station, Code, Min Delay, Min Gap, Bound, Line, Vehicle
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors="coerce"),
        "time": df["Time"].astype(str),
        "day": df["Day"],
        "mode": "subway",
        "line": df["Line"],
        "station": df["Station"],
        "code": df["Code"],
        "min_delay": pd.to_numeric(df["Min Delay"], errors="coerce"),
        "min_gap": pd.to_numeric(df["Min Gap"], errors="coerce"),
        "bound": df["Bound"],
        "vehicle": df["Vehicle"],
    })


def _load_subway_csv_2025(path: str) -> pd.DataFrame:
    """Load subway CSV (2025+ format with _id column)."""
    df = pd.read_csv(path)
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors="coerce"),
        "time": df["Time"].astype(str),
        "day": df["Day"],
        "mode": "subway",
        "line": df["Line"],
        "station": df["Station"],
        "code": df["Code"],
        "min_delay": pd.to_numeric(df["Min Delay"], errors="coerce"),
        "min_gap": pd.to_numeric(df["Min Gap"], errors="coerce"),
        "bound": df["Bound"],
        "vehicle": df["Vehicle"],
    })


def _load_streetcar_xlsx(path: str) -> pd.DataFrame:
    """Load streetcar XLSX (2022-2024 format)."""
    df = pd.read_excel(path)
    # Columns: Date, Line, Time, Day, Location, Incident, Min Delay, Min Gap, Bound, Vehicle
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors="coerce"),
        "time": df["Time"].astype(str),
        "day": df["Day"],
        "mode": "streetcar",
        "line": df["Line"].astype(str),
        "station": df["Location"],
        "code": df["Incident"],
        "min_delay": pd.to_numeric(df["Min Delay"], errors="coerce"),
        "min_gap": pd.to_numeric(df["Min Gap"], errors="coerce"),
        "bound": df["Bound"],
        "vehicle": df["Vehicle"],
    })


def _load_streetcar_csv_2025(path: str) -> pd.DataFrame:
    """Load streetcar CSV (2025+ format)."""
    df = pd.read_csv(path)
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors="coerce"),
        "time": df["Time"].astype(str),
        "day": df["Day"],
        "mode": "streetcar",
        "line": df["Line"].astype(str),
        "station": df["Station"],
        "code": df["Code"],
        "min_delay": pd.to_numeric(df["Min Delay"], errors="coerce"),
        "min_gap": pd.to_numeric(df["Min Gap"], errors="coerce"),
        "bound": df["Bound"],
        "vehicle": df["Vehicle"],
    })


def _load_bus_xlsx(path: str) -> pd.DataFrame:
    """Load bus XLSX (2022-2024 format)."""
    df = pd.read_excel(path)
    # Columns: Date, Route, Time, Day, Location, Incident, Min Delay, Min Gap, Direction, Vehicle
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors="coerce"),
        "time": df["Time"].astype(str),
        "day": df["Day"],
        "mode": "bus",
        "line": df["Route"].astype(str),
        "station": df["Location"],
        "code": df["Incident"],
        "min_delay": pd.to_numeric(df["Min Delay"], errors="coerce"),
        "min_gap": pd.to_numeric(df["Min Gap"], errors="coerce"),
        "bound": df["Direction"],
        "vehicle": df["Vehicle"],
    })


def _load_bus_csv_2025(path: str) -> pd.DataFrame:
    """Load bus CSV (2025+ format)."""
    df = pd.read_csv(path)
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors="coerce"),
        "time": df["Time"].astype(str),
        "day": df["Day"],
        "mode": "bus",
        "line": df["Line"].astype(str),
        "station": df["Station"],
        "code": df["Code"],
        "min_delay": pd.to_numeric(df["Min Delay"], errors="coerce"),
        "min_gap": pd.to_numeric(df["Min Gap"], errors="coerce"),
        "bound": df["Bound"],
        "vehicle": df["Vehicle"],
    })


def combine():
    """Load all raw files and combine into unified CSV."""
    all_frames = []

    # --- Subway ---
    for year in [2022, 2023, 2024]:
        path = os.path.join(RAW_DIR, f"subway-{year}.xlsx")
        if os.path.exists(path):
            df = _load_subway_xlsx(path)
            logger.info(f"Subway {year}: {len(df)} rows")
            all_frames.append(df)

    path_2025 = os.path.join(RAW_DIR, "subway-2025.csv")
    if os.path.exists(path_2025):
        df = _load_subway_csv_2025(path_2025)
        logger.info(f"Subway 2025: {len(df)} rows")
        all_frames.append(df)

    # --- Streetcar ---
    for year in [2022, 2023, 2024]:
        path = os.path.join(RAW_DIR, f"streetcar-{year}.xlsx")
        if os.path.exists(path):
            df = _load_streetcar_xlsx(path)
            logger.info(f"Streetcar {year}: {len(df)} rows")
            all_frames.append(df)

    path_2025 = os.path.join(RAW_DIR, "streetcar-2025.csv")
    if os.path.exists(path_2025):
        df = _load_streetcar_csv_2025(path_2025)
        logger.info(f"Streetcar 2025: {len(df)} rows")
        all_frames.append(df)

    # --- Bus ---
    for year in [2022, 2023, 2024]:
        path = os.path.join(RAW_DIR, f"bus-{year}.xlsx")
        if os.path.exists(path):
            df = _load_bus_xlsx(path)
            logger.info(f"Bus {year}: {len(df)} rows")
            all_frames.append(df)

    path_2025 = os.path.join(RAW_DIR, "bus-2025.csv")
    if os.path.exists(path_2025):
        df = _load_bus_csv_2025(path_2025)
        logger.info(f"Bus 2025: {len(df)} rows")
        all_frames.append(df)

    if not all_frames:
        logger.error("No data files found!")
        return

    combined = pd.concat(all_frames, ignore_index=True)

    # Clean up
    combined = combined.dropna(subset=["date"])
    combined["min_delay"] = combined["min_delay"].fillna(0)
    combined["min_gap"] = combined["min_gap"].fillna(0)

    # Sort by date
    combined = combined.sort_values("date").reset_index(drop=True)

    # Format date as string for CSV
    combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

    logger.info(f"\n{'='*50}")
    logger.info(f"COMBINED DATASET")
    logger.info(f"{'='*50}")
    logger.info(f"Total rows: {len(combined)}")
    logger.info(f"Date range: {combined['date'].min()} to {combined['date'].max()}")
    logger.info(f"Mode breakdown:")
    for mode, count in combined["mode"].value_counts().items():
        logger.info(f"  {mode}: {count}")
    logger.info(f"Columns: {list(combined.columns)}")

    # Delay distribution
    delays = combined["min_delay"]
    logger.info(f"\nDelay stats:")
    logger.info(f"  Mean: {delays.mean():.1f} min")
    logger.info(f"  Median: {delays.median():.1f} min")
    logger.info(f"  >5 min delays: {(delays > 5).sum()} ({(delays > 5).mean():.1%})")
    logger.info(f"  >10 min delays: {(delays > 10).sum()} ({(delays > 10).mean():.1%})")

    # Top incident codes
    logger.info(f"\nTop 15 incident codes:")
    for code, count in combined["code"].value_counts().head(15).items():
        logger.info(f"  {code}: {count}")

    combined.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    combine()
