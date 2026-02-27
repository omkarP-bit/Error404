"""
financial_shock_engine/feature_engine/feature_builder.py
=========================================================
Step 2 — Feature Engineering.

Computes three feature groups from raw user data:
  A. Financial Capacity  (income, surplus, spend averages)
  B. Behavioral Stability (volatility, discretionary ratio, trends)
  C. Liquidity            (burn rate, days-to-depletion)

Input  : output of data_ingestion.fetch_user_data()
Output : FeatureSet dict ready for simulation + LLM
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from configs import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────

def build_features(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Orchestrate all three feature groups and return a unified FeatureSet.
    """
    txns_6m: pd.DataFrame = raw["transactions_6m"]
    txns_cm: pd.DataFrame = raw["current_month_txns"]
    user: dict            = raw["user_profile"]
    accounts: list[dict]  = raw["accounts"]
    goals: list[dict]     = raw["goals"]
    budget: dict | None   = raw["budget_profile"]
    patterns: list[dict]  = raw["txn_patterns"]
    today                 = date.today()

    has_sufficient_data = _has_sufficient_data(txns_6m, today)

    capacity   = _financial_capacity(txns_6m, txns_cm, user, budget, today)
    behavioral = _behavioral_stability(txns_6m, txns_cm, patterns, today)
    liquidity  = _liquidity(accounts, txns_cm, today)
    goal_f     = _goal_features(goals, capacity)

    return {
        **capacity,
        **behavioral,
        **liquidity,
        **goal_f,
        "has_sufficient_data": has_sufficient_data,
        "data_months_available": _months_of_data(txns_6m, today),
        "snapshot_date": today.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  A. Financial Capacity
# ─────────────────────────────────────────────────────────────────────────────

def _financial_capacity(
    txns_6m: pd.DataFrame,
    txns_cm: pd.DataFrame,
    user: dict,
    budget: dict | None,
    today: date,
) -> dict:
    monthly_income = float(user.get("monthly_income", 0.0))

    # Monthly totals for last 3–6 months (exclude current partial month)
    monthly = _monthly_totals(txns_6m, today)
    completed_months = monthly[:-1] if len(monthly) > 1 else monthly  # drop current

    avg_monthly_expense = float(np.median(completed_months)) if completed_months else 0.0
    avg_monthly_3m      = float(np.median(completed_months[-3:])) if len(completed_months) >= 3 else avg_monthly_expense

    current_month_spend = float(txns_cm["amount"].sum()) if not txns_cm.empty else 0.0

    monthly_surplus = monthly_income - avg_monthly_expense

    # Goal contribution required per month
    goals_monthly = budget.get("safe_investable_amount", 0.0) if budget else 0.0
    if goals_monthly == 0.0:
        goals_monthly = monthly_income * (budget.get("savings_ratio", 0.20) if budget else 0.20)

    safe_surplus = max(monthly_surplus - goals_monthly, 0.0)

    days_in_month = _days_in_month(today)
    days_passed   = today.day

    # Projected spend via pace (capped at 2x avg to avoid outlier inflation)
    daily_pace = current_month_spend / days_passed if days_passed > 0 else 0.0
    projected_month_spend = min(daily_pace * days_in_month, avg_monthly_expense * 2.0)

    # Category breakdown for current month
    cat_spend = {}
    if not txns_cm.empty:
        cat_spend = txns_cm.groupby("category")["amount"].sum().round(2).to_dict()

    return {
        "monthly_income":         round(monthly_income, 2),
        "avg_monthly_expense":    round(avg_monthly_expense, 2),
        "avg_monthly_expense_3m": round(avg_monthly_3m, 2),
        "current_month_spend":    round(current_month_spend, 2),
        "projected_month_spend":  round(projected_month_spend, 2),
        "monthly_surplus":        round(monthly_surplus, 2),
        "goals_monthly_required": round(goals_monthly, 2),
        "safe_surplus":           round(safe_surplus, 2),
        "days_passed":            days_passed,
        "days_in_month":          days_in_month,
        "days_remaining":         days_in_month - days_passed,
        "category_spend_cm":      cat_spend,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  B. Behavioral Stability
# ─────────────────────────────────────────────────────────────────────────────

def _behavioral_stability(
    txns_6m: pd.DataFrame,
    txns_cm: pd.DataFrame,
    patterns: list[dict],
    today: date,
) -> dict:
    if txns_6m.empty:
        return _zero_behavioral()

    # Daily spend series
    daily = txns_6m.groupby("txn_date")["amount"].sum()
    mean_daily  = float(daily.mean())
    std_daily   = float(daily.std()) if len(daily) > 1 else 0.0
    expense_volatility = std_daily / mean_daily if mean_daily > 0 else 0.0

    # Discretionary ratio
    disc_cats   = settings.DISCRETIONARY_CATEGORIES
    disc_spend  = txns_6m[txns_6m["category"].isin(disc_cats)]["amount"].sum()
    total_spend = txns_6m["amount"].sum()
    discretionary_ratio = float(disc_spend / total_spend) if total_spend > 0 else 0.0

    # Recurring ratio
    if "is_recurring" in txns_6m.columns:
        recur_spend = txns_6m[txns_6m["is_recurring"] == True]["amount"].sum()
        recurring_ratio = float(recur_spend / total_spend) if total_spend > 0 else 0.0
    else:
        recurring_ratio = 0.0

    # Spending trend slope — linear regression over monthly totals
    monthly = _monthly_totals(txns_6m, today)
    trend_slope = 0.0
    if len(monthly) >= 3:
        x = np.arange(len(monthly), dtype=float)
        y = np.array(monthly, dtype=float)
        coeffs = np.polyfit(x, y, 1)
        trend_slope = float(coeffs[0])   # ₹/month

    # Weekend vs weekday spending ratio
    txns_6m_copy = txns_6m.copy()
    txns_6m_copy["dow"] = pd.to_datetime(txns_6m_copy["txn_date"]).dt.dayofweek
    weekend = txns_6m_copy[txns_6m_copy["dow"].isin([5, 6])]["amount"].sum()
    weekday = txns_6m_copy[~txns_6m_copy["dow"].isin([5, 6])]["amount"].sum()
    weekend_ratio = float(weekend / (weekend + weekday)) if (weekend + weekday) > 0 else 0.0

    # Top spending categories (6m)
    top_cats = (
        txns_6m.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )

    # Category-level volatility (for risk scoring)
    cat_volatility: dict[str, float] = {}
    for cat, grp in txns_6m.groupby("category"):
        monthly_cat = grp.groupby(grp["txn_date"].dt.to_period("M"))["amount"].sum()
        if len(monthly_cat) >= 2:
            cat_volatility[cat] = float(monthly_cat.std() / monthly_cat.mean()) if monthly_cat.mean() > 0 else 0.0

    return {
        "expense_volatility":    round(expense_volatility, 4),
        "discretionary_ratio":   round(discretionary_ratio, 4),
        "recurring_ratio":       round(recurring_ratio, 4),
        "trend_slope":           round(trend_slope, 2),
        "weekend_spend_ratio":   round(weekend_ratio, 4),
        "top_categories_6m":     top_cats,
        "cat_volatility":        {k: round(v, 4) for k, v in cat_volatility.items()},
        "mean_daily_spend":      round(mean_daily, 2),
        "std_daily_spend":       round(std_daily, 2),
    }


def _zero_behavioral() -> dict:
    return {
        "expense_volatility": 0.0, "discretionary_ratio": 0.0,
        "recurring_ratio": 0.0, "trend_slope": 0.0,
        "weekend_spend_ratio": 0.0, "top_categories_6m": [],
        "cat_volatility": {}, "mean_daily_spend": 0.0, "std_daily_spend": 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  C. Liquidity
# ─────────────────────────────────────────────────────────────────────────────

def _liquidity(
    accounts: list[dict],
    txns_cm: pd.DataFrame,
    today: date,
) -> dict:
    liquid_balance = sum(float(a.get("current_balance", 0.0)) for a in accounts)

    days_passed = today.day
    current_month_spend = float(txns_cm["amount"].sum()) if not txns_cm.empty else 0.0
    burn_rate = current_month_spend / days_passed if days_passed > 0 else 0.0
    days_to_depletion = liquid_balance / burn_rate if burn_rate > 0 else 9999.0

    return {
        "liquid_balance":     round(liquid_balance, 2),
        "burn_rate":          round(burn_rate, 2),           # ₹/day
        "days_to_depletion":  round(days_to_depletion, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Goal features
# ─────────────────────────────────────────────────────────────────────────────

def _goal_features(goals: list[dict], capacity: dict) -> dict:
    total_required = 0.0
    goal_details   = []

    today = date.today()
    for g in goals:
        deadline_str = g.get("deadline")
        if deadline_str:
            try:
                deadline = date.fromisoformat(str(deadline_str))
                months_left = max(
                    (deadline.year - today.year) * 12 + (deadline.month - today.month),
                    1,
                )
            except (ValueError, TypeError):
                months_left = 12
        else:
            months_left = 12

        remaining = max(float(g.get("target_amount", 0)) - float(g.get("current_amount", 0)), 0.0)
        monthly_need = remaining / months_left if months_left > 0 else remaining

        total_required += monthly_need
        goal_details.append({
            "goal_id":      g["goal_id"],
            "goal_name":    g["goal_name"],
            "target":       float(g.get("target_amount", 0)),
            "saved":        float(g.get("current_amount", 0)),
            "remaining":    round(remaining, 2),
            "months_left":  months_left,
            "monthly_need": round(monthly_need, 2),
            "priority":     g.get("priority", 2),
        })

    return {
        "goals_monthly_total_required": round(total_required, 2),
        "goal_details":                 goal_details,
        "goals_count":                  len(goals),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _monthly_totals(txns: pd.DataFrame, today: date) -> list[float]:
    if txns.empty:
        return []
    txns = txns.copy()
    txns["month"] = pd.to_datetime(txns["txn_date"]).dt.to_period("M")
    return txns.groupby("month")["amount"].sum().tolist()


def _months_of_data(txns: pd.DataFrame, today: date) -> int:
    if txns.empty:
        return 0
    min_date = pd.to_datetime(txns["txn_date"]).min().date()
    return max((today.year - min_date.year) * 12 + (today.month - min_date.month), 1)


def _has_sufficient_data(txns: pd.DataFrame, today: date) -> bool:
    return _months_of_data(txns, today) >= settings.MIN_DATA_MONTHS


def _days_in_month(today: date) -> int:
    import calendar
    return calendar.monthrange(today.year, today.month)[1]
