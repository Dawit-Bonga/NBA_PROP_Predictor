import pandas as pd
import numpy as np
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from datetime import datetime
import time

def get_current_season():
    """Determine current NBA season based on today's date"""
    today = datetime.now()
    year = today.year
    month = today.month
    
    # NBA season runs from October to April
    # If we're in Jan-June, current season started last year
    # If we're in July-Dec, current season starts this year
    if month <= 6:
        return f"{year-1}-{str(year)[-2:]}"
    else:
        return f"{year}-{str(year+1)[-2:]}"

def find_player_id(player_name):
    """Get NBA API player ID from name"""
    all_players = players.get_active_players()
    
    for player in all_players:
        if player['full_name'].lower() == player_name.lower():
            return player['id']
    
    # Try partial match
    for player in all_players:
        if player_name.lower() in player['full_name'].lower():
            return player['id']
    
    return None

def fetch_recent_games(player_name, season=None, num_games=15):
    """Fetch player's most recent games from NBA API"""
    # Auto-detect current season if not specified
    if season is None:
        season = get_current_season()
    
    player_id = find_player_id(player_name)
    
    if not player_id:
        return None
    
    try:
        # Fetch game log
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            timeout=30
        )
        
        df = gamelog.get_data_frames()[0]
        
        if df.empty:
            return None
        
        # Convert date first
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        
        # Filter out future games (games that haven't been played yet)
        # NBA API includes scheduled games with no WL value
        df = df[df['WL'].notna()]
        
        # Also filter out any games after today (safety check)
        from datetime import datetime
        today = pd.Timestamp(datetime.now())
        df = df[df['GAME_DATE'] <= today]
        
        # Sort by date (most recent first) BEFORE taking head
        df = df.sort_values('GAME_DATE', ascending=False)
        
        # NOW take most recent games
        df = df.head(num_games)
        
        return df
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def extract_opponent(matchup):
    """Extract opponent from matchup string"""
    if 'vs.' in matchup:
        return matchup.split(' vs. ')[1]
    elif ' @ ' in matchup:
        return matchup.split(' @ ')[1]
    return 'UNK'

def calculate_realtime_features(recent_games_df, opponent, is_home, rest_days):
    """
    Calculate features from recent games on-the-fly
    
    Args:
        recent_games_df: DataFrame with recent games (most recent first)
        opponent: Opponent team abbreviation
        is_home: 1 if home game, 0 if away
        rest_days: Days since last game
    
    Returns:
        Dictionary with all features needed for prediction
    """
    if recent_games_df is None or len(recent_games_df) < 5:
        return None
    
    # Add opponent column
    recent_games_df['OPPONENT'] = recent_games_df['MATCHUP'].apply(extract_opponent)
    
    # Reverse to calculate rolling stats correctly (oldest to newest)
    df = recent_games_df.sort_values('GAME_DATE', ascending=True)
    
    # Calculate features
    features = {}
    
    # === POINTS FEATURES ===
    features['L5_PTS'] = df['PTS'].tail(5).mean()
    features['L10_PTS'] = df['PTS'].tail(10).mean() if len(df) >= 10 else df['PTS'].mean()
    features['SEASON_AVG_PTS'] = df['PTS'].mean()
    features['L10_PTS_STD'] = df['PTS'].tail(10).std() if len(df) >= 10 else df['PTS'].std()
    features['RECENT_TREND_PTS'] = features['L5_PTS'] - features['L10_PTS']
    
    # === REBOUNDS FEATURES ===
    features['L5_REB'] = df['REB'].tail(5).mean()
    features['L10_REB'] = df['REB'].tail(10).mean() if len(df) >= 10 else df['REB'].mean()
    features['L10_REB_STD'] = df['REB'].tail(10).std() if len(df) >= 10 else df['REB'].std()
    features['RECENT_TREND_REB'] = features['L5_REB'] - features['L10_REB']
    
    # === ASSISTS FEATURES ===
    features['L5_AST'] = df['AST'].tail(5).mean()
    features['L10_AST'] = df['AST'].tail(10).mean() if len(df) >= 10 else df['AST'].mean()
    features['L10_AST_STD'] = df['AST'].tail(10).std() if len(df) >= 10 else df['AST'].std()
    features['RECENT_TREND_AST'] = features['L5_AST'] - features['L10_AST']
    
    # === MINUTES & USAGE ===
    features['L5_MIN'] = df['MIN'].tail(5).mean()
    features['L10_MIN'] = df['MIN'].tail(10).mean() if len(df) >= 10 else df['MIN'].mean()
    features['L5_FGA'] = df['FGA'].tail(5).mean()
    features['L5_FTA'] = df['FTA'].tail(5).mean()
    
    features['USAGE_RATE'] = features['L5_FGA'] / (features['L5_MIN'] + 0.1)
    features['FT_RATE'] = features['L5_FTA'] / (features['L5_MIN'] + 0.1)
    features['PPM_L5'] = features['L5_PTS'] / (features['L5_MIN'] + 0.1)
    features['PPM_L10'] = features['L10_PTS'] / (features['L10_MIN'] + 0.1)
    
    # === SHOOTING ===
    features['L5_FG_PCT'] = df['FG_PCT'].tail(5).mean()
    features['L5_FG3_PCT'] = df['FG3_PCT'].tail(5).mean()
    features['L5_FG3M'] = df['FG3M'].tail(5).mean()
    
    # === GAME CONTEXT ===
    features['IS_HOME'] = is_home
    features['REST_DAYS'] = min(rest_days, 7)  # Cap at 7
    features['IS_BACK_TO_BACK'] = 1 if rest_days == 0 else 0
    features['IS_RESTED'] = 1 if rest_days >= 2 else 0
    
    # === MATCHUP HISTORY vs OPPONENT ===
    opp_games = df[df['OPPONENT'] == opponent]
    if len(opp_games) > 0:
        features['VS_OPP_AVG_PTS'] = opp_games['PTS'].mean()
        features['VS_OPP_AVG_REB'] = opp_games['REB'].mean()
        features['VS_OPP_AVG_AST'] = opp_games['AST'].mean()
    else:
        # Use overall averages if no history
        features['VS_OPP_AVG_PTS'] = features['SEASON_AVG_PTS']
        features['VS_OPP_AVG_REB'] = features['L10_REB']
        features['VS_OPP_AVG_AST'] = features['L10_AST']
    
    # === OPPONENT DEFENSIVE STRENGTH ===
    # Use league average as placeholder (ideally fetch from training data)
    features['OPP_DEF_STRENGTH_PTS'] = 15.0  # League avg ~15 pts per player
    features['OPP_DEF_STRENGTH_REB'] = 5.5   # League avg ~5.5 reb per player
    features['OPP_DEF_STRENGTH_AST'] = 3.5   # League avg ~3.5 ast per player
    
    # === PACE METRICS ===
    features['OPP_PACE'] = df['FGA'].tail(10).mean() if len(df) >= 10 else df['FGA'].mean()
    features['TEAM_PACE'] = df['FGA'].tail(10).mean() if len(df) >= 10 else df['FGA'].mean()
    
    # === ADVANCED ===
    features['L5_WIN_PCT'] = (df['WL'].tail(5) == 'W').mean()
    features['L5_PLUS_MINUS'] = df['PLUS_MINUS'].tail(5).mean()
    
    return features

def get_realtime_prediction_features(player_name, opponent, is_home, rest_days, season=None):
    """
    Main function to get real-time features for prediction
    
    Returns:
        Tuple of (pts_features_dict, reb_features_dict, ast_features_dict, recent_games_df)
    """
    # Fetch recent games
    recent_games = fetch_recent_games(player_name, season=season, num_games=15)
    
    if recent_games is None:
        return None, None, None, None
    
    # Calculate features
    features = calculate_realtime_features(recent_games, opponent, is_home, rest_days)
    
    if features is None:
        return None, None, None, None
    
    # Separate features for each model
    pts_features = {k: features[k] for k in [
        'L5_PTS', 'L10_PTS', 'SEASON_AVG_PTS', 'L10_PTS_STD', 'RECENT_TREND_PTS',
        'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
        'L5_MIN', 'L10_MIN', 'USAGE_RATE', 'FT_RATE', 'PPM_L5', 'PPM_L10',
        'L5_FG_PCT', 'L5_FG3_PCT', 'L5_FG3M',
        'L5_REB', 'L5_AST',
        'VS_OPP_AVG_PTS', 'OPP_DEF_STRENGTH_PTS', 'OPP_PACE', 'TEAM_PACE',
        'L5_WIN_PCT', 'L5_PLUS_MINUS'
    ]}
    
    reb_features = {k: features[k] for k in [
        'L5_REB', 'L10_REB', 'L10_REB_STD', 'RECENT_TREND_REB',
        'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
        'L5_MIN', 'L10_MIN', 'USAGE_RATE',
        'L5_PTS', 'L5_AST',
        'VS_OPP_AVG_REB', 'OPP_DEF_STRENGTH_REB', 'OPP_PACE', 'TEAM_PACE',
        'L5_WIN_PCT', 'L5_PLUS_MINUS'
    ]}
    
    ast_features = {k: features[k] for k in [
        'L5_AST', 'L10_AST', 'L10_AST_STD', 'RECENT_TREND_AST',
        'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
        'L5_MIN', 'L10_MIN', 'USAGE_RATE',
        'L5_PTS', 'L5_REB',
        'VS_OPP_AVG_AST', 'OPP_DEF_STRENGTH_AST', 'OPP_PACE', 'TEAM_PACE',
        'L5_WIN_PCT', 'L5_PLUS_MINUS'
    ]}
    
    return pts_features, reb_features, ast_features, recent_games

def run_realtime_prediction():
    """
    Load today's props from CSV, generate predictions, and save results
    """
    import pandas as pd
    import xgboost as xgb
    import os
    from datetime import datetime
    
    print("\n" + "="*60)
    print("🔮 GENERATING PREDICTIONS")
    print("="*60)
    
    # Paths
    TODAYS_PROPS = '../data/todays_props.csv'
    MODELS_DIR = '../models/'
    OUTPUT_PATH = '../data/analysis_results.csv'
    
    # Check if props file exists
    if not os.path.exists(TODAYS_PROPS):
        print(f"❌ Props file not found: {TODAYS_PROPS}")
        return False
    
    # Load props
    print(f"\n📂 Loading props from: {TODAYS_PROPS}")
    props_df = pd.read_csv(TODAYS_PROPS)
    print(f"  Found {len(props_df)} props")
    
    # Load models
    print(f"\n🤖 Loading models from: {MODELS_DIR}")
    models = {}
    for stat_type in ['pts', 'reb', 'ast']:
        model_path = os.path.join(MODELS_DIR, f"{stat_type}_model.json")
        if os.path.exists(model_path):
            model = xgb.XGBRegressor()
            model.load_model(model_path)
            models[stat_type.upper()] = model
            print(f"  ✓ Loaded {stat_type.upper()} model")
        else:
            print(f"  ⚠️ Missing {stat_type.upper()} model: {model_path}")
    
    if not models:
        print("❌ No models found!")
        return False
    
    # Generate predictions
    results = []
    print(f"\n🔍 Generating predictions...")
    
    for idx, row in props_df.iterrows():
        player = row['player']
        stat_type = row['stat_mapped']
        line = row['line']
        
        print(f"\n  📊 {player} - {stat_type} (Line: {line})")
        
        # Check if we have a model for this stat type
        if stat_type not in models:
            print(f"    ⚠️ No model for {stat_type}, skipping...")
            continue
        
        # For now, use dummy features (opponent="N/A", home=True, rest_days=1)
        # In production, you'd fetch actual game info
        try:
            pts_features, reb_features, ast_features, recent_games = get_realtime_prediction_features(
                player, 
                opponent="N/A",  # TODO: Get actual opponent
                is_home=True,     # TODO: Get actual home/away
                rest_days=1       # TODO: Get actual rest days
            )
            
            if stat_type == 'PTS' and pts_features:
                features_df = pd.DataFrame([pts_features])
                prediction = models['PTS'].predict(features_df)[0]
            elif stat_type == 'REB' and reb_features:
                features_df = pd.DataFrame([reb_features])
                prediction = models['REB'].predict(features_df)[0]
            elif stat_type == 'AST' and ast_features:
                features_df = pd.DataFrame([ast_features])
                prediction = models['AST'].predict(features_df)[0]
            else:
                print(f"    ⚠️ Could not generate features")
                continue
            
            # Calculate L5 average for context
            l5_avg = recent_games.tail(5)[stat_type].mean() if recent_games is not None and len(recent_games) > 0 else 0
            last_game_date = recent_games.iloc[0]['GAME_DATE'] if recent_games is not None and len(recent_games) > 0 else None
            
            print(f"    ✓ Prediction: {prediction:.1f} (L5 Avg: {l5_avg:.1f})")
            
            results.append({
                'player': player,
                'stat': row['stat'],
                'line': line,
                'prediction': prediction,
                'l5_avg': l5_avg,
                'last_game': last_game_date,
                'edge': prediction - line
            })
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    # Save results
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(OUTPUT_PATH, index=False)
        print(f"\n✅ Saved {len(results_df)} predictions to: {OUTPUT_PATH}")
        return True
    else:
        print("\n⚠️ No predictions generated")
        return False