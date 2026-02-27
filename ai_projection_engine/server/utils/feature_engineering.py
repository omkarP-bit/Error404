"""
ai_projection_engine/server/utils/feature_engineering.py
=========================================================
Computes all behavioural and spending features from raw transaction data.
Pure in-memory computation on pandas DataFrames — no ML model required.

Key features computed:
  • avg_daily_spend (overall + per-category)
  • mid_month_burn_rate
  • spend_volatility (std-dev of monthly totals)
  • discretionary_vs_fixed ratio
  • weekend_spending_multiplier
  • recurring_expense_count
  • ema_30d  (exponential moving average of last 30 days)
  • median_3m_spend  (3-month category median)
  • current_month_pace (projected full-month spend at current rate)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.core.constants import (
    DISCRETIONARY_EXPENSE_CATEGORIES,
    EMA_ALPHA,
    FIXED_EXPENSE_CATEGORIES,
)


# ── Data Loader ────────────────────────────────────────────────────────────────

def load_user_transactions(
    db: Session,
    user_id: int,
    lookback_months: int = 6,
) -> pd.DataFrame:
    """
    Load DEBIT transactions for *user_id* from the last *lookback_months* months.
    Returns an empty DataFrame if no data exists.
    """
    since = datetime.now() - timedelta(days=lookback_months * 31)

    query = text("""
        SELECT
            txn_id,
            user_id,
            amount,
            txn_type,
            category,
            txn_timestamp,
            is_recurring,
            balance_after_txn
        FROM transactions
        WHERE user_id          = :user_id
          AND lower(txn_type)  = 'debit'
          AND txn_timestamp   >= :since
        ORDER BY txn_timestamp
    """)

    rows = db.execute(query, {"user_id": user_id, "since": since}).fetchall()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        rows,
        columns=[
            "txn_id", "user_id", "amount", "txn_type",
            "category", "txn_timestamp", "is_recurring", "balance_after_txn",
        ],
    )

    df["txn_timestamp"] = pd.to_datetime(df["txn_timestamp"])
    df["date"] = df["txn_timestamp"].dt.date
    df["month_year"] = df["txn_timestamp"].dt.to_period("M").astype(str)
    df["day_of_week"] = df["txn_timestamp"].dt.dayofweek   # 0=Mon … 6=Sun
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    df["day_of_month"] = df["txn_timestamp"].dt.day
    df["amount"] = df["amount"].abs()
    df["category"] = df["category"].fillna("Uncategorised")

    return df


# ── Individual Feature Functions ───────────────────────────────────────────────

def compute_avg_daily_spend(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(df.groupby("date")["amount"].sum().mean())


def compute_category_avg_daily(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {}
    result: Dict[str, float] = {}
    for cat, grp in df.groupby("category", observed=True):
        daily = grp.groupby("date")["amount"].sum()
        result[str(cat)] = float(daily.mean())
    return result


def compute_mid_month_burn_rate(df: pd.DataFrame) -> float:
    """
    Ratio of first-half spend (days 1–15) vs second-half spend (days 16–31).
    > 1  → front-loaded spending pattern.
    """
    if df.empty:
        return 1.0
    first = df[df["day_of_month"] <= 15]["amount"].sum()
    second = df[df["day_of_month"] > 15]["amount"].sum()
    return float(first / second) if second > 0 else 1.0


def compute_spend_volatility(df: pd.DataFrame) -> float:
    """Std-dev of monthly total spend across available months."""
    if df.empty:
        return 0.0
    monthly = df.groupby("month_year")["amount"].sum()
    return float(monthly.std()) if len(monthly) > 1 else 0.0


def compute_category_volatility(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {}
    result: Dict[str, float] = {}
    for cat, grp in df.groupby("category", observed=True):
        monthly = grp.groupby("month_year")["amount"].sum()
        result[str(cat)] = float(monthly.std()) if len(monthly) > 1 else 0.0
    return result


def compute_discretionary_ratio(df: pd.DataFrame) -> Tuple[float, float]:
    """Returns (discretionary_ratio, fixed_ratio) of total spend."""
    if df.empty:
        return 0.5, 0.5
    total = df["amount"].sum()
    if total == 0:
        return 0.5, 0.5
    disc = df[df["category"].isin(DISCRETIONARY_EXPENSE_CATEGORIES)]["amount"].sum()
    fixed = df[df["category"].isin(FIXED_EXPENSE_CATEGORIES)]["amount"].sum()
    return float(disc / total), float(fixed / total)


def compute_weekend_multiplier(df: pd.DataFrame) -> float:
    """Average daily weekend spend ÷ average daily weekday spend."""
    if df.empty:
        return 1.0
    weekend_days = max(df[df["is_weekend"]]["date"].nunique(), 1)
    weekday_days = max(df[~df["is_weekend"]]["date"].nunique(), 1)
    avg_weekend = df[df["is_weekend"]]["amount"].sum() / weekend_days
    avg_weekday = df[~df["is_weekend"]]["amount"].sum() / weekday_days
    return float(avg_weekend / avg_weekday) if avg_weekday > 0 else 1.0


def compute_recurring_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int(df["is_recurring"].sum())


def compute_ema_30d(df: pd.DataFrame, alpha: float = EMA_ALPHA) -> Dict[str, float]:
    """Exponential moving average of daily spend per category (last 30 days)."""
    if df.empty:
        return {}
    cutoff = datetime.now() - timedelta(days=30)
    recent = df[df["txn_timestamp"] >= cutoff]
    if recent.empty:
        return {}
    result: Dict[str, float] = {}
    for cat, grp in recent.groupby("category", observed=True):
        daily = grp.groupby("date")["amount"].sum().sort_index()
        ema_val = float(daily.ewm(alpha=alpha, adjust=False).mean().iloc[-1])
        result[str(cat)] = ema_val
    return result


def compute_current_month_pace(
    df: pd.DataFrame, current_month: str
) -> Dict[str, float]:
    """
    Project full-month category spend from current pace:
      projected = (spend_so_far / days_elapsed) × days_in_month
    """
    now = datetime.now()
    days_elapsed = max(now.day, 1)

    # Days in current month
    if now.month == 12:
        days_in_month = 31
    else:
        import calendar
        days_in_month = calendar.monthrange(now.year, now.month)[1]

    cur = df[df["month_year"] == current_month]
    if cur.empty:
        return {}
    result: Dict[str, float] = {}
    for cat, grp in cur.groupby("category", observed=True):
        spend_so_far = grp["amount"].sum()
        result[str(cat)] = float((spend_so_far / days_elapsed) * days_in_month)
    return result


def compute_median_3m_spend(df: pd.DataFrame) -> Dict[str, float]:
    """Median monthly spend per category over the last 3 months."""
    if df.empty:
        return {}
    cutoff = datetime.now() - timedelta(days=93)
    recent = df[df["txn_timestamp"] >= cutoff]
    result: Dict[str, float] = {}
    for cat, grp in recent.groupby("category", observed=True):
        monthly = grp.groupby("month_year")["amount"].sum()
        result[str(cat)] = float(monthly.median())
    return result


# ── Master Feature Builder ─────────────────────────────────────────────────────

def build_all_features(
    db: Session,
    user_id: int,
    lookback_months: int = 6,
) -> dict:
    """
    Load transactions and return a single feature dict consumed by all services.
    If no data exists, returns a safe zero-valued dict with has_data=False.
    """
    df = load_user_transactions(db, user_id, lookback_months)
    current_month = datetime.now().strftime("%Y-%m")

    if df.empty:
        return {
            "df": df,
            "has_data": False,
            "data_days": 0,
            "avg_daily_spend": 0.0,
            "category_avg_daily": {},
            "mid_month_burn_rate": 1.0,
            "spend_volatility": 0.0,
            "category_volatility": {},
            "discretionary_ratio": 0.5,
            "fixed_ratio": 0.5,
            "weekend_multiplier": 1.0,
            "recurring_count": 0,
            "ema_30d": {},
            "current_month_pace": {},
            "median_3m_spend": {},
            "current_month": current_month,
        }

    data_days = int(
        (df["txn_timestamp"].max() - df["txn_timestamp"].min()).total_seconds()
        / 86_400
    ) + 1
    disc_ratio, fixed_ratio = compute_discretionary_ratio(df)

    return {
        "df": df,
        "has_data": True,
        "data_days": data_days,
        "avg_daily_spend": compute_avg_daily_spend(df),
        "category_avg_daily": compute_category_avg_daily(df),
        "mid_month_burn_rate": compute_mid_month_burn_rate(df),
        "spend_volatility": compute_spend_volatility(df),
        "category_volatility": compute_category_volatility(df),
        "discretionary_ratio": disc_ratio,
        "fixed_ratio": fixed_ratio,
        "weekend_multiplier": compute_weekend_multiplier(df),
        "recurring_count": compute_recurring_count(df),
        "ema_30d": compute_ema_30d(df),
        "current_month_pace": compute_current_month_pace(df, current_month),
        "median_3m_spend": compute_median_3m_spend(df),
        "current_month": current_month,
    }
