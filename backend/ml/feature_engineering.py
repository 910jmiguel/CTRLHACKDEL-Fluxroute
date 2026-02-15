import logging
import os

import pandas as pd

logger = logging.getLogger("fluxroute.ml.features")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ENRICHED_PATH = os.path.join(DATA_DIR, "ttc-all-delay-data-enriched.csv")
ORIGINAL_PATH = os.path.join(DATA_DIR, "ttc-all-delay-data.csv")

# Transit mode encoding
MODE_ENCODING = {"subway": 1, "bus": 2, "streetcar": 3}

# Top incident codes across all modes (frequency-based encoding)
CODE_ENCODING = {
    # Bus / streetcar text codes
    "Operations - Operator": 1,
    "Mechanical": 2,
    "Operations": 3,
    "Security": 4,
    "Utilized Off Route": 5,
    "Cleaning - Unsanitary": 6,
    "Collision - TTC": 7,
    "Emergency Services": 8,
    "Diversion": 9,
    "General Delay": 10,
    "Investigation": 11,
    "Road Blocked - NON-TTC Collision": 12,
    "Vision": 13,
    "Held By": 14,
    "Collision - TTC Involved": 15,
    # Subway alpha codes
    "MUATC": 16, "TUSC": 17, "MUIS": 18, "MUNOA": 19, "MUSC": 20,
    "TRSIG": 21, "SUDP": 22, "EUAC": 23, "PUOPO": 24, "MUSAN": 25,
    "PUMST": 26, "PUMEL": 27, "MUO": 28, "SUO": 29, "SUUT": 30,
    "MUIRS": 31, "MUPAA": 32, "TUNOA": 33, "TUO": 34, "MUNCA": 35,
}

# Direction / bound encoding
BOUND_ENCODING = {"N": 1, "S": 2, "E": 3, "W": 4, "B": 5}


def get_season(month: int) -> int:
    """Map month to season: 1=Winter, 2=Spring, 3=Summer, 4=Fall."""
    if month in (12, 1, 2):
        return 1
    elif month in (3, 4, 5):
        return 2
    elif month in (6, 7, 8):
        return 3
    return 4


