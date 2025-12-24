# 🏀 NBA Prop Bet Predictor

An advanced machine learning system for predicting NBA player prop bets using XGBoost models with 38+ engineered features.

## 🎯 Features

- **3 Specialized Models**: Separate models for Points, Rebounds, and Assists predictions
- **38+ Advanced Features**: Including rolling averages, opponent matchups, usage rates, pace metrics, and more
- **Interactive Dashboard**: Beautiful Streamlit UI for real-time predictions
- **Smart Recommendations**: AI-powered over/under betting suggestions with confidence scores
- **Historical Analysis**: View player performance trends and opponent-specific statistics

## 📊 Model Performance

| Prop | Test MAE | Within 3 Units | Within 5 Units |
|------|----------|----------------|----------------|
| Points | 4.98 | 38.1% | 60.4% |
| Rebounds | 2.11 | 76.4% | 93.1% |
| Assists | 1.49 | 88.6% | 97.8% |

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Scrape NBA Data (Optional - data already included)

```bash
python src/scraper.py
```

This will download game logs for 300+ active NBA players over 2 seasons.

### 3. Process Features

```bash
python src/features.py
```

Creates 38+ advanced features from raw game logs including:
- Rolling averages (L5, L10, season)
- Volatility metrics (standard deviation)
- Trend analysis (hot/cold streaks)
- Usage rates and efficiency metrics
- Opponent-specific matchup history
- Team and opponent pace metrics
- Rest days and back-to-back indicators

### 4. Train Models

```bash
python src/train.py
```

Trains 3 separate XGBoost models with:
- Time series cross-validation (5 folds)
- Optimized hyperparameters
- Feature importance analysis
- Comprehensive evaluation metrics
- Automatic model versioning

### 5. Launch Dashboard

```bash
streamlit run src/dashboard.py
```

Access at: **http://localhost:8501**

## 🎨 Dashboard Features

### Main Interface
- **Player Selection**: Dropdown with 400+ NBA players
- **Opponent Selection**: Choose from all NBA teams
- **Game Context**: Home/Away, Rest Days
- **Vegas Lines**: Input betting lines for PTS, REB, AST

### Predictions Display
- **AI Predictions**: ML-powered predictions for all three props
- **Betting Recommendations**: Clear OVER/UNDER signals with edge calculations
- **Confidence Scores**: Low/Medium/High confidence indicators
- **Visual Indicators**: Color-coded recommendation boxes

### Analytics
- **Recent Performance**: Last 10 games statistics
- **vs Opponent History**: Historical performance against specific teams
- **Season Averages**: L5, L10, and full season statistics
- **Feature Insights**: See exactly what features the model used

## 📁 Project Structure

```
backend/
├── src/
│   ├── scraper.py          # NBA data collection
│   ├── features.py         # Feature engineering (38+ features)
│   ├── train.py            # Model training with CV
│   ├── dashboard.py        # Streamlit app
│   └── inference.py        # CLI prediction tool
├── data/
│   ├── raw/
│   │   └── nba_logs.csv   # Raw game logs
│   └── processed/
│       └── training_data1.csv  # Engineered features
├── models/
│   ├── pts_model.json     # Points prediction model
│   ├── reb_model.json     # Rebounds prediction model
│   └── ast_model.json     # Assists prediction model
├── results/
│   ├── pts_results.json   # Points model metrics
│   ├── reb_results.json   # Rebounds model metrics
│   └── ast_results.json   # Assists model metrics
└── requirements.txt
```

## 🧠 Model Architecture

### XGBoost Hyperparameters
```python
{
    'n_estimators': 1000,
    'learning_rate': 0.05,
    'max_depth': 5,
    'min_child_weight': 3,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'gamma': 0.1,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0
}
```

### Feature Categories

1. **Core Stats** (15 features)
   - L5/L10 averages for PTS, REB, AST
   - Season averages
   - Standard deviations
   - Recent trends

2. **Usage & Minutes** (8 features)
   - L5/L10 minutes played
   - Usage rate (FGA per minute)
   - Free throw rate
   - Points per minute efficiency

3. **Game Context** (4 features)
   - Home/Away
   - Rest days
   - Back-to-back games
   - Well-rested indicator

4. **Shooting** (3 features)
   - Field goal percentage
   - 3-point percentage
   - 3-pointers made

5. **Matchup History** (3 features)
   - Career vs opponent averages
   - Opponent-specific trends

6. **Team Metrics** (4 features)
   - Opponent defensive strength
   - Team pace
   - Opponent pace
   - Win percentage

7. **Advanced** (2 features)
   - Plus/minus
   - Win percentage momentum

## 🎓 How It Works

### 1. Data Collection
Uses `nba_api` to scrape game-by-game logs for all active players across multiple seasons.

### 2. Feature Engineering
Transforms raw stats into predictive features:
- **Temporal Features**: Rolling windows prevent data leakage
- **Matchup Features**: Player performance vs specific opponents
- **Context Features**: Rest, home/away, team dynamics

### 3. Model Training
- **Time Series Split**: Respects temporal order (80/20 split)
- **Cross-Validation**: 5-fold time series CV for robust evaluation
- **Early Stopping**: Prevents overfitting
- **Regularization**: L1 and L2 penalties

### 4. Prediction & Betting Logic
```python
edge = model_prediction - vegas_line

if edge > 2.0:
    recommendation = "BET OVER"
elif edge < -2.0:
    recommendation = "BET UNDER"
else:
    recommendation = "NO BET"
```

## 📈 Usage Examples

### Dashboard
1. Select "LeBron James"
2. Select opponent "GSW"
3. Set context: Home game, 1 day rest
4. Input Vegas lines: 25.5 PTS, 7.5 REB, 6.5 AST
5. View predictions and betting recommendations

### Command Line
```bash
python src/inference.py
```

## 🔧 Advanced Configuration

### Adjust Betting Threshold
In `dashboard.py`:
```python
edge_threshold = st.sidebar.slider(
    "Minimum Edge for Bet",
    min_value=1.0,
    max_value=5.0,
    value=2.0  # Adjust this
)
```

### Retrain with New Data
```bash
# 1. Scrape latest games
python src/scraper.py

# 2. Regenerate features
python src/features.py

# 3. Retrain models
python src/train.py
```

### Hyperparameter Tuning
Uncomment the Optuna section in `train.py` for automated hyperparameter optimization.

## 📊 Model Evaluation Metrics

- **MAE**: Mean Absolute Error (primary metric)
- **RMSE**: Root Mean Squared Error
- **R²**: Coefficient of determination
- **Within X**: Percentage of predictions within X units of actual
- **CV Score**: Cross-validation performance

## ⚠️ Disclaimer

This tool is for **informational and educational purposes only**. 

- Past performance does not guarantee future results
- Always gamble responsibly
- Never bet more than you can afford to lose
- Sports betting involves risk

## 🚀 Future Enhancements

Potential improvements:
- [ ] Add injury status integration
- [ ] Implement quantile regression for probability estimates
- [ ] Add player role classification (starter vs bench)
- [ ] Include referee tendencies
- [ ] Add prop combinations (PTS + REB + AST)
- [ ] Real-time odds scraping
- [ ] Bankroll management calculator
- [ ] Historical bet tracking
- [ ] Mobile-responsive UI
- [ ] API endpoint for programmatic access

## 🤝 Contributing

Feel free to:
- Report bugs
- Suggest new features
- Improve model performance
- Add more prop types (steals, blocks, etc.)

## 📝 License

This project is for educational purposes. Use responsibly.

---

**Built with:** Python, XGBoost, Pandas, Streamlit, NBA API

**Last Updated:** December 2024

