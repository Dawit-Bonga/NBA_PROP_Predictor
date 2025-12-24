import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
import numpy as np
import json
from datetime import datetime
import os

# ==================== CONFIGURATION ====================
DATA_PATH = "../data/processed/training_data1.csv"
MODELS_DIR = "../models/"
RESULTS_DIR = "../results/"

# Create directories if they don't exist
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Training configuration
TRAIN_SPLIT = 0.8
RANDOM_STATE = 42

# Feature sets for different targets
POINTS_FEATURES = [
    # Core points stats
    'L5_PTS', 'L10_PTS', 'SEASON_AVG_PTS', 'L10_PTS_STD', 'RECENT_TREND_PTS',
    
    # Context
    'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
    
    # Minutes & Usage
    'L5_MIN', 'L10_MIN', 'USAGE_RATE', 'FT_RATE', 'PPM_L5', 'PPM_L10',
    
    # Shooting
    'L5_FG_PCT', 'L5_FG3_PCT', 'L5_FG3M',
    
    # Supporting stats
    'L5_REB', 'L5_AST',
    
    # Matchup
    'VS_OPP_AVG_PTS', 'OPP_DEF_STRENGTH_PTS', 'OPP_PACE', 'TEAM_PACE',
    
    # Advanced
    'L5_WIN_PCT', 'L5_PLUS_MINUS'
]

REBOUNDS_FEATURES = [
    # Core rebounds stats
    'L5_REB', 'L10_REB', 'L10_REB_STD', 'RECENT_TREND_REB',
    
    # Context
    'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
    
    # Minutes & Usage
    'L5_MIN', 'L10_MIN', 'USAGE_RATE',
    
    # Supporting stats
    'L5_PTS', 'L5_AST',
    
    # Matchup
    'VS_OPP_AVG_REB', 'OPP_DEF_STRENGTH_REB', 'OPP_PACE', 'TEAM_PACE',
    
    # Advanced
    'L5_WIN_PCT', 'L5_PLUS_MINUS'
]

ASSISTS_FEATURES = [
    # Core assists stats
    'L5_AST', 'L10_AST', 'L10_AST_STD', 'RECENT_TREND_AST',
    
    # Context
    'IS_HOME', 'REST_DAYS', 'IS_BACK_TO_BACK', 'IS_RESTED',
    
    # Minutes & Usage
    'L5_MIN', 'L10_MIN', 'USAGE_RATE',
    
    # Supporting stats
    'L5_PTS', 'L5_REB',
    
    # Matchup
    'VS_OPP_AVG_AST', 'OPP_DEF_STRENGTH_AST', 'OPP_PACE', 'TEAM_PACE',
    
    # Advanced
    'L5_WIN_PCT', 'L5_PLUS_MINUS'
]

# Best hyperparameters (tune these with optuna if you want even better results)
BEST_PARAMS = {
    'n_estimators': 1000,
    'learning_rate': 0.05,
    'max_depth': 5,
    'min_child_weight': 3,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'gamma': 0.1,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'random_state': RANDOM_STATE
}


def evaluate_model(y_true, y_pred, model_name="Model"):
    """Comprehensive model evaluation"""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    # Accuracy within X points (crucial for props!)
    within_1 = np.mean(np.abs(y_pred - y_true) < 1) * 100
    within_2 = np.mean(np.abs(y_pred - y_true) < 2) * 100
    within_3 = np.mean(np.abs(y_pred - y_true) < 3) * 100
    within_5 = np.mean(np.abs(y_pred - y_true) < 5) * 100
    
    print(f"\n{'='*50}")
    print(f"📊 {model_name} - EVALUATION RESULTS")
    print(f"{'='*50}")
    print(f"  MAE (Mean Absolute Error):  {mae:.3f}")
    print(f"  RMSE (Root Mean Squared):   {rmse:.3f}")
    print(f"  R² Score:                   {r2:.3f}")
    print(f"\n  Accuracy Thresholds:")
    print(f"    Within 1 unit:  {within_1:.1f}%")
    print(f"    Within 2 units: {within_2:.1f}%")
    print(f"    Within 3 units: {within_3:.1f}%")
    print(f"    Within 5 units: {within_5:.1f}%")
    print(f"{'='*50}\n")
    
    return {
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'within_1': within_1,
        'within_2': within_2,
        'within_3': within_3,
        'within_5': within_5
    }


def plot_feature_importance(model, feature_names, target_name, top_n=15):
    """Display top N most important features"""
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n🔍 Top {top_n} Features for {target_name}:")
    print("-" * 50)
    for idx, row in importance_df.head(top_n).iterrows():
        bar_length = int(row['importance'] * 50)
        bar = '█' * bar_length
        print(f"  {row['feature']:25s} {bar} {row['importance']:.4f}")
    print("-" * 50)
    
    return importance_df


def cross_validate_model(X, y, features, params, n_splits=5):
    """Time Series Cross-Validation"""
    print(f"\n🔄 Running {n_splits}-Fold Time Series Cross-Validation...")
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_train_cv, X_val_cv = X.iloc[train_idx], X.iloc[val_idx]
        y_train_cv, y_val_cv = y.iloc[train_idx], y.iloc[val_idx]
        
        model = xgb.XGBRegressor(**params)
        model.fit(
            X_train_cv, y_train_cv,
            eval_set=[(X_val_cv, y_val_cv)],
            verbose=False
        )
        
        preds = model.predict(X_val_cv)
        mae = mean_absolute_error(y_val_cv, preds)
        cv_scores.append(mae)
        print(f"  Fold {fold}: MAE = {mae:.3f}")
    
    mean_cv_score = np.mean(cv_scores)
    std_cv_score = np.std(cv_scores)
    print(f"\n  Average CV MAE: {mean_cv_score:.3f} (+/- {std_cv_score:.3f})")
    
    return mean_cv_score, std_cv_score


