from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from nba_api.stats.static import players
from pydantic import BaseModel, Field

from config import ANALYSIS_OUTPUT_PATH, TARGETS, TODAYS_PROPS_PATH, TOP_BETS_OUTPUT_PATH, model_metadata_path
from pipeline import generate_predictions, rank_bets
from prediction_service import build_player_insights, predict_single_player


app = FastAPI(title="NBA Prop Predictor API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    player: str = Field(..., description="Full player name")
    opponent: str | None = Field(default=None, description="Opponent team abbreviation")
    is_home: int | None = Field(default=None, description="1 for home, 0 for away")
    rest_days: int | None = Field(default=None, ge=0, le=7)
    season: str | None = Field(default=None, description="NBA season like 2025-26")
    game_date: str | None = Field(default=None, description="Override date in YYYY-MM-DD")


class PredictionResponse(BaseModel):
    player: str
    opponent: str
    is_home: int
    rest_days: int
    last_game_date: str
    data_source: str
    context_source: str
    PTS: dict[str, float]
    REB: dict[str, float]
    AST: dict[str, float]


class PlayerInsightsResponse(BaseModel):
    player: str
    opponent: str
    is_home: int
    rest_days: int
    last_game_date: str
    data_source: str
    context_source: str
    summary: dict[str, float]
    recent_games: list[dict[str, Any]]


def _load_csv_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def get_config() -> dict[str, Any]:
    return {"targets": list(TARGETS), "api_version": app.version}


@app.get("/players")
def list_players() -> dict[str, list[str]]:
    names = sorted(player["full_name"] for player in players.get_players())
    return {"players": names}


@app.get("/models")
def list_models() -> dict[str, Any]:
    output = {}
    for target in TARGETS:
        metadata_path = model_metadata_path(target)
        if metadata_path.exists():
            output[target] = json.loads(metadata_path.read_text())
        else:
            output[target] = {"available": False}
    return output


@app.get("/props")
def list_props() -> dict[str, Any]:
    return {"props": _load_csv_records(TODAYS_PROPS_PATH)}


@app.get("/predictions")
def list_predictions() -> dict[str, Any]:
    return {"predictions": _load_csv_records(ANALYSIS_OUTPUT_PATH)}


@app.get("/bets")
def list_bets() -> dict[str, Any]:
    return {"bets": _load_csv_records(TOP_BETS_OUTPUT_PATH)}


@app.post("/pipeline/refresh")
def refresh_pipeline(min_edge: float = 2.0) -> dict[str, Any]:
    predictions_df = generate_predictions()
    bets_df = rank_bets(predictions_df, min_edge=min_edge)
    return {
        "predictions": int(len(predictions_df)),
        "bets": int(len(bets_df)),
        "min_edge": min_edge,
    }


@app.post("/player-insights", response_model=PlayerInsightsResponse)
def player_insights(payload: PredictionRequest) -> PlayerInsightsResponse:
    try:
        insights = build_player_insights(
            player_name=payload.player,
            opponent=payload.opponent,
            is_home=payload.is_home,
            rest_days=payload.rest_days,
            season=payload.season,
            game_date=payload.game_date,
        )
        return PlayerInsightsResponse(**insights)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    try:
        prediction = predict_single_player(
            player_name=payload.player,
            opponent=payload.opponent,
            is_home=payload.is_home,
            rest_days=payload.rest_days,
            season=payload.season,
            game_date=payload.game_date,
        )
        return PredictionResponse(**prediction)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
