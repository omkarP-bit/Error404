"""
ml_models/goal_feasibility_model/dataset_loader.py
====================================================
Synthetic binary-classification training data for the Goal Probability Engine.

Design principles:
  * Covers the full 28-feature vector defined in feature_builder.py
  * Ground-truth label is derived from a financially sound formula so the
    model learns realistic decision boundaries, not noise.
  * 6 000 samples, class balance ~55/45 (reflecting real-world skew).
  * Can later be fine-tuned by swapping in real goal-outcome rows.

Label formula (domain-encoded logic):
  y = sigmoid(
        +3.0 × feasibility_ratio          # can you afford it?
        −1.2 × expense_volatility_ratio    # is spending stable?
        −0.8 × (dining_slope + shopping_slope)  # rising discretionary spend?
        +0.6 × behavioral_consistency      # spending discipline
        +0.4 × progress_pct               # already saved some
        +0.3 × health_score
        −0.5 × (missed_saving_months / 12) # missed contribution months
        −0.4 × debit_ratio_3m_6m          # accelerating spend
        + normal noise(0, 0.25)           # real-world uncertainty
      ) > 0.5
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from typing import Tuple

from ml_models.goal_feasibility_model.feature_builder import FEATURE_NAMES


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def generate_synthetic_dataset(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    """
    Generate n synthetic goal records with all 28 features + binary label.
    Sampling ranges are calibrated against real Indian personal-finance data.
    """
    rng = np.random.default_rng(seed)

    # ── A. Goal ──────────────────────────────────────────────────────────────
    target_amount    = rng.uniform(30_000, 2_000_000, n)
    progress_pct     = rng.uniform(0.0, 0.85, n)
    current_amount   = target_amount * progress_pct
    remaining        = target_amount - current_amount
    months_left      = rng.integers(2, 60, n).astype(float)
    monthly_required = remaining / np.maximum(months_left, 1)

    log_target_amount    = np.log1p(target_amount)
    log_remaining_amount = np.log1p(remaining)

    # ── B. Capacity ───────────────────────────────────────────────────────────
    monthly_income      = rng.uniform(20_000, 300_000, n)
    avg_monthly_surplus = monthly_income * rng.uniform(0.05, 0.45, n)
    expense_volatility  = avg_monthly_surplus * rng.uniform(0.1, 1.2, n)
    current_balance     = monthly_income * rng.uniform(1, 18, n)
    safe_surplus        = avg_monthly_surplus * 0.85
    savings_rate        = safe_surplus / np.maximum(monthly_income, 1)
    feasibility_ratio   = safe_surplus / np.maximum(monthly_required, 1)

    # ── C. Transaction Behaviour ──────────────────────────────────────────────
    avg_monthly_expenses    = monthly_income - avg_monthly_surplus
    expense_volatility_ratio = expense_volatility / np.maximum(avg_monthly_expenses, 1)
    anomaly_count_3m        = rng.integers(0, 8, n).astype(float)
    recurring_expense_ratio = rng.uniform(0.1, 0.6, n)
    discretionary_ratio     = rng.uniform(0.05, 0.55, n)
    txn_frequency           = rng.uniform(5, 50, n)
    high_value_txn_count    = rng.integers(0, 10, n).astype(float)

    # ── D. Category Drift ─────────────────────────────────────────────────────
    dining_slope        = rng.uniform(-0.15, 0.25, n)
    shopping_slope      = rng.uniform(-0.10, 0.30, n)
    entertainment_slope = rng.uniform(-0.05, 0.20, n)

    # ── E. Stability ──────────────────────────────────────────────────────────
    contribution_streak  = rng.integers(0, 12, n).astype(float)
    missed_saving_months = 12.0 - contribution_streak + rng.integers(0, 3, n).astype(float)
    missed_saving_months = np.clip(missed_saving_months, 0, 12)
    behavioral_consistency = rng.uniform(0.2, 1.0, n)

    # ── F. Health ─────────────────────────────────────────────────────────────
    health_score        = rng.uniform(0.2, 0.95, n)
    debit_ratio_3m_6m   = rng.uniform(0.7, 1.5, n)
    income_stability    = rng.choice([1.0, 0.7, 0.6], size=n, p=[0.6, 0.3, 0.1])

    # ── Ground-truth label ────────────────────────────────────────────────────
    logit = (
        +3.0 * np.clip(feasibility_ratio, 0, 5)
        - 1.2 * np.clip(expense_volatility_ratio, 0, 3)
        - 0.8 * (dining_slope + shopping_slope)
        + 0.6 * behavioral_consistency
        + 0.4 * progress_pct
        + 0.3 * health_score
        - 0.5 * (missed_saving_months / 12)
        - 0.4 * np.clip(debit_ratio_3m_6m - 1, 0, 1)
        + rng.normal(0, 0.25, n)   # realistic noise
    )
    prob = _sigmoid(logit - 1.2)   # shift centre to ~45 % positive rate
    y    = (prob > 0.5).astype(int)

    df = pd.DataFrame({
        "log_target_amount":         log_target_amount,
        "log_remaining_amount":      log_remaining_amount,
        "months_left":               months_left,
        "monthly_required":          monthly_required,
        "progress_pct":              progress_pct,
        "monthly_income":            monthly_income,
        "avg_monthly_surplus":       avg_monthly_surplus,
        "expense_volatility":        expense_volatility,
        "current_balance":           current_balance,
        "safe_surplus":              safe_surplus,
        "savings_rate":              savings_rate,
        "feasibility_ratio":         feasibility_ratio,
        "avg_monthly_expenses":      avg_monthly_expenses,
        "expense_volatility_ratio":  expense_volatility_ratio,
        "anomaly_count_3m":          anomaly_count_3m,
        "recurring_expense_ratio":   recurring_expense_ratio,
        "discretionary_ratio":       discretionary_ratio,
        "txn_frequency":             txn_frequency,
        "high_value_txn_count":      high_value_txn_count,
        "dining_slope":              dining_slope,
        "shopping_slope":            shopping_slope,
        "entertainment_slope":       entertainment_slope,
        "contribution_streak":       contribution_streak,
        "missed_saving_months":      missed_saving_months,
        "behavioral_consistency":    behavioral_consistency,
        "health_score":              health_score,
        "debit_ratio_3m_6m":         debit_ratio_3m_6m,
        "income_stability":          income_stability,
        "y":                         y,
    })
    return df


def load_for_goal_feasibility() -> Tuple[pd.DataFrame, pd.Series]:
    """Entry-point for model training — returns (X_df, y)."""
    df = generate_synthetic_dataset()
    X  = df[FEATURE_NAMES]
    y  = df["y"]
    return X, y


if __name__ == "__main__":
    X, y = load_for_goal_feasibility()
    print(f"Shape : {X.shape}")
    print(f"Labels: {y.value_counts().to_dict()}")
    print(X.describe().round(2))

