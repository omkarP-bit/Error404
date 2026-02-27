"""
ml_models/goal_feasibility_engine/surplus_forecaster.py
========================================================
Predicts future monthly surplus from the last 6 months of expense history.

Uses robust statistics (trimmed mean) rather than simple mean to avoid
outlier months distorting the forecast.

No sklearn dependency — numpy only.

Output dict:
  predicted_expenses  — trimmed mean of non-zero monthly expense months
  expense_std         — standard deviation across months
  predicted_surplus   — monthly_income − predicted_expenses
  stable_surplus      — conservative: effective_income − (mean + 0.5×std)
  surplus_std         — combined income + expense variability
  confidence_lower    — 90% CI lower bound on monthly surplus
  confidence_upper    — 90% CI upper bound on monthly surplus
"""
from __future__ import annotations

import numpy as np
from typing import List


def forecast_surplus(ctx: dict) -> dict:
    """
    Derive a realistic, confidence-bounded surplus forecast from
    the FinancialContext produced by feature_builder.

    Conservative design:
      - Uses trimmed mean (drops highest outlier month) to reduce skew
      - Adjusts effective income for income_stability (freelancers earn variably)
      - Stable surplus = effective_income − (trimmed_mean + 0.5 × std)
        i.e. we budget for slightly-above-average expense months
      - Surplus std combines expense volatility + income uncertainty
    """
    monthly_expenses: List[float] = ctx["monthly_expenses"]
    monthly_income:   float       = ctx["monthly_income"]
    income_stability: float       = ctx["income_stability"]

    non_zero = [e for e in monthly_expenses if e > 0]

    if not non_zero:
        # No transaction history — assume 70% of income as expenses
        predicted_expenses = monthly_income * 0.70
        expense_std        = monthly_income * 0.10

    elif len(non_zero) == 1:
        predicted_expenses = non_zero[0]
        expense_std        = predicted_expenses * 0.15

    else:
        # Trimmed mean: drop the single highest outlier month when >= 4 data points
        sorted_e = sorted(non_zero)
        trimmed  = sorted_e[:-1] if len(sorted_e) >= 4 else sorted_e
        predicted_expenses = float(np.mean(trimmed))
        expense_std        = float(np.std(non_zero))

    # Raw surplus (no adjustments)
    raw_surplus = max(monthly_income - predicted_expenses, 0.0)

    # Stable surplus: effective income (stability-adjusted) minus buffer
    effective_income = monthly_income * income_stability
    stable_surplus   = max(
        effective_income - (predicted_expenses + 0.5 * expense_std),
        0.0,
    )

    # Surplus std: expense volatility + income disruption uncertainty
    income_uncertainty = monthly_income * (1.0 - income_stability) * 0.30
    surplus_std        = expense_std + income_uncertainty
    surplus_std        = max(surplus_std, raw_surplus * 0.05)  # floor at 5%

    # 90% confidence interval (z=1.64)
    ci_lower = max(raw_surplus - 1.64 * surplus_std, 0.0)
    ci_upper = raw_surplus + 1.64 * surplus_std

    return {
        "predicted_expenses": round(predicted_expenses, 2),
        "expense_std":        round(expense_std,        2),
        "predicted_surplus":  round(raw_surplus,        2),
        "stable_surplus":     round(stable_surplus,     2),
        "surplus_std":        round(surplus_std,        2),
        "confidence_lower":   round(ci_lower,           2),
        "confidence_upper":   round(ci_upper,           2),
    }
