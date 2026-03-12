from __future__ import annotations

import random
import time

import pandas as pd
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
from requests.exceptions import ConnectionError, ReadTimeout
from tqdm import tqdm

from config import RAW_LOGS_PATH, ensure_directories
from feature_pipeline import build_season_list


SEASONS = build_season_list(n_seasons=3)


def fetch_with_retry(player_id: int, season: str, retries: int = 3) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season, timeout=60)
            return gamelog.get_data_frames()[0]
        except (ReadTimeout, ConnectionError):
            time.sleep(2 ** (attempt + 1))
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def fetch_data() -> pd.DataFrame:
    ensure_directories()
    nba_players = players.get_active_players()
    all_logs = []
    for player in tqdm(nba_players, desc="Scraping player game logs"):
        player_name = player["full_name"]
        player_id = player["id"]
        for season in SEASONS:
            df = fetch_with_retry(player_id, season)
            if not df.empty:
                df["PLAYER_NAME"] = player_name
                df["PLAYER_ID"] = player_id
                df["SEASON_ID"] = season
                all_logs.append(df)
            time.sleep(random.uniform(0.4, 0.8))

    if not all_logs:
        raise RuntimeError("No game logs were fetched.")

    raw_df = pd.concat(all_logs, ignore_index=True)
    raw_df.to_csv(RAW_LOGS_PATH, index=False)
    print(f"Saved {len(raw_df)} rows to {RAW_LOGS_PATH}")
    return raw_df


if __name__ == "__main__":
    fetch_data()
