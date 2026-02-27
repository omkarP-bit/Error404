"""
ml_models/categorization_model/dataset_loader.py
=================================================
Independently loads finance_ml_dataset.csv for the Categorisation model.
No imports from other ML modules.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple

DATASET_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "finance_ml_dataset.csv"


def load_raw() -> pd.DataFrame:
    """Return the raw CSV as a DataFrame."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_PATH}. "
            "Run: python data/generate_dataset.py"
        )
    df = pd.read_csv(DATASET_PATH, parse_dates=["txn_timestamp"])
    return df


def load_for_training() -> Tuple[pd.DataFrame, pd.Series]:
    """
    Returns (X_features_df, y_labels_series) for the categorisation task.
    Uses 'category' as the label; corrects with 'user_corrected_label' where available.
    """
    df = load_raw()

    # Apply user corrections
    mask = df["user_corrected_label"].notna() & (df["user_corrected_label"] != "")
    df.loc[mask, "category"] = df.loc[mask, "user_corrected_label"]

    # Feature columns for text-based categorisation
    df["text_input"] = (
        df["cleaned_description"].fillna("") + " "
        + df["merchant_name"].fillna("")
    ).str.strip()

    X = df[["text_input", "amount", "txn_type", "payment_mode",
            "month", "day_of_week", "hour", "is_recurring"]]
    y = df["category"]

    return X, y


def load_merchant_cache() -> dict[str, str]:
    """Returns {merchant_name: category} lookup from dataset."""
    df = load_raw()
    return (
        df.groupby("merchant_name")["category"]
        .agg(lambda s: s.mode().iloc[0] if len(s) > 0 else "Uncategorized")
        .to_dict()
    )


if __name__ == "__main__":
    X, y = load_for_training()
    print(f"Loaded {len(X)} samples, {y.nunique()} categories")
    print(y.value_counts().head(10))
