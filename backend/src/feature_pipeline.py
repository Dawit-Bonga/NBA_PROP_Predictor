from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from config import METADATA_COLUMNS, TARGETS


ROLLING_METRICS = ("PTS", "REB", "AST", "MIN", "FGA", "FTA", "USAGE")
EMA_SPANS = (3, 5, 10)
STD_WINDOWS = (5, 10)
PER_MIN_METRICS = ("PTS", "REB", "AST")
CONTEXT_FEATURES = (
    "IS_HOME",
    "REST_DAYS",
    "IS_B2B",
    "DAYS_SINCE_3_GAMES",
    "OPP_PACE",
    "ARCHETYPE",
)
TARGET_COLUMNS = TARGETS


@dataclass(frozen=True)
class FeatureContext:
    generated_at: str
    feature_columns: list[str]
    defaults: dict[str, float]
    opponent_pace: dict[str, float]
    opponent_dvp: dict[str, dict[str, dict[str, float]]]
    player_archetypes: dict[str, int]


def get_current_season(today: datetime | None = None) -> str:
    current = today or datetime.now()
    if current.month >= 10:
        start_year = current.year
    else:
        start_year = current.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def build_season_list(n_seasons: int = 3, today: datetime | None = None) -> list[str]:
    current = get_current_season(today)
    start_year = int(current[:4])
    return [f"{year}-{str(year + 1)[-2:]}" for year in range(start_year - n_seasons + 1, start_year + 1)]


def get_opponent_info(matchup: str) -> tuple[str, int]:
    if "vs." in matchup:
        return matchup.split(" vs. ")[1], 1
    if " @ " in matchup:
        return matchup.split(" @ ")[1], 0
    return "UNK", 0


def _coerce_minutes(series: pd.Series) -> pd.Series:
    if np.issubdtype(series.dtype, np.number):
        return pd.to_numeric(series, errors="coerce")
    as_str = series.astype(str)
    if as_str.str.contains(":").any():
        parts = as_str.str.split(":", expand=True)
        minutes = pd.to_numeric(parts[0], errors="coerce").fillna(0)
        seconds = pd.to_numeric(parts[1], errors="coerce").fillna(0)
        return minutes + (seconds / 60.0)
    return pd.to_numeric(as_str, errors="coerce")


