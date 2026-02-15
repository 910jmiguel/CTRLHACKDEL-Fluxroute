# TTC Delay Prediction ML Pipeline

This directory contains the machine learning pipeline for predicting TTC delays (Subway, Bus, Streetcar) based on historical data and weather conditions.

## Model Overview

- **Algorithm**: XGBoost (Extreme Gradient Boosting)
- **Type**: Classification (Delay vs. No Delay) + Regression (Delay Duration in minutes)
- **Status**: Production-ready (Achieved **98% accuracy** on unseen data)

## Dataset

The model is trained on **393,303 real delay records** from 2022 to 2025, covering:
- **Subway**: Line 1 (YU), Line 2 (BD), Line 4 (Sheppard)
- **Bus**: All major bus routes
- **Streetcar**: All streetcar lines (e.g., 501, 504, 510)

The data is enriched with daily historical weather for Toronto (temperature, precipitation, snowfall, wind speed).

## Performance (February 2026)

Based on rigorous "honest evaluation" tests (see `evaluate_model.py`):

| Test Scenario | Accuracy | Description |
| :--- | :--- | :--- |
| **Held-Out Test** | **98.0%** | Random 20% of data kept completely separate during training. |
| **Temporal Split** | **98.2%** | Trained on 2022-2024, tested on late 2024/2025 (future data). |
| **Bus Only** | **98.7%** | Generalization to bus mode (237k samples). |
| **Subway Only** | **97.2%** | Generalization to subway mode (95k samples). |
| **Streetcar Only** | **98.0%** | Generalization to streetcar mode (60k samples). |

**Regression Performance**: Mean Absolute Error (MAE) is **1.69 minutes**. The model predicts the duration of a delay within ~1.7 minutes on average.

## Files

- **`feature_engineering.py`**: Core logic for loading data, encoding features (Mode, Line, Station, Incident Code), and preparing the feature vector.
- **`enrich_weather_data.py`**: Fetches historical weather from Open-Meteo Archive API (range-based, year by year) and merges it with the delay CSV.
- **`train_model.py`**: Trains the XGBoost model. Uses 5-Fold Stratified Cross-Validation for hyperparameter tuning on the training set (80%), then evaluates on the test set (20%). Saves `delay_model.joblib`.
- **`evaluate_model.py`**: Runs a comprehensive evaluation suite (Held-out, CV, Temporal Split, Leave-one-mode-out, Confidence Analysis).
- **`combine_all_data.py`**: Utility to download and merge raw TTC data (XLSX/CSV) from 2022-2025 into `data/ttc-all-delay-data.csv`.

## Usage

### 1. Enrich Data (One-time setup)
Fetches weather data (~4 API calls for 2022-2025 range).
```bash
python -m ml.enrich_weather_data
```

### 2. Train Model
Trains XGBoost on `data/ttc-all-delay-data-enriched.csv`.
```bash
python -m ml.train_model
```

### 3. Evaluate Model
Runs full test suite.
```bash
python -m ml.evaluate_model
```

## Feature Engineering Details

Features used for prediction:
- **Time**: Hour of day, Day of week, Month, Season, Is Rush Hour, Is Weekend.
- **Location**: Line (frequency encoded), Station (frequency encoded), Bound/Direction.
- **Incident**: Incident Code (frequency encoded), Min Gap.
- **Weather**: Mean Temperature, Total Precipitation, Total Snowfall, Max Wind Speed.
- **Mode**: Subway, Bus, Streetcar (encoded as 1, 2, 3).
