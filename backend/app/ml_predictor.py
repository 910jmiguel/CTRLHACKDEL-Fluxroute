import logging
import os
from datetime import datetime
from typing import Optional

import joblib

logger = logging.getLogger("fluxroute.ml")

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "delay_model.joblib")

# Line name normalization mapping
LINE_MAP = {
    "line 1": "1", "yu": "1", "yonge": "1", "yonge-university": "1", "line1": "1", "1": "1",
    "line 2": "2", "bd": "2", "bloor": "2", "bloor-danforth": "2", "line2": "2", "2": "2",
    "line 4": "4", "sheppard": "4", "shep": "4", "line4": "4", "4": "4",
    "line 5": "5", "eglinton": "5", "crosstown": "5", "lrt": "5", "line5": "5", "5": "5",
    "line 6": "6", "finch west": "6", "finch": "6", "line6": "6", "6": "6",
}

# Transit mode encoding (must match feature_engineering.py)
MODE_MAP = {"subway": 1, "bus": 2, "streetcar": 3, "lrt": 1}


def _get_season(month: int) -> int:
    """Map month to season: 1=Winter, 2=Spring, 3=Summer, 4=Fall."""
    if month in (12, 1, 2):
        return 1
    elif month in (3, 4, 5):
        return 2
    elif month in (6, 7, 8):
        return 3
    return 4


