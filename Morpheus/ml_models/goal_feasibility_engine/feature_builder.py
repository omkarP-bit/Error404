"""
ml_models/goal_feasibility_engine/feature_builder.py
=====================================================
Aggregates all financial context from the live DB for one user × goal pair.

Queries (read-only, no schema changes):
  transactions   — 6-month history bucketed by calendar month
  users          — monthly_income, income_type
  accounts       — current_balance (liquidity)
  budget_profiles — baseline_expense, expense_volatility (fallback)
  goals          — all active goals (multi-goal allocation context)

Returned dict keys (FinancialContext):
  Goal:        goal_id, goal_name, goal_type, target_amount, current_amount,
               remaining_amount, months_left, required_monthly_raw, priority, progress_pct
  Income:      monthly_income, income_type, income_stability
  Expenses:    monthly_expenses[6], avg_expenses_3m, avg_expenses_6m, std_expenses,
               expense_volatility_factor, avg_essential_monthly
  Surplus:     monthly_net[6], surplus_3m_avg, historical_median_savings
  Discr.:      discretionary_monthly, discretionary_ratio, dining_monthly,
               shopping_monthly, entertainment_monthly, lifestyle_drift
  Behavioral:  contribution_streak, missed_saving_months, anomaly_count_3m
  Balance:     total_balance, liquidity_buffer_months
  Multi-goal:  all_active_goals, num_competing_goals
  Quality:     has_enough_data, total_txn_count, months_of_data
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List

import numpy as np

# ── Category classifiers (lower-case substring matching) ────────────────────
_DISC_KW = {
    "food & dining", "dining", "restaurants", "shopping",
    "entertainment", "food", "cafe", "eating out", "fast food",
    "takeaway", "pub", "bar", "cinema", "streaming",
}
_ESSENTIAL_KW = {
    "housing", "utilities", "healthcare", "insurance",
    "education", "groceries", "transport", "rent", "emi",
    "bills", "medical", "electricity", "water", "gas",
    "broadband", "mobile", "phone", "fuel",
}


def _month_keys(n: int = 6) -> List[tuple]:
    """Return last n calendar months as (year, month) tuples, oldest first."""
    today = date.today()
    keys = []
    for i in range(n - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        keys.append((y, m))
    return keys


def _slope(series: List[float]) -> float:
    """OLS slope of a series; returns 0 if too short."""
    n = len(series)
    if n < 2:
        return 0.0
    x = list(range(n))
    xm = sum(x) / n
    ym = sum(series) / n
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, series))
    den = sum((xi - xm) ** 2 for xi in x) + 1e-9
    return num / den


def build_financial_context(db, user_id: int, goal) -> dict:
    """
    Extract the full FinancialContext dict for one user × goal pair.
    All DB queries are read-only; no schema mutations.
    """
    from sqlalchemy import func as F
    from app.models.transaction import Transaction
    from app.models.account import Account
    from app.models.budget_profile import BudgetProfile
    from app.models.goal import Goal
    from app.models.user import User
    from app.models.enums import TxnType, GoalStatus

    today = date.today()
    now   = datetime.utcnow()
    c6m   = now - timedelta(days=184)
    c3m   = now - timedelta(days=92)

    # ── User ─────────────────────────────────────────────────────────────────
    user           = db.query(User).filter(User.user_id == user_id).first()
    monthly_income = float(user.monthly_income or 0) if user else 0.0
    income_type    = user.income_type.value if user else "salaried"
    income_stability = {
        "salaried": 1.00, "self_employed": 0.70,
        "freelance": 0.65, "business": 0.75, "retired": 0.90,
    }.get(income_type, 0.80)

    # ── Goal ──────────────────────────────────────────────────────────────────
    target    = float(goal.target_amount  or 0)
    current   = float(goal.current_amount or 0)
    remaining = max(target - current, 0.0)
    priority  = int(goal.priority or 2)

    months_left = 12.0
    if goal.deadline:
        days_left   = (goal.deadline - today).days
        months_left = max(days_left / 30.44, 0.1)

    required_monthly_raw = remaining / months_left if months_left > 0 else remaining

    # ── Pull 6 months of transactions ────────────────────────────────────────
    txns_raw = db.query(
        Transaction.txn_timestamp,
        Transaction.amount,
        Transaction.txn_type,
        Transaction.category,
        Transaction.is_recurring,
    ).filter(
        Transaction.user_id  == user_id,
        Transaction.txn_timestamp >= c6m,
    ).all()

    m_keys = _month_keys(6)

    # Per-month buckets
    m_debit:         Dict[tuple, float] = defaultdict(float)
    m_credit:        Dict[tuple, float] = defaultdict(float)
    m_disc:          Dict[tuple, float] = defaultdict(float)
    m_essential:     Dict[tuple, float] = defaultdict(float)
    m_dining:        Dict[tuple, float] = defaultdict(float)
    m_shopping:      Dict[tuple, float] = defaultdict(float)
    m_entertainment: Dict[tuple, float] = defaultdict(float)

    all_amounts_6m: List[float] = []
    all_amounts_3m: List[float] = []

    for txn in txns_raw:
        ts  = txn.txn_timestamp
        key = (ts.year, ts.month)
        amt = float(txn.amount)
        cat = (txn.category or "").lower().strip()
        typ = txn.txn_type.value

        if typ == "debit":
            m_debit[key] += amt
            all_amounts_6m.append(amt)
            if ts >= c3m:
                all_amounts_3m.append(amt)

            # Discretionary
            is_disc = any(kw in cat for kw in _DISC_KW)
            if is_disc:
                m_disc[key] += amt
                if any(kw in cat for kw in {"food", "dining", "restaurant", "cafe", "takeaway"}):
                    m_dining[key] += amt
                elif "shopping" in cat:
                    m_shopping[key] += amt
                elif "entertainment" in cat or "cinema" in cat or "streaming" in cat:
                    m_entertainment[key] += amt

            # Essential
            if any(kw in cat for kw in _ESSENTIAL_KW):
                m_essential[key] += amt

        elif typ == "credit":
            m_credit[key] += amt

    # ── Monthly arrays (oldest → newest) ─────────────────────────────────────
    monthly_expenses      = [m_debit.get(k, 0.0)         for k in m_keys]
    monthly_credits       = [m_credit.get(k, 0.0)        for k in m_keys]
    monthly_disc_list     = [m_disc.get(k, 0.0)          for k in m_keys]
    monthly_essential_lst = [m_essential.get(k, 0.0)     for k in m_keys]
    monthly_dining_lst    = [m_dining.get(k, 0.0)        for k in m_keys]
    monthly_shopping_lst  = [m_shopping.get(k, 0.0)      for k in m_keys]
    monthly_entmt_lst     = [m_entertainment.get(k, 0.0) for k in m_keys]

    non_zero_exp = [e for e in monthly_expenses if e > 0]

    # Averages
    avg_exp_3m = float(np.mean(monthly_expenses[-3:])) if any(monthly_expenses[-3:]) else 0.0
    avg_exp_6m = float(np.mean(non_zero_exp))           if non_zero_exp else 0.0
    std_exp    = float(np.std(non_zero_exp))             if len(non_zero_exp) > 1 else avg_exp_6m * 0.15

    # Fallback from budget_profile when transaction history is thin
    bp = db.query(BudgetProfile).filter(BudgetProfile.user_id == user_id).first()
    if avg_exp_6m == 0.0 and bp and bp.baseline_expense > 0:
        avg_exp_6m = float(bp.baseline_expense)
        avg_exp_3m = avg_exp_6m
    if std_exp == 0.0 and bp and bp.expense_volatility > 0:
        std_exp = float(bp.expense_volatility)

    # ── Surplus per month ─────────────────────────────────────────────────────
    monthly_net: List[float] = []
    for i, _k in enumerate(m_keys):
        # Use declared monthly_income as floor when transaction credits are sparse
        credit_this_month = monthly_credits[i]
        if credit_this_month < monthly_income * 0.40 and monthly_income > 0:
            credit_this_month = monthly_income
        monthly_net.append(credit_this_month - monthly_expenses[i])

    positive_nets             = [n for n in monthly_net if n > 0]
    historical_median_savings = float(np.median(positive_nets)) if positive_nets else 0.0

    # Raw surplus estimate (3-month window)
    if monthly_income > 0:
        surplus_3m_avg = max(monthly_income - avg_exp_3m, 0.0)
    else:
        surplus_3m_avg = max(float(np.mean(monthly_net[-3:])), 0.0)

    # Expense volatility factor (0–1, lower is more stable)
    exp_vol_factor = min(std_exp / max(avg_exp_6m, 1.0), 1.0)

    # ── Discretionary & essential averages ───────────────────────────────────
    avg_essential = (
        float(np.mean([e for e in monthly_essential_lst[-3:] if e > 0]))
        if any(monthly_essential_lst[-3:]) else avg_exp_3m * 0.60
    )
    avg_disc    = float(np.mean(monthly_disc_list[-3:])) if any(monthly_disc_list[-3:]) else 0.0
    disc_ratio  = avg_disc / max(avg_exp_3m, 1.0)

    # Lifestyle drift: normalised slope of discretionary over 6 months
    lifestyle_drift = _slope(monthly_disc_list) / max(avg_exp_6m, 1.0)

    # ── Contribution streak (consecutive recent months with net >= required) ──
    streak = 0
    for net in reversed(monthly_net):
        if net >= required_monthly_raw:
            streak += 1
        else:
            break
    missed = sum(1 for n in monthly_net if n < required_monthly_raw)

    # ── Anomalies (amount > 3× user median in last 3 months) ──────────────────
    median_3m        = float(np.median(all_amounts_3m)) if all_amounts_3m else 1.0
    anomaly_count_3m = sum(1 for a in all_amounts_3m if a > median_3m * 3)

    # ── Balance & liquidity ───────────────────────────────────────────────────
    total_balance = float(
        db.query(F.sum(Account.current_balance))
        .filter(Account.user_id == user_id)
        .scalar() or 0.0
    )
    liquidity_buffer_months = total_balance / max(avg_essential, 1.0)

    # ── All active goals (multi-goal context) ──────────────────────────────────
    all_goals = (
        db.query(Goal)
        .filter(Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE)
        .order_by(Goal.priority.asc())
        .all()
    )
    all_goals_summary = []
    for g in all_goals:
        g_t   = float(g.target_amount  or 0)
        g_c   = float(g.current_amount or 0)
        g_rem = max(g_t - g_c, 0.0)
        g_ml  = 12.0
        if g.deadline:
            g_days = (g.deadline - today).days
            g_ml   = max(g_days / 30.44, 0.1)
        g_req = g_rem / g_ml if g_ml > 0 else g_rem
        all_goals_summary.append({
            "goal_id":          g.goal_id,
            "goal_name":        g.goal_name,
            "priority":         int(g.priority or 2),
            "required_monthly": g_req,
            "goal_type":        (g.goal_type or "").lower().strip(),
            "is_current":       g.goal_id == goal.goal_id,
        })

    has_enough_data = len(all_amounts_6m) >= 15 and len(non_zero_exp) >= 2

    # ── Dining / Shopping / Entertainment averages (last 3 months) ───────────
    def _avg3(lst):
        vals = [v for v in lst[-3:] if v > 0]
        return float(np.mean(vals)) if vals else 0.0

    return {
        # Goal
        "goal_id":              goal.goal_id,
        "goal_name":            goal.goal_name,
        "goal_type":            (goal.goal_type or "").lower().strip(),
        "target_amount":        target,
        "current_amount":       current,
        "remaining_amount":     remaining,
        "months_left":          months_left,
        "required_monthly_raw": required_monthly_raw,
        "priority":             priority,
        "progress_pct":         (current / max(target, 1.0)) * 100,
        # Income
        "monthly_income":       monthly_income,
        "income_type":          income_type,
        "income_stability":     income_stability,
        # Expenses
        "monthly_expenses":         monthly_expenses,
        "avg_expenses_3m":          avg_exp_3m,
        "avg_expenses_6m":          avg_exp_6m,
        "std_expenses":             std_exp,
        "expense_volatility_factor": exp_vol_factor,
        "avg_essential_monthly":    avg_essential,
        # Surplus
        "monthly_net":              monthly_net,
        "surplus_3m_avg":           surplus_3m_avg,
        "historical_median_savings": historical_median_savings,
        # Discretionary
        "discretionary_monthly":    avg_disc,
        "discretionary_ratio":      disc_ratio,
        "dining_monthly":           _avg3(monthly_dining_lst),
        "shopping_monthly":         _avg3(monthly_shopping_lst),
        "entertainment_monthly":    _avg3(monthly_entmt_lst),
        "lifestyle_drift":          lifestyle_drift,
        # Behavioral
        "contribution_streak":  streak,
        "missed_saving_months": missed,
        "anomaly_count_3m":     anomaly_count_3m,
        # Balance
        "total_balance":            total_balance,
        "liquidity_buffer_months":  liquidity_buffer_months,
        # Multi-goal
        "all_active_goals":   all_goals_summary,
        "num_competing_goals": max(len(all_goals_summary) - 1, 0),
        # Data quality
        "has_enough_data":  has_enough_data,
        "total_txn_count":  len(all_amounts_6m),
        "months_of_data":   len(non_zero_exp),
    }
