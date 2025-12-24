import xgboost as xgb
import pandas as pd
import numpy as np
import os

# --- CONFIG ---
MODEL_PATH = "../models/current/pts_model.json"

def load_model():
    # Check if model exists
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: Model not found at {MODEL_PATH}")
        print("Did you run train.py?")
        return None
    
    # Load the XGBoost Regressor
    model = xgb.XGBRegressor()
    model.load_model(MODEL_PATH)
    return model

def predict_player(model):
    print("\n--- 🏀 PLAYER PREDICTOR ---")
    print("Enter the stats to see the predicted point total.\n")
    
    # 1. Collect Inputs (Simulating an upcoming game)
    try:
        l5_pts = float(input("Last 5 Games Avg Points (L5_PTS): "))
        l10_pts = float(input("Last 10 Games Avg Points (L10_PTS): "))
        season_avg = float(input("Season Average Points (SEASON_AVG_PTS): "))
        l5_reb = float(input("Last 5 Games Avg Rebounds (L5_REB): "))
        l5_ast = float(input("Last 5 Games Avg Assists (L5_AST): "))
        rest_days = float(input("Days Rest (0, 1, 2, 3+): "))
        is_home = int(input("Home Game? (1 for Yes, 0 for No): "))
        
        # 2. Create DataFrame (Must match the training columns EXACTLY)
        input_data = pd.DataFrame({
            'L5_PTS': [l5_pts],
            'L10_PTS': [l10_pts],
            'SEASON_AVG_PTS': [season_avg],
            'L5_REB': [l5_reb],
            'L5_AST': [l5_ast],
            'REST_DAYS': [rest_days],
            'IS_HOME': [is_home]
        })
        
        # 3. Predict
        prediction = model.predict(input_data)[0]
        
        print("\n" + "="*30)
        print(f"🔮 PREDICTED POINTS: {prediction:.1f}")
        print("="*30)
        
        # 4. Optional: Compare to Vegas
        line = input("\n(Optional) Enter Vegas Line: ")
        if line:
            line = float(line)
            diff = prediction - line
            if diff > 3.0:
                print(f"🔥 Signal: BET OVER (+{diff:.1f} edge)")
            elif diff < -3.0:
                print(f"❄️ Signal: BET UNDER ({diff:.1f} edge)")
            else:
                print(f"⚠️ Signal: NO BET (Edge too small)")
                
    except ValueError:
        print("❌ Invalid input. Please enter numbers only.")

if __name__ == "__main__":
    trained_model = load_model()
    if trained_model:
        while True:
            predict_player(trained_model)
            if input("\nTry another? (y/n): ").lower() != 'y':
                break