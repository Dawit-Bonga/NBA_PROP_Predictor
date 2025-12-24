"""
Automated Pipeline: Scrape -> Train (if needed) -> Predict -> Pick Best Bets
"""

import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import subprocess

# Add src to path
sys.path.append(os.path.dirname(__file__))

# Configuration
DATA_DIR = '../data/'
MODELS_DIR = '../models/'
TRAINING_DATA = os.path.join(DATA_DIR, 'processed/training_data1.csv')
TODAYS_PROPS = os.path.join(DATA_DIR, 'todays_props.csv')
TOP_BETS_OUTPUT = os.path.join(DATA_DIR, 'top_bets.csv')
ANALYSIS_OUTPUT = os.path.join(DATA_DIR, 'analysis_results.csv')

# Thresholds
MODEL_MAX_AGE_DAYS = 7  # Retrain if model is older than this
MIN_EDGE_THRESHOLD = 3.0  # Minimum edge to consider a bet

def check_model_freshness():
    """Check if models need retraining"""
    print("\n🔍 Checking model freshness...")
    
    model_files = ['pts_model.json', 'reb_model.json', 'ast_model.json']
    needs_training = False
    
    for model_file in model_files:
        model_path = os.path.join(MODELS_DIR, model_file)
        
        if not os.path.exists(model_path):
            print(f"  ❌ Missing: {model_file}")
            needs_training = True
        else:
            # Check age
            mod_time = os.path.getmtime(model_path)
            age_days = (datetime.now().timestamp() - mod_time) / 86400
            
            if age_days > MODEL_MAX_AGE_DAYS:
                print(f"  ⚠️ Old: {model_file} ({age_days:.1f} days old)")
                needs_training = True
            else:
                print(f"  ✓ Fresh: {model_file} ({age_days:.1f} days old)")
    
    return needs_training

def scrape_prizepicks():
    """Run PrizePicks scraper"""
    print("\n" + "="*60)
    print("STEP 1: SCRAPING PRIZEPICKS")
    print("="*60)
    
    try:
        from prizepicks_scrapper import scrape_prizepicks as scraper
        df = scraper()
        
        if df is not None and len(df) > 0:
            print(f"✅ Scraped {len(df)} props")
            return True
        else:
            print("⚠️ No props scraped, but continuing with existing data...")
            return os.path.exists(TODAYS_PROPS)
            
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        print("⚠️ Continuing with existing data if available...")
        return os.path.exists(TODAYS_PROPS)

def train_models():
    """Run model training"""
    print("\n" + "="*60)
    print("STEP 2: TRAINING MODELS")
    print("="*60)
    
    try:
        # Check if training data exists
        if not os.path.exists(TRAINING_DATA):
            print(f"❌ Training data not found: {TRAINING_DATA}")
            print("ℹ️ Run scraper.py first to collect historical data")
            return False
        
        # Import and run training
        from train import train_all_models
        models, metrics = train_all_models()
        
        print("✅ Models trained successfully")
        return True
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return False

def generate_predictions():
    """Generate predictions using realtime_features"""
    print("\n" + "="*60)
    print("STEP 3: GENERATING PREDICTIONS")
    print("="*60)
    
    try:
        from realtime_features import run_realtime_prediction
        
        # This should create analysis_results.csv
        run_realtime_prediction()
        
        if os.path.exists(ANALYSIS_OUTPUT):
            print(f"✅ Predictions generated")
            return True
        else:
            print("⚠️ Predictions file not created")
            return False
            
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def pick_best_bets():
    """Analyze predictions and pick best bets"""
    print("\n" + "="*60)
    print("STEP 4: PICKING BEST BETS")
    print("="*60)
    
    try:
        # Load predictions
        if not os.path.exists(ANALYSIS_OUTPUT):
            print(f"❌ No predictions found: {ANALYSIS_OUTPUT}")
            return False
        
        df = pd.read_csv(ANALYSIS_OUTPUT)
        
        print(f"\n📊 Analyzing {len(df)} predictions...")
        
        # Calculate edge and confidence
        df['edge'] = df['prediction'] - df['line']
        df['abs_edge'] = df['edge'].abs()
        
        # Confidence levels based on edge magnitude
        def get_confidence(abs_edge):
            if abs_edge >= 5.0:
                return 'High'
            elif abs_edge >= 3.0:
                return 'Medium'
            else:
                return 'Low'
        
        df['confidence'] = df['abs_edge'].apply(get_confidence)
        
        # Recommendation
        def get_recommendation(edge):
            if edge > 0:
                return 'OVER'
            elif edge < 0:
                return 'UNDER'
            else:
                return 'PASS'
        
        df['recommendation'] = df['edge'].apply(get_recommendation)
        
        # Filter for bets with sufficient edge
        strong_bets = df[df['abs_edge'] >= MIN_EDGE_THRESHOLD].copy()
        
        # Sort by edge magnitude (highest first)
        strong_bets = strong_bets.sort_values('abs_edge', ascending=False)
        
        # Save top bets
        strong_bets.to_csv(TOP_BETS_OUTPUT, index=False)
        
        print(f"\n✅ Found {len(strong_bets)} bets with edge >= {MIN_EDGE_THRESHOLD}")
        
        if len(strong_bets) > 0:
            print(f"\n🏆 TOP BETS:")
            print("="*80)
            
            for idx, row in strong_bets.head(10).iterrows():
                edge_sign = '+' if row['edge'] > 0 else ''
                print(f"\n{row['player']} - {row['stat']}")
                print(f"  Line: {row['line']:.1f} | Prediction: {row['prediction']:.1f}")
                print(f"  Edge: {edge_sign}{row['edge']:.1f} | Recommendation: {row['recommendation']}")
                print(f"  Confidence: {row['confidence']}")
        else:
            print("\n⚠️ No strong bets found today")
        
        print(f"\n📁 Saved to: {TOP_BETS_OUTPUT}")
        return True
        
    except Exception as e:
        print(f"❌ Bet picking failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_full_pipeline(force_retrain=False):
    """Run the complete automated pipeline"""
    print("\n" + "#"*60)
    print("# 🏀 NBA PROP PROJECTOR - AUTOMATED PIPELINE")
    print("#"*60)
    print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Scrape PrizePicks
    if not scrape_prizepicks():
        print("\n❌ Pipeline failed: No props data available")
        return False
    
    # Step 2: Check if training is needed
    needs_training = force_retrain or check_model_freshness()
    
    if needs_training:
        print("\n🔄 Models need retraining...")
        if not train_models():
            print("\n⚠️ Training failed, using existing models...")
    else:
        print("\n✓ Models are fresh, skipping training")
    
    # Step 3: Generate predictions
    if not generate_predictions():
        print("\n❌ Pipeline failed: Could not generate predictions")
        return False
    
    # Step 4: Pick best bets
    if not pick_best_bets():
        print("\n❌ Pipeline failed: Could not pick bets")
        return False
    
    # Success!
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE!")
    print("="*60)
    print(f"\n📊 View your bets:")
    print(f"  Dashboard: streamlit run src/dashboard.py")
    print(f"  CSV: {TOP_BETS_OUTPUT}")
    print(f"\n⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NBA Prop Projector Automated Pipeline')
    parser.add_argument('--force-retrain', action='store_true', 
                       help='Force model retraining even if models are fresh')
    
    args = parser.parse_args()
    
    success = run_full_pipeline(force_retrain=args.force_retrain)
    sys.exit(0 if success else 1)