from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from nba_api.stats.static import players, teams

from config import TARGETS, model_metadata_path
from prediction_service import fetch_recent_games, infer_live_game_context, predict_single_player


st.set_page_config(page_title="NBA Prop Predictor", layout="wide")

PLAYER_OPTIONS = sorted(player["full_name"] for player in players.get_active_players())
TEAM_OPTIONS = sorted(team["abbreviation"] for team in teams.get_teams())


@st.cache_data
def load_model_summaries():
    summaries = {}
    for target in TARGETS:
        path = model_metadata_path(target)
        if path.exists():
            summaries[target] = json.loads(path.read_text())
    return summaries


def recommendation_text(prediction: float, line: float, threshold: float) -> tuple[str, float]:
    edge = prediction - line
    if abs(edge) < threshold:
        return "No bet", edge
    return ("Over" if edge > 0 else "Under"), edge


def main():
    st.title("NBA Prop Predictor")
    st.caption("Shared training and inference pipeline with saved model artifacts.")

    model_summaries = load_model_summaries()
    if len(model_summaries) != len(TARGETS):
        st.error("Models are not fully available. Run `python3 src/train.py` from `backend/` first.")
        return

    with st.sidebar:
        st.header("Prediction Input")
        player_name = st.selectbox("Player", PLAYER_OPTIONS)
        use_auto_context = st.checkbox("Infer today's matchup automatically", value=True)
        opponent = st.selectbox("Opponent", TEAM_OPTIONS, index=0, disabled=use_auto_context)
        is_home = st.radio("Location", options=["Home", "Away"], horizontal=True, disabled=use_auto_context)
        rest_days = st.slider("Rest days", min_value=0, max_value=7, value=1, disabled=use_auto_context)
        edge_threshold = st.slider("Recommendation threshold", min_value=1.0, max_value=5.0, value=2.0, step=0.5)
        line_inputs = {
            "PTS": st.number_input("Points line", value=20.5, step=0.5),
            "REB": st.number_input("Rebounds line", value=5.5, step=0.5),
            "AST": st.number_input("Assists line", value=4.5, step=0.5),
        }

    with st.spinner(f"Loading recent games for {player_name}..."):
        recent_games = fetch_recent_games(player_name)

    if recent_games is None or recent_games.empty:
        st.error(f"Could not load recent games for {player_name}.")
        return

    inferred_context = None
    if use_auto_context:
        try:
            inferred_context = infer_live_game_context(player_name, recent_games)
        except Exception as exc:
            st.warning(f"Automatic context unavailable: {exc}")

    active_opponent = inferred_context["opponent"] if inferred_context else opponent
    active_is_home = inferred_context["is_home"] if inferred_context else int(is_home == "Home")
    active_rest_days = inferred_context["rest_days"] if inferred_context else rest_days

    try:
        payload = predict_single_player(
            player_name=player_name,
            opponent=active_opponent,
            is_home=active_is_home,
            rest_days=active_rest_days,
        )
    except Exception as exc:
        st.error(f"Prediction failed: {exc}")
        return

    st.subheader("Game Context")
    col1, col2, col3 = st.columns(3)
    col1.metric("Opponent", active_opponent)
    col2.metric("Location", "Home" if active_is_home else "Away")
    col3.metric("Rest days", active_rest_days)

    st.subheader("Predictions")
    prediction_cols = st.columns(3)
    for idx, target in enumerate(TARGETS):
        with prediction_cols[idx]:
            result = payload[target]
            line = line_inputs[target]
            recommendation, edge = recommendation_text(result["mean"], line, edge_threshold)
            st.metric(f"{target} mean", f"{result['mean']:.2f}", delta=f"{edge:+.2f} vs line")
            st.write(f"Line: {line:.1f}")
            st.write(f"Range: {result['lower']:.2f} to {result['upper']:.2f}")
            st.write(f"Recommendation: {recommendation}")

    st.subheader("Recent Games")
    recent_display = recent_games.sort_values("GAME_DATE", ascending=False)[
        ["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "MIN"]
    ].copy()
    recent_display["GAME_DATE"] = recent_display["GAME_DATE"].dt.strftime("%Y-%m-%d")
    st.dataframe(recent_display, use_container_width=True)

    st.subheader("Model Summary")
    summary_rows = []
    for target, metadata in model_summaries.items():
        holdout = metadata["metrics"]["holdout"]
        summary_rows.append(
            {
                "target": target,
                "mae": holdout["mae"],
                "rmse": holdout["rmse"],
                "baseline_mae": holdout["baseline_mae"],
                "interval_coverage": holdout["interval_coverage"],
                "features": len(metadata["feature_columns"]),
            }
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)


if __name__ == "__main__":
    main()
