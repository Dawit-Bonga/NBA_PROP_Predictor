from __future__ import annotations

from datetime import datetime

import pandas as pd
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.static import teams


TEAM_ID_TO_ABBREV = {team["id"]: team["abbreviation"] for team in teams.get_teams()}


def fetch_todays_schedule(game_date: str | None = None) -> pd.DataFrame:
    target_date = game_date or datetime.now().strftime("%Y-%m-%d")
    try:
        board = scoreboardv2.ScoreboardV2(game_date=target_date, day_offset="0", timeout=30)
        header = board.get_data_frames()[2]
        if header.empty:
            return pd.DataFrame(columns=["HOME_TEAM_ID", "VISITOR_TEAM_ID", "HOME_ABBREV", "VISITOR_ABBREV"])
        schedule = header[["GAME_ID", "HOME_TEAM_ID", "VISITOR_TEAM_ID"]].copy()
        schedule["HOME_ABBREV"] = schedule["HOME_TEAM_ID"].map(TEAM_ID_TO_ABBREV)
        schedule["VISITOR_ABBREV"] = schedule["VISITOR_TEAM_ID"].map(TEAM_ID_TO_ABBREV)
        return schedule
    except Exception:
        return pd.DataFrame(columns=["HOME_TEAM_ID", "VISITOR_TEAM_ID", "HOME_ABBREV", "VISITOR_ABBREV"])


def infer_matchup_for_team(team_abbrev: str, game_date: str | None = None) -> dict | None:
    schedule = fetch_todays_schedule(game_date)
    if schedule.empty:
        return None
    matching = schedule[
        (schedule["HOME_ABBREV"] == team_abbrev) | (schedule["VISITOR_ABBREV"] == team_abbrev)
    ]
    if matching.empty:
        return None
    row = matching.iloc[0]
    if row["HOME_ABBREV"] == team_abbrev:
        return {"opponent": row["VISITOR_ABBREV"], "is_home": 1}
    return {"opponent": row["HOME_ABBREV"], "is_home": 0}
