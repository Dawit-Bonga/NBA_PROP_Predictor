from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import xgboost as xgb


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from artifacts import load_model_bundle, save_model_bundle
from feature_pipeline import build_prediction_row, build_season_list, build_training_dataset
from prediction_service import (
    _fallback_game_context_from_recent_games,
    _normalize_recent_games_frame,
    build_player_insights,
    fetch_recent_games_with_source,
)


def synthetic_raw_logs() -> pd.DataFrame:
    rows = []
    players = [
        ("Alpha Guard", "AAA", 0),
        ("Beta Wing", "BBB", 1),
        ("Gamma Big", "CCC", 2),
        ("Delta Guard", "DDD", 3),
    ]
    opponents = ["LAL", "BOS", "NYK", "MIA", "DAL", "DEN"]
    start = pd.Timestamp("2025-10-01")
    for game_idx in range(18):
        game_date = start + pd.Timedelta(days=game_idx * 2)
        for player_idx, (player_name, team_abbrev, player_id) in enumerate(players):
            opponent = opponents[(game_idx + player_idx) % len(opponents)]
            matchup = f"{team_abbrev} vs. {opponent}" if game_idx % 2 == 0 else f"{team_abbrev} @ {opponent}"
            rows.append(
                {
                    "PLAYER_NAME": player_name,
                    "PLAYER_ID": player_id + 1,
                    "GAME_DATE": game_date.strftime("%Y-%m-%d"),
                    "MATCHUP": matchup,
                    "PTS": 14 + player_idx * 3 + (game_idx % 9),
                    "REB": 4 + player_idx + (game_idx % 5),
                    "AST": 3 + player_idx + (game_idx % 4),
                    "MIN": 24 + player_idx * 2 + (game_idx % 6),
                    "FGA": 10 + player_idx * 2 + (game_idx % 7),
                    "FG3A": 3 + (player_idx % 3),
                    "BLK": player_idx % 2,
                    "FTA": 4 + (game_idx % 3),
                    "TOV": 2 + (game_idx % 2),
                    "WL": "W" if game_idx % 2 == 0 else "L",
                }
            )
    return pd.DataFrame(rows)


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_df = synthetic_raw_logs()
        cls.training_df, cls.context = build_training_dataset(cls.raw_df)

    def test_dynamic_season_list_includes_current_season(self):
        seasons = build_season_list(n_seasons=3, today=pd.Timestamp("2026-03-11").to_pydatetime())
        self.assertEqual(seasons[-1], "2025-26")
        self.assertEqual(len(seasons), 3)

    def test_training_dataset_contains_expected_contract(self):
        self.assertGreater(len(self.training_df), 0)
        self.assertIn("OPPONENT", self.training_df.columns)
        self.assertIn("EMA_10_PTS", self.training_df.columns)
        self.assertIn("OPP_DVP_AST", self.training_df.columns)
        self.assertIn("IS_HOME", self.context.feature_columns)
        self.assertIn("OPP_PACE", self.context.feature_columns)

    def test_prediction_row_matches_feature_schema(self):
        recent_games = self.raw_df[self.raw_df["PLAYER_NAME"] == "Alpha Guard"].tail(15).copy()
        prediction_df = build_prediction_row(
            recent_games_df=recent_games,
            opponent="LAL",
            is_home=1,
            rest_days=2,
            feature_context=self.context,
        )
        self.assertEqual(list(prediction_df.columns), self.context.feature_columns)
        self.assertFalse(prediction_df.isna().any().any())

    def test_recent_games_normalizer_sorts_and_limits_rows(self):
        recent_games = self.raw_df[self.raw_df["PLAYER_NAME"] == "Alpha Guard"].copy().iloc[::-1]
        normalized = _normalize_recent_games_frame(recent_games, "Alpha Guard", num_games=5)
        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(len(normalized), 5)
        self.assertEqual(normalized["PLAYER_NAME"].iloc[-1], "Alpha Guard")
        self.assertTrue(normalized["GAME_DATE"].is_monotonic_increasing)

    def test_fallback_context_uses_latest_matchup(self):
        recent_games = self.raw_df[self.raw_df["PLAYER_NAME"] == "Alpha Guard"].tail(5).copy()
        context = _fallback_game_context_from_recent_games(recent_games, game_date="2026-03-11")
        self.assertIn("opponent", context)
        self.assertIn("is_home", context)
        self.assertEqual(context["context_source"], "fallback_recent_game")

    def test_missing_player_returns_unavailable_source(self):
        recent_games, source = fetch_recent_games_with_source("No Such Player")
        self.assertIsNone(recent_games)
        self.assertEqual(source, "player_not_found")

    def test_player_insights_returns_summary_and_recent_games(self):
        from unittest.mock import patch

        recent_games = self.raw_df[self.raw_df["PLAYER_NAME"] == "Alpha Guard"].tail(12).copy()
        recent_games["GAME_DATE"] = pd.to_datetime(recent_games["GAME_DATE"])
        with patch("prediction_service.fetch_recent_games_with_source", return_value=(recent_games, "raw_logs")):
            insights = build_player_insights("Alpha Guard")
        self.assertEqual(insights["player"], "Alpha Guard")
        self.assertEqual(insights["data_source"], "raw_logs")
        self.assertIn("summary", insights)
        self.assertGreater(len(insights["recent_games"]), 0)

    def test_model_artifact_metadata_round_trip(self):
        feature_columns = self.context.feature_columns
        train_df = self.training_df.copy()
        X = train_df[feature_columns]
        y = train_df["PTS"]
        models = {}
        for variant in ("mean", "lower", "upper"):
            params = {
                "n_estimators": 5,
                "max_depth": 2,
                "learning_rate": 0.2,
                "random_state": 42,
                "n_jobs": 1,
            }
            if variant == "lower":
                params.update({"objective": "reg:quantileerror", "quantile_alpha": 0.15})
            elif variant == "upper":
                params.update({"objective": "reg:quantileerror", "quantile_alpha": 0.85})
            model = xgb.XGBRegressor(**params)
            model.fit(X, y, verbose=False)
            models[variant] = model

        with tempfile.TemporaryDirectory() as tmpdir:
            save_model_bundle(
                target="PTS",
                models=models,
                feature_columns=feature_columns,
                metrics={"holdout": {"mae": 1.0}},
                base_dir=Path(tmpdir),
            )
            loaded_models, metadata = load_model_bundle("PTS", base_dir=Path(tmpdir))

        self.assertEqual(metadata["feature_columns"], feature_columns)
        self.assertEqual(set(loaded_models.keys()), {"mean", "lower", "upper"})


if __name__ == "__main__":
    unittest.main()
