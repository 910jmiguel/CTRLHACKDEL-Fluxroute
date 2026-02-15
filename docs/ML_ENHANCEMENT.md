# ML Delay Prediction Enhancement

## Overview

FluxRoute's delay prediction model uses **XGBoost** (classifier + regressor) trained on TTC historical delay data enriched with weather from the Open-Meteo Archive API.

**Outputs:**
- `delay_probability` (0.0 - 1.0) — chance of a significant delay (>5 min)
- `expected_delay_minutes` (float) — predicted delay duration
- `confidence` (0.85 ML / 0.65 heuristic)
- `contributing_factors` — human-readable list of reasons

---

## Features (15 total)

### Time Features (6)
| Feature | Description |
|---------|-------------|
| `hour` | Hour of day (0-23) |
| `day_of_week` | 0=Monday to 6=Sunday |
| `month` | 1-12 |
| `season` | 1=Winter, 2=Spring, 3=Summer, 4=Fall |
| `is_rush_hour` | 1 if 7-9am or 5-7pm |
| `is_weekend` | 1 if Saturday/Sunday |

### Line/Location Features (2)
| Feature | Description |
|---------|-------------|
| `line_encoded` | YU=1, BD=2, SRT=3, SHEP=4 |
| `station_encoded` | Alphabetically sorted ordinal per station |

### Incident Features (3)
| Feature | Description |
|---------|-------------|
| `code_encoded` | Incident type (see table below) |
| `bound_encoded` | Direction: N=1, S=2, E=3, W=4 |
| `min_gap` | Service gap in minutes |

### Weather Features (4)
| Feature | Source | Description |
|---------|--------|-------------|
| `temperature_mean` | Open-Meteo | Daily mean temp (C) |
| `precipitation_sum` | Open-Meteo | Daily precipitation (mm) |
| `snowfall_sum` | Open-Meteo | Daily snowfall (cm) |
| `wind_speed_max` | Open-Meteo | Max wind speed (km/h) |

### Incident Code Reference
| Code | Encoding | Description |
|------|----------|-------------|
| MUATC | 1 | Miscellaneous at Track Level |
| TUSC | 2 | Trespasser at Station (high delay) |
| MUIS | 3 | Miscellaneous In-Station |
| MUNOA | 4 | Miscellaneous No Alarm |
| MUSC | 5 | Miscellaneous Security |
| TRSIG | 6 | Signal/Track Related (high delay) |
| SUDP | 7 | Subway Door Problem |
| EUAC | 8 | Equipment at Car |
| PUOPO | 9 | Passenger On Platform |
| MUSAN | 10 | Miscellaneous Safety |

---

## Training Pipeline

### Step 1: Enrich Data with Weather

```bash
cd backend
python -m ml.enrich_weather_data
```

- Reads `data/ttc-subway-delay-data.csv` (514 rows, 10 columns)
- Fetches historical weather from Open-Meteo Archive API for each unique date (~247 dates)
- Outputs `data/ttc-subway-delay-data-enriched.csv` (514 rows, 16 columns)
- Takes ~3 minutes (rate-limited API calls)

### Step 2: Train Model

```bash
cd backend
python -m ml.train_model
```

- Loads enriched CSV (falls back to original if enriched not found)
- Extracts 15 features via `ml/feature_engineering.py`
- Augments with 2000 synthetic samples (dataset is small)
- Trains XGBoost classifier (delay probability) + regressor (delay minutes)
- Logs feature importance
- Saves to `ml/delay_model.joblib`

### Step 3: Verify

Start the backend and check logs:
```bash
python -m uvicorn app.main:app --reload
```

You should see:
```
ML model loaded successfully (15 features)
ML predictor mode: ml
```

---

## How Predictions Work at Runtime

1. User requests routes via `/api/routes`
2. Route engine fetches **real-time weather** from Open-Meteo
3. For each transit route, calls `predictor.predict()` with:
   - Line, hour, day of week, month
   - Temperature, precipitation, snowfall, wind speed (from real-time weather)
4. XGBoost classifier returns delay probability
5. XGBoost regressor returns expected delay minutes
6. Results shown in route cards + delay indicator badge

### Fallback Behavior

| Scenario | Behavior |
|----------|----------|
| Model file missing | Heuristic mode (rule-based, confidence 0.65) |
| Weather API down | Default weather values (5C, no precipitation) |
| Enriched CSV missing | Trains on original CSV (11 features, no weather) |
| <50 training rows | Synthetic data only |

---

## Architecture

```
ttc-subway-delay-data.csv (514 rows)
        |
        v
ml/enrich_weather_data.py  <-- Open-Meteo Archive API
        |
        v
ttc-subway-delay-data-enriched.csv (514 rows + 6 weather cols)
        |
        v
ml/feature_engineering.py  --> 15 features
        |
        v
ml/train_model.py  --> delay_model.joblib
        |                  (XGBoost classifier + regressor)
        v
app/ml_predictor.py  <-- Real-time weather from Open-Meteo
        |
        v
app/route_engine.py + app/otp_client.py
        |
        v
/api/routes response (delay_info per route)
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/ml/enrich_weather_data.py` | Fetch historical weather, create enriched CSV |
| `backend/ml/feature_engineering.py` | Extract 15 features from CSV data |
| `backend/ml/train_model.py` | Train XGBoost models, save joblib |
| `backend/app/ml_predictor.py` | Load model, serve predictions |
| `backend/app/route_engine.py` | Integrate predictions into routing |
| `backend/app/otp_client.py` | Integrate predictions into OTP routes |
| `backend/app/weather.py` | Real-time weather from Open-Meteo |

---

## Future: Data Collection Pipeline

The current model trains on a static 514-row CSV from 2023. To grow the dataset:

1. **OTP provides scheduled times** (from GTFS static feeds)
2. **GTFS-RT provides actual vehicle positions** (real-time)
3. **Delta = actual - scheduled = delay**
4. A future `ml/data_collector.py` would monitor this delta and log new delay observations
5. Periodic retraining would incorporate the growing dataset

This is designed but not yet implemented — the static model works well for the hackathon demo.
