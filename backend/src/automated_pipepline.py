from __future__ import annotations

import argparse
from datetime import datetime

from config import ANALYSIS_OUTPUT_PATH, TARGETS, TOP_BETS_OUTPUT_PATH, model_metadata_path
from pipeline import generate_predictions, rank_bets
from train import train_all_models


MODEL_MAX_AGE_DAYS = 7


def check_model_freshness() -> bool:
    now = datetime.now().timestamp()
    for target in TARGETS:
        metadata_path = model_metadata_path(target)
        if not metadata_path.exists():
            return False
        age_days = (now - metadata_path.stat().st_mtime) / 86400
        if age_days > MODEL_MAX_AGE_DAYS:
            return False
    return True


def run_full_pipeline(force_retrain: bool = False, min_edge: float = 2.0) -> bool:
    if force_retrain or not check_model_freshness():
        train_all_models()

    predictions_df = generate_predictions()
    ranked_df = rank_bets(predictions_df, min_edge=min_edge)
    print(f"Saved predictions to {ANALYSIS_OUTPUT_PATH}")
    print(f"Saved ranked bets to {TOP_BETS_OUTPUT_PATH}")
    print(f"Generated {len(predictions_df)} predictions and ranked {len(ranked_df)} bets.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local NBA prop prediction pipeline")
    parser.add_argument("--force-retrain", action="store_true")
    parser.add_argument("--min-edge", type=float, default=2.0)
    args = parser.parse_args()
    run_full_pipeline(force_retrain=args.force_retrain, min_edge=args.min_edge)
