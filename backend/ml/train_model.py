import logging
import os
import sys

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, mean_absolute_error
from xgboost import XGBClassifier, XGBRegressor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ml.feature_engineering import load_and_engineer_features

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fluxroute.ml.train")

MODEL_OUTPUT = os.path.join(os.path.dirname(__file__), "delay_model.joblib")


def train():
    """Train delay prediction models and save to disk."""
    logger.info("Starting model training...")

    try:
        X, y_class, y_reg, feature_cols = load_and_engineer_features()
    except Exception as e:
        logger.error(f"Failed to load features: {e}")
        logger.info("Creating model from synthetic patterns instead...")
        _train_synthetic()
        return

    if len(X) < 50:
        logger.warning("Not enough data for reliable training. Using synthetic.")
        _train_synthetic()
        return

    # With small datasets (<1000), augment with synthetic data for better patterns
    if len(X) < 1000:
        logger.info(f"Small dataset ({len(X)} rows), augmenting with synthetic data...")
        X_aug, y_cls_aug, y_reg_aug = _generate_synthetic_data(2000)
        X_combined = np.vstack([X.values, X_aug])
        y_class_combined = np.concatenate([y_class.values, y_cls_aug])
        y_reg_combined = np.concatenate([y_reg.values, y_reg_aug])
    else:
        X_combined = X.values
        y_class_combined = y_class.values
        y_reg_combined = y_reg.values

    # Split data (stratified for classification)
    X_train, X_test, y_cls_train, y_cls_test, y_reg_train, y_reg_test = train_test_split(
        X_combined, y_class_combined, y_reg_combined, test_size=0.2, random_state=42,
        stratify=y_class_combined
    )

    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # Compute class weight for imbalanced data
    n_pos = y_cls_train.sum()
    n_neg = len(y_cls_train) - n_pos
    scale_weight = n_neg / max(n_pos, 1)

    # Train classifier (delay probability)
    classifier = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=scale_weight,
        random_state=42,
        eval_metric="logloss",
    )
    classifier.fit(X_train, y_cls_train)

    # Evaluate classifier
    y_cls_pred = classifier.predict(X_test)
    acc = accuracy_score(y_cls_test, y_cls_pred)
    prec = precision_score(y_cls_test, y_cls_pred, zero_division=0)
    rec = recall_score(y_cls_test, y_cls_pred, zero_division=0)
    logger.info(f"Classifier — Accuracy: {acc:.3f}, Precision: {prec:.3f}, Recall: {rec:.3f}")

    # Train regressor (delay minutes)
    regressor = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
    )
    regressor.fit(X_train, y_reg_train)

    # Evaluate regressor
    y_reg_pred = regressor.predict(X_test)
    mae = mean_absolute_error(y_reg_test, y_reg_pred)
    logger.info(f"Regressor — MAE: {mae:.2f} minutes")

    # Save model
    model_data = {
        "classifier": classifier,
        "regressor": regressor,
        "feature_cols": feature_cols,
        "metrics": {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "mae": mae,
        },
    }

    joblib.dump(model_data, MODEL_OUTPUT)
    logger.info(f"Model saved to {MODEL_OUTPUT}")


def _generate_synthetic_data(n: int = 2000) -> tuple:
    """Generate synthetic delay data with realistic TTC patterns."""
    np.random.seed(42)

    hours = np.random.randint(0, 24, n)
    days = np.random.randint(0, 7, n)
    months = np.random.randint(1, 13, n)
    is_rush = ((hours >= 7) & (hours <= 9) | (hours >= 17) & (hours <= 19)).astype(int)
    is_weekend = (days >= 5).astype(int)
    lines = np.random.choice([1, 2, 3, 4], n, p=[0.4, 0.3, 0.1, 0.2])
    stations = np.random.randint(0, 50, n)

    # Simulate delay patterns based on real TTC data
    base_prob = np.where(lines == 1, 0.25, np.where(lines == 2, 0.18, np.where(lines == 4, 0.12, 0.15)))
    prob = base_prob + is_rush * 0.15 - is_weekend * 0.08 + np.where(np.isin(months, [12, 1, 2]), 0.1, 0)
    prob = np.clip(prob, 0.05, 0.9)

    is_delay = (np.random.random(n) < prob).astype(int)
    delay_mins = np.where(is_delay, np.random.exponential(5, n) + 2, np.random.exponential(2, n))
    delay_mins = np.clip(delay_mins, 0, 60)

    X = np.column_stack([hours, days, months, is_rush, is_weekend, lines, stations])
    return X, is_delay, delay_mins


def _train_synthetic():
    """Train on synthetic data if real data isn't available."""
    logger.info("Generating synthetic training data...")

    X, y_class, y_reg = _generate_synthetic_data(2000)

    X_train, X_test, y_cls_train, y_cls_test, y_reg_train, y_reg_test = train_test_split(
        X, y_class, y_reg, test_size=0.2, random_state=42, stratify=y_class
    )

    classifier = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42, eval_metric="logloss")
    classifier.fit(X_train, y_cls_train)

    regressor = XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42)
    regressor.fit(X_train, y_reg_train)

    acc = accuracy_score(y_cls_test, classifier.predict(X_test))
    mae = mean_absolute_error(y_reg_test, regressor.predict(X_test))
    logger.info(f"Synthetic model — Accuracy: {acc:.3f}, MAE: {mae:.2f} min")

    model_data = {
        "classifier": classifier,
        "regressor": regressor,
        "feature_cols": ["hour", "day_of_week", "month", "is_rush_hour", "is_weekend", "line_encoded", "station_encoded"],
        "metrics": {"accuracy": acc, "mae": mae},
    }

    joblib.dump(model_data, MODEL_OUTPUT)
    logger.info(f"Synthetic model saved to {MODEL_OUTPUT}")


if __name__ == "__main__":
    train()
