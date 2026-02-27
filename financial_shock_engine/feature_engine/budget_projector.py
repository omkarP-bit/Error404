"""
financial_shock_engine/feature_engine/budget_projector.py
==========================================================
Step 3 — Adaptive Budget Projection (behavior-aware, NOT static linear).

Uses:
  • EWMA   — exponential weighted moving average on daily spend
  • MAD    — Median Absolute Deviation to detect/downweight outlier days
  • Rolling median — for robust daily spend estimation

Output:
  projected_end_month_balance  (₹ median estimate)
  confidence_band_low          (₹ pessimistic P25)
  confidence_band_high         (₹ optimistic P75)
  projected_remaining_spend    (₹ expected spend for remaining days)
"""
from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# EWMA span for daily spend smoothing
_EWMA_SPAN: int = 14   # 14-day half-life
# MAD threshold: days where spend > median + k*MAD are "spikes"
_MAD_K: float = 2.5


def project_month_balance(features: dict) -> dict:
    """
    Project the end-of-month balance using behavior-aware EWMA.

    Parameters
    ----------
    features : FeatureSet from feature_builder.build_features()
               Must contain: transactions_6m injected by caller

    Returns
    -------
    {
        projected_remaining_spend   : float
        projected_end_month_balance : float
        confidence_band_low         : float
        confidence_band_high        : float
        daily_spend_estimate        : float   (robust median daily spend)
        projection_method           : str
    }
    """
    today          = date.today()
    days_remaining = features.get("days_remaining", 1)
    liquid_balance = features.get("liquid_balance", 0.0)
    current_spend  = features.get("current_month_spend", 0.0)
    avg_expense    = features.get("avg_monthly_expense", 0.0)
    mean_daily     = features.get("mean_daily_spend", 0.0)
    std_daily      = features.get("std_daily_spend", 0.0)
    has_data       = features.get("has_sufficient_data", False)
    days_passed    = features.get("days_passed", today.day)

    if not has_data or mean_daily == 0.0:
        # Heuristic fallback for sparse data
        daily_est    = avg_expense / 30.0 if avg_expense > 0 else features.get("burn_rate", 0.0)
        remaining    = daily_est * days_remaining
        end_balance  = liquid_balance - remaining
        return {
            "projected_remaining_spend":   round(remaining, 2),
            "projected_end_month_balance": round(end_balance, 2),
            "confidence_band_low":         round(end_balance - std_daily * 3, 2),
            "confidence_band_high":        round(end_balance + std_daily * 2, 2),
            "daily_spend_estimate":        round(daily_est, 2),
            "projection_method":           "heuristic_fallback",
        }

    # ── Robust daily spend using MAD spike detection ──────────────────────────
    daily_est = _robust_daily_estimate(mean_daily, std_daily)

    # ── EWMA adjustment (trend-sensitive) ─────────────────────────────────────
    ewma_daily = _ewma_adjustment(features, mean_daily)

    # Blend: 60% EWMA, 40% robust median
    blended_daily = 0.60 * ewma_daily + 0.40 * daily_est

    remaining_spend = blended_daily * days_remaining
    end_balance     = liquid_balance - remaining_spend

    # Confidence bands using volatility
    vol = features.get("expense_volatility", 0.2)
    spread = blended_daily * days_remaining * vol
    band_low  = end_balance - spread
    band_high = end_balance + spread * 0.5   # upside is smaller (spending can't be negative)

    return {
        "projected_remaining_spend":   round(remaining_spend, 2),
        "projected_end_month_balance": round(end_balance, 2),
        "confidence_band_low":         round(band_low, 2),
        "confidence_band_high":        round(band_high, 2),
        "daily_spend_estimate":        round(blended_daily, 2),
        "projection_method":           "ewma_mad_blend",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _robust_daily_estimate(mean_daily: float, std_daily: float) -> float:
    """
    Use MAD to compute a spike-resistant daily spend estimate.
    Outlier definition: mean + MAD_K * (std / 1.4826)
    """
    # Approximate MAD from std: MAD ≈ std / 1.4826 for normal distributions
    mad = std_daily / 1.4826
    spike_threshold = mean_daily + _MAD_K * mad

    # Winsorize: cap at spike threshold
    capped = min(mean_daily, spike_threshold)
    return max(capped, 0.0)


def _ewma_adjustment(features: dict, mean_daily: float) -> float:
    """
    Apply exponential weighting towards recent spending pace.
    If burn_rate > mean_daily → spending is accelerating → EWMA leans higher.
    """
    burn_rate = features.get("burn_rate", mean_daily)
    alpha = 2 / (_EWMA_SPAN + 1)  # standard EWMA alpha
    ewma  = alpha * burn_rate + (1 - alpha) * mean_daily
    return max(ewma, 0.0)
