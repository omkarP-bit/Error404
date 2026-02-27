"""
ml_models/categorization_model/preprocessing.py
================================================
Feature engineering pipeline for the Categorisation model.
Independently processes text + structured features.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import hstack, csr_matrix
from typing import Tuple, Optional
import joblib
from pathlib import Path

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# ── Text Cleaning ─────────────────────────────────────────────────────────────

_NOISE_PATTERNS = re.compile(
    r"(\b\d{4,}\b|[*#@!&]|(?:pvt|ltd|india|online|pay|app)\b)",
    flags=re.IGNORECASE,
)

def clean_text(text: str) -> str:
    """Lowercase, strip noise tokens, normalise whitespace."""
    text = str(text).lower()
    text = _NOISE_PATTERNS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Preprocessing Pipeline ────────────────────────────────────────────────────

class CategorizationPreprocessor:
    """
    Transforms raw transaction features into a combined sparse feature matrix.
    Handles:
      • TF-IDF on text_input
      • Label-encoded categoricals
      • Scaled numeric features
    """

    def __init__(self):
        self.tfidf     = TfidfVectorizer(max_features=3000, ngram_range=(1, 2))
        self.scaler    = StandardScaler()
        self.txn_enc   = LabelEncoder()
        self.pay_enc   = LabelEncoder()
        self._fitted   = False

    def _encode_categoricals(self, df: pd.DataFrame, fit: bool) -> np.ndarray:
        txn_vals = df["txn_type"].fillna("debit").astype(str)
        pay_vals = df["payment_mode"].fillna("UPI").astype(str)

        if fit:
            self.txn_enc.fit(txn_vals)
            self.pay_enc.fit(pay_vals)

        txn_enc = self._safe_transform(self.txn_enc, txn_vals).reshape(-1, 1)
        pay_enc = self._safe_transform(self.pay_enc, pay_vals).reshape(-1, 1)
        return np.hstack([txn_enc, pay_enc])

    @staticmethod
    def _safe_transform(encoder: LabelEncoder, values: pd.Series) -> np.ndarray:
        """Handle unseen labels gracefully."""
        known = set(encoder.classes_)
        mapped = values.apply(lambda v: v if v in known else encoder.classes_[0])
        return encoder.transform(mapped)

    def _numeric_features(self, df: pd.DataFrame) -> np.ndarray:
        cols = ["amount", "month", "day_of_week", "hour", "is_recurring"]
        arr  = df[cols].fillna(0).values.astype(float)
        return arr

    def fit_transform(self, df: pd.DataFrame) -> csr_matrix:
        text_clean = df["text_input"].fillna("").apply(clean_text)
        tfidf_mat  = self.tfidf.fit_transform(text_clean)

        cat_arr    = self._encode_categoricals(df, fit=True)
        num_arr    = self._numeric_features(df)
        num_scaled = self.scaler.fit_transform(num_arr)

        cat_sparse  = csr_matrix(cat_arr)
        num_sparse  = csr_matrix(num_scaled)
        self._fitted = True
        return hstack([tfidf_mat, cat_sparse, num_sparse])

    def transform(self, df: pd.DataFrame) -> csr_matrix:
        if not self._fitted:
            raise RuntimeError("Preprocessor not fitted. Call fit_transform first.")
        text_clean = df["text_input"].fillna("").apply(clean_text)
        tfidf_mat  = self.tfidf.transform(text_clean)

        cat_arr    = self._encode_categoricals(df, fit=False)
        num_arr    = self._numeric_features(df)
        num_scaled = self.scaler.transform(num_arr)

        cat_sparse  = csr_matrix(cat_arr)
        num_sparse  = csr_matrix(num_scaled)
        return hstack([tfidf_mat, cat_sparse, num_sparse])

    def save(self):
        joblib.dump(self, ARTIFACT_DIR / "preprocessor.pkl")

    @classmethod
    def load(cls) -> "CategorizationPreprocessor":
        path = ARTIFACT_DIR / "preprocessor.pkl"
        if not path.exists():
            raise FileNotFoundError(f"Preprocessor artifact not found at {path}")
        return joblib.load(path)


if __name__ == "__main__":
    from ml_models.categorization_model.dataset_loader import load_for_training
    X, y = load_for_training()
    prep = CategorizationPreprocessor()
    X_feat = prep.fit_transform(X)
    print(f"Feature matrix shape: {X_feat.shape}")
