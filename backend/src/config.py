from __future__ import annotations

from datetime import datetime
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SRC_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
PREDICTIONS_DIR = DATA_DIR / "predictions"
CACHE_DIR = DATA_DIR / "cache"
RECENT_GAMES_CACHE_DIR = CACHE_DIR / "recent_games"
MODELS_DIR = BACKEND_DIR / "models"
CURRENT_MODELS_DIR = MODELS_DIR / "current"
ARCHIVED_MODELS_DIR = MODELS_DIR / "archived"
RESULTS_DIR = BACKEND_DIR / "results"

RAW_LOGS_PATH = RAW_DATA_DIR / "nba_logs.csv"
TRAINING_DATA_PATH = PROCESSED_DATA_DIR / "training_data.csv"
TODAYS_PROPS_PATH = PREDICTIONS_DIR / "todays_props.csv"
ANALYSIS_OUTPUT_PATH = PREDICTIONS_DIR / "analysis_results.csv"
TOP_BETS_OUTPUT_PATH = PREDICTIONS_DIR / "top_bets.csv"
SHARED_CONTEXT_PATH = CURRENT_MODELS_DIR / "shared_context.json"

TARGETS = ("PTS", "REB", "AST")
METADATA_COLUMNS = ("GAME_DATE", "PLAYER_ID", "PLAYER_NAME", "OPPONENT")
MODEL_OBJECTIVES = {
    "mean": {},
    "lower": {"objective": "reg:quantileerror", "quantile_alpha": 0.15},
    "upper": {"objective": "reg:quantileerror", "quantile_alpha": 0.85},
}

DEFAULT_MODEL_PARAMS = {
    "n_estimators": 500,
    "learning_rate": 0.03,
    "max_depth": 5,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
}


def ensure_directories() -> None:
    for path in (
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        PREDICTIONS_DIR,
        RECENT_GAMES_CACHE_DIR,
        CURRENT_MODELS_DIR,
        RESULTS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def model_artifact_path(target: str, variant: str = "mean") -> Path:
    suffix = "" if variant == "mean" else f"_{variant}"
    return CURRENT_MODELS_DIR / f"{target.lower()}_model{suffix}.json"


def model_metadata_path(target: str) -> Path:
    return CURRENT_MODELS_DIR / f"{target.lower()}_model.meta.json"


def archived_run_dir(timestamp: str | None = None) -> Path:
    value = timestamp or datetime.now().strftime("v%Y%m%d")
    return ARCHIVED_MODELS_DIR / value
