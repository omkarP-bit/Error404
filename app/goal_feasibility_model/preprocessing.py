"""
ml_models/goal_feasibility_model/preprocessing.py
===================================================
Feature preprocessing for the 28-feature Goal Probability pipeline.
Scales all features to zero-mean unit-variance using StandardScaler.
Derived feature engineering (log, ratios) is handled upstream in
feature_builder.py; this module only scales.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler

from ml_models.goal_feasibility_model.feature_builder import FEATURE_NAMES

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


class GoalPreprocessor:
    def __init__(self):
        self.scaler  = StandardScaler()
        self._fitted = False

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        X = df[FEATURE_NAMES].fillna(0).values.astype(np.float32)
        X_scaled     = self.scaler.fit_transform(X)
        self._fitted = True
        return X_scaled

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("GoalPreprocessor not fitted — call fit_transform first.")
        X = df[FEATURE_NAMES].fillna(0).values.astype(np.float32)
        return self.scaler.transform(X)

    def transform_dict(self, feature_dict: dict) -> np.ndarray:
        """Transform a single feature dict into a (1, 28) scaled array."""
        row = pd.DataFrame([{k: feature_dict.get(k, 0.0) for k in FEATURE_NAMES}])
        return self.transform(row)

    def save(self):
        joblib.dump(self, ARTIFACT_DIR / "preprocessor.pkl")

    @classmethod
    def load(cls) -> "GoalPreprocessor":
        return joblib.load(ARTIFACT_DIR / "preprocessor.pkl")


if __name__ == "__main__":
    from ml_models.goal_feasibility_model.dataset_loader import load_for_goal_feasibility
    X, _ = load_for_goal_feasibility()
    prep  = GoalPreprocessor()
    Xs    = prep.fit_transform(X)
    print(f"Processed shape : {Xs.shape}")
    print(f"Feature columns : {FEATURE_NAMES[:5]} …")

