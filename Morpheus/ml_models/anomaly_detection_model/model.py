"""
ml_models/anomaly_detection_model/model.py
============================================
Model 2 — Transaction Anomaly Detection

Algorithm : IsolationForest
Features  : amount deviation, time anomaly, frequency spike,
            category variance, rolling deviation
Outputs   : anomaly flag (-1 = anomaly), anomaly score
Side-effect: inserts ALERTS into the database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import cross_val_score

from ml_models.anomaly_detection_model.dataset_loader import load_for_anomaly_detection
from ml_models.anomaly_detection_model.preprocessing import AnomalyPreprocessor

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

CONTAMINATION   = 0.05      # ~5% of transactions expected to be anomalies
ALERT_THRESHOLD = -0.05     # IsolationForest score below this → alert


class AnomalyDetectionModel:
    """
    IsolationForest-based anomaly detector with StandardScaler preprocessing.
    """

    def __init__(self):
        self.preprocessor: Optional[AnomalyPreprocessor] = None
        self.model: Optional[IsolationForest] = None
        self._fitted = False

    def train(self, verbose: bool = True) -> dict:
        """Train on finance_ml_dataset.csv and persist artifacts."""
        print("📚  Loading dataset for anomaly detection …")
        feat_df, meta_df = load_for_anomaly_detection()

        print("🔧  Preprocessing …")
        self.preprocessor = AnomalyPreprocessor()
        X_scaled = self.preprocessor.fit_transform(feat_df)

        print("🌲  Training IsolationForest …")
        self.model = IsolationForest(
            n_estimators=200,
            contamination=CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_scaled)
        self._fitted = True

        # Evaluate: count anomalies found
        preds  = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)
        n_anomalies = int(np.sum(preds == -1))
        anomaly_rate = n_anomalies / len(preds)

        report = {
            "total_samples": len(preds),
            "anomalies_found": n_anomalies,
            "anomaly_rate": round(anomaly_rate, 4),
            "score_mean": float(np.mean(scores)),
            "score_std":  float(np.std(scores)),
        }

        if verbose:
            print(f"   Total samples  : {report['total_samples']:,}")
            print(f"   Anomalies found: {report['anomalies_found']} ({report['anomaly_rate']:.1%})")

        # Save artifacts
        self.preprocessor.save()
        joblib.dump(self.model, ARTIFACT_DIR / "isolation_forest.pkl")
        self._fitted = True
        print("✅  Anomaly model saved")
        return report

    def load(self):
        self.preprocessor = AnomalyPreprocessor.load()
        self.model        = joblib.load(ARTIFACT_DIR / "isolation_forest.pkl")
        self._fitted = True

    def is_trained(self) -> bool:
        return (ARTIFACT_DIR / "isolation_forest.pkl").exists()

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Input df must have the anomaly feature columns.
        Returns df with columns: is_anomaly, anomaly_score, severity.
        """
        if not self._fitted:
            if self.is_trained():
                self.load()
            else:
                raise RuntimeError("Model not trained.")

        from ml_models.anomaly_detection_model.preprocessing import FEATURE_COLS
        feat_df  = df[FEATURE_COLS].fillna(0)
        X_scaled = self.preprocessor.transform(feat_df)

        preds  = self.model.predict(X_scaled)            # 1 = normal, -1 = anomaly
        scores = self.model.decision_function(X_scaled)  # lower = more anomalous

        result = df.copy()
        result["is_anomaly"]    = (preds == -1).astype(int)
        result["anomaly_score"] = scores.round(4)
        result["severity"]      = result["anomaly_score"].apply(_score_to_severity)
        return result

    def predict_single(self, feature_row: dict) -> dict:
        """
        Predict on a single transaction dict with feature keys.
        """
        if not self._fitted:
            if self.is_trained():
                self.load()
            else:
                raise RuntimeError("Model not trained.")

        from ml_models.anomaly_detection_model.preprocessing import FEATURE_COLS
        row_df   = pd.DataFrame([feature_row])[FEATURE_COLS].fillna(0)
        X_scaled = self.preprocessor.transform(row_df)
        pred     = int(self.model.predict(X_scaled)[0])
        score    = float(self.model.decision_function(X_scaled)[0])

        return {
            "is_anomaly":   pred == -1,
            "anomaly_score": round(score, 4),
            "severity":     _score_to_severity(score),
            "explanation":  _explain_score(score),
        }


def _score_to_severity(score: float) -> str:
    if score < -0.15:
        return "critical"
    elif score < -0.08:
        return "high"
    elif score < -0.03:
        return "medium"
    return "low"


def _explain_score(score: float) -> str:
    if score < -0.15:
        return "Highly unusual transaction pattern — immediate review recommended."
    elif score < -0.08:
        return "Significant deviation from normal spending behaviour."
    elif score < -0.03:
        return "Mildly unusual — monitor for recurring pattern."
    return "Normal transaction."


if __name__ == "__main__":
    m = AnomalyDetectionModel()
    m.train(verbose=True)
