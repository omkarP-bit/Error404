"""
ml_models/anomaly_detection_model/preprocessing.py
====================================================
Preprocessing for Anomaly Detection — StandardScaler only.
Handles missing values and outlier clipping before scaling.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "amount", "amount_z_score", "daily_txn_freq",
    "category_variance", "is_odd_hour",
    "avg_spend_per_category", "spend_std_dev",
    "expense_volatility",
]


class AnomalyPreprocessor:
    def __init__(self):
        self.scaler  = StandardScaler()
        self._fitted = False

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        X = df[FEATURE_COLS].fillna(0).values.astype(float)
        # Clip extreme outliers before scaling (IQR × 5)
        for col_idx in range(X.shape[1]):
            q1, q3 = np.percentile(X[:, col_idx], [25, 75])
            iqr = q3 - q1
            lo, hi = q1 - 5 * iqr, q3 + 5 * iqr
            X[:, col_idx] = np.clip(X[:, col_idx], lo, hi)
        X_scaled = self.scaler.fit_transform(X)
        self._fitted = True
        return X_scaled

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Preprocessor not fitted.")
        X = df[FEATURE_COLS].fillna(0).values.astype(float)
        return self.scaler.transform(X)

    def transform_array(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Preprocessor not fitted.")
        return self.scaler.transform(X)

    def save(self):
        joblib.dump(self, ARTIFACT_DIR / "preprocessor.pkl")

    @classmethod
    def load(cls) -> "AnomalyPreprocessor":
        return joblib.load(ARTIFACT_DIR / "preprocessor.pkl")


if __name__ == "__main__":
    from ml_models.anomaly_detection_model.dataset_loader import load_for_anomaly_detection
    feat, _ = load_for_anomaly_detection()
    prep = AnomalyPreprocessor()
    X = prep.fit_transform(feat)
    print(f"Scaled shape: {X.shape}, mean≈0: {X.mean():.4f}, std≈1: {X.std():.4f}")
