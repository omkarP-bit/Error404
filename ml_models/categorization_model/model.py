"""
ml_models/categorization_model/model.py
========================================
Model 1 — Transaction Categorisation

Pipeline:
  1. Merchant cache lookup  (exact match, DB-derived)
  2. User-specific mapping  (DB category_mappings)
  3. TF-IDF + LinearSVC     (ML fallback)
  4. SentenceTransformer     (semantic fallback if SVC confidence < threshold)
  5. Confidence scoring
  6. Below 0.85 → user confirmation flag

Features:
  • OCR receipt ingestion (via ocr_service)
  • PDF bank statement ingestion (via pdf_service)
  • Feedback loop → updates CATEGORY_MAPPINGS
  • Audit logging
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from ml_models.categorization_model.dataset_loader import load_for_training, load_merchant_cache
from ml_models.categorization_model.preprocessing import CategorizationPreprocessor

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

CONFIDENCE_THRESHOLD = 0.85


class CategorizationModel:
    """
    Full categorisation pipeline with merchant lookup, ML, and semantic fallback.
    """

    def __init__(self):
        self.preprocessor: Optional[CategorizationPreprocessor] = None
        self.classifier   = None        # CalibratedClassifierCV(LinearSVC)
        self.label_classes: list[str]  = []
        self.merchant_cache: dict[str, str] = {}
        self._sentence_model = None     # lazy-load to save startup time
        self._fitted = False

    # ── SentenceTransformer (lazy) ────────────────────────────────────────────
    def _get_sentence_model(self):
        if self._sentence_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self._sentence_model = None
        return self._sentence_model

    # ── Training ─────────────────────────────────────────────────────────────
    def train(self, verbose: bool = True) -> dict:
        """Train on finance_ml_dataset.csv and persist artifacts."""
        print("📚  Loading dataset …")
        X_df, y = load_for_training()
        self.merchant_cache = load_merchant_cache()

        print("🔧  Preprocessing …")
        self.preprocessor = CategorizationPreprocessor()
        X_feat = self.preprocessor.fit_transform(X_df)

        X_train, X_test, y_train, y_test = train_test_split(
            X_feat, y, test_size=0.2, random_state=42, stratify=y
        )

        print("🤖  Training CalibratedLinearSVC …")
        base_svc = LinearSVC(max_iter=2000, C=1.0)
        self.classifier = CalibratedClassifierCV(base_svc, cv=3)
        self.classifier.fit(X_train, y_train)
        self.label_classes = list(self.classifier.classes_)

        y_pred = self.classifier.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True)

        if verbose:
            print(classification_report(y_test, y_pred))

        # Save artifacts
        self.preprocessor.save()
        joblib.dump(self.classifier,    ARTIFACT_DIR / "classifier.pkl")
        joblib.dump(self.label_classes, ARTIFACT_DIR / "label_classes.pkl")
        joblib.dump(self.merchant_cache, ARTIFACT_DIR / "merchant_cache.pkl")
        self._fitted = True
        print("✅  Model saved to artifacts/")
        return report

    # ── Loading ───────────────────────────────────────────────────────────────
    def load(self):
        """Load pre-trained artifacts from disk."""
        self.preprocessor    = CategorizationPreprocessor.load()
        self.classifier      = joblib.load(ARTIFACT_DIR / "classifier.pkl")
        self.label_classes   = joblib.load(ARTIFACT_DIR / "label_classes.pkl")
        self.merchant_cache  = joblib.load(ARTIFACT_DIR / "merchant_cache.pkl")
        self._fitted = True

    def is_trained(self) -> bool:
        return (ARTIFACT_DIR / "classifier.pkl").exists()

    # ── Prediction ────────────────────────────────────────────────────────────
    def predict_single(
        self,
        text_input: str,
        amount: float,
        merchant_name: str,
        txn_type: str = "debit",
        payment_mode: str = "UPI",
        month: int = 1,
        day_of_week: int = 0,
        hour: int = 12,
        is_recurring: int = 0,
        user_mappings: Optional[dict[str, str]] = None,
    ) -> dict:
        """
        Returns {
            category, subcategory, confidence, needs_confirmation,
            pipeline_step, probabilities
        }
        """
        if not self._fitted:
            if self.is_trained():
                self.load()
            else:
                raise RuntimeError("Model not trained. Run train() first.")

        # ── Step 1: User-specific mapping override ────────────────────────
        if user_mappings and merchant_name in user_mappings:
            return {
                "category":          user_mappings[merchant_name],
                "subcategory":       "",
                "confidence":        1.0,
                "needs_confirmation": False,
                "pipeline_step":     "user_mapping",
                "probabilities":     {},
            }

        # ── Step 2: Merchant cache lookup ─────────────────────────────────
        if merchant_name in self.merchant_cache:
            cached_cat = self.merchant_cache[merchant_name]
            return {
                "category":          cached_cat,
                "subcategory":       "",
                "confidence":        0.96,
                "needs_confirmation": False,
                "pipeline_step":     "merchant_cache",
                "probabilities":     {},
            }

        # ── Step 3: TF-IDF + LinearSVC ────────────────────────────────────
        row = pd.DataFrame([{
            "text_input":   text_input,
            "amount":       amount,
            "txn_type":     txn_type,
            "payment_mode": payment_mode,
            "month":        month,
            "day_of_week":  day_of_week,
            "hour":         hour,
            "is_recurring": is_recurring,
        }])
        X_feat = self.preprocessor.transform(row)
        proba  = self.classifier.predict_proba(X_feat)[0]
        top_idx  = int(np.argmax(proba))
        category = self.label_classes[top_idx]
        confidence = float(proba[top_idx])

        if confidence >= CONFIDENCE_THRESHOLD:
            return {
                "category":          category,
                "subcategory":       "",
                "confidence":        round(confidence, 4),
                "needs_confirmation": False,
                "pipeline_step":     "ml_svc",
                "probabilities":     dict(zip(self.label_classes, proba.tolist())),
            }

        # ── Step 4: SentenceTransformer semantic fallback ─────────────────
        st_model = self._get_sentence_model()
        if st_model is not None:
            category_labels = self.label_classes
            query_emb  = st_model.encode([text_input + " " + merchant_name])
            label_embs = st_model.encode(category_labels)
            sims = np.dot(query_emb, label_embs.T)[0]
            sims = (sims + 1) / 2   # normalise cosine → [0, 1]
            best_idx = int(np.argmax(sims))
            sem_conf = float(sims[best_idx])
            if sem_conf > confidence:
                category   = category_labels[best_idx]
                confidence = round(sem_conf, 4)

        return {
            "category":          category,
            "subcategory":       "",
            "confidence":        round(confidence, 4),
            "needs_confirmation": confidence < CONFIDENCE_THRESHOLD,
            "pipeline_step":     "semantic_fallback" if st_model else "ml_svc_low",
            "probabilities":     dict(zip(self.label_classes, proba.tolist())),
        }

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run prediction on every row in a DataFrame."""
        results = []
        for _, row in df.iterrows():
            res = self.predict_single(
                text_input   = str(row.get("cleaned_description", row.get("raw_description", ""))),
                amount       = float(row.get("amount", 0)),
                merchant_name= str(row.get("merchant_name", "")),
                txn_type     = str(row.get("txn_type", "debit")),
                payment_mode = str(row.get("payment_mode", "UPI")),
                month        = int(row.get("month", 1)),
                day_of_week  = int(row.get("day_of_week", 0)),
                hour         = int(row.get("hour", 12)),
                is_recurring = int(row.get("is_recurring", 0)),
            )
            results.append(res)
        return pd.DataFrame(results)


# ── CLI training entry-point ──────────────────────────────────────────────────
if __name__ == "__main__":
    model = CategorizationModel()
    model.train(verbose=True)
