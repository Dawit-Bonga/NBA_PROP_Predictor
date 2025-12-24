import pandas as pd
import numpy as np

INPUT_PATH = '../data/raw/nba_logs.csv'
OUTPUT_PATH = "../data/processed/training_data.csv"

def get_opponent(matchup):
    """Extract opponent team from matchup string"""
    if 'vs.' in matchup: 
        return matchup.split(' vs. ')[1]
    elif ' @ ' in matchup: 
        return matchup.split(' @ ')[1]
    else: 
        return 'UNK'

def get_team(matchup):
    """Extract player's team from matchup string"""
    if 'vs.' in matchup:
        return matchup.split(' vs. ')[0]
    elif ' @ ' in matchup:
        return matchup.split(' @ ')[0]
    else:
        return 'UNK'

def clean_outliers(df):
    """Remove bad data and handle outliers"""
    print("Cleaning outliers and bad data...")
    initial_rows = len(df)
    
    # Remove games with very low minutes (likely DNPs or garbage time)
    df = df[df['MIN'] > 5].copy()
    
    # Remove statistical anomalies
    df = df[df['PTS'] < 70].copy()
    df = df[df['REB'] < 30].copy()
    df = df[df['AST'] < 25].copy()
    
    # Cap extreme rest days (7+ days treated the same)
    df['REST_DAYS'] = df['REST_DAYS'].clip(0, 7)
    
    # Replace infinity values with NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    
    print(f"  Removed {initial_rows - len(df)} outlier rows")
    return df

