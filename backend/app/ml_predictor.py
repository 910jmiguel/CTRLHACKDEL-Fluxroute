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


class DelayPredictor:
    def __init__(self):
        self.classifier = None
        self.regressor = None
        self.mode = "heuristic"

    def load(self):
        """Try to load trained model, fall back to heuristic."""
        try:
            if os.path.exists(MODEL_PATH):
                model_data = joblib.load(MODEL_PATH)
                self.classifier = model_data.get("classifier")
                self.regressor = model_data.get("regressor")
                self.mode = "ml"
                logger.info("ML model loaded successfully")
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
        is_adverse_weather: bool = False,
    ) -> dict:
        """Predict delay probability and expected duration."""
        now = datetime.now()
        hour = hour if hour is not None else now.hour
        day_of_week = day_of_week if day_of_week is not None else now.weekday()
        month = month if month is not None else now.month

        normalized_line = LINE_MAP.get(line.lower().strip(), "1")

        if self.mode == "ml" and self.classifier is not None:
            return self._ml_predict(normalized_line, hour, day_of_week, month, is_adverse_weather)

        return self._heuristic_predict(normalized_line, hour, day_of_week, month, is_adverse_weather, station)

    def _ml_predict(self, line: str, hour: int, day_of_week: int, month: int, is_adverse_weather: bool) -> dict:
        """Use trained XGBoost model for prediction."""
        import numpy as np

        is_rush = 1 if (7 <= hour <= 9 or 17 <= hour <= 19) else 0
        is_weekend = 1 if day_of_week >= 5 else 0

        # Features must match training order: hour, day_of_week, month, is_rush_hour, is_weekend, line_encoded, station_encoded
        features = np.array([[
            hour,
            day_of_week,
            month,
            is_rush,
            is_weekend,
            int(line),
            0,  # station_encoded (default, no specific station mapping at prediction time)
        ]])

        try:
            prob = float(self.classifier.predict_proba(features)[0][1])
            expected_min = float(self.regressor.predict(features)[0])
            expected_min = max(0, expected_min)

            factors = self._get_factors(line, hour, day_of_week, month, is_adverse_weather)

            return {
                "delay_probability": round(prob, 3),
                "expected_delay_minutes": round(expected_min, 1),
                "confidence": 0.85,
                "contributing_factors": factors,
            }
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}, falling back to heuristic")
            return self._heuristic_predict(line, hour, day_of_week, month, is_adverse_weather)

    def _heuristic_predict(
        self,
        line: str,
        hour: int,
        day_of_week: int,
        month: int,
        is_adverse_weather: bool,
        station: Optional[str] = None,
    ) -> dict:
        """Heuristic prediction based on real TTC patterns."""
        # Base delay probabilities by line
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
        if day_of_week == 0:  # Monday
            modifier += 0.05
            factors.append("Monday (historically most delays)")
        elif day_of_week == 4:  # Friday
            modifier -= 0.03
            factors.append("Friday (fewer delays)")
        elif day_of_week >= 5:  # Weekend
            modifier -= 0.08
            factors.append("Weekend (reduced service, fewer delays)")

        # Seasonal effect
        if month in (12, 1, 2):
            modifier += 0.10
            factors.append("Winter months (+10% — weather, switch heaters)")
        elif month in (6, 7, 8):
            modifier += 0.03
            factors.append("Summer (slight increase — AC failures)")

        # Weather effect
        if is_adverse_weather:
            modifier += 0.12
            factors.append("Adverse weather conditions (+12%)")

        # Line-specific notes
        line_names = {"1": "Line 1 Yonge-University", "2": "Line 2 Bloor-Danforth", "4": "Line 4 Sheppard", "5": "Line 5 Eglinton", "6": "Line 6 Finch West"}
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

    def _get_factors(self, line: str, hour: int, day_of_week: int, month: int, is_adverse_weather: bool) -> list[str]:
        """Generate human-readable contributing factors."""
        factors = []
        line_names = {"1": "Line 1 Yonge-University", "2": "Line 2 Bloor-Danforth", "4": "Line 4 Sheppard", "5": "Line 5 Eglinton", "6": "Line 6 Finch West"}
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

        if is_adverse_weather:
            factors.append("Adverse weather")

        return factors
