"""
Model 1 — Transaction Categorisation

Pipeline:
  1. Merchant cache lookup  (exact match, DB-derived)
  2. User-specific mapping  (DB category_mappings)
  3. TF-IDF + LinearSVC     (ML fallback)
  4. SentenceTransformer     (semantic fallback if SVC confidence < threshold)
  5. Confidence scoring
  6. Below 0.85 → user confirmation flag
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

CONFIDENCE_THRESHOLD = 0.85


class CategorizationModel:
    """Full categorisation pipeline with merchant lookup, ML, and semantic fallback."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self.scaler = StandardScaler()
        self.classifier = None
        self.label_classes = []
        self.merchant_cache = {}
        self._sentence_model = None
        self._fitted = False

    def _get_sentence_model(self):
        if self._sentence_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self._sentence_model = None
        return self._sentence_model

    def train(self, X_df: pd.DataFrame, y: pd.Series, merchant_cache: dict = None):
        """Train on transaction data."""
        if merchant_cache:
            self.merchant_cache = merchant_cache

        # Extract text features
        text_features = self.vectorizer.fit_transform(X_df['text_input'])
        
        # Numerical features
        num_features = X_df[['amount', 'month', 'day_of_week', 'hour']].fillna(0).values
        num_features = self.scaler.fit_transform(num_features)
        
        # Combine features
        from scipy.sparse import hstack
        X_combined = hstack([text_features, num_features])

        # Train calibrated SVC
        base_svc = LinearSVC(max_iter=2000, C=1.0, random_state=42)
        self.classifier = CalibratedClassifierCV(base_svc, cv=3)
        self.classifier.fit(X_combined, y)
        self.label_classes = list(self.classifier.classes_)
        self._fitted = True

        # Save artifacts
        joblib.dump(self.vectorizer, ARTIFACT_DIR / "vectorizer.pkl")
        joblib.dump(self.scaler, ARTIFACT_DIR / "scaler.pkl")
        joblib.dump(self.classifier, ARTIFACT_DIR / "classifier.pkl")
        joblib.dump(self.label_classes, ARTIFACT_DIR / "label_classes.pkl")
        joblib.dump(self.merchant_cache, ARTIFACT_DIR / "merchant_cache.pkl")

    def load(self):
        """Load pre-trained artifacts."""
        self.vectorizer = joblib.load(ARTIFACT_DIR / "vectorizer.pkl")
        self.scaler = joblib.load(ARTIFACT_DIR / "scaler.pkl")
        self.classifier = joblib.load(ARTIFACT_DIR / "classifier.pkl")
        self.label_classes = joblib.load(ARTIFACT_DIR / "label_classes.pkl")
        self.merchant_cache = joblib.load(ARTIFACT_DIR / "merchant_cache.pkl")
        self._fitted = True

    def is_trained(self) -> bool:
        return (ARTIFACT_DIR / "classifier.pkl").exists()

    def predict_single(
        self,
        text_input: str,
        amount: float,
        merchant_name: str,
        month: int = 1,
        day_of_week: int = 0,
        hour: int = 12,
        user_mappings: Optional[dict] = None,
    ) -> dict:
        """Predict category for a single transaction."""
        if not self._fitted:
            if self.is_trained():
                self.load()
            else:
                raise RuntimeError("Model not trained")

        # Step 1: User-specific mapping
        if user_mappings and merchant_name in user_mappings:
            return {
                "category": user_mappings[merchant_name],
                "subcategory": "",
                "confidence": 1.0,
                "needs_confirmation": False,
                "pipeline_step": "user_mapping",
            }

        # Step 2: Merchant cache
        if merchant_name in self.merchant_cache:
            return {
                "category": self.merchant_cache[merchant_name],
                "subcategory": "",
                "confidence": 0.96,
                "needs_confirmation": False,
                "pipeline_step": "merchant_cache",
            }

        # Step 3: TF-IDF + LinearSVC
        text_feat = self.vectorizer.transform([text_input])
        num_feat = self.scaler.transform([[amount, month, day_of_week, hour]])
        
        from scipy.sparse import hstack
        X_combined = hstack([text_feat, num_feat])
        
        proba = self.classifier.predict_proba(X_combined)[0]
        top_idx = int(np.argmax(proba))
        category = self.label_classes[top_idx]
        confidence = float(proba[top_idx])

        if confidence >= CONFIDENCE_THRESHOLD:
            return {
                "category": category,
                "subcategory": "",
                "confidence": round(confidence, 4),
                "needs_confirmation": False,
                "pipeline_step": "ml_svc",
            }

        # Step 4: SentenceTransformer fallback
        st_model = self._get_sentence_model()
        if st_model is not None:
            query_emb = st_model.encode([text_input + " " + merchant_name])
            label_embs = st_model.encode(self.label_classes)
            sims = np.dot(query_emb, label_embs.T)[0]
            sims = (sims + 1) / 2
            best_idx = int(np.argmax(sims))
            sem_conf = float(sims[best_idx])
            if sem_conf > confidence:
                category = self.label_classes[best_idx]
                confidence = round(sem_conf, 4)

        return {
            "category": category,
            "subcategory": "",
            "confidence": round(confidence, 4),
            "needs_confirmation": confidence < CONFIDENCE_THRESHOLD,
            "pipeline_step": "semantic_fallback" if st_model else "ml_svc_low",
        }
