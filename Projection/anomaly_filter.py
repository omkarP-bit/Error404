"""
ai_projection_engine/server/utils/anomaly_filter.py
====================================================
IQR-based outlier detection and down-weighting.

Rationale: rare high-spend events (travel, weddings, gadgets) would
skew monthly forecasts if treated equally with routine transactions.
Outliers are *not removed* — they are assigned a lower weight so that
the simulation still reflects them, but with reduced influence.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from config import settings


# ── Core Detection ─────────────────────────────────────────────────────────────

def detect_outliers_iqr(
    series: pd.Series,
    multiplier: float | None = None,
) -> pd.Series:
    """
    Returns a boolean mask (True = outlier) using Tukey's IQR fencing.

    fence_lower = Q1 − multiplier × IQR
    fence_upper = Q3 + multiplier × IQR

    A multiplier of 2.0 is less aggressive than the classic 1.5,
    keeping only genuinely extreme values as outliers.
    """
    if multiplier is None:
        multiplier = settings.ANOMALY_IQR_MULTIPLIER

    if len(series) < 4:
        return pd.Series(False, index=series.index)

    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr

    return (series < lower) | (series > upper)


# ── Weight Assignment ──────────────────────────────────────────────────────────

def apply_outlier_weights(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a *weight* column to the DataFrame.

    Normal transactions  → weight = 1.0
    Outlier transactions → weight = OUTLIER_WEIGHT (default 0.25)

    Outlier detection is done per-category so a ₹50 000 flight is
    not classified as normal just because some categories are expensive.
    """
    df = df.copy()
    df["weight"] = 1.0

    for cat, grp in df.groupby("category", observed=True):
        if len(grp) < 4:
            continue  # Too few samples for reliable IQR
        outlier_mask = detect_outliers_iqr(grp["amount"])
        df.loc[grp[outlier_mask].index, "weight"] = settings.OUTLIER_WEIGHT

    return df


# ── Weighted Aggregation ───────────────────────────────────────────────────────

def get_robust_category_spend(df: pd.DataFrame) -> Dict[str, float]:
    """
    Return weighted total spend per category for the DataFrame slice provided.
    Outliers contribute only OUTLIER_WEIGHT × their amount.
    """
    df = apply_outlier_weights(df)
    result: Dict[str, float] = {}
    for cat, grp in df.groupby("category", observed=True):
        result[str(cat)] = float((grp["amount"] * grp["weight"]).sum())
    return result


def filter_current_month_outliers(
    df: pd.DataFrame, current_month: str
) -> pd.DataFrame:
    """
    Convenience wrapper: returns the current-month slice with weights applied.
    """
    cur = df[df["month_year"] == current_month].copy()
    if cur.empty:
        return cur
    return apply_outlier_weights(cur)
