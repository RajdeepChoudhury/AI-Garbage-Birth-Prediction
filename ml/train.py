"""Training and model comparison pipeline.

Trains four tree based model families on two tasks and compares them:
  1. Regression: Garbage Volume Tomorrow  (MAE, RMSE, R2)
  2. Classification: Risk Level           (Precision, Recall, F1, macro averaged)

Evaluation uses a chronological split (last 20 percent of dates as test) so
the numbers reflect forecasting the future, not shuffled interpolation.

Outputs, written to ml/artifacts/:
  metrics.json         model comparison for the dashboard
  best_regressor.joblib, best_classifier.joblib
  feature_importance.json   SHAP global importance of the best regressor
  feature_columns.json      exact feature order the models expect

Usage:
    python train.py --data data/garbage_synthetic.csv
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from xgboost import XGBClassifier, XGBRegressor

from features import CLS_TARGET, REG_TARGET, RISK_ORDER, prepare_features

logger = logging.getLogger("train")



def chronological_split(df: pd.DataFrame, test_frac: float = 0.2) -> tuple[pd.Series, pd.Series]:
    cutoff = df["Date"].sort_values().iloc[int(len(df) * (1 - test_frac))]
    return df["Date"] < cutoff, df["Date"] >= cutoff


def regressors(seed: int) -> dict[str, object]:
    return {
        "Random Forest": RandomForestRegressor(n_estimators=200, min_samples_leaf=3, n_jobs=-1, random_state=seed),
        "XGBoost": XGBRegressor(n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.9,
                                colsample_bytree=0.9, n_jobs=-1, random_state=seed),
        "LightGBM": LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=48, subsample=0.9,
                                  colsample_bytree=0.9, random_state=seed, verbose=-1),
        "CatBoost": CatBoostRegressor(iterations=500, learning_rate=0.06, depth=6, random_seed=seed, verbose=0),
    }


def classifiers(seed: int) -> dict[str, object]:
    return {
        "Random Forest": RandomForestClassifier(n_estimators=200, min_samples_leaf=3, n_jobs=-1,
                                                class_weight="balanced", random_state=seed),
        "XGBoost": XGBClassifier(n_estimators=300, learning_rate=0.06, max_depth=6, subsample=0.9,
                                 colsample_bytree=0.9, n_jobs=-1, random_state=seed),
        "LightGBM": LGBMClassifier(n_estimators=300, learning_rate=0.06, num_leaves=48, class_weight="balanced",
                                   random_state=seed, verbose=-1),
        "CatBoost": CatBoostClassifier(iterations=400, learning_rate=0.08, depth=6, random_seed=seed, verbose=0,
                                       auto_class_weights="Balanced"),
    }


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "Precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "Recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "F1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "F1 High and Critical": float(
            f1_score(y_true >= 2, y_pred >= 2, zero_division=0)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--data", type=Path, default=Path("data/garbage_synthetic.csv"))
    parser.add_argument("--out", type=Path, default=Path("artifacts"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args.out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.data, parse_dates=["Date"])
    train_mask, test_mask = chronological_split(df)
    X = prepare_features(df)
    y_reg = df[REG_TARGET].to_numpy()
    y_cls = df[CLS_TARGET].map({r: i for i, r in enumerate(RISK_ORDER)}).to_numpy()
    logger.info("Train rows %d, test rows %d, features %d", train_mask.sum(), test_mask.sum(), X.shape[1])

    results: dict[str, dict] = {"regression": {}, "classification": {}}
    fitted_reg: dict[str, object] = {}
    fitted_cls: dict[str, object] = {}

    for name, model in regressors(args.seed).items():
        t0 = time.time()
        model.fit(X[train_mask], y_reg[train_mask])
        m = regression_metrics(y_reg[test_mask], model.predict(X[test_mask]))
        m["Train Seconds"] = round(time.time() - t0, 2)
        results["regression"][name] = m
        fitted_reg[name] = model
        logger.info("REG %-14s MAE %.3f RMSE %.3f R2 %.3f", name, m["MAE"], m["RMSE"], m["R2"])

    for name, model in classifiers(args.seed).items():
        t0 = time.time()
        model.fit(X[train_mask], y_cls[train_mask])
        pred = np.asarray(model.predict(X[test_mask])).ravel().astype(int)
        m = classification_metrics(y_cls[test_mask], pred)
        m["Train Seconds"] = round(time.time() - t0, 2)
        results["classification"][name] = m
        fitted_cls[name] = model
        logger.info("CLS %-14s P %.3f R %.3f F1 %.3f", name, m["Precision"], m["Recall"], m["F1"])

    best_reg = min(results["regression"], key=lambda k: results["regression"][k]["RMSE"])
    best_cls = max(results["classification"], key=lambda k: results["classification"][k]["F1"])
    results["best"] = {"regressor": best_reg, "classifier": best_cls}
    results["not_yet_evaluated"] = ["LSTM", "Temporal Fusion Transformer", "Graph Neural Network"]
    results["data_note"] = "Metrics come from synthetic data and will differ on real municipal data."

    joblib.dump(fitted_reg[best_reg], args.out / "best_regressor.joblib")
    joblib.dump(fitted_cls[best_cls], args.out / "best_classifier.joblib")
    (args.out / "feature_columns.json").write_text(json.dumps(list(X.columns), indent=2))

    # Global explainability: mean absolute SHAP value of the best regressor.
    sample = X[test_mask].sample(n=min(1500, int(test_mask.sum())), random_state=args.seed)
    shap_values = shap.TreeExplainer(fitted_reg[best_reg]).shap_values(sample)
    importance = pd.Series(np.abs(shap_values).mean(axis=0), index=X.columns).sort_values(ascending=False)
    results["feature_importance"] = {k: round(float(v), 5) for k, v in importance.items()}
    (args.out / "feature_importance.json").write_text(json.dumps(results["feature_importance"], indent=2))
    (args.out / "metrics.json").write_text(json.dumps(results, indent=2))

    logger.info("Best regressor: %s | Best classifier: %s", best_reg, best_cls)
    logger.info("Top SHAP features: %s", list(importance.index[:6]))


if __name__ == "__main__":
    main()