def process_data():
    print(f"Loading raw data from {INPUT_PATH}...")
    df = pd.read_csv(INPUT_PATH)
    
    print(f"  Loaded {len(df)} rows")
    
    # 1. DATA CLEANING
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values(['Player_ID', 'GAME_DATE']).reset_index(drop=True)
    
    # Extract team and opponent info
    df['OPPONENT'] = df['MATCHUP'].apply(get_opponent)
    df['TEAM'] = df['MATCHUP'].apply(get_team)
    df['IS_HOME'] = df['MATCHUP'].apply(lambda x: 1 if 'vs.' in x else 0)
    
    # 2. FEATURE ENGINEERING
    print("Calculating player-level features...")
    player_group = df.groupby('Player_ID')
    
    # === TIER 1: BASIC ROLLING STATS ===
    # Points
    df['L5_PTS'] = player_group['PTS'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    df['L10_PTS'] = player_group['PTS'].transform(lambda x: x.shift(1).rolling(10, min_periods=5).mean())
    df['SEASON_AVG_PTS'] = player_group['PTS'].transform(lambda x: x.shift(1).expanding().mean())
    
    # Rebounds & Assists
    df['L5_REB'] = player_group['REB'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    df['L10_REB'] = player_group['REB'].transform(lambda x: x.shift(1).rolling(10, min_periods=5).mean())
    df['L5_AST'] = player_group['AST'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    df['L10_AST'] = player_group['AST'].transform(lambda x: x.shift(1).rolling(10, min_periods=5).mean())
    
    # === TIER 2: VOLATILITY & CONSISTENCY ===
    df['L10_PTS_STD'] = player_group['PTS'].transform(lambda x: x.shift(1).rolling(10, min_periods=5).std())
    df['L10_REB_STD'] = player_group['REB'].transform(lambda x: x.shift(1).rolling(10, min_periods=5).std())
    df['L10_AST_STD'] = player_group['AST'].transform(lambda x: x.shift(1).rolling(10, min_periods=5).std())
    
    # Recent trend (hot or cold?)
    df['RECENT_TREND_PTS'] = df['L5_PTS'] - df['L10_PTS']
    df['RECENT_TREND_REB'] = df['L5_REB'] - df['L10_REB']
    df['RECENT_TREND_AST'] = df['L5_AST'] - df['L10_AST']
    
    # === TIER 3: MINUTES & USAGE ===
    df['L5_MIN'] = player_group['MIN'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    df['L10_MIN'] = player_group['MIN'].transform(lambda x: x.shift(1).rolling(10, min_periods=5).mean())
    df['L5_FGA'] = player_group['FGA'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    df['L5_FTA'] = player_group['FTA'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    
    # Usage rate (shot attempts per minute)
    df['USAGE_RATE'] = df['L5_FGA'] / (df['L5_MIN'] + 0.1)  # Add 0.1 to avoid division by zero
    df['FT_RATE'] = df['L5_FTA'] / (df['L5_MIN'] + 0.1)
    
    # Points per minute efficiency
    df['PPM_L5'] = df['L5_PTS'] / (df['L5_MIN'] + 0.1)
    df['PPM_L10'] = df['L10_PTS'] / (df['L10_MIN'] + 0.1)
    
    # === TIER 4: GAME CONTEXT & REST ===
    df['REST_DAYS'] = player_group['GAME_DATE'].diff().dt.days - 1
    df['DAYS_SINCE_LAST'] = player_group['GAME_DATE'].diff().dt.days
    df['IS_BACK_TO_BACK'] = (df['DAYS_SINCE_LAST'] == 1).astype(int)
    df['IS_RESTED'] = (df['REST_DAYS'] >= 2).astype(int)
    
    # === TIER 5: SHOOTING EFFICIENCY ===
    df['L5_FG_PCT'] = player_group['FG_PCT'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    df['L5_FG3_PCT'] = player_group['FG3_PCT'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    df['L5_FG3M'] = player_group['FG3M'].transform(lambda x: x.shift(1).rolling(5, min_periods=3).mean())
    
    # === TIER 6: MATCHUP HISTORY ===
    print("Calculating matchup-specific features...")
    df['VS_OPP_AVG_PTS'] = df.groupby(['Player_ID', 'OPPONENT'])['PTS'].transform(
        lambda x: x.shift(1).expanding().mean()
    )
    df['VS_OPP_AVG_REB'] = df.groupby(['Player_ID', 'OPPONENT'])['REB'].transform(
        lambda x: x.shift(1).expanding().mean()
    )
    df['VS_OPP_AVG_AST'] = df.groupby(['Player_ID', 'OPPONENT'])['AST'].transform(
        lambda x: x.shift(1).expanding().mean()
    )
    
    # === TIER 7: TEAM & OPPONENT METRICS ===
    print("Calculating team and opponent metrics...")
    
    # Sort by opponent to calculate defensive metrics
    df = df.sort_values(['OPPONENT', 'GAME_DATE']).reset_index(drop=True)
    opp_group = df.groupby('OPPONENT')
    
    # Opponent defensive strength (average points allowed)
    df['OPP_DEF_STRENGTH_PTS'] = opp_group['PTS'].transform(
        lambda x: x.shift(1).rolling(window=30, min_periods=5).mean()
    )
    df['OPP_DEF_STRENGTH_REB'] = opp_group['REB'].transform(
        lambda x: x.shift(1).rolling(window=30, min_periods=5).mean()
    )
    df['OPP_DEF_STRENGTH_AST'] = opp_group['AST'].transform(
        lambda x: x.shift(1).rolling(window=30, min_periods=5).mean()
    )
    
    # Opponent pace (field goal attempts as proxy)
    df['OPP_PACE'] = opp_group['FGA'].transform(
        lambda x: x.shift(1).rolling(window=20, min_periods=5).mean()
    )
    
    # Sort back by player and date
    df = df.sort_values(['Player_ID', 'GAME_DATE']).reset_index(drop=True)
    
    # Team pace
    team_group = df.groupby('TEAM')
    df['TEAM_PACE'] = team_group['FGA'].transform(
        lambda x: x.shift(1).rolling(window=20, min_periods=5).mean()
    )
    
    # === TIER 8: WIN/LOSS MOMENTUM ===
    # Recreate player_group after sorting
    player_group = df.groupby('Player_ID')
    df['WL_BINARY'] = (df['WL'] == 'W').astype(int)
    df['L5_WIN_PCT'] = player_group['WL_BINARY'].transform(
        lambda x: x.shift(1).rolling(5, min_periods=3).mean()
    )
    
    # === TIER 9: ADVANCED STATS ===
    df['L5_PLUS_MINUS'] = player_group['PLUS_MINUS'].transform(
        lambda x: x.shift(1).rolling(5, min_periods=3).mean()
    )
    
    # 3. DATA CLEANING & VALIDATION
    df = clean_outliers(df)
    
    # Handle missing values intelligently
    print("Handling missing values...")
    
    # Fill opponent metrics with global averages if missing
    for col in ['OPP_DEF_STRENGTH_PTS', 'OPP_DEF_STRENGTH_REB', 'OPP_DEF_STRENGTH_AST', 'OPP_PACE']:
        if col in df.columns:
            df[col] = df.groupby('OPPONENT')[col].transform(
                lambda x: x.fillna(x.mean())
            )
    
    # Fill matchup history with player's overall average if no history
    df['VS_OPP_AVG_PTS'] = df['VS_OPP_AVG_PTS'].fillna(df['SEASON_AVG_PTS'])
    df['VS_OPP_AVG_REB'] = df['VS_OPP_AVG_REB'].fillna(df['L10_REB'])
    df['VS_OPP_AVG_AST'] = df['VS_OPP_AVG_AST'].fillna(df['L10_AST'])
    
    # Drop rows with critical missing values
    critical_features = ['L10_PTS', 'L10_MIN', 'REST_DAYS', 'OPP_DEF_STRENGTH_PTS']
    df = df.dropna(subset=critical_features)
    
    # 4. FINAL OUTPUT
    final_cols = [
        # Metadata
        'GAME_DATE', 'PLAYER_NAME', 'MATCHUP', 'TEAM', 'OPPONENT',
        
        # Context
        'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
        
        # Points Features
        'L5_PTS', 'L10_PTS', 'SEASON_AVG_PTS', 'L10_PTS_STD', 'RECENT_TREND_PTS',
        
        # Rebounds Features  
        'L5_REB', 'L10_REB', 'L10_REB_STD', 'RECENT_TREND_REB',
        
        # Assists Features
        'L5_AST', 'L10_AST', 'L10_AST_STD', 'RECENT_TREND_AST',
        
        # Minutes & Usage
        'L5_MIN', 'L10_MIN', 'USAGE_RATE', 'FT_RATE', 'PPM_L5', 'PPM_L10',
        
        # Shooting
        'L5_FG_PCT', 'L5_FG3_PCT', 'L5_FG3M',
        
        # Matchup History
        'VS_OPP_AVG_PTS', 'VS_OPP_AVG_REB', 'VS_OPP_AVG_AST',
        
        # Opponent Metrics
        'OPP_DEF_STRENGTH_PTS', 'OPP_DEF_STRENGTH_REB', 'OPP_DEF_STRENGTH_AST', 'OPP_PACE',
        
        # Team Metrics
        'TEAM_PACE',
        
        # Advanced
        'L5_WIN_PCT', 'L5_PLUS_MINUS',
        
        # Targets (what we're predicting)
        'PTS', 'REB', 'AST'
    ]
    
    final_df = df[final_cols].copy()
    final_df.to_csv(OUTPUT_PATH, index=False)
    
    print("\n" + "="*50)
    print(f"✅ SUCCESS! Feature Engineering Complete")
    print("="*50)
    print(f"  Total Rows: {len(final_df):,}")
    print(f"  Total Features: {len(final_cols) - 6}")  # Minus metadata and targets
    print(f"  Date Range: {final_df['GAME_DATE'].min()} to {final_df['GAME_DATE'].max()}")
    print(f"  Unique Players: {final_df['PLAYER_NAME'].nunique()}")
    print(f"  Saved to: {OUTPUT_PATH}")
    print("="*50)

if __name__ == "__main__":
    process_data()