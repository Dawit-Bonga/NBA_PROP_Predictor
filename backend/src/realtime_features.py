from __future__ import annotations

import pandas as pd

from pipeline import generate_predictions
from prediction_service import fetch_recent_games, infer_live_game_context, predict_single_player


def get_realtime_prediction_features(
    player_name: str,
    opponent: str | None = None,
    is_home: int | None = None,
    rest_days: int | None = None,
    season: str | None = None,
):
    recent_games = fetch_recent_games(player_name, season=season)
    if recent_games is None:
        return None, None
    if opponent is None or is_home is None or rest_days is None:
        inferred = infer_live_game_context(player_name, recent_games)
        opponent = opponent or inferred["opponent"]
        is_home = is_home if is_home is not None else inferred["is_home"]
        rest_days = rest_days if rest_days is not None else inferred["rest_days"]
    prediction_payload = predict_single_player(
        player_name=player_name,
        opponent=opponent,
        is_home=is_home,
        rest_days=rest_days,
        season=season,
    )
    return prediction_payload, recent_games


def run_realtime_prediction() -> bool:
    results_df = generate_predictions()
    return not results_df.empty


if __name__ == "__main__":
    success = run_realtime_prediction()
    print("Generated predictions." if success else "No predictions generated.")
