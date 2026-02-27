"""
Model 2 — Transaction Anomaly Detection

Algorithm : IsolationForest
Features  : amount deviation, time anomaly, frequency spike,
            category variance, rolling deviation
Outputs   : anomaly flag (-1 = anomaly), anomaly score
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

CONTAMINATION = 0.05
ALERT_THRESHOLD = -0.05


class AnomalyDetectionModel:
    """IsolationForest-based anomaly detector with StandardScaler preprocessing."""

    def __init__(self):
        self.scaler = StandardScaler()
        self.model = None
        self._fitted = False

    def train(self, X_df: pd.DataFrame):
        """Train on transaction features."""
        # Feature columns expected: amount_deviation, time_anomaly, frequency_spike, etc.
        X_scaled = self.scaler.fit_transform(X_df.fillna(0))

        self.model = IsolationForest(
            n_estimators=200,
            contamination=CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_scaled)
        self._fitted = True

        # Save artifacts
        joblib.dump(self.scaler, ARTIFACT_DIR / "scaler.pkl")
        joblib.dump(self.model, ARTIFACT_DIR / "isolation_forest.pkl")

        # Evaluation
        preds = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)
        n_anomalies = int(np.sum(preds == -1))

        return {
            "total_samples": len(preds),
            "anomalies_found": n_anomalies,
            "anomaly_rate": round(n_anomalies / len(preds), 4),
            "score_mean": float(np.mean(scores)),
            "score_std": float(np.std(scores)),
        }

    def load(self):
        """Load pre-trained artifacts."""
        self.scaler = joblib.load(ARTIFACT_DIR / "scaler.pkl")
        self.model = joblib.load(ARTIFACT_DIR / "isolation_forest.pkl")
        self._fitted = True

    def is_trained(self) -> bool:
        return (ARTIFACT_DIR / "isolation_forest.pkl").exists()

    def predict_single(self, feature_row: dict) -> dict:
        """Predict on a single transaction."""
        if not self._fitted:
            if self.is_trained():
                self.load()
            else:
                raise RuntimeError("Model not trained")

        # Expected features: amount_deviation, time_anomaly, frequency_spike, etc.
        features = [
            feature_row.get('amount_deviation', 0),
            feature_row.get('time_anomaly', 0),
            feature_row.get('frequency_spike', 0),
            feature_row.get('category_variance', 0),
            feature_row.get('rolling_deviation', 0),
        ]
        
        X_scaled = self.scaler.transform([features])
        pred = int(self.model.predict(X_scaled)[0])
        score = float(self.model.decision_function(X_scaled)[0])

        return {
            "is_anomalous": pred == -1,
            "anomaly_score": round(score, 4),
            "severity": _score_to_severity(score),
            "explanation": _explain_score(score),
        }

    def detect(self, user_id: int, transaction: dict, user_history: list) -> dict:
        """Detect anomaly with context from user history."""
        if not user_history or len(user_history) < 10:
            return {
                "is_anomalous": False,
                "anomaly_score": 0,
                "severity": "low",
                "reason": "Insufficient history"
            }

        # Calculate features
        amounts = [float(t['amount']) for t in user_history]
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)
        
        current_amount = float(transaction['amount'])
        z_score = abs((current_amount - mean_amount) / std_amount) if std_amount > 0 else 0

        # Build feature dict
        features = {
            'amount_deviation': z_score,
            'time_anomaly': 1 if transaction.get('hour', 12) < 6 or transaction.get('hour', 12) > 23 else 0,
            'frequency_spike': len([t for t in user_history[-20:] if t.get('merchant_id') == transaction.get('merchant_id')]) / 20,
            'category_variance': 0,
            'rolling_deviation': z_score,
        }

        return self.predict_single(features)


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