def train_prop_model(df, target_name, features, params):
    """Train a model for a specific prop (PTS, REB, AST)"""
    print(f"\n{'#'*60}")
    print(f"# Training Model for: {target_name}")
    print(f"{'#'*60}")
    
    # Sort by date
    df = df.sort_values('GAME_DATE').reset_index(drop=True)
    
    # Prepare data
    X = df[features].copy()
    y = df[target_name].copy()
    
    # Train/Test split (chronological)
    split_index = int(len(df) * TRAIN_SPLIT)
    
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
    
    train_end = df.iloc[split_index]['GAME_DATE'].date()
    test_start = df.iloc[split_index]['GAME_DATE'].date()
    
    print(f"\n📅 Data Split:")
    print(f"  Training:   {len(X_train):,} samples (up to {train_end})")
    print(f"  Testing:    {len(X_test):,} samples (from {test_start})")
    print(f"  Features:   {len(features)}")
    
    # Cross-validation on training set
    cv_mae, cv_std = cross_validate_model(X_train, y_train, features, params, n_splits=5)
    
    # Train final model
    print(f"\n🚀 Training Final Model...")
    model = xgb.XGBRegressor(**params)
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False
    )
    
    # Predictions
    train_preds = model.predict(X_train)
    test_preds = model.predict(X_test)
    
    # Evaluate
    print(f"\n📈 Training Set Performance:")
    train_metrics = evaluate_model(y_train, train_preds, f"{target_name} (Train)")
    
    print(f"\n🎯 Test Set Performance:")
    test_metrics = evaluate_model(y_test, test_preds, f"{target_name} (Test)")
    
    # Feature importance
    importance_df = plot_feature_importance(model, features, target_name, top_n=15)
    
    # Save model
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_path = os.path.join(MODELS_DIR, f"{target_name.lower()}_model.json")
    versioned_path = os.path.join(MODELS_DIR, f"{target_name.lower()}_model_v{timestamp}.json")
    
    # Use get_booster() for compatibility
    model.get_booster().save_model(model_path)
    model.get_booster().save_model(versioned_path)
    
    print(f"\n💾 Model Saved:")
    print(f"  Primary: {model_path}")
    print(f"  Backup:  {versioned_path}")
    
    # Save metrics and metadata
    results = {
        'target': target_name,
        'timestamp': timestamp,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': features,
        'num_features': len(features),
        'hyperparameters': params,
        'cv_mae': cv_mae,
        'cv_std': cv_std,
        'train_metrics': train_metrics,
        'test_metrics': test_metrics,
        'feature_importance': importance_df.to_dict('records')
    }
    
    results_path = os.path.join(RESULTS_DIR, f"{target_name.lower()}_results.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"  Results:  {results_path}")
    
    return model, test_metrics


def train_all_models():
    """Train models for all prop types"""
    print("\n" + "="*60)
    print("🏀 NBA PROP PROJECTOR - MODEL TRAINING")
    print("="*60)
    
    # Load data
    print(f"\n📂 Loading data from: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    
    print(f"  Total samples: {len(df):,}")
    print(f"  Date range: {df['GAME_DATE'].min().date()} to {df['GAME_DATE'].max().date()}")
    print(f"  Unique players: {df['PLAYER_NAME'].nunique()}")
    
    # Train models for each prop type
    models = {}
    all_metrics = {}
    
    # 1. Points Model
    pts_model, pts_metrics = train_prop_model(df, 'PTS', POINTS_FEATURES, BEST_PARAMS)
    models['PTS'] = pts_model
    all_metrics['PTS'] = pts_metrics
    
    # 2. Rebounds Model
    reb_model, reb_metrics = train_prop_model(df, 'REB', REBOUNDS_FEATURES, BEST_PARAMS)
    models['REB'] = reb_model
    all_metrics['REB'] = reb_metrics
    
    # 3. Assists Model
    ast_model, ast_metrics = train_prop_model(df, 'AST', ASSISTS_FEATURES, BEST_PARAMS)
    models['AST'] = ast_model
    all_metrics['AST'] = ast_metrics
    
    # Summary
    print("\n" + "="*60)
    print("📊 TRAINING COMPLETE - SUMMARY")
    print("="*60)
    
    summary_df = pd.DataFrame({
        'Prop': ['Points', 'Rebounds', 'Assists'],
        'Target': ['PTS', 'REB', 'AST'],
        'Test MAE': [
            all_metrics['PTS']['mae'],
            all_metrics['REB']['mae'],
            all_metrics['AST']['mae']
        ],
        'Test R²': [
            all_metrics['PTS']['r2'],
            all_metrics['REB']['r2'],
            all_metrics['AST']['r2']
        ],
        'Within 3': [
            f"{all_metrics['PTS']['within_3']:.1f}%",
            f"{all_metrics['REB']['within_3']:.1f}%",
            f"{all_metrics['AST']['within_3']:.1f}%"
        ]
    })
    
    print(summary_df.to_string(index=False))
    print("="*60)
    print(f"\n✅ All models trained and saved to: {MODELS_DIR}")
    print(f"✅ Results saved to: {RESULTS_DIR}")
    print("\n🎯 Ready for inference! Use inference.py to make predictions.\n")
    
    return models, all_metrics


if __name__ == "__main__":
    train_all_models()