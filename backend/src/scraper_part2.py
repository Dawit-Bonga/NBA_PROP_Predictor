import pandas as pd
import time
import random
import os
from tqdm import tqdm
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from requests.exceptions import ReadTimeout, ConnectionError

# --- CONFIG ---
SEASONS = ['2023-24', '2024-25'] 
OUTPUT_PATH = '../data/raw/nba_logs.csv'

def fetch_with_retry(player_id, season, retries=3):
    for attempt in range(retries):
        try:
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id, 
                season=season,
                timeout=60
            )
            return gamelog.get_data_frames()[0]
        except (ReadTimeout, ConnectionError) as e:
            wait_time = 2 ** (attempt + 1)
            time.sleep(wait_time)
        except Exception as e:
            return pd.DataFrame()
    return pd.DataFrame()

def fetch_data():
    print("Fetching active player list...")
    nba_players = players.get_active_players()
    
    # --- CRITICAL CHANGE ---
    # slice [300:] means "start at 300 and go to the end"
    remaining_players = nba_players[300:]
    print(f"Resuming scrape. Found {len(remaining_players)} players left.")
    
    all_logs = []
    
    for player in tqdm(remaining_players):
        player_name = player['full_name']
        player_id = player['id']
        
        for season in SEASONS:
            df = fetch_with_retry(player_id, season)
            if not df.empty:
                df['PLAYER_NAME'] = player_name
                df['SEASON_ID'] = season
                all_logs.append(df)
            
            time.sleep(random.uniform(0.6, 1.0))
    
    # --- SAVE LOGIC (APPEND MODE) ---
    if all_logs:
        new_data = pd.concat(all_logs, ignore_index=True)
        
        # Check if file exists so we append correctly
        if os.path.exists(OUTPUT_PATH):
            new_data.to_csv(OUTPUT_PATH, mode='a', header=False, index=False)
            print(f"\n✅ SUCCESS: Appended {len(new_data)} new rows to {OUTPUT_PATH}")
        else:
            # Fallback if file was deleted
            new_data.to_csv(OUTPUT_PATH, mode='w', header=True, index=False)
            print(f"\n⚠️ File was missing. Created new {OUTPUT_PATH}")
            
    else:
        print("\n❌ No new data found.")

if __name__ == "__main__":
    fetch_data()