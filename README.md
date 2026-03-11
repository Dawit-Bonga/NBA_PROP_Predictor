# NBA Prop Predictor

This project collects NBA player game logs, builds engineered features, trains XGBoost models for points, rebounds, and assists, and exposes predictions through a Streamlit dashboard.

The repository had several overlapping markdown files. This README is now the main source of project documentation.

## What the Project Does

- Scrapes historical NBA game logs with `nba_api`
- Builds rolling and matchup-based features from those logs
- Trains separate models for `PTS`, `REB`, and `AST`
- Scrapes current props from PrizePicks
- Generates prediction outputs and bet recommendations
- Provides a local dashboard for exploring predictions

## Repository Layout

```text
backend/
  data/
    raw/          Raw scraped game logs
    processed/    Engineered training data
    predictions/  Current props and prediction outputs
  docs/           Empty or removable project notes
  models/
    current/      Current model artifacts
    archived/     Older saved model versions
  results/        Evaluation outputs
  src/
    scraper.py                Historical NBA data collection
    features.py               Feature engineering
    train.py                  Model training
    realtime_features.py      Real-time feature generation and prediction
    prizepicks_scrapper.py    PrizePicks prop scraping
    dashboard.py              Streamlit dashboard
    automated_pipepline.py    End-to-end runner
    inference.py              Older CLI inference script
```

## Setup

From the project root:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Typical Workflow

### 1. Collect historical data

```bash
cd backend
python3 src/scraper.py
```

This writes raw game logs to `backend/data/raw/nba_logs.csv`.

### 2. Build training features

```bash
cd backend
python3 src/features.py
```

This creates `backend/data/processed/training_data.csv`.

### 3. Train models

```bash
cd backend
python3 src/train.py
```

This trains the current predictor code on the processed dataset.

### 4. Scrape current props

```bash
cd backend
python3 src/prizepicks_scrapper.py
```

This writes the current board to `backend/data/predictions/todays_props.csv`.

### 5. Generate prediction outputs

```bash
cd backend
python3 src/automated_pipepline.py
```

This runs the automated flow that checks models, generates predictions, and writes ranked bets to `backend/data/predictions/top_bets.csv`.

### 6. Launch the dashboard

```bash
cd backend
streamlit run src/dashboard.py
```

## Main Files

- `backend/src/scraper.py`: pulls historical game logs from `nba_api`
- `backend/src/features.py`: builds rolling averages, volatility, rest, pace, and opponent archetype features
- `backend/src/train.py`: trains one model set per target stat
- `backend/src/realtime_features.py`: fetches recent player games and prepares prediction inputs
- `backend/src/prizepicks_scrapper.py`: scrapes live props from PrizePicks
- `backend/src/dashboard.py`: interactive local UI

## Current Limitations

- The codebase is still in progress and some modules are not fully aligned
- Training features and real-time inference features are not yet fully standardized
- The automated pipeline expects saved model artifacts and consistent function names
- Some scripts use placeholder game context when real schedule data is not available

If you keep working on this project, fixing feature parity between training and inference should be the top priority.

## Notes

- Use this project for learning and experimentation, not as a production betting system
- Model outputs depend heavily on data freshness and feature quality
