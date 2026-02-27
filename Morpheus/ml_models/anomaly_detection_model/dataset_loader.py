"""
ml_models/anomaly_detection_model/dataset_loader.py
====================================================
Independently loads finance_ml_dataset.csv for anomaly detection.
No cross-model imports.
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
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_PATH}. "
            "Run: python data/generate_dataset.py"
        )
    df = pd.read_csv(DATASET_PATH, parse_dates=["txn_timestamp"])
    return df


def load_for_anomaly_detection() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (feature_df, meta_df).
    feature_df: numeric features for IsolationForest
    meta_df:    full rows for display / alert generation
    """
    df = load_raw()

    # Only debit transactions are candidates for anomaly detection
    df = df[df["txn_type"] == "debit"].copy()
    df = df.sort_values(["user_id", "txn_timestamp"]).reset_index(drop=True)

    # ── Rolling statistics per user (last 30 transactions) ───────────────────
    df["rolling_mean"]   = (
        df.groupby("user_id")["amount"]
        .transform(lambda s: s.rolling(30, min_periods=1).mean())
    )
    df["rolling_std"]    = (
        df.groupby("user_id")["amount"]
        .transform(lambda s: s.rolling(30, min_periods=1).std().fillna(1))
    )
    df["amount_z_score"] = (df["amount"] - df["rolling_mean"]) / df["rolling_std"].clip(lower=1)

    # ── Transaction frequency per user per day ────────────────────────────────
    df["date"]           = df["txn_timestamp"].dt.date
    daily_freq           = df.groupby(["user_id","date"])["txn_id"].transform("count")
    df["daily_txn_freq"] = daily_freq.fillna(1)

    # ── Category variance per user (encoded as nunique count) ─────────────────
    cat_var = df.groupby("user_id")["category"].transform("nunique")
    df["category_variance"] = cat_var.fillna(1)

    # ── Hour anomaly (flag off-hours: 0–5 AM) ─────────────────────────────────
    df["is_odd_hour"] = df["hour"].apply(lambda h: 1 if h < 5 else 0)

    feature_cols = [
        "amount", "amount_z_score", "daily_txn_freq",
        "category_variance", "is_odd_hour",
        "avg_spend_per_category", "spend_std_dev",
        "expense_volatility",
    ]

    feature_df = df[feature_cols].fillna(0)
    return feature_df, df


def load_from_db(db_session, user_id: int = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load LIVE transactions from SQLite DB and engineer the same 8 anomaly features.
    Returns (feature_df, meta_df) — same contract as load_for_anomaly_detection().
    """
    from ml_models.anomaly_detection_model.preprocessing import FEATURE_COLS

    # ── Pull from DB ──────────────────────────────────────────────────────────
    try:
        from app.models import Transaction
        from app.models.enums import TxnType
        q = db_session.query(Transaction).filter(Transaction.txn_type == TxnType.DEBIT)
        if user_id:
            q = q.filter(Transaction.user_id == user_id)
        rows = q.order_by(Transaction.user_id, Transaction.txn_timestamp).all()
    except Exception as exc:
        raise RuntimeError(f"DB query failed: {exc}")

    if not rows:
        return pd.DataFrame(columns=FEATURE_COLS), pd.DataFrame()

    data = [{
        "txn_id":          t.txn_id,
        "user_id":         t.user_id,
        "amount":          t.amount,
        "category":        t.category or "Uncategorized",
        "txn_timestamp":   t.txn_timestamp,
        "raw_description": t.raw_description or "",
        "payment_mode":    t.payment_mode or "",
        "merchant_id":     t.merchant_id,
    } for t in rows]

    df = pd.DataFrame(data)
    df["txn_timestamp"] = pd.to_datetime(df["txn_timestamp"])
    df = df.sort_values(["user_id", "txn_timestamp"]).reset_index(drop=True)

    # ── Rolling stats per user (30-txn window) ────────────────────────────────
    df["rolling_mean"] = (
        df.groupby("user_id")["amount"]
        .transform(lambda s: s.rolling(30, min_periods=1).mean())
    )
    df["rolling_std"] = (
        df.groupby("user_id")["amount"]
        .transform(lambda s: s.rolling(30, min_periods=1).std().fillna(1))
    )
    df["amount_z_score"] = (
        (df["amount"] - df["rolling_mean"]) / df["rolling_std"].clip(lower=1)
    )

    # ── Daily transaction frequency per user ─────────────────────────────────
    df["date"] = df["txn_timestamp"].dt.date
    df["daily_txn_freq"] = (
        df.groupby(["user_id", "date"])["txn_id"].transform("count").fillna(1)
    )

    # ── Category variance per user ────────────────────────────────────────────
    df["category_variance"] = (
        df.groupby("user_id")["category"].transform("nunique").fillna(1)
    )

    # ── Off-hours flag (midnight – 5 AM) ─────────────────────────────────────
    df["is_odd_hour"] = df["txn_timestamp"].dt.hour.apply(lambda h: 1 if h < 5 else 0)

    # ── Per-user aggregate stats ──────────────────────────────────────────────
    agg = df.groupby("user_id")["amount"].agg(["mean", "std"]).reset_index()
    agg.columns = ["user_id", "_mean", "_std"]
    agg["avg_spend_per_category"] = agg["_mean"]
    agg["spend_std_dev"]          = agg["_std"].fillna(0)
    agg["expense_volatility"]     = (agg["_std"] / agg["_mean"].clip(lower=1)).fillna(0)
    df = df.merge(
        agg[["user_id", "avg_spend_per_category", "spend_std_dev", "expense_volatility"]],
        on="user_id", how="left",
    )

    feature_df = df[FEATURE_COLS].fillna(0)
    return feature_df, df


if __name__ == "__main__":
    feat, meta = load_for_anomaly_detection()
    print(f"Feature shape: {feat.shape}")
    print(feat.describe())
