from __future__ import annotations

import pandas as pd

from config import RAW_LOGS_PATH, TRAINING_DATA_PATH, ensure_directories
from feature_pipeline import build_training_dataset


def process_data() -> None:
    ensure_directories()
    if not RAW_LOGS_PATH.exists():
        raise FileNotFoundError(f"Raw data not found at {RAW_LOGS_PATH}")

    raw_df = pd.read_csv(RAW_LOGS_PATH)
    training_df, feature_context = build_training_dataset(raw_df)
    training_df.to_csv(TRAINING_DATA_PATH, index=False)

    print(f"Saved {len(training_df)} rows to {TRAINING_DATA_PATH}")
    print(f"Feature columns: {len(feature_context.feature_columns)}")


if __name__ == "__main__":
    process_data()
