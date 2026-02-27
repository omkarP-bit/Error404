"""
ml_models/anomaly_detection_model/inference.py
===============================================
High-level inference interface for Anomaly Detection.
Inserts ALERTS into the database for detected anomalies.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from typing import Optional, List
import pandas as pd

from ml_models.anomaly_detection_model.model import AnomalyDetectionModel
from ml_models.anomaly_detection_model.dataset_loader import load_for_anomaly_detection

_model: Optional[AnomalyDetectionModel] = None


def _get_model() -> AnomalyDetectionModel:
    global _model
    if _model is None:
        _model = AnomalyDetectionModel()
        if _model.is_trained():
            _model.load()
        else:
            print("⚠️  Anomaly model not trained — training now …")
            _model.train(verbose=False)
    return _model


def detect_anomaly(feature_row: dict) -> dict:
    """Detect anomaly in a single transaction feature dict."""
    return _get_model().predict_single(feature_row)


def scan_dataset_anomalies() -> pd.DataFrame:
    """
    Run anomaly detection on the full dataset.
    Returns DataFrame with is_anomaly, anomaly_score, severity columns.
    """
    feat_df, meta_df = load_for_anomaly_detection()
    model = _get_model()
    result = model.predict_batch(meta_df)
    return result


def scan_and_insert_alerts(db_session=None) -> List[dict]:
    """
    Scan dataset, find anomalies, optionally insert ALERTS into the database.
    Returns list of alert dicts.
    """
    result_df = scan_dataset_anomalies()
    anomalies = result_df[result_df["is_anomaly"] == 1]

    alerts = []
    for _, row in anomalies.iterrows():
        alert = {
            "txn_id":        int(row.get("txn_id", 0)),
            "user_id":       int(row.get("user_id", 0)),
            "alert_type":    "anomaly",
            "severity":      row["severity"],
            "anomaly_score": float(row["anomaly_score"]),
            "amount":        float(row.get("amount", 0)),
            "category":      str(row.get("category", "")),
            "message":       (
                f"Anomalous transaction of ₹{row.get('amount',0):.0f} "
                f"in {row.get('category','unknown')} "
                f"(score: {row['anomaly_score']:.3f})"
            ),
        }
        alerts.append(alert)

        # Insert into DB if session provided
        if db_session is not None:
            try:
                from app.models import Alert, AlertType, AlertSeverity, AlertStatus
                from datetime import datetime
                db_alert = Alert(
                    user_id    = alert["user_id"],
                    txn_id     = alert["txn_id"] or None,
                    alert_type = AlertType.ANOMALY,
                    severity   = AlertSeverity(alert["severity"]),
                    status     = AlertStatus.OPEN,
                    message    = alert["message"],
                    created_at = datetime.utcnow(),
                )
                db_session.add(db_alert)
            except Exception:
                pass  # Graceful degradation if DB not available

    if db_session is not None:
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

    return alerts


def retrain_model() -> dict:
    global _model
    _model = AnomalyDetectionModel()
    return _model.train(verbose=True)


def scan_user_from_db(db_session, user_id: int = None) -> list:
    """
    Scan LIVE DB transactions for anomalies using the trained IsolationForest.

    Steps:
      1. Pull debit transactions from SQLite (for user_id, or all users)
      2. Engineer the same 8 features as the CSV pipeline
      3. Run predict_batch() → anomaly score + severity per row
      4. Clear stale OPEN anomaly alerts for the user, insert fresh ones
      5. Return ALL transactions (normal + anomaly) with scores attached

    Returns list of dicts with keys:
      txn_id, user_id, amount, category, txn_timestamp, raw_description,
      is_anomaly, anomaly_score, severity, message
    """
    from ml_models.anomaly_detection_model.dataset_loader import load_from_db

    _, meta_df = load_from_db(db_session, user_id=user_id)
    if meta_df.empty:
        return []

    model     = _get_model()
    result_df = model.predict_batch(meta_df)   # adds is_anomaly, anomaly_score, severity

    # ── Clear stale open alerts before inserting fresh ones ──────────────────
    if db_session is not None:
        try:
            from app.models import Alert, AlertType, AlertStatus
            q = db_session.query(Alert).filter(
                Alert.alert_type == AlertType.ANOMALY,
                Alert.status     == AlertStatus.OPEN,
            )
            if user_id:
                q = q.filter(Alert.user_id == user_id)
            q.delete(synchronize_session=False)
            db_session.flush()
        except Exception:
            pass

    results = []
    for _, row in result_df.iterrows():
        is_anom  = bool(row["is_anomaly"])
        score    = float(row["anomaly_score"])
        severity = str(row["severity"])
        msg      = _build_alert_message(row)

        item = {
            "txn_id":          int(row.get("txn_id", 0)),
            "user_id":         int(row.get("user_id", 0)),
            "amount":          float(row.get("amount", 0)),
            "category":        str(row.get("category", "")),
            "txn_timestamp":   str(row.get("txn_timestamp", "")),
            "raw_description": str(row.get("raw_description", "")),
            "is_anomaly":      is_anom,
            "anomaly_score":   round(score, 4),
            "severity":        severity,
            "message":         msg,
        }
        results.append(item)

        if is_anom and db_session is not None:
            try:
                from app.models import Alert, AlertType, AlertSeverity, AlertStatus
                from datetime import datetime
                db_session.add(Alert(
                    user_id    = item["user_id"],
                    txn_id     = item["txn_id"] or None,
                    alert_type = AlertType.ANOMALY,
                    severity   = AlertSeverity(severity),
                    status     = AlertStatus.OPEN,
                    message    = msg,
                    created_at = datetime.utcnow(),
                ))
            except Exception:
                pass

    if db_session is not None:
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

    return results


def _build_alert_message(row) -> str:
    z = row.get("amount_z_score", 0)
    return (
        f"Anomalous txn of {row.get('amount', 0):.0f} "
        f"in {row.get('category', 'unknown')} "
        f"(score: {row['anomaly_score']:.3f}, z-score: {float(z):.2f}x above normal)"
    )


if __name__ == "__main__":
    result = scan_dataset_anomalies()
    anomalies = result[result["is_anomaly"] == 1]
    print(f"Found {len(anomalies)} anomalies out of {len(result)} transactions")
    print(anomalies[["txn_id","user_id","amount","category","anomaly_score","severity"]].head(10))
