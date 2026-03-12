from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

from artifacts import load_model_bundle, load_shared_context
from config import RAW_LOGS_PATH, RECENT_GAMES_CACHE_DIR, TARGETS, ensure_directories
from feature_pipeline import build_prediction_row, get_current_season
from schedule_context import infer_matchup_for_team


PLAYER_CACHE = {player["full_name"].lower(): player["id"] for player in players.get_players()}


def _cache_key(player_name: str, season: str) -> Path:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in player_name).strip("_")
    return RECENT_GAMES_CACHE_DIR / f"{slug}_{season}.csv"


def _normalize_recent_games_frame(df: pd.DataFrame, player_name: str, num_games: int) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    normalized = df.copy()
    normalized["GAME_DATE"] = pd.to_datetime(normalized["GAME_DATE"], errors="coerce")
    normalized = normalized.dropna(subset=["GAME_DATE"])
    if "WL" in normalized.columns:
        normalized = normalized[normalized["WL"].notna()]
    normalized = normalized.sort_values("GAME_DATE").tail(num_games).reset_index(drop=True)
    normalized["PLAYER_NAME"] = player_name
    return normalized if not normalized.empty else None


def _save_recent_games_cache(player_name: str, season: str, df: pd.DataFrame) -> None:
    ensure_directories()
    cache_path = _cache_key(player_name, season)
    df.to_csv(cache_path, index=False)


def _load_recent_games_cache(player_name: str, season: str, num_games: int) -> pd.DataFrame | None:
    cache_path = _cache_key(player_name, season)
    if not cache_path.exists():
        return None
    cached = pd.read_csv(cache_path)
    return _normalize_recent_games_frame(cached, player_name, num_games)


def _load_recent_games_from_raw_logs(player_name: str, season: str, num_games: int) -> pd.DataFrame | None:
    if not RAW_LOGS_PATH.exists():
        return None
    raw_df = pd.read_csv(RAW_LOGS_PATH)
    player_rows = raw_df[raw_df["PLAYER_NAME"].str.lower() == player_name.lower()].copy()
    if "SEASON_ID" in player_rows.columns:
        season_rows = player_rows[player_rows["SEASON_ID"] == season].copy()
        if not season_rows.empty:
            player_rows = season_rows
    return _normalize_recent_games_frame(player_rows, player_name, num_games)


def fetch_recent_games_with_source(
    player_name: str,
    season: str | None = None,
    num_games: int = 20,
) -> tuple[pd.DataFrame | None, str]:
    player_id = find_player_id(player_name)
    if not player_id:
        return None, "player_not_found"

    active_season = season or get_current_season()
    try:
        gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=active_season, timeout=30)
        df = gamelog.get_data_frames()[0]
        normalized = _normalize_recent_games_frame(df, player_name, num_games)
        if normalized is not None:
            _save_recent_games_cache(player_name, active_season, normalized)
            return normalized, "live_api"
    except Exception:
        pass

    cached = _load_recent_games_cache(player_name, active_season, num_games)
    if cached is not None:
        return cached, "cache"

    raw_logs = _load_recent_games_from_raw_logs(player_name, active_season, num_games)
    if raw_logs is not None:
        return raw_logs, "raw_logs"

    return None, "unavailable"


def find_player_id(player_name: str) -> int | None:
    direct = PLAYER_CACHE.get(player_name.lower())
    if direct:
        return direct
    for full_name, player_id in PLAYER_CACHE.items():
        if player_name.lower() in full_name:
            return player_id
    return None


def _fallback_game_context_from_recent_games(
    recent_games_df: pd.DataFrame,
    game_date: str | None = None,
) -> dict[str, Any]:
    recent_games_df = recent_games_df.copy()
    recent_games_df["GAME_DATE"] = pd.to_datetime(recent_games_df["GAME_DATE"], errors="coerce")
    latest_matchup = str(recent_games_df.iloc[-1]["MATCHUP"])
    if "vs." in latest_matchup:
        opponent = latest_matchup.split(" vs. ")[1]
        is_home = 1
    elif " @ " in latest_matchup:
        opponent = latest_matchup.split(" @ ")[1]
        is_home = 0
    else:
        opponent = "UNK"
        is_home = 0

    game_day = pd.Timestamp(game_date or datetime.now().strftime("%Y-%m-%d"))
    rest_days = int((game_day.normalize() - recent_games_df.iloc[-1]["GAME_DATE"].normalize()).days)
    return {
        "opponent": opponent,
        "is_home": is_home,
        "rest_days": max(rest_days, 0),
        "context_source": "fallback_recent_game",
    }


def fetch_recent_games(player_name: str, season: str | None = None, num_games: int = 20) -> pd.DataFrame | None:
    recent_games, _ = fetch_recent_games_with_source(player_name, season=season, num_games=num_games)
    return recent_games


