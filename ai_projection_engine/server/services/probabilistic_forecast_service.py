"""
ai_projection_engine/server/services/probabilistic_forecast_service.py
=======================================================================
Core Monte Carlo engine for probabilistic end-of-month expenditure forecasting.

Algorithm:
  1. Load DEBIT transactions (last LOOKBACK_MONTHS months).
  2. Apply IQR outlier down-weighting.
  3. Per-category: fit Gamma distribution to historical daily spend.
  4. Simulate *remaining_days × n_simulations* draws per category.
  5. Aggregate → distribution of total month-end spend.
  6. Extract P25 / P50 / P90 confidence bands.
  7. Compute balance trajectory and depletion risk.

Falls back to a simple heuristic model when < MIN_DAYS_FOR_ML_MODEL days of data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.core.config import settings
from server.core.constants import DEPLETION_RISK_BALANCE_THRESHOLD
from server.utils.anomaly_filter import apply_outlier_weights
from server.utils.feature_engineering import build_all_features
from server.utils.simulation_utils import (
    compute_percentiles,
    estimate_depletion_date,
    get_remaining_days_in_month,
    simulate_category_forecast,
)


# ── DB Helpers ─────────────────────────────────────────────────────────────────

def get_user_current_balance(db: Session, user_id: int) -> float:
    """Sum of current_balance across all accounts owned by *user_id*."""
    row = db.execute(
        text("SELECT COALESCE(SUM(current_balance), 0) FROM accounts WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()
    return float(row[0]) if row else 0.0


def get_user_income(db: Session, user_id: int) -> float:
    """Monthly income declared in the users table."""
    row = db.execute(
        text("SELECT monthly_income FROM users WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()
    return float(row[0]) if row and row[0] else 0.0


# ── Main Forecast ──────────────────────────────────────────────────────────────

def run_probabilistic_forecast(db: Session, user_id: int) -> Dict:
    """
    Run the full Monte Carlo forecast pipeline for *user_id*.

    Returns a comprehensive forecast dict ready for JSON serialisation.
    All monetary values are in ₹ (Indian Rupees).
    """
    features = build_all_features(db, user_id, settings.LOOKBACK_MONTHS)
    current_month = features["current_month"]
    remaining_days = get_remaining_days_in_month()
    current_balance = get_user_current_balance(db, user_id)
    monthly_income = get_user_income(db, user_id)

    # ── Heuristic fallback ────────────────────────────────────────────────────
    if not features["has_data"] or features["data_days"] < settings.MIN_DAYS_FOR_ML_MODEL:
        return _heuristic_forecast(
            user_id, current_month, current_balance, monthly_income,
            remaining_days, features,
        )

    # ── Monte Carlo path ──────────────────────────────────────────────────────
    df = apply_outlier_weights(features["df"])

    cur_month_df = df[df["month_year"] == current_month]
    spent_this_month = float(cur_month_df["amount"].sum())

    rng = np.random.default_rng(42)
    n_sims = settings.MC_SIMULATIONS

    # Per-category simulations (remaining spend only)
    categories = [str(c) for c in df["category"].dropna().unique()]
    cat_sims: Dict[str, np.ndarray] = {}
    for cat in categories:
        cat_sims[cat] = simulate_category_forecast(
            df, cat, remaining_days, n_sims, rng
        )

    # Total remaining spend across all categories
    if cat_sims:
        total_remaining_sims = np.sum(list(cat_sims.values()), axis=0)
    else:
        avg_daily = features["avg_daily_spend"]
        std_daily = avg_daily * 0.3
        total_remaining_sims = rng.normal(
            avg_daily * remaining_days,
            std_daily * np.sqrt(max(remaining_days, 1)),
            n_sims,
        ).clip(min=0)

    total_month_sims = spent_this_month + total_remaining_sims
    balance_sims = current_balance - total_remaining_sims

    # Confidence bands
    spend_bands = compute_percentiles(total_month_sims)
    balance_bands = compute_percentiles(balance_sims)

    # Depletion risk
    avg_daily_remaining = (
        float(total_remaining_sims.mean()) / max(remaining_days, 1)
    )
    depletion_date = estimate_depletion_date(current_balance, avg_daily_remaining)
    depletion_risk = (
        balance_bands["p50"] < DEPLETION_RISK_BALANCE_THRESHOLD
        or depletion_date is not None
    )

    # Per-category breakdown
    category_breakdown: Dict[str, Dict] = {}
    for cat, sims in cat_sims.items():
        cat_spent = float(
            cur_month_df[cur_month_df["category"] == cat]["amount"].sum()
        )
        cat_total_sims = cat_spent + sims
        bands = compute_percentiles(cat_total_sims)
        category_breakdown[cat] = {
            "spent_so_far": round(cat_spent, 2),
            "projected_p25": round(bands["p25"], 2),
            "projected_p50": round(bands["p50"], 2),
            "projected_p90": round(bands["p90"], 2),
        }

    return {
        "user_id": user_id,
        "month_year": current_month,
        "computed_at": datetime.utcnow().isoformat(),
        "is_ml_forecast": True,
        "simulations_run": n_sims,
        "data_days_available": features["data_days"],
        "remaining_days_in_month": remaining_days,
        "spent_this_month_so_far": round(spent_this_month, 2),
        "current_balance": round(current_balance, 2),
        "monthly_income": round(monthly_income, 2),
        "projected_month_spend": {
            "lower_p25": round(spend_bands["p25"], 2),
            "median_p50": round(spend_bands["p50"], 2),
            "upper_p90": round(spend_bands["p90"], 2),
        },
        "projected_balance_at_month_end": {
            "lower": round(balance_bands["p25"], 2),
            "median": round(balance_bands["p50"], 2),
            "upper": round(balance_bands["p90"], 2),
        },
        "depletion_risk_flag": depletion_risk,
        "depletion_risk_date": depletion_date,
        "category_breakdown": category_breakdown,
        # Behaviour summary
        "avg_daily_spend": round(features["avg_daily_spend"], 2),
        "spend_volatility": round(features["spend_volatility"], 2),
        "mid_month_burn_rate": round(features["mid_month_burn_rate"], 2),
        "weekend_spending_multiplier": round(features["weekend_multiplier"], 2),
        "discretionary_ratio": round(features["discretionary_ratio"], 3),
        "fixed_ratio": round(features["fixed_ratio"], 3),
    }


# ── Heuristic Fallback ─────────────────────────────────────────────────────────

def _heuristic_forecast(
    user_id: int,
    current_month: str,
    current_balance: float,
    monthly_income: float,
    remaining_days: int,
    features: Dict,
) -> Dict:
    """
    Simple heuristic used when < MIN_DAYS_FOR_ML_MODEL days of data exist.
    Assumes 70% of monthly income will be spent.
    Confidence bands are ±15% / +20% of the heuristic estimate.
    """
    avg_daily = features.get("avg_daily_spend", 0.0)
    if avg_daily == 0.0 and monthly_income > 0:
        avg_daily = (monthly_income * 0.70) / 30.0

    projected_remaining = avg_daily * remaining_days
    p50 = round(projected_remaining, 2)
    p25 = round(projected_remaining * 0.85, 2)
    p90 = round(projected_remaining * 1.20, 2)

    return {
        "user_id": user_id,
        "month_year": current_month,
        "computed_at": datetime.utcnow().isoformat(),
        "is_ml_forecast": False,
        "simulations_run": 0,
        "data_days_available": features.get("data_days", 0),
        "remaining_days_in_month": remaining_days,
        "spent_this_month_so_far": 0.0,
        "current_balance": round(current_balance, 2),
        "monthly_income": round(monthly_income, 2),
        "projected_month_spend": {
            "lower_p25": p25,
            "median_p50": p50,
            "upper_p90": p90,
        },
        "projected_balance_at_month_end": {
            "lower": round(current_balance - p90, 2),
            "median": round(current_balance - p50, 2),
            "upper": round(current_balance - p25, 2),
        },
        "depletion_risk_flag": current_balance < projected_remaining,
        "depletion_risk_date": None,
        "category_breakdown": {},
        "avg_daily_spend": round(avg_daily, 2),
        "spend_volatility": 0.0,
        "mid_month_burn_rate": 1.0,
        "weekend_spending_multiplier": 1.0,
        "discretionary_ratio": 0.5,
        "fixed_ratio": 0.5,
    }
