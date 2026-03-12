from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

from config import ANALYSIS_OUTPUT_PATH, TARGETS, TODAYS_PROPS_PATH, TOP_BETS_OUTPUT_PATH
from prediction_service import predict_single_player


def generate_predictions(props_path=TODAYS_PROPS_PATH, output_path=ANALYSIS_OUTPUT_PATH) -> pd.DataFrame:
    props_df = pd.read_csv(props_path)
    results = []
    for _, row in props_df.iterrows():
        player = row["player"]
        target = row["stat_mapped"]
        try:
            payload = predict_single_player(player)
            bundle = payload[target]
            prediction = bundle["mean"]
            results.append(
                {
                    "player": player,
                    "stat": row["stat"],
                    "stat_mapped": target,
                    "line": float(row["line"]),
                    "prediction": prediction,
                    "lower": bundle["lower"],
                    "upper": bundle["upper"],
                    "opponent": payload["opponent"],
                    "is_home": payload["is_home"],
                    "rest_days": payload["rest_days"],
                    "last_game_date": payload["last_game_date"],
                    "data_source": payload.get("data_source", ""),
                    "context_source": payload.get("context_source", ""),
                    "edge": prediction - float(row["line"]),
                    "generated_at": datetime.now().isoformat(),
                    "error": "",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "player": player,
                    "stat": row["stat"],
                    "stat_mapped": target,
                    "line": float(row["line"]),
                    "prediction": None,
                    "lower": None,
                    "upper": None,
                    "opponent": None,
                    "is_home": None,
                    "rest_days": None,
                    "last_game_date": None,
                    "data_source": None,
                    "context_source": None,
                    "edge": None,
                    "generated_at": datetime.now().isoformat(),
                    "error": str(exc),
                }
            )
    results_df = pd.DataFrame(results)
    if "edge" in results_df.columns:
        results_df = results_df.sort_values("edge", ascending=False, na_position="last")
    results_df.to_csv(output_path, index=False)
    return results_df


def rank_bets(predictions_df: pd.DataFrame, min_edge: float = 2.0) -> pd.DataFrame:
    df = predictions_df.dropna(subset=["prediction", "edge"]).copy()
    df["abs_edge"] = df["edge"].abs()
    df["recommendation"] = df["edge"].apply(lambda value: "OVER" if value > 0 else "UNDER")
    df["confidence"] = df["abs_edge"].apply(
        lambda value: "High" if value >= 5 else ("Medium" if value >= 3 else "Low")
    )
    top_bets = df[df["abs_edge"] >= min_edge].sort_values("abs_edge", ascending=False)
    top_bets.to_csv(TOP_BETS_OUTPUT_PATH, index=False)
    return top_bets


def main() -> None:
    parser = argparse.ArgumentParser(description="NBA Prop Predictor local pipeline")
    parser.add_argument("--props-path", default=str(TODAYS_PROPS_PATH))
    parser.add_argument("--min-edge", type=float, default=2.0)
    args = parser.parse_args()

    predictions_df = generate_predictions(props_path=args.props_path)
    ranked_df = rank_bets(predictions_df, min_edge=args.min_edge)
    print(f"Generated {len(predictions_df)} predictions.")
    print(f"Ranked {len(ranked_df)} bets with abs edge >= {args.min_edge}.")


if __name__ == "__main__":
    main()
