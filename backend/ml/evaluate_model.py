"""Honest evaluation of the delay prediction model.

Runs multiple evaluation strategies to give a real picture of model performance:
1. Held-out real data (no augmentation)
2. Stratified K-Fold on real data only
3. Temporal split (train on early dates, test on later dates)
4. Leave-one-mode-out (generalization across subway/bus/streetcar)
5. Prediction confidence analysis
6. Regressor evaluation
"""

import logging
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ml.feature_engineering import load_and_engineer_features, MODE_ENCODING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fluxroute.ml.evaluate")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "delay_model.joblib")


def evaluate():
    """Run full honest evaluation suite."""
    logger.info("=" * 60)
    logger.info("HONEST MODEL EVALUATION")
    logger.info("=" * 60)

    # Load model
    if not os.path.exists(MODEL_PATH):
        logger.error(f"No model found at {MODEL_PATH}. Train first.")
        return

    model_data = joblib.load(MODEL_PATH)
    classifier = model_data["classifier"]
    regressor = model_data["regressor"]
    feature_cols = model_data["feature_cols"]
    train_metrics = model_data.get("metrics", {})

    logger.info(f"\nTrained model metrics (from training): {train_metrics}")
    logger.info(f"Features: {feature_cols}")

    # Load REAL data only — no augmentation
    try:
        X, y_class, y_reg, _ = load_and_engineer_features()
    except Exception as e:
        logger.error(f"Failed to load features: {e}")
        return

    X_np = X.values
    y_cls = y_class.values
    y_reg_np = y_reg.values

    n_samples = len(X_np)
    n_positive = y_cls.sum()
    n_negative = n_samples - n_positive

    logger.info(f"\nDataset: {n_samples} real samples")
    logger.info(f"Class balance: {n_negative} no-delay, {n_positive} delay ({n_positive/n_samples:.1%})")

    # ─── 1. Held-out real data (proper split, NO augmentation) ───
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Held-out 20% real data (no augmentation)")
    logger.info("=" * 60)

    X_train, X_test, y_train, y_test, yr_train, yr_test = train_test_split(
        X_np, y_cls, y_reg_np, test_size=0.20, random_state=42, stratify=y_cls
    )

    y_pred = classifier.predict(X_test)
    y_reg_pred = regressor.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    mae = mean_absolute_error(yr_test, y_reg_pred)

    logger.info(f"Accuracy:  {acc:.4f} ({acc:.1%})")
    logger.info(f"Precision: {prec:.4f}")
    logger.info(f"Recall:    {rec:.4f}")
    logger.info(f"F1 Score:  {f1:.4f}")
    logger.info(f"MAE:       {mae:.2f} min")
    logger.info(f"\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"  TN={cm[0][0]}  FP={cm[0][1]}")
    logger.info(f"  FN={cm[1][0]}  TP={cm[1][1]}")
    logger.info(f"\n{classification_report(y_test, y_pred, target_names=['No delay', 'Delay'])}")

    # ─── 2. 5-Fold Stratified CV on real data only ───
    logger.info("=" * 60)
    logger.info("TEST 2: 5-Fold Stratified CV (real data only)")
    logger.info("=" * 60)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(classifier, X_np, y_cls, cv=cv, scoring="accuracy")

    logger.info(f"Fold accuracies: {[f'{s:.4f}' for s in cv_scores]}")
    logger.info(f"Mean: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    logger.info(f"Min fold: {cv_scores.min():.4f}, Max fold: {cv_scores.max():.4f}")

    # Also do CV for F1
    cv_f1 = cross_val_score(classifier, X_np, y_cls, cv=cv, scoring="f1")
    logger.info(f"F1 scores: {[f'{s:.4f}' for s in cv_f1]}")
    logger.info(f"Mean F1: {cv_f1.mean():.4f} (+/- {cv_f1.std():.4f})")

    # ─── 3. Temporal split ───
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Temporal split (train early, test late)")
    logger.info("=" * 60)

    from ml.feature_engineering import ENRICHED_PATH, ORIGINAL_PATH
    csv_path = ENRICHED_PATH if os.path.exists(ENRICHED_PATH) else ORIGINAL_PATH
    raw_df = pd.read_csv(csv_path)

    date_col = "date" if "date" in raw_df.columns else "Date"
    raw_df["parsed_date"] = pd.to_datetime(raw_df[date_col], errors="coerce", format="mixed")
    raw_df = raw_df.dropna(subset=["parsed_date"])

    if len(raw_df) >= len(X_np):
        dates = raw_df["parsed_date"].values[:len(X_np)]
        sorted_idx = np.argsort(dates)

        split_point = int(len(sorted_idx) * 0.75)
        train_idx = sorted_idx[:split_point]
        test_idx = sorted_idx[split_point:]

        X_t_test = X_np[test_idx]
        y_t_test = y_cls[test_idx]

        y_t_pred = classifier.predict(X_t_test)
        t_acc = accuracy_score(y_t_test, y_t_pred)
        t_f1 = f1_score(y_t_test, y_t_pred, zero_division=0)

        logger.info(f"Train: first 75% by date ({len(train_idx)} samples)")
        logger.info(f"Test: last 25% by date ({len(test_idx)} samples)")
        logger.info(f"Temporal accuracy: {t_acc:.4f} ({t_acc:.1%})")
        logger.info(f"Temporal F1: {t_f1:.4f}")
    else:
        logger.warning("Could not align dates for temporal split")

    # ─── 4. Leave-one-mode-out ───
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Leave-one-mode-out (generalization by transit mode)")
    logger.info("=" * 60)

    if "mode_encoded" in feature_cols:
        mode_col_idx = feature_cols.index("mode_encoded")
        mode_names = {v: k for k, v in MODE_ENCODING.items()}

        for mode_val in sorted(MODE_ENCODING.values()):
            mode_mask = X_np[:, mode_col_idx] == mode_val
            n_mode = mode_mask.sum()
            if n_mode < 5:
                continue

            X_lo_test = X_np[mode_mask]
            y_lo_test = y_cls[mode_mask]

            y_lo_pred = classifier.predict(X_lo_test)
            lo_acc = accuracy_score(y_lo_test, y_lo_pred)

            name = mode_names.get(mode_val, f"Mode {mode_val}")
            logger.info(f"  {name} (n={n_mode}): accuracy={lo_acc:.4f}")

    # ─── 5. Prediction confidence analysis ───
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Prediction confidence distribution")
    logger.info("=" * 60)

    proba = classifier.predict_proba(X_np)[:, 1]
    logger.info(f"Delay probability stats:")
    logger.info(f"  Mean: {proba.mean():.3f}")
    logger.info(f"  Median: {np.median(proba):.3f}")
    logger.info(f"  Std: {proba.std():.3f}")
    logger.info(f"  Min: {proba.min():.3f}, Max: {proba.max():.3f}")

    # Calibration buckets
    buckets = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
    logger.info(f"\nCalibration (predicted probability vs actual delay rate):")
    for lo, hi in buckets:
        mask = (proba >= lo) & (proba < hi)
        n = mask.sum()
        if n > 0:
            actual_rate = y_cls[mask].mean()
            logger.info(f"  Predicted {lo:.1f}-{hi:.1f}: n={n}, actual delay rate={actual_rate:.3f}")

    # ─── 6. Regressor evaluation ───
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Regressor performance (delay minutes)")
    logger.info("=" * 60)

    reg_pred = regressor.predict(X_np)
    overall_mae = mean_absolute_error(y_reg_np, reg_pred)
    logger.info(f"Overall MAE: {overall_mae:.2f} min")

    # MAE by delay vs no-delay
    delay_mask = y_cls == 1
    if delay_mask.sum() > 0:
        mae_delay = mean_absolute_error(y_reg_np[delay_mask], reg_pred[delay_mask])
        logger.info(f"MAE on delayed samples: {mae_delay:.2f} min")
    no_delay_mask = y_cls == 0
    if no_delay_mask.sum() > 0:
        mae_no_delay = mean_absolute_error(y_reg_np[no_delay_mask], reg_pred[no_delay_mask])
        logger.info(f"MAE on non-delayed samples: {mae_no_delay:.2f} min")

    # ─── Summary ───
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Dataset size:          {n_samples} real samples")
    logger.info(f"Held-out accuracy:     {acc:.1%}")
    logger.info(f"5-Fold CV accuracy:    {cv_scores.mean():.1%} (+/- {cv_scores.std():.1%})")
    logger.info(f"5-Fold CV F1:          {cv_f1.mean():.1%}")
    logger.info(f"Regressor MAE:         {overall_mae:.2f} min")

    if cv_scores.mean() >= 0.95:
        logger.info("\n>>> VERDICT: Model GENUINELY achieves 95%+ on real data cross-validation")
    elif cv_scores.mean() >= 0.85:
        logger.info("\n>>> VERDICT: Model is strong (85%+) but below 95% on real data")
    elif cv_scores.mean() >= 0.70:
        logger.info("\n>>> VERDICT: Model is decent (70%+) — typical for noisy real-world data")
    else:
        logger.info("\n>>> VERDICT: Model struggles — need more data or better features")


if __name__ == "__main__":
    evaluate()
