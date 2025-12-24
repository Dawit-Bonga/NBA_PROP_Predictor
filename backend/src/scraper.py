import pandas as pd
import time
import random
from tqdm import tqdm
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from requests.exceptions import ReadTimeout, ConnectionError

# --- CONFIG ---
SEASONS = ['2023-24', '2024-25'] 
OUTPUT_PATH = '../data/raw/nba_logs.csv'

# Custom function to handle "flaky" API calls
def fetch_with_retry(player_id, season, retries=3):
    for attempt in range(retries):
        try:
            # timeout=60 tells the API to wait 60 seconds before giving up (default is 30)
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id, 
                season=season,
                timeout=60
            )
            return gamelog.get_data_frames()[0]
        
        except (ReadTimeout, ConnectionError) as e:
            # If it fails, wait longer each time (2s, 4s, 8s...)
            wait_time = 2 ** (attempt + 1)
            print(f"⚠️ Timeout for {player_id}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
        except Exception as e:
            # If it's a different error (like bad data), skip it
            print(f"❌ Unknown error: {e}")
            return pd.DataFrame() # Return empty if totally failed
            
    return pd.DataFrame() # Return empty if all retries failed

def fetch_data():
    print("Fetching active player list...")
    nba_players = players.get_active_players()
    print(f"Found {len(nba_players)} active players.")
    
    all_logs = []
    
    # tqdm creates the progress bar
    for player in tqdm(nba_players[:300]):
        player_name = player['full_name']
        player_id = player['id']
        
        for season in SEASONS:
            # Call our new "Robust" function
            df = fetch_with_retry(player_id, season)
            
            if not df.empty:
                df['PLAYER_NAME'] = player_name
                df['SEASON_ID'] = season
                all_logs.append(df)
            
            # Random sleep 0.6 to 1.0 seconds to look more human
            time.sleep(random.uniform(0.6, 1.0))
    
    # Save
    if all_logs:
        master_df = pd.concat(all_logs, ignore_index=True)
        master_df.to_csv(OUTPUT_PATH, index=False)
        print(f"\n✅ SUCCESS: Scraped {len(master_df)} rows. Saved to {OUTPUT_PATH}")
    else:
        print("\n❌ FAILED: No data found.")

if __name__ == "__main__":
    fetch_data()