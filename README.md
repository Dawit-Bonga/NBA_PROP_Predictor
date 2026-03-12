# NBA Prop Predictor

This project collects NBA player game logs, builds a shared feature set, trains XGBoost models for points, rebounds, and assists, saves model artifacts with metadata, and serves predictions through a local pipeline and a temporary Streamlit dashboard.

The backend now uses one canonical contract for training and inference so the models, prediction service, and UI all consume the same feature schema.

## What the Project Does

- Scrapes historical NBA game logs with `nba_api`
- Builds rolling, volatility, trend, pace, rest, and opponent archetype features
- Trains separate `PTS`, `REB`, and `AST` models with saved metadata and evaluation outputs
- Scrapes current props from PrizePicks
- Generates prediction outputs and ranked bet candidates through a shared prediction service
- Provides a local Streamlit dashboard as a thin client over the backend

## Repository Layout

```text
backend/
  data/
    raw/          Raw scraped game logs
    processed/    Engineered training data
    predictions/  Current props and prediction outputs
  models/
    current/      Current model artifacts and metadata
    archived/     Archived model snapshots
  results/        Evaluation JSON outputs
  src/
    scraper.py                Historical NBA data collection
    feature_pipeline.py       Shared feature engineering
    features.py               Process raw logs into training data
    train.py                  Train models and save artifacts
    prediction_service.py     Shared inference service
    pipeline.py               Local prediction pipeline
    api.py                    FastAPI service layer
    prizepicks_scrapper.py    PrizePicks prop scraping
    dashboard.py              Temporary Streamlit client
    run_pipeline.py           Main local prediction entry point
    run_api.py                API server entry point
    automated_pipepline.py    Compatibility wrapper
  tests/
    test_contracts.py         Contract and artifact tests
    test_api_contract.py      API import contract
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

This:

- rebuilds the processed training set from raw logs
- trains `mean`, `lower`, and `upper` models for each target
- saves model artifacts and metadata under `backend/models/current/`
- writes evaluation outputs under `backend/results/`

### 4. Scrape current props

```bash
cd backend
python3 src/prizepicks_scrapper.py
```

This writes the current board to `backend/data/predictions/todays_props.csv`.

### 5. Generate prediction outputs

```bash
cd backend
python3 src/run_pipeline.py
```

This loads the saved artifacts, infers same-day game context, scores the current props file, and writes:

- `backend/data/predictions/analysis_results.csv`
- `backend/data/predictions/top_bets.csv`

### 6. Launch the dashboard

```bash
cd backend
streamlit run src/dashboard.py
```

### 7. Start the API foundation

```bash
cd backend
python3 src/run_api.py
```

Endpoints currently included:

- `GET /health`
- `GET /config`
- `GET /players`
- `GET /models`
- `GET /props`
- `GET /predictions`
- `GET /bets`
- `POST /predict`
- `POST /player-insights`
- `POST /pipeline/refresh`

### 8. Start the React frontend

```bash
cd frontend
npm install
npm run dev
```

Optional environment override:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Main Files

- `backend/src/scraper.py`: pulls historical game logs from `nba_api`
- `backend/src/feature_pipeline.py`: shared training and inference feature logic
- `backend/src/train.py`: trains one model bundle per target stat and persists metadata
- `backend/src/prediction_service.py`: validates schema and generates live predictions
- `backend/src/prizepicks_scrapper.py`: scrapes live props from PrizePicks
- `backend/src/pipeline.py`: generates ranked prediction outputs from today's props
- `backend/src/dashboard.py`: interactive local UI over the shared backend
- `backend/src/api.py`: FastAPI wrapper for the shared prediction backend
- `frontend/`: React + TypeScript client scaffold for replacing Streamlit

## Artifact Contract

Each trained target now has:

- model files for `mean`, `lower`, and `upper`
- a metadata JSON file with:
  - feature columns
  - generation timestamp
  - evaluation summary
- a shared context JSON file used by live inference for:
  - player archetypes
  - opponent pace priors
  - opponent defense-vs-archetype priors
  - default feature values

## Current Limitations

- The project is still local-first and not yet a deployed backend service
- PrizePicks scraping is brittle by nature because it depends on site structure
- Same-day matchup inference depends on NBA schedule data being available
- Streamlit is temporary and will be replaced later by a React + FastAPI frontend

## Tests

Run the contract tests with:

```bash
cd backend/src
../venv/bin/python -m unittest discover -s ../tests -p 'test_*.py' -v
```

## Notes

- Use this project for learning and experimentation, not as a production betting system
- Model outputs depend heavily on data freshness and feature quality
