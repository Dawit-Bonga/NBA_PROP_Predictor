from __future__ import annotations

import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from artifacts import archive_current_models, save_model_bundle, save_shared_context
from config import (
    CURRENT_MODELS_DIR,
    DEFAULT_MODEL_PARAMS,
    MODEL_OBJECTIVES,
    RAW_LOGS_PATH,
    RESULTS_DIR,
    TARGETS,
    TRAINING_DATA_PATH,
    ensure_directories,
)
from feature_pipeline import build_training_dataset


def walk_forward_scores(df: pd.DataFrame, feature_columns: list[str], target: str) -> list[dict]:
    tscv = TimeSeriesSplit(n_splits=4)
    scores = []
    X = df[feature_columns]
    y = df[target]
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), start=1):
        model = xgb.XGBRegressor(**DEFAULT_MODEL_PARAMS)
        model.fit(X.iloc[train_idx], y.iloc[train_idx], verbose=False)
        preds = model.predict(X.iloc[test_idx])
        scores.append(
            {
                "fold": fold,
                "mae": float(mean_absolute_error(y.iloc[test_idx], preds)),
                "rmse": float(np.sqrt(mean_squared_error(y.iloc[test_idx], preds))),
                "rows": int(len(test_idx)),
            }
        )
    return scores


def evaluate_models(
    df: pd.DataFrame,
    feature_columns: list[str],
    target: str,
    models: dict[str, xgb.XGBRegressor],
) -> dict:
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    X_test = test_df[feature_columns]
    y_test = test_df[target]

    mean_preds = models["mean"].predict(X_test)
    lower_preds = models["lower"].predict(X_test)
    upper_preds = models["upper"].predict(X_test)

    player_counts = train_df.groupby("PLAYER_NAME").size()
    player_volume = test_df["PLAYER_NAME"].map(player_counts).fillna(0)
    tier_labels = pd.cut(
        player_volume,
        bins=[-1, 24, 59, 10_000],
        labels=["low_sample", "mid_sample", "high_sample"],
    )
    error_by_tier = {}
    for label in ["low_sample", "mid_sample", "high_sample"]:
        mask = tier_labels == label
        if mask.any():
            error_by_tier[label] = float(mean_absolute_error(y_test[mask], mean_preds[mask]))

    coverage = float(((y_test >= lower_preds) & (y_test <= upper_preds)).mean())
    interval_width = float(np.mean(upper_preds - lower_preds))
    baseline = X_test[f"EMA_10_{target}"]
    baseline_mae = float(mean_absolute_error(y_test, baseline))

    return {
        "holdout": {
            "rows": int(len(test_df)),
            "mae": float(mean_absolute_error(y_test, mean_preds)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, mean_preds))),
            "baseline_mae": baseline_mae,
            "interval_coverage": coverage,
            "mean_interval_width": interval_width,
        },
        "walk_forward": walk_forward_scores(df, feature_columns, target),
        "error_by_player_sample_tier": error_by_tier,
        "baseline_label": f"EMA_10_{target} rolling baseline",
    }


def train_models(df: pd.DataFrame, feature_columns: list[str], target: str) -> dict[str, xgb.XGBRegressor]:
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    X_train = train_df[feature_columns]
    y_train = train_df[target]
    X_test = test_df[feature_columns]
    y_test = test_df[target]

    models = {}
    for variant, overrides in MODEL_OBJECTIVES.items():
        params = dict(DEFAULT_MODEL_PARAMS)
        params.update(overrides)
        if variant == "mean":
            params["early_stopping_rounds"] = 30
        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        models[variant] = model
    return models


def train_all_models() -> tuple[dict, dict]:
    ensure_directories()
    if not RAW_LOGS_PATH.exists():
        raise FileNotFoundError(f"Raw data not found at {RAW_LOGS_PATH}")

    raw_df = pd.read_csv(RAW_LOGS_PATH)
    training_df, feature_context = build_training_dataset(raw_df)
    training_df.to_csv(TRAINING_DATA_PATH, index=False)

    if any(path.exists() for path in CURRENT_MODELS_DIR.glob("*.json")):
        archive_current_models()

    save_shared_context(feature_context)
    feature_columns = feature_context.feature_columns

    trained_models = {}
    all_metrics = {}
    for target in TARGETS:
        models = train_models(training_df, feature_columns, target)
        metrics = evaluate_models(training_df, feature_columns, target, models)
        save_model_bundle(target, models, feature_columns, metrics)
        (RESULTS_DIR / f"{target.lower()}_results.json").write_text(json.dumps(metrics, indent=2))
        trained_models[target] = models
        all_metrics[target] = metrics

    return trained_models, all_metrics


def run_pipeline() -> None:
    _, metrics = train_all_models()
    for target, result in metrics.items():
        holdout = result["holdout"]
        print(
            f"{target}: MAE={holdout['mae']:.3f} RMSE={holdout['rmse']:.3f} "
            f"Coverage={holdout['interval_coverage']:.3f}"
        )


if __name__ == "__main__":
    run_pipeline()