def infer_live_game_context(player_name: str, recent_games_df: pd.DataFrame, game_date: str | None = None) -> dict[str, Any]:
    if recent_games_df is None or recent_games_df.empty:
        raise ValueError(f"No recent games found for {player_name}.")

    latest_matchup = str(recent_games_df.iloc[-1]["MATCHUP"])
    if "vs." in latest_matchup:
        team_abbrev = latest_matchup.split(" vs. ")[0]
    elif " @ " in latest_matchup:
        team_abbrev = latest_matchup.split(" @ ")[0]
    else:
        raise ValueError(f"Could not infer team abbreviation from matchup for {player_name}.")

    matchup = infer_matchup_for_team(team_abbrev, game_date=game_date)
    if matchup is None:
        return _fallback_game_context_from_recent_games(recent_games_df, game_date=game_date)

    game_day = pd.Timestamp(game_date or datetime.now().strftime("%Y-%m-%d"))
    rest_days = int((game_day.normalize() - recent_games_df.iloc[-1]["GAME_DATE"].normalize()).days)
    matchup["rest_days"] = max(rest_days, 0)
    matchup["context_source"] = "live_schedule"
    return matchup


def validate_prediction_frame(features_df: pd.DataFrame, feature_columns: list[str]) -> None:
    missing = [column for column in feature_columns if column not in features_df.columns]
    extra = [column for column in features_df.columns if column not in feature_columns]
    if missing or extra:
        raise ValueError(
            f"Prediction feature mismatch. Missing={missing or '[]'} Extra={extra or '[]'}"
        )


def build_player_insights(
    player_name: str,
    opponent: str | None = None,
    is_home: int | None = None,
    rest_days: int | None = None,
    season: str | None = None,
    game_date: str | None = None,
) -> dict[str, Any]:
    recent_games, data_source = fetch_recent_games_with_source(player_name, season=season)
    if recent_games is None:
        raise ValueError(f"Could not load recent games for {player_name}.")

    context_source = "manual_input"
    if opponent is None or is_home is None or rest_days is None:
        inferred = infer_live_game_context(player_name, recent_games, game_date=game_date)
        opponent = opponent or inferred["opponent"]
        is_home = is_home if is_home is not None else inferred["is_home"]
        rest_days = rest_days if rest_days is not None else inferred["rest_days"]
        context_source = inferred.get("context_source", "live_schedule")

    display_games = recent_games.sort_values("GAME_DATE", ascending=False).head(10).copy()
    display_games["GAME_DATE"] = display_games["GAME_DATE"].dt.strftime("%Y-%m-%d")

    last5 = recent_games.tail(5)
    last10 = recent_games.tail(10)
    summary = {
        "last5_pts": float(last5["PTS"].mean()),
        "last5_reb": float(last5["REB"].mean()),
        "last5_ast": float(last5["AST"].mean()),
        "last10_pts": float(last10["PTS"].mean()),
        "last10_reb": float(last10["REB"].mean()),
        "last10_ast": float(last10["AST"].mean()),
        "season_pts": float(recent_games["PTS"].mean()),
        "season_reb": float(recent_games["REB"].mean()),
        "season_ast": float(recent_games["AST"].mean()),
        "last_game_pts": float(recent_games.iloc[-1]["PTS"]),
        "last_game_reb": float(recent_games.iloc[-1]["REB"]),
        "last_game_ast": float(recent_games.iloc[-1]["AST"]),
        "last_game_min": float(pd.to_numeric(recent_games.iloc[-1]["MIN"], errors="coerce")),
    }

    return {
        "player": player_name,
        "opponent": opponent,
        "is_home": int(is_home),
        "rest_days": int(rest_days),
        "last_game_date": recent_games.iloc[-1]["GAME_DATE"].strftime("%Y-%m-%d"),
        "data_source": data_source,
        "context_source": context_source,
        "summary": summary,
        "recent_games": display_games[
            ["GAME_DATE", "MATCHUP", "WL", "MIN", "PTS", "REB", "AST", "FGA", "FTA", "TOV"]
        ].to_dict(orient="records"),
    }


def predict_single_player(
    player_name: str,
    opponent: str | None = None,
    is_home: int | None = None,
    rest_days: int | None = None,
    season: str | None = None,
    game_date: str | None = None,
) -> dict[str, Any]:
    feature_context = load_shared_context()
    recent_games, data_source = fetch_recent_games_with_source(player_name, season=season)
    if recent_games is None:
        raise ValueError(f"Could not load recent games for {player_name}.")

    context_source = "manual_input"
    if opponent is None or is_home is None or rest_days is None:
        inferred = infer_live_game_context(player_name, recent_games, game_date=game_date)
        opponent = opponent or inferred["opponent"]
        is_home = is_home if is_home is not None else inferred["is_home"]
        rest_days = rest_days if rest_days is not None else inferred["rest_days"]
        context_source = inferred.get("context_source", "live_schedule")

    features_df = build_prediction_row(
        recent_games,
        opponent=opponent,
        is_home=is_home,
        rest_days=rest_days,
        feature_context=feature_context,
    )

    predictions: dict[str, Any] = {
        "player": player_name,
        "opponent": opponent,
        "is_home": int(is_home),
        "rest_days": int(rest_days),
        "last_game_date": recent_games.iloc[-1]["GAME_DATE"].strftime("%Y-%m-%d"),
        "data_source": data_source,
        "context_source": context_source,
    }
    for target in TARGETS:
        models, metadata = load_model_bundle(target)
        validate_prediction_frame(features_df, metadata["feature_columns"])
        predictions[target] = {
            variant: float(model.predict(features_df)[0])
            for variant, model in models.items()
        }
    return predictions