class DelayPredictor:
    def __init__(self):
        self.classifier = None
        self.regressor = None
        self.feature_cols = None
        self.mode = "heuristic"

    def load(self):
        """Try to load trained model, fall back to heuristic."""
        try:
            if os.path.exists(MODEL_PATH):
                model_data = joblib.load(MODEL_PATH)
                self.classifier = model_data.get("classifier")
                self.regressor = model_data.get("regressor")
                self.feature_cols = model_data.get("feature_cols", [])
                self.mode = "ml"
                logger.info(f"ML model loaded successfully ({len(self.feature_cols)} features)")
            else:
                logger.info("No ML model found, using heuristic mode")
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}. Using heuristic mode")
            self.mode = "heuristic"

    def predict(
        self,
        line: str,
        station: Optional[str] = None,
        hour: Optional[int] = None,
        day_of_week: Optional[int] = None,
        month: Optional[int] = None,
        temperature: Optional[float] = None,
        precipitation: Optional[float] = None,
        snowfall: Optional[float] = None,
        wind_speed: Optional[float] = None,
        mode: Optional[str] = None,
        # Backward compat
        is_adverse_weather: Optional[bool] = None,
    ) -> dict:
        """Predict delay probability and expected duration."""
        now = datetime.now()
        hour = hour if hour is not None else now.hour
        day_of_week = day_of_week if day_of_week is not None else now.weekday()
        month = month if month is not None else now.month

        # Default weather values if not provided
        if temperature is None:
            temperature = 5.0
        if precipitation is None:
            precipitation = 0.0
        if snowfall is None:
            snowfall = 0.0
        if wind_speed is None:
            wind_speed = 15.0

        # Backward compat: if old is_adverse_weather was passed, set weather values
        if is_adverse_weather is not None and is_adverse_weather:
            if temperature == 5.0 and precipitation == 0.0:
                temperature = -10.0
                precipitation = 5.0
                snowfall = 2.0
                wind_speed = 45.0

        normalized_line = LINE_MAP.get(line.lower().strip(), "1")
        mode_encoded = MODE_MAP.get((mode or "subway").lower().strip(), 1)

        if self.mode == "ml" and self.classifier is not None:
            return self._ml_predict(
                normalized_line, hour, day_of_week, month,
                temperature, precipitation, snowfall, wind_speed,
                mode_encoded,
            )

        return self._heuristic_predict(
            normalized_line, hour, day_of_week, month,
            temperature, precipitation, snowfall, wind_speed,
            station,
        )

    def _ml_predict(
        self, line: str, hour: int, day_of_week: int, month: int,
        temperature: float, precipitation: float, snowfall: float, wind_speed: float,
        mode_encoded: int = 1,
    ) -> dict:
        """Use trained XGBoost model for prediction."""
        import numpy as np

        is_rush = 1 if (7 <= hour <= 9 or 17 <= hour <= 19) else 0
        is_weekend = 1 if day_of_week >= 5 else 0
        season = _get_season(month)

        # Build feature vector matching training order
        # Full set: hour, day_of_week, month, season, is_rush_hour, is_weekend,
        #           line_encoded, station_encoded, bound_encoded, code_encoded, min_gap,
        #           temperature_mean, precipitation_sum, snowfall_sum, wind_speed_max
        all_features = {
            "hour": hour,
            "day_of_week": day_of_week,
            "month": month,
            "season": season,
            "is_rush_hour": is_rush,
            "is_weekend": is_weekend,
            "mode_encoded": mode_encoded,
            "line_encoded": int(line),
            "station_encoded": 0,
            "bound_encoded": 0,
            "code_encoded": 0,
            "min_gap": 0,
            "temperature_mean": temperature,
            "precipitation_sum": precipitation,
            "snowfall_sum": snowfall,
            "wind_speed_max": wind_speed,
        }

        # Build feature vector in the exact order the model expects
        feature_vector = []
        for col in self.feature_cols:
            feature_vector.append(all_features.get(col, 0))

        features = np.array([feature_vector])

        try:
            prob = float(self.classifier.predict_proba(features)[0][1])
            expected_min = float(self.regressor.predict(features)[0])
            expected_min = max(0, expected_min)

            factors = self._get_factors(line, hour, day_of_week, month, temperature, precipitation, snowfall, wind_speed)

            return {
                "delay_probability": round(prob, 3),
                "expected_delay_minutes": round(expected_min, 1),
                "confidence": 0.85,
                "contributing_factors": factors,
            }
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}, falling back to heuristic")
            return self._heuristic_predict(
                line, hour, day_of_week, month,
                temperature, precipitation, snowfall, wind_speed,
            )

    def _heuristic_predict(
        self,
        line: str,
        hour: int,
        day_of_week: int,
        month: int,
        temperature: float,
        precipitation: float,
        snowfall: float,
        wind_speed: float,
        station: Optional[str] = None,
    ) -> dict:
        """Heuristic prediction based on real TTC patterns."""
        base_prob = {"1": 0.25, "2": 0.18, "4": 0.12, "5": 0.15, "6": 0.13}.get(line, 0.20)

        factors = []
        modifier = 0.0

        # Rush hour effect
        if 7 <= hour <= 9:
            modifier += 0.15
            factors.append("Morning rush hour (+15%)")
        elif 17 <= hour <= 19:
            modifier += 0.15
            factors.append("Evening rush hour (+15%)")
        elif 22 <= hour or hour <= 5:
            modifier -= 0.05
            factors.append("Off-peak hours (-5%)")

        # Day of week effect
        if day_of_week == 0:
            modifier += 0.05
            factors.append("Monday (historically most delays)")
        elif day_of_week == 4:
            modifier -= 0.03
            factors.append("Friday (fewer delays)")
        elif day_of_week >= 5:
            modifier -= 0.08
            factors.append("Weekend (reduced service, fewer delays)")

        # Seasonal effect
        if month in (12, 1, 2):
            modifier += 0.10
            factors.append("Winter months (+10%)")
        elif month in (6, 7, 8):
            modifier += 0.03
            factors.append("Summer (slight increase)")

        # Granular weather effects
        weather_modifier = 0.0
        if precipitation > 5.0:
            weather_modifier += 0.10
            factors.append(f"Heavy precipitation ({precipitation:.1f}mm, +10%)")
        elif precipitation > 2.0:
            weather_modifier += 0.05
            factors.append(f"Moderate precipitation ({precipitation:.1f}mm, +5%)")

        if snowfall > 1.0:
            weather_modifier += 0.08
            factors.append(f"Snowfall ({snowfall:.1f}cm, +8%)")

        if temperature < -15.0:
            weather_modifier += 0.07
            factors.append(f"Extreme cold ({temperature:.0f}C, +7%)")
        elif temperature < -5.0:
            weather_modifier += 0.03
            factors.append(f"Cold weather ({temperature:.0f}C, +3%)")

        if wind_speed > 40.0:
            weather_modifier += 0.05
            factors.append(f"High winds ({wind_speed:.0f}km/h, +5%)")

        modifier += weather_modifier

        # Line-specific notes
        line_names = {
            "1": "Line 1 Yonge-University", "2": "Line 2 Bloor-Danforth",
            "4": "Line 4 Sheppard", "5": "Line 5 Eglinton", "6": "Line 6 Finch West",
        }
        factors.insert(0, f"{line_names.get(line, 'Unknown line')} base rate: {base_prob:.0%}")

        probability = max(0.01, min(0.95, base_prob + modifier))

        # Expected delay minutes (correlated with probability)
        if probability > 0.4:
            expected_min = 8.0 + (probability - 0.4) * 20
        elif probability > 0.2:
            expected_min = 4.0 + (probability - 0.2) * 20
        else:
            expected_min = probability * 20

        return {
            "delay_probability": round(probability, 3),
            "expected_delay_minutes": round(expected_min, 1),
            "confidence": 0.65,
            "contributing_factors": factors,
        }

    def _get_factors(
        self, line: str, hour: int, day_of_week: int, month: int,
        temperature: float, precipitation: float, snowfall: float, wind_speed: float,
    ) -> list[str]:
        """Generate human-readable contributing factors."""
        factors = []
        line_names = {
            "1": "Line 1 Yonge-University", "2": "Line 2 Bloor-Danforth",
            "4": "Line 4 Sheppard", "5": "Line 5 Eglinton", "6": "Line 6 Finch West",
        }
        factors.append(f"Line: {line_names.get(line, 'Unknown')}")

        if 7 <= hour <= 9:
            factors.append("Morning rush hour")
        elif 17 <= hour <= 19:
            factors.append("Evening rush hour")

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if 0 <= day_of_week < 7:
            factors.append(f"Day: {days[day_of_week]}")

        if month in (12, 1, 2):
            factors.append("Winter season")

        if precipitation > 2.0:
            factors.append(f"Precipitation: {precipitation:.1f}mm")
        if snowfall > 0.5:
            factors.append(f"Snowfall: {snowfall:.1f}cm")
        if temperature < -10:
            factors.append(f"Cold: {temperature:.0f}C")
        if wind_speed > 30:
            factors.append(f"Wind: {wind_speed:.0f}km/h")

        return factors
