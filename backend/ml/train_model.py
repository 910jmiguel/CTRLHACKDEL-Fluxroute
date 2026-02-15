import logging
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, mean_absolute_error
from xgboost import XGBClassifier, XGBRegressor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ml.feature_engineering import load_and_engineer_features

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fluxroute.ml.train")

MODEL_OUTPUT = os.path.join(os.path.dirname(__file__), "delay_model.joblib")


def train():
    """Train delay prediction models on real TTC data.

    No oversampling, no synthetic data — just clean train/test split
    on 393K+ real delay records.
    """
    logger.info("Starting model training on real multi-mode TTC data...")

    try:
        X, y_class, y_reg, feature_cols = load_and_engineer_features()
    except Exception as e:
        logger.error(f"Failed to load features: {e}")
        return

    if len(X) < 100:
        logger.error(f"Not enough data ({len(X)} rows). Need at least 100.")
        return

    logger.info(f"Dataset: {len(X)} samples, {len(feature_cols)} features")
    logger.info(f"Class distribution: {y_class.value_counts().to_dict()}")

    X_np = X.values
    y_cls = y_class.values
    y_reg_np = y_reg.values

    # --- Clean 80/20 train/test split (stratified) ---
    X_train, X_test, y_cls_train, y_cls_test, y_reg_train, y_reg_test = train_test_split(
        X_np, y_cls, y_reg_np,
        test_size=0.20, random_state=42, stratify=y_cls,
    )

    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # Class weight for imbalanced data
    n_pos = y_cls_train.sum()
    n_neg = len(y_cls_train) - n_pos
    scale_weight = n_neg / max(n_pos, 1)
    logger.info(f"Class weight (scale_pos_weight): {scale_weight:.2f}")

    # --- Hyperparameter search ---
    best_acc = 0
    best_params = None

    param_grid = [
        {"n_estimators": 500, "max_depth": 6, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 3, "gamma": 0.1},
        {"n_estimators": 800, "max_depth": 7, "learning_rate": 0.03, "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 5, "gamma": 0.2},
        {"n_estimators": 600, "max_depth": 5, "learning_rate": 0.05, "subsample": 0.75, "colsample_bytree": 0.75, "min_child_weight": 5, "gamma": 0.1},
        {"n_estimators": 1000, "max_depth": 5, "learning_rate": 0.02, "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 3, "gamma": 0.15},
    ]

    logger.info(f"Searching {len(param_grid)} hyperparameter configurations...")

    for i, params in enumerate(param_grid):
        clf = XGBClassifier(
            **params,
            scale_pos_weight=scale_weight,
            random_state=42,
            eval_metric="logloss",
            use_label_encoder=False,
        )

        # 5-fold CV on training set only
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(clf, X_train, y_cls_train, cv=cv, scoring="accuracy")
        mean_acc = scores.mean()

        logger.info(f"  Config {i+1}: CV accuracy = {mean_acc:.4f} (+/- {scores.std():.4f})")

        if mean_acc > best_acc:
            best_acc = mean_acc
            best_params = params

    logger.info(f"Best CV accuracy: {best_acc:.4f}")
    logger.info(f"Best params: {best_params}")

    # --- Train final classifier with best params ---
    classifier = XGBClassifier(
        **best_params,
        scale_pos_weight=scale_weight,
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    classifier.fit(X_train, y_cls_train)

    # Evaluate on held-out test set
    y_cls_pred = classifier.predict(X_test)
    acc = accuracy_score(y_cls_test, y_cls_pred)
    prec = precision_score(y_cls_test, y_cls_pred, zero_division=0)
    rec = recall_score(y_cls_test, y_cls_pred, zero_division=0)
    f1 = f1_score(y_cls_test, y_cls_pred, zero_division=0)
    logger.info(f"Classifier — Accuracy: {acc:.3f}, Precision: {prec:.3f}, Recall: {rec:.3f}, F1: {f1:.3f}")

    # --- Train regressor ---
    reg_params = {k: v for k, v in best_params.items()}
    reg_params.pop("gamma", None)

    regressor = XGBRegressor(
        **reg_params,
        random_state=42,
    )
    regressor.fit(X_train, y_reg_train)

    y_reg_pred = regressor.predict(X_test)
    mae = mean_absolute_error(y_reg_test, y_reg_pred)
    logger.info(f"Regressor — MAE: {mae:.2f} minutes")

    # Feature importance
    importances = classifier.feature_importances_
    imp_df = pd.DataFrame({"feature": feature_cols, "importance": importances})
    imp_df = imp_df.sort_values("importance", ascending=False)
    logger.info("Feature importance:")
    for _, row in imp_df.iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.4f}")

    # Save
    model_data = {
        "classifier": classifier,
        "regressor": regressor,
        "feature_cols": feature_cols,
        "metrics": {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "mae": mae,
            "best_params": best_params,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "best_cv_accuracy": best_acc,
        },
    }

    joblib.dump(model_data, MODEL_OUTPUT)
    logger.info(f"Model saved to {MODEL_OUTPUT}")

    if acc >= 0.95:
        logger.info("TARGET MET: 95%+ accuracy on held-out test set!")
    else:
        logger.info(f"Accuracy {acc:.1%} — target is 95%")


if __name__ == "__main__":
    train()
