# NBA Prop Projector - Quick Start Guide

## ✅ System Status: WORKING!

Your NBA prop projection system is now fully operational with PrizePicks integration!

## 🚀 How to Use

### Option 1: Run Everything Manually (RECOMMENDED)

Since PrizePicks has CAPTCHA in headless mode, run each step separately:

```bash
cd backend
source venv/bin/activate

# Step 1: Scrape PrizePicks (visible mode to handle CAPTCHA)
cd src
python prizepicks_scrapper.py --visible

# Step 2: Generate Predictions
python -c "from realtime_features import run_realtime_prediction; run_realtime_prediction()"

# Step 3: Pick Best Bets
python -c "
import pandas as pd

df = pd.read_csv('../data/analysis_results.csv')
df['edge'] = df['prediction'] - df['line']
df['abs_edge'] = df['edge'].abs()
df['confidence'] = df['abs_edge'].apply(lambda x: 'High' if x >= 5.0 else ('Medium' if x >= 3.0 else 'Low'))
df['recommendation'] = df['edge'].apply(lambda x: 'OVER' if x > 0 else 'UNDER')

strong_bets = df[df['abs_edge'] >= 3.0].sort_values('abs_edge', ascending=False)
strong_bets.to_csv('../data/top_bets.csv', index=False)

print(f'\n🎯 Found {len(strong_bets)} strong bets!')
for idx, row in strong_bets.head(10).iterrows():
    print(f\"{row['player']} - {row['stat']}: {row['recommendation']} (Edge: {row['edge']:.1f})\")
"

# Step 4: View Dashboard
streamlit run dashboard.py
```

### Option 2: Automated Pipeline (Headless - may fail with CAPTCHA)

```bash
cd backend
source venv/bin/activate
cd src
python automated_pipepline.py
```

## 📊 Today's Results

**Scraped:** 14 real props from PrizePicks  
**Predictions:** 12 generated  
**Top Bets:** 6 with edge ≥ 3.0

### 🏆 Best Bets:

1. **Giannis Antetokounmpo - Points UNDER 30.5** (Edge: -6.9, High Confidence)
2. **Chris Paul - Assists UNDER 8.5** (Edge: -5.7, High Confidence)
3. **LeBron James - Points UNDER 25.5** (Edge: -4.7, Medium Confidence)
4. **Kevin Durant - Points UNDER 27.5** (Edge: -4.5, Medium Confidence)
5. **Stephen Curry - Points OVER 28.5** (Edge: +3.7, Medium Confidence)
6. **Anthony Davis - Points UNDER 24.5** (Edge: -3.1, Medium Confidence)

## 📁 Output Files

- `data/todays_props.csv` - Props scraped from PrizePicks
- `data/analysis_results.csv` - All predictions with edges
- `data/top_bets.csv` - Best bets (edge ≥ 3.0)

## 🔧 Troubleshooting

### CAPTCHA Issues
- **Visible Mode**: Use `--visible` flag to manually solve CAPTCHA
- **Timing**: Try scraping at different times (less detection at off-peak hours)
- **Already Scraped**: If data exists, skip scraping and just run predictions

### Missing Players
Some players may not have predictions if:
- Not enough recent game history
- Player name doesn't match NBA API exactly
- Player is injured/inactive

### Model Retraining
Models auto-retrain if older than 7 days, or manually:
```bash
python train.py
```

## 🔄 Daily Workflow

1. **Morning**: Run scraper to get today's props
2. **Generate Predictions**: Run prediction script
3. **Review Bets**: Check `top_bets.csv` or dashboard
4. **Track Results**: Monitor and adjust thresholds

## 🎯 Configuration

Edit thresholds in `automated_pipepline.py`:
- `MIN_EDGE_THRESHOLD = 3.0` - Minimum edge for "strong bet"
- `MODEL_MAX_AGE_DAYS = 7` - When to retrain models

## 📈 Next Steps

1. Add opponent/game context fetching (currently uses placeholders)
2. Set up cron job for daily automation
3. Track bet results to calculate ROI
4. Fine-tune edge thresholds based on results

## ⚠️ Disclaimer

This is for educational purposes. Always do your own research and bet responsibly!

