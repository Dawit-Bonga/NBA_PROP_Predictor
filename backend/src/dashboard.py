import streamlit as st
import pandas as pd
import xgboost as xgb
import numpy as np
import os
from datetime import datetime
from realtime_features import get_realtime_prediction_features

# ==================== CONFIG ====================
st.set_page_config(
    page_title="🏀 NBA Prop Predictor",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_PATH = "../data/processed/training_data1.csv"
MODELS_DIR = "../models/"

# Load feature sets from train.py
POINTS_FEATURES = [
    'L5_PTS', 'L10_PTS', 'SEASON_AVG_PTS', 'L10_PTS_STD', 'RECENT_TREND_PTS',
    'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
    'L5_MIN', 'L10_MIN', 'USAGE_RATE', 'FT_RATE', 'PPM_L5', 'PPM_L10',
    'L5_FG_PCT', 'L5_FG3_PCT', 'L5_FG3M',
    'L5_REB', 'L5_AST',
    'VS_OPP_AVG_PTS', 'OPP_DEF_STRENGTH_PTS', 'OPP_PACE', 'TEAM_PACE',
    'L5_WIN_PCT', 'L5_PLUS_MINUS'
]

REBOUNDS_FEATURES = [
    'L5_REB', 'L10_REB', 'L10_REB_STD', 'RECENT_TREND_REB',
    'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
    'L5_MIN', 'L10_MIN', 'USAGE_RATE',
    'L5_PTS', 'L5_AST',
    'VS_OPP_AVG_REB', 'OPP_DEF_STRENGTH_REB', 'OPP_PACE', 'TEAM_PACE',
    'L5_WIN_PCT', 'L5_PLUS_MINUS'
]

ASSISTS_FEATURES = [
    'L5_AST', 'L10_AST', 'L10_AST_STD', 'RECENT_TREND_AST',
    'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
    'L5_MIN', 'L10_MIN', 'USAGE_RATE',
    'L5_PTS', 'L5_REB',
    'VS_OPP_AVG_AST', 'OPP_DEF_STRENGTH_AST', 'OPP_PACE', 'TEAM_PACE',
    'L5_WIN_PCT', 'L5_PLUS_MINUS'
]

# ==================== CACHING ====================
@st.cache_data
def load_data():
    """Load training data for player stats lookup"""
    df = pd.read_csv(DATA_PATH)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    return df

@st.cache_resource
def load_models():
    """Load all trained models"""
    models = {}
    for prop in ['pts', 'reb', 'ast']:
        model_path = os.path.join(MODELS_DIR, f"{prop}_model.json")
        if os.path.exists(model_path):
            model = xgb.XGBRegressor()
            model.load_model(model_path)
            models[prop.upper()] = model
        else:
            st.error(f"Model not found: {model_path}. Please run train.py first!")
    return models

# ==================== HELPER FUNCTIONS ====================
def get_player_latest_stats(df, player_name):
    """Get the most recent game stats for a player"""
    player_df = df[df['PLAYER_NAME'] == player_name].sort_values('GAME_DATE', ascending=False)
    
    if len(player_df) == 0:
        return None
    
    return player_df.iloc[0]

def get_player_opponent_stats(df, player_name, opponent):
    """Get player's stats against a specific opponent"""
    player_opp_df = df[
        (df['PLAYER_NAME'] == player_name) & 
        (df['OPPONENT'] == opponent)
    ].sort_values('GAME_DATE', ascending=False)
    
    if len(player_opp_df) == 0:
        return None
    
    return player_opp_df

def calculate_confidence_score(prediction, vegas_line):
    """Calculate confidence score based on prediction vs vegas line"""
    edge = abs(prediction - vegas_line)
    
    if edge < 2:
        return "🟡 Low Confidence", edge
    elif edge < 4:
        return "🟠 Medium Confidence", edge
    else:
        return "🟢 High Confidence", edge

def get_betting_recommendation(prediction, vegas_line, threshold=2.0):
    """Get betting recommendation"""
    edge = prediction - vegas_line
    
    if abs(edge) < threshold:
        return "⚪ NO BET", "Edge too small", edge, "neutral"
    elif edge > 0:
        return "🔥 BET OVER", f"+{edge:.1f} point edge", edge, "over"
    else:
        return "❄️ BET UNDER", f"{edge:.1f} point edge", edge, "under"

# ==================== STREAMLIT APP ====================
def main():
    # Custom CSS - Enhanced visibility with bolder colors
    st.markdown("""
        <style>
        .big-font {
            font-size:30px !important;
            font-weight: bold;
        }
        .pred-box {
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .over-bet {
            background: linear-gradient(135deg, #ff6b6b 0%, #ff8787 100%);
            border-left: 6px solid #c92a2a;
            color: white;
        }
        .over-bet h3, .over-bet p, .over-bet strong {
            color: white !important;
        }
        .under-bet {
            background: linear-gradient(135deg, #4dabf7 0%, #74c0fc 100%);
            border-left: 6px solid #1971c2;
            color: white;
        }
        .under-bet h3, .under-bet p, .under-bet strong {
            color: white !important;
        }
        .no-bet {
            background: linear-gradient(135deg, #868e96 0%, #adb5bd 100%);
            border-left: 6px solid #495057;
            color: white;
        }
        .no-bet h3, .no-bet p, .no-bet strong {
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Header
    st.title("🏀 NBA Prop Bet Predictor")
    st.markdown("### Advanced ML-Powered Betting Recommendations")
    st.markdown("---")
    
    # Load data and models
    with st.spinner("Loading data and models..."):
        df = load_data()
        models = load_models()
    
    if not models:
        st.error("⚠️ Models not loaded. Please run train.py first!")
        return
    
    # Sidebar - Player Selection
    st.sidebar.header("🎯 Bet Configuration")
    
    # Get unique players and opponents
    players = sorted(df['PLAYER_NAME'].unique())
    opponents = sorted(df['OPPONENT'].unique())
    
    selected_player = st.sidebar.selectbox(
        "Select Player",
        options=players,
        help="Choose the player you want to analyze"
    )
    
    # Get player's recent stats
    latest_stats = get_player_latest_stats(df, selected_player)
    
    if latest_stats is None:
        st.error(f"No data found for {selected_player}")
        return
    
    # Opponent selection
    selected_opponent = st.sidebar.selectbox(
        "Select Opponent",
        options=opponents,
        help="Choose the opponent team"
    )
    
    # Game context
    st.sidebar.subheader("📅 Game Context")
    is_home = st.sidebar.radio(
        "Home or Away?",
        options=["Home", "Away"],
        horizontal=True
    )
    is_home_value = 1 if is_home == "Home" else 0
    
    rest_days = st.sidebar.slider(
        "Days of Rest",
        min_value=0,
        max_value=7,
        value=1,
        help="Number of days since last game"
    )
    
    # Vegas lines
    st.sidebar.subheader("💰 Vegas Lines")
    vegas_pts = st.sidebar.number_input(
        "Points Line",
        min_value=0.0,
        max_value=60.0,
        value=20.5,
        step=0.5
    )
    
    vegas_reb = st.sidebar.number_input(
        "Rebounds Line",
        min_value=0.0,
        max_value=30.0,
        value=5.5,
        step=0.5
    )
    
    vegas_ast = st.sidebar.number_input(
        "Assists Line",
        min_value=0.0,
        max_value=20.0,
        value=3.5,
        step=0.5
    )
    
    edge_threshold = st.sidebar.slider(
        "Minimum Edge for Bet",
        min_value=1.0,
        max_value=5.0,
        value=2.0,
        step=0.5,
        help="Minimum prediction edge to recommend a bet"
    )
    
    # ==================== MAIN CONTENT ====================
    
    # Fetch REAL-TIME data from NBA API
    with st.spinner(f"🔄 Fetching real-time data for {selected_player}..."):
        pts_features_dict, reb_features_dict, ast_features_dict, recent_games = \
            get_realtime_prediction_features(
                selected_player, 
                selected_opponent, 
                is_home_value, 
                rest_days,
                season=None  # Auto-detect current season
            )
    
    # Check if data was fetched successfully
    if pts_features_dict is None or recent_games is None:
        st.error(f"❌ Could not fetch real-time data for {selected_player}")
        st.warning("**Possible reasons:**")
        st.markdown("""
        - Player name might not match exactly (try full name)
        - No recent games in current season
        - NBA API timeout or rate limit
        - Player might be inactive
        """)
        st.info("💡 **Tip:** Try selecting a different player or wait a moment and refresh")
        return
    
    # Show data freshness indicator
    if len(recent_games) > 0:
        last_game_date = recent_games.iloc[0]['GAME_DATE'].strftime('%Y-%m-%d')
        days_ago = (datetime.now() - recent_games.iloc[0]['GAME_DATE']).days
        
        st.success(f"✅ Using REAL-TIME data | Last game: {last_game_date} ({days_ago} days ago)")
    
    # Player Info Header
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 👤 {selected_player}")
        st.markdown(f"**vs {selected_opponent}** | **{is_home}** | **Rest: {rest_days} days**")
    
    with col2:
        if len(recent_games) > 0:
            st.metric("Last Game", f"{recent_games.iloc[0]['PTS']:.0f} pts")
    
    with col3:
        if len(recent_games) > 0:
            last_game_date = recent_games.iloc[0]['GAME_DATE'].strftime('%Y-%m-%d')
            st.markdown(f"**Last Game:** {last_game_date}")
    
    st.markdown("---")
    
    # Get opponent-specific stats from recent games
    opp_games = recent_games[recent_games['MATCHUP'].str.contains(selected_opponent)]
    
    # Create DataFrames for prediction
    pts_input = pd.DataFrame([pts_features_dict])
    reb_input = pd.DataFrame([reb_features_dict])
    ast_input = pd.DataFrame([ast_features_dict])
    
    # Make predictions
    pts_pred = models['PTS'].predict(pts_input)[0]
    reb_pred = models['REB'].predict(reb_input)[0]
    ast_pred = models['AST'].predict(ast_input)[0]
    
    # Get recommendations
    pts_rec, pts_msg, pts_edge, pts_type = get_betting_recommendation(pts_pred, vegas_pts, edge_threshold)
    reb_rec, reb_msg, reb_edge, reb_type = get_betting_recommendation(reb_pred, vegas_reb, edge_threshold)
    ast_rec, ast_msg, ast_edge, ast_type = get_betting_recommendation(ast_pred, vegas_ast, edge_threshold)
    
    # Display predictions in columns
    st.subheader("🎯 Predictions & Recommendations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        box_class = "over-bet" if pts_type == "over" else "under-bet" if pts_type == "under" else "no-bet"
        st.markdown(f"""
        <div class="pred-box {box_class}">
            <h3>🏀 POINTS</h3>
            <p style="font-size: 32px; font-weight: bold; margin: 10px 0;">{pts_pred:.1f}</p>
            <p>Vegas Line: <strong>{vegas_pts}</strong></p>
            <p style="font-size: 20px; margin-top: 10px;">{pts_rec}</p>
            <p>{pts_msg}</p>
        </div>
        """, unsafe_allow_html=True)
        
        confidence, edge_val = calculate_confidence_score(pts_pred, vegas_pts)
        st.markdown(f"**Confidence:** {confidence}")
    
    with col2:
        box_class = "over-bet" if reb_type == "over" else "under-bet" if reb_type == "under" else "no-bet"
        st.markdown(f"""
        <div class="pred-box {box_class}">
            <h3>📊 REBOUNDS</h3>
            <p style="font-size: 32px; font-weight: bold; margin: 10px 0;">{reb_pred:.1f}</p>
            <p>Vegas Line: <strong>{vegas_reb}</strong></p>
            <p style="font-size: 20px; margin-top: 10px;">{reb_rec}</p>
            <p>{reb_msg}</p>
        </div>
        """, unsafe_allow_html=True)
        
        confidence, edge_val = calculate_confidence_score(reb_pred, vegas_reb)
        st.markdown(f"**Confidence:** {confidence}")
    
    with col3:
        box_class = "over-bet" if ast_type == "over" else "under-bet" if ast_type == "under" else "no-bet"
        st.markdown(f"""
        <div class="pred-box {box_class}">
            <h3>🎯 ASSISTS</h3>
            <p style="font-size: 32px; font-weight: bold; margin: 10px 0;">{ast_pred:.1f}</p>
            <p>Vegas Line: <strong>{vegas_ast}</strong></p>
            <p style="font-size: 20px; margin-top: 10px;">{ast_rec}</p>
            <p>{ast_msg}</p>
        </div>
        """, unsafe_allow_html=True)
        
        confidence, edge_val = calculate_confidence_score(ast_pred, vegas_ast)
        st.markdown(f"**Confidence:** {confidence}")
    
    st.markdown("---")
    
    # Recent Performance
    st.subheader("📈 Recent Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Last 10 Games**")
        if len(recent_games) > 0:
            display_games = recent_games.head(10)[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST']].copy()
            display_games['GAME_DATE'] = display_games['GAME_DATE'].dt.strftime('%Y-%m-%d')
            st.dataframe(display_games, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("**Season Averages (Real-Time)**")
        st.metric("Points (Season)", f"{pts_features_dict['SEASON_AVG_PTS']:.1f}")
        st.metric("Points (L10)", f"{pts_features_dict['L10_PTS']:.1f}")
        st.metric("Points (L5)", f"{pts_features_dict['L5_PTS']:.1f}")
        st.metric("Minutes (L5)", f"{pts_features_dict['L5_MIN']:.1f}")
    
    # vs Opponent History
    if len(opp_games) > 0:
        st.markdown("---")
        st.subheader(f"🎯 vs {selected_opponent} History")
        
        opp_display = opp_games[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST']].head(5).copy()
        opp_display['GAME_DATE'] = opp_display['GAME_DATE'].dt.strftime('%Y-%m-%d')
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.dataframe(opp_display, use_container_width=True, hide_index=True)
        
        with col2:
            st.metric("Avg vs OPP (PTS)", f"{opp_games['PTS'].mean():.1f}")
            st.metric("Avg vs OPP (REB)", f"{opp_games['REB'].mean():.1f}")
            st.metric("Avg vs OPP (AST)", f"{opp_games['AST'].mean():.1f}")
    else:
        st.info(f"ℹ️ No recent matchup history vs {selected_opponent} in current dataset")
    
    # Feature Insights
    with st.expander("🔍 Feature Insights"):
        st.markdown("**Key Features Used in Prediction:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Points Model Features:**")
            st.json({k: f"{v:.2f}" if isinstance(v, (int, float)) else v for k, v in list(pts_features_dict.items())[:8]})
        
        with col2:
            st.markdown("**Rebounds Model Features:**")
            st.json({k: f"{v:.2f}" if isinstance(v, (int, float)) else v for k, v in list(reb_features_dict.items())[:8]})
        
        with col3:
            st.markdown("**Assists Model Features:**")
            st.json({k: f"{v:.2f}" if isinstance(v, (int, float)) else v for k, v in list(ast_features_dict.items())[:8]})
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: gray;'>
            <p>🏀 NBA Prop Predictor | Powered by XGBoost ML Models</p>
            <p style='font-size: 12px;'>Predictions are for informational purposes only. Always gamble responsibly.</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

