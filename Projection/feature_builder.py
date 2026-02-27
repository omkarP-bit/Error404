"""
server/shock_engine/feature_builder.py
=======================================
Computes all financial features needed by the shock simulation.
  A. Financial Capacity
  B. Behavioral Stability (EWMA, MAD, volatility, trend)
  C. Liquidity (burn rate, days-to-depletion)
"""
from __future__ import annotations

import calendar
import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DISCRETIONARY = ["Food & Dining", "Shopping", "Entertainment", "Travel", "Groceries"]
FIXED_CATS    = ["Rent", "Utilities", "Healthcare", "Transport", "Finance", "Investments"]

# EWMA span for daily spend smoothing
_EWMA_SPAN = 14
_MAD_K     = 2.5


def build_features(raw: dict[str, Any]) -> dict[str, Any]:
    txns_6m  = raw["transactions_6m"]
    txns_cm  = raw["current_month_txns"]
    user     = raw["user_profile"]
    accounts = raw["accounts"]
    goals    = raw["goals"]
    budget   = raw["budget_profile"]
    patterns = raw["txn_patterns"]
    today    = date.today()

    capacity   = _capacity(txns_6m, txns_cm, user, budget, today)
    behavioral = _behavioral(txns_6m, txns_cm, patterns, today)
    liquidity  = _liquidity(accounts, txns_cm, today)
    goal_feat  = _goal_features(goals, today)
    projection = _project_balance(capacity, behavioral, liquidity, today)

    months_data = _months_of_data(txns_6m, today)

    return {
        **capacity,
        **behavioral,
        **liquidity,
        **goal_feat,
        **projection,
        "has_sufficient_data":   months_data >= 2,
        "data_months_available": months_data,
        "snapshot_date":         today.isoformat(),
    }


# ── A. Capacity ───────────────────────────────────────────────────────────────

def _capacity(txns_6m, txns_cm, user, budget, today):
    income = float(user.get("monthly_income", 0.0))
    monthly_totals = _monthly_totals(txns_6m, today)
    completed = monthly_totals[:-1] if len(monthly_totals) > 1 else monthly_totals

    avg_expense    = float(np.median(completed)) if completed else 0.0
    avg_expense_3m = float(np.median(completed[-3:])) if len(completed) >= 3 else avg_expense
    cm_spend       = float(txns_cm["amount"].sum()) if not txns_cm.empty else 0.0

    savings_ratio  = budget.get("savings_ratio", 0.20) if budget else 0.20
    goals_monthly  = income * savings_ratio

    surplus      = income - avg_expense
    safe_surplus = max(surplus - goals_monthly, 0.0)

    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed   = today.day
    days_remaining = days_in_month - days_passed

    daily_pace = cm_spend / days_passed if days_passed > 0 else 0.0
    projected  = min(daily_pace * days_in_month, avg_expense * 2.0)

    cat_spend = {}
    if not txns_cm.empty:
        cat_spend = txns_cm.groupby("category")["amount"].sum().round(2).to_dict()

    return {
        "monthly_income":         round(income, 2),
        "avg_monthly_expense":    round(avg_expense, 2),
        "avg_monthly_expense_3m": round(avg_expense_3m, 2),
        "current_month_spend":    round(cm_spend, 2),
        "projected_month_spend":  round(projected, 2),
        "monthly_surplus":        round(surplus, 2),
        "goals_monthly_required": round(goals_monthly, 2),
        "safe_surplus":           round(safe_surplus, 2),
        "days_passed":            days_passed,
        "days_in_month":          days_in_month,
        "days_remaining":         days_remaining,
        "category_spend_cm":      cat_spend,
    }


# ── B. Behavioral ─────────────────────────────────────────────────────────────

