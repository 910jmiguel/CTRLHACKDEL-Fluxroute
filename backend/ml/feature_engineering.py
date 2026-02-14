import logging
import os

import pandas as pd

logger = logging.getLogger("fluxroute.ml.features")

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ttc-subway-delay-data.csv")

# Line encoding
LINE_ENCODING = {"YU": 1, "BD": 2, "SRT": 3, "SHEP": 4}


def load_and_engineer_features(filepath: str = DATA_PATH) -> tuple:
    """Load TTC delay CSV and extract ML features."""
    logger.info(f"Loading delay data from {filepath}")
    df = pd.read_csv(filepath)

    logger.info(f"Loaded {len(df)} rows. Columns: {list(df.columns)}")

    # Dynamically inspect columns
    date_col = _find_column(df, ["Date", "date", "DATE"])
    time_col = _find_column(df, ["Time", "time", "TIME"])
    day_col = _find_column(df, ["Day", "day", "DAY"])
    station_col = _find_column(df, ["Station", "station", "STATION"])
    delay_col = _find_column(df, ["Min Delay", "min_delay", "Min delay", "MinDelay", "Delay"])
    line_col = _find_column(df, ["Line", "line", "LINE"])

    if not all([date_col, time_col, delay_col, line_col]):
        raise ValueError(f"Missing required columns. Found: {list(df.columns)}")

    # Parse date
    df["parsed_date"] = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    df = df.dropna(subset=["parsed_date"])

    # Extract time features
    df["hour"] = df[time_col].apply(_parse_hour)
    df["month"] = df["parsed_date"].dt.month
    df["day_of_week"] = df["parsed_date"].dt.dayofweek  # 0=Monday

    # Derived features
    df["is_rush_hour"] = df["hour"].apply(lambda h: 1 if (7 <= h <= 9 or 17 <= h <= 19) else 0)
    df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)

    # Encode line
    df["line_encoded"] = df[line_col].map(LINE_ENCODING).fillna(0).astype(int)

    # Encode station (simple ordinal)
    if station_col:
        stations = df[station_col].unique()
        station_map = {s: i for i, s in enumerate(stations)}
        df["station_encoded"] = df[station_col].map(station_map).fillna(0).astype(int)
    else:
        df["station_encoded"] = 0

    # Target variables
    df["delay_minutes"] = pd.to_numeric(df[delay_col], errors="coerce").fillna(0)
    df["is_significant_delay"] = (df["delay_minutes"] > 5).astype(int)

    # Feature columns
    feature_cols = ["hour", "day_of_week", "month", "is_rush_hour", "is_weekend", "line_encoded", "station_encoded"]

    # Drop rows with NaN in features
    df = df.dropna(subset=feature_cols + ["delay_minutes"])

    X = df[feature_cols]
    y_class = df["is_significant_delay"]
    y_reg = df["delay_minutes"]

    logger.info(f"Feature engineering complete: {len(X)} samples, {len(feature_cols)} features")
    logger.info(f"Significant delays: {y_class.sum()} / {len(y_class)} ({y_class.mean():.1%})")

    return X, y_class, y_reg, feature_cols


def _find_column(df: pd.DataFrame, candidates: list[str]):
    """Find a column by trying multiple name variants."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _parse_hour(time_str) -> int:
    """Parse hour from time string like '08:30' or '8:30 AM'."""
    try:
        s = str(time_str).strip()
        parts = s.split(":")
        hour = int(parts[0])
        if "PM" in s.upper() and hour != 12:
            hour += 12
        elif "AM" in s.upper() and hour == 12:
            hour = 0
        return hour % 24
    except (ValueError, IndexError):
        return 12  # Default to noon