def create_player_archetypes(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    stats = (
        df.groupby("PLAYER_NAME")
        .agg(
            {
                "AST": "mean",
                "REB": "mean",
                "FGA": "mean",
                "FG3A": "mean",
                "BLK": "mean",
                "MIN": "mean",
            }
        )
        .reset_index()
    )
    stats_filtered = stats[stats["MIN"] > 10].copy()
    if stats_filtered.empty:
        return df.assign(ARCHETYPE=-1), {}

    X = stats_filtered[["AST", "REB", "FG3A", "BLK"]]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    stats_filtered["ARCHETYPE"] = kmeans.fit_predict(X_scaled)

    archetype_map = dict(zip(stats_filtered["PLAYER_NAME"], stats_filtered["ARCHETYPE"]))
    merged = df.merge(stats_filtered[["PLAYER_NAME", "ARCHETYPE"]], on="PLAYER_NAME", how="left")
    return merged.fillna({"ARCHETYPE": -1}), {player: int(value) for player, value in archetype_map.items()}


def _last_ema(values: Iterable[float], span: int) -> float:
    series = pd.Series(list(values), dtype=float)
    if series.empty:
        return np.nan
    return float(series.ewm(span=span, adjust=False).mean().iloc[-1])


def _last_std(values: Iterable[float], window: int) -> float:
    series = pd.Series(list(values), dtype=float)
    if series.empty:
        return np.nan
    tail = series.tail(window)
    return float(tail.std()) if len(tail) > 1 else 0.0


def _days_since_recent_games(dates: pd.Series, n_games: int = 3) -> float:
    if len(dates) < n_games:
        return np.nan
    relevant = pd.to_datetime(dates.tail(n_games))
    return float((relevant.iloc[-1] - relevant.iloc[0]).days)


def _apply_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    player_group = df.groupby("PLAYER_NAME", sort=False)
    for metric in ROLLING_METRICS:
        source = "USAGE_RAW" if metric == "USAGE" else metric
        for span in EMA_SPANS:
            df[f"EMA_{span}_{metric}"] = player_group[source].transform(
                lambda values: values.shift(1).ewm(span=span, adjust=False).mean()
            )
        for window in STD_WINDOWS:
            df[f"STD_{window}_{metric}"] = player_group[source].transform(
                lambda values: values.shift(1).rolling(window, min_periods=2).std()
            )

    for metric in ("PTS", "REB", "AST"):
        df[f"TREND_{metric}"] = df[f"EMA_3_{metric}"] - df[f"EMA_10_{metric}"]
        df[f"LAST_{metric}"] = player_group[metric].shift(1)

    df["LAST_MIN"] = player_group["MIN"].shift(1)
    df["DAYS_SINCE_3_GAMES"] = (
        player_group["GAME_DATE"].shift(1) - player_group["GAME_DATE"].shift(3)
    ).dt.days
    return df


def build_training_dataset(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, FeatureContext]:
    df = raw_df.copy()
    if "PLAYER_ID" not in df.columns:
        df["PLAYER_ID"] = pd.factorize(df["PLAYER_NAME"])[0] + 1
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df["MIN"] = _coerce_minutes(df["MIN"])
    df = df.sort_values(["PLAYER_NAME", "GAME_DATE"]).reset_index(drop=True)
    df[["OPPONENT", "IS_HOME"]] = df["MATCHUP"].apply(lambda value: pd.Series(get_opponent_info(value)))
    df["USAGE_RAW"] = df["FGA"] + 0.44 * df["FTA"] + df["TOV"]
    df, player_archetypes = create_player_archetypes(df)

    df = _apply_rolling_features(df)

    player_group = df.groupby("PLAYER_NAME", sort=False)
    df["REST_DAYS"] = player_group["GAME_DATE"].diff().dt.days.fillna(3).clip(0, 7)
    df["IS_B2B"] = (df["REST_DAYS"] <= 1).astype(int)

    for metric in PER_MIN_METRICS:
        df[f"{metric}_PER_MIN"] = df[f"EMA_10_{metric}"] / (df["EMA_10_MIN"] + 0.1)

    df["MIN_TREND"] = df["EMA_3_MIN"] - df["EMA_10_MIN"]
    df["USAGE_TREND"] = df["EMA_3_USAGE"] - df["EMA_10_USAGE"]

    df = df.sort_values(["OPPONENT", "GAME_DATE", "PLAYER_NAME"]).reset_index(drop=True)
    opp_archetype_group = df.groupby(["OPPONENT", "ARCHETYPE"], sort=False)
    for stat in TARGETS:
        df[f"OPP_DVP_{stat}"] = opp_archetype_group[stat].transform(
            lambda values: values.shift(1).rolling(window=30, min_periods=5).mean()
        )

    df["OPP_PACE"] = df.groupby("OPPONENT", sort=False)["FGA"].transform(
        lambda values: values.shift(1).rolling(20, min_periods=5).mean()
    )

    df = df.sort_values(["GAME_DATE", "PLAYER_NAME"]).reset_index(drop=True)

    feature_columns = list(METADATA_COLUMNS) + list(TARGET_COLUMNS) + [
        "IS_HOME",
        "REST_DAYS",
        "IS_B2B",
        "DAYS_SINCE_3_GAMES",
        "ARCHETYPE",
        "OPP_PACE",
        "PTS_PER_MIN",
        "REB_PER_MIN",
        "AST_PER_MIN",
        "MIN_TREND",
        "USAGE_TREND",
    ]
    generated_columns = [
        column
        for column in df.columns
        if column.startswith(("EMA_", "STD_", "TREND_", "LAST_", "OPP_DVP_"))
    ]
    feature_columns.extend(generated_columns)

    final_df = df[feature_columns].copy()
    final_df = final_df.dropna(
        subset=[
            "EMA_10_PTS",
            "EMA_10_REB",
            "EMA_10_AST",
            "EMA_10_MIN",
            "OPP_DVP_PTS",
            "OPP_DVP_REB",
            "OPP_DVP_AST",
            "ARCHETYPE",
        ]
    )
    final_df = final_df[final_df["ARCHETYPE"] != -1].reset_index(drop=True)

    model_feature_columns = [
        column for column in final_df.columns if column not in set(METADATA_COLUMNS + TARGET_COLUMNS)
    ]
    defaults = {
        column: float(final_df[column].median())
        for column in model_feature_columns
    }

    opponent_pace = (
        final_df.groupby("OPPONENT")["OPP_PACE"].median().dropna().round(6).to_dict()
    )
    opponent_dvp: dict[str, dict[str, dict[str, float]]] = {}
    for (opponent, archetype), group in final_df.groupby(["OPPONENT", "ARCHETYPE"]):
        opponent_dvp.setdefault(opponent, {})[str(int(archetype))] = {
            stat: float(group[f"OPP_DVP_{stat}"].median())
            for stat in TARGETS
        }

    context = FeatureContext(
        generated_at=datetime.now().isoformat(),
        feature_columns=model_feature_columns,
        defaults=defaults,
        opponent_pace={key: float(value) for key, value in opponent_pace.items()},
        opponent_dvp=opponent_dvp,
        player_archetypes=player_archetypes,
    )
    return final_df, context


def build_prediction_row(
    recent_games_df: pd.DataFrame,
    opponent: str,
    is_home: int,
    rest_days: int,
    feature_context: FeatureContext,
) -> pd.DataFrame:
    if recent_games_df is None or len(recent_games_df) < 5:
        raise ValueError("At least five recent games are required to build prediction features.")

    df = recent_games_df.copy()
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df["MIN"] = _coerce_minutes(df["MIN"])
    df = df.sort_values("GAME_DATE").reset_index(drop=True)
    df["USAGE_RAW"] = df["FGA"] + 0.44 * df["FTA"] + df["TOV"]

    player_name = str(df.iloc[-1]["PLAYER_NAME"])
    archetype = feature_context.player_archetypes.get(player_name, -1)
    row: dict[str, float] = {}

    for metric in ROLLING_METRICS:
        source = "USAGE_RAW" if metric == "USAGE" else metric
        values = df[source].astype(float)
        for span in EMA_SPANS:
            row[f"EMA_{span}_{metric}"] = _last_ema(values, span)
        for window in STD_WINDOWS:
            row[f"STD_{window}_{metric}"] = _last_std(values, window)

    for metric in ("PTS", "REB", "AST"):
        row[f"TREND_{metric}"] = row[f"EMA_3_{metric}"] - row[f"EMA_10_{metric}"]
        row[f"LAST_{metric}"] = float(df[metric].iloc[-1])

    row["LAST_MIN"] = float(df["MIN"].iloc[-1])
    row["IS_HOME"] = float(is_home)
    row["REST_DAYS"] = float(max(0, min(rest_days, 7)))
    row["IS_B2B"] = float(1 if rest_days <= 1 else 0)
    row["DAYS_SINCE_3_GAMES"] = _days_since_recent_games(df["GAME_DATE"])
    row["ARCHETYPE"] = float(archetype)
    row["PTS_PER_MIN"] = row["EMA_10_PTS"] / (row["EMA_10_MIN"] + 0.1)
    row["REB_PER_MIN"] = row["EMA_10_REB"] / (row["EMA_10_MIN"] + 0.1)
    row["AST_PER_MIN"] = row["EMA_10_AST"] / (row["EMA_10_MIN"] + 0.1)
    row["MIN_TREND"] = row["EMA_3_MIN"] - row["EMA_10_MIN"]
    row["USAGE_TREND"] = row["EMA_3_USAGE"] - row["EMA_10_USAGE"]
    row["OPP_PACE"] = feature_context.opponent_pace.get(opponent, feature_context.defaults["OPP_PACE"])

    archetype_key = str(int(archetype))
    dvp_defaults = feature_context.opponent_dvp.get(opponent, {}).get(archetype_key, {})
    for stat in TARGETS:
        key = f"OPP_DVP_{stat}"
        row[key] = dvp_defaults.get(stat, feature_context.defaults[key])

    prediction_df = pd.DataFrame([row])
    for column in feature_context.feature_columns:
        if column not in prediction_df.columns:
            prediction_df[column] = feature_context.defaults[column]
    prediction_df = prediction_df[feature_context.feature_columns]
    return prediction_df.fillna(feature_context.defaults)