def _behavioral(txns_6m, txns_cm, patterns, today):
    if txns_6m.empty:
        return {"expense_volatility": 0.0, "discretionary_ratio": 0.0,
                "recurring_ratio": 0.0, "trend_slope": 0.0,
                "weekend_spend_ratio": 0.0, "top_categories_6m": [],
                "cat_volatility": {}, "mean_daily_spend": 0.0, "std_daily_spend": 0.0}

    daily = txns_6m.groupby("txn_date")["amount"].sum()
    mean_d = float(daily.mean())
    std_d  = float(daily.std()) if len(daily) > 1 else 0.0
    vol    = std_d / mean_d if mean_d > 0 else 0.0

    total  = float(txns_6m["amount"].sum())
    disc   = float(txns_6m[txns_6m["category"].isin(DISCRETIONARY)]["amount"].sum())
    disc_ratio = disc / total if total > 0 else 0.0

    recur = float(txns_6m[txns_6m["is_recurring"] == True]["amount"].sum()) if "is_recurring" in txns_6m.columns else 0.0
    recur_ratio = recur / total if total > 0 else 0.0

    monthly = _monthly_totals(txns_6m, today)
    slope = 0.0
    if len(monthly) >= 3:
        x = np.arange(len(monthly), dtype=float)
        y = np.array(monthly, dtype=float)
        slope = float(np.polyfit(x, y, 1)[0])

    tmp = txns_6m.copy()
    tmp["dow"] = pd.to_datetime(tmp["txn_date"]).dt.dayofweek
    wknd = float(tmp[tmp["dow"].isin([5, 6])]["amount"].sum())
    wkdy = float(tmp[~tmp["dow"].isin([5, 6])]["amount"].sum())
    wknd_ratio = wknd / (wknd + wkdy) if (wknd + wkdy) > 0 else 0.0

    top_cats = (txns_6m.groupby("category")["amount"].sum()
                .sort_values(ascending=False).head(5).index.tolist())

    cat_vol = {}
    for cat, grp in txns_6m.groupby("category"):
        m = grp.groupby(grp["txn_date"].dt.to_period("M"))["amount"].sum()
        if len(m) >= 2:
            cat_vol[cat] = round(float(m.std() / m.mean()) if m.mean() > 0 else 0.0, 4)

    return {
        "expense_volatility":  round(vol, 4),
        "discretionary_ratio": round(disc_ratio, 4),
        "recurring_ratio":     round(recur_ratio, 4),
        "trend_slope":         round(slope, 2),
        "weekend_spend_ratio": round(wknd_ratio, 4),
        "top_categories_6m":   top_cats,
        "cat_volatility":      cat_vol,
        "mean_daily_spend":    round(mean_d, 2),
        "std_daily_spend":     round(std_d, 2),
    }


# ── C. Liquidity ──────────────────────────────────────────────────────────────

def _liquidity(accounts, txns_cm, today):
    liquid = sum(float(a.get("current_balance", 0.0)) for a in accounts)
    cm_spend = float(txns_cm["amount"].sum()) if not txns_cm.empty else 0.0
    days_passed = today.day
    burn = cm_spend / days_passed if days_passed > 0 else 0.0
    dtd  = liquid / burn if burn > 0 else 9999.0
    return {
        "liquid_balance":    round(liquid, 2),
        "burn_rate":         round(burn, 2),
        "days_to_depletion": round(dtd, 1),
    }


# ── Goal features ─────────────────────────────────────────────────────────────

def _goal_features(goals, today):
    total_req = 0.0
    details   = []
    for g in goals:
        try:
            deadline = date.fromisoformat(str(g["deadline"])) if g.get("deadline") else None
            months_left = max((deadline.year - today.year) * 12 + (deadline.month - today.month), 1) if deadline else 12
        except Exception:
            months_left = 12
        remaining    = max(float(g.get("target_amount", 0)) - float(g.get("current_amount", 0)), 0.0)
        monthly_need = remaining / months_left
        total_req   += monthly_need
        details.append({
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
        "goals_monthly_total_required": round(total_req, 2),
        "goal_details":                 details,
        "goals_count":                  len(goals),
    }


# ── Budget projection (EWMA + MAD) ────────────────────────────────────────────

def _project_balance(capacity, behavioral, liquidity, today):
    mean_d = behavioral["mean_daily_spend"]
    std_d  = behavioral["std_daily_spend"]
    burn   = liquidity["burn_rate"]
    liquid = liquidity["liquid_balance"]
    days_r = capacity["days_remaining"]
    vol    = behavioral["expense_volatility"]

    if mean_d == 0.0:
        mean_d = capacity.get("avg_monthly_expense", 30000) / 30.0
    if std_d == 0.0:
        std_d = mean_d * 0.30
    std_d = max(std_d, mean_d * 0.05)

    # MAD-robust daily estimate
    mad      = std_d / 1.4826
    spike_th = mean_d + _MAD_K * mad
    robust_d = min(mean_d, spike_th)

    # EWMA adjustment toward recent burn rate
    alpha   = 2 / (_EWMA_SPAN + 1)
    ewma_d  = alpha * burn + (1 - alpha) * mean_d
    blended = 0.60 * ewma_d + 0.40 * robust_d

    remaining_spend = blended * days_r
    end_balance     = liquid - remaining_spend
    spread          = blended * days_r * vol

    return {
        "projected_remaining_spend":   round(remaining_spend, 2),
        "projected_end_month_balance": round(end_balance, 2),
        "proj_band_low":               round(end_balance - spread, 2),
        "proj_band_high":              round(end_balance + spread * 0.5, 2),
        "daily_spend_estimate":        round(blended, 2),
    }


# ── Utilities ─────────────────────────────────────────────────────────────────

def _monthly_totals(txns, today):
    if txns.empty:
        return []
    t = txns.copy()
    t["month"] = pd.to_datetime(t["txn_date"]).dt.to_period("M")
    return t.groupby("month")["amount"].sum().tolist()


def _months_of_data(txns, today):
    if txns.empty:
        return 0
    mn = pd.to_datetime(txns["txn_date"]).min().date()
    return max((today.year - mn.year) * 12 + (today.month - mn.month), 1)
