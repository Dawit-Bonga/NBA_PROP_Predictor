from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import xgboost as xgb

from config import (
    CURRENT_MODELS_DIR,
    SHARED_CONTEXT_PATH,
    archived_run_dir,
    ensure_directories,
)
from feature_pipeline import FeatureContext


def _artifact_path(base_dir: Path, target: str, variant: str) -> Path:
    suffix = "" if variant == "mean" else f"_{variant}"
    return base_dir / f"{target.lower()}_model{suffix}.json"


def _metadata_path(base_dir: Path, target: str) -> Path:
    return base_dir / f"{target.lower()}_model.meta.json"


def save_shared_context(feature_context: FeatureContext, path: Path = SHARED_CONTEXT_PATH) -> None:
    ensure_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(feature_context), indent=2))


def load_shared_context(path: Path = SHARED_CONTEXT_PATH) -> FeatureContext:
    payload = json.loads(path.read_text())
    return FeatureContext(**payload)


def save_model_bundle(
    target: str,
    models: dict[str, xgb.XGBRegressor],
    feature_columns: list[str],
    metrics: dict,
    base_dir: Path = CURRENT_MODELS_DIR,
) -> None:
    ensure_directories()
    base_dir.mkdir(parents=True, exist_ok=True)
    for variant, model in models.items():
        model.get_booster().save_model(_artifact_path(base_dir, target, variant))

    metadata = {
        "target": target,
        "feature_columns": feature_columns,
        "generated_at": datetime.now().isoformat(),
        "artifacts": {variant: _artifact_path(base_dir, target, variant).name for variant in models},
        "metrics": metrics,
    }
    _metadata_path(base_dir, target).write_text(json.dumps(metadata, indent=2))


def load_model_bundle(target: str, base_dir: Path = CURRENT_MODELS_DIR) -> tuple[dict[str, xgb.XGBRegressor], dict]:
    metadata = json.loads(_metadata_path(base_dir, target).read_text())
    models: dict[str, xgb.XGBRegressor] = {}
    for variant, filename in metadata["artifacts"].items():
        model = xgb.XGBRegressor()
        model.load_model(str(base_dir / filename))
        models[variant] = model
    return models, metadata


def archive_current_models() -> Path:
    run_dir = archived_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    for path in CURRENT_MODELS_DIR.glob("*"):
        if path.is_file():
            target_path = run_dir / path.name
            target_path.write_bytes(path.read_bytes())
    return run_dir