def load_and_engineer_features(filepath: str | None = None) -> tuple:
    """Load TTC delay CSV and extract ML features.

    Automatically uses enriched CSV (with weather) if available,
    falls back to original CSV.
    """
    if filepath is None:
        if os.path.exists(ENRICHED_PATH):
            filepath = ENRICHED_PATH
            logger.info("Using enriched CSV with weather data")
        else:
            filepath = ORIGINAL_PATH
            logger.info("Enriched CSV not found, using original")

    logger.info(f"Loading delay data from {filepath}")
    df = pd.read_csv(filepath)
    logger.info(f"Loaded {len(df)} rows. Columns: {list(df.columns)}")

    # Dynamically inspect columns
    date_col = _find_column(df, ["date", "Date", "DATE"])
    time_col = _find_column(df, ["time", "Time", "TIME"])
    station_col = _find_column(df, ["station", "Station", "STATION", "Location"])
    delay_col = _find_column(df, ["min_delay", "Min Delay", "Min delay", "MinDelay", "Delay"])
    line_col = _find_column(df, ["line", "Line", "LINE", "Route"])
    code_col = _find_column(df, ["code", "Code", "CODE", "Incident"])
    bound_col = _find_column(df, ["bound", "Bound", "BOUND", "Direction"])
    gap_col = _find_column(df, ["min_gap", "Min Gap", "Min gap", "MinGap", "Gap"])
    mode_col = _find_column(df, ["mode", "Mode", "MODE"])

    if not all([date_col, time_col, delay_col]):
        raise ValueError(f"Missing required columns. Found: {list(df.columns)}")

    # Parse date
    df["parsed_date"] = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    df = df.dropna(subset=["parsed_date"])

    # --- Time features ---
    df["hour"] = df[time_col].apply(_parse_hour)
    df["month"] = df["parsed_date"].dt.month
    df["day_of_week"] = df["parsed_date"].dt.dayofweek  # 0=Monday
    df["season"] = df["month"].apply(get_season)
    df["is_rush_hour"] = df["hour"].apply(lambda h: 1 if (7 <= h <= 9 or 17 <= h <= 19) else 0)
    df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)

    # --- Mode feature (subway/bus/streetcar) ---
    if mode_col and mode_col in df.columns:
        df["mode_encoded"] = df[mode_col].str.lower().str.strip().map(MODE_ENCODING).fillna(0).astype(int)
    else:
        df["mode_encoded"] = 1  # Default to subway if no mode column

    # --- Line/route encoding ---
    # Frequency-encode: top routes get their own code, rest bucketed to 0
    if line_col and line_col in df.columns:
        top_lines = df[line_col].astype(str).value_counts().head(60).index.tolist()
        line_map = {line: i + 1 for i, line in enumerate(top_lines)}
        df["line_encoded"] = df[line_col].astype(str).map(line_map).fillna(0).astype(int)
    else:
        df["line_encoded"] = 0

    # --- Station / location encoding ---
    if station_col and station_col in df.columns:
        top_stations = df[station_col].dropna().astype(str).value_counts().head(100).index.tolist()
        station_map = {s: i + 1 for i, s in enumerate(top_stations)}
        df["station_encoded"] = df[station_col].astype(str).map(station_map).fillna(0).astype(int)
    else:
        df["station_encoded"] = 0

    # --- Incident code encoding ---
    if code_col and code_col in df.columns:
        df["code_encoded"] = df[code_col].astype(str).map(CODE_ENCODING).fillna(0).astype(int)
    else:
        df["code_encoded"] = 0

    # --- Bound / direction encoding ---
    if bound_col and bound_col in df.columns:
        df["bound_encoded"] = df[bound_col].astype(str).str.strip().str.upper().map(BOUND_ENCODING).fillna(0).astype(int)
    else:
        df["bound_encoded"] = 0

    # --- Gap feature ---
    if gap_col and gap_col in df.columns:
        df["min_gap"] = pd.to_numeric(df[gap_col], errors="coerce").fillna(0)
    else:
        df["min_gap"] = 0

    # --- Weather features (from enriched CSV) ---
    weather_features = []
    if "temperature_mean" in df.columns:
        for col in ["temperature_mean", "precipitation_sum", "snowfall_sum", "wind_speed_max"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        weather_features = ["temperature_mean", "precipitation_sum", "snowfall_sum", "wind_speed_max"]
        logger.info("Weather features found and included")
    else:
        logger.info("No weather columns found, skipping weather features")

    # --- Target variables ---
    df["delay_minutes"] = pd.to_numeric(df[delay_col], errors="coerce").fillna(0)
    df["is_significant_delay"] = (df["delay_minutes"] > 5).astype(int)

    # --- Feature column list ---
    feature_cols = [
        "hour", "day_of_week", "month", "season",
        "is_rush_hour", "is_weekend",
        "mode_encoded", "line_encoded", "station_encoded",
        "bound_encoded", "code_encoded", "min_gap",
    ] + weather_features

    # Drop rows with NaN in features
    df = df.dropna(subset=feature_cols + ["delay_minutes"])

    X = df[feature_cols]
    y_class = df["is_significant_delay"]
    y_reg = df["delay_minutes"]

    logger.info(f"Feature engineering complete: {len(X)} samples, {len(feature_cols)} features")
    logger.info(f"Features: {feature_cols}")
    logger.info(f"Significant delays: {y_class.sum()} / {len(y_class)} ({y_class.mean():.1%})")

    if mode_col and mode_col in df.columns:
        for mode_name, mode_val in MODE_ENCODING.items():
            count = (df["mode_encoded"] == mode_val).sum()
            logger.info(f"  {mode_name}: {count} samples")

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
        return 12
