"""
ml_models/goal_feasibility_model/feature_builder.py
====================================================
Schema v2.0 Compatible Feature Extraction Engine.

Derives all 28 ML features from live SQLAlchemy DB without schema changes.
Every field marked "DERIVED" means it does NOT exist as a DB column and is
computed on-the-fly from existing v2.0 tables.

Compatibility Checklist (v2.0 audit):
  ✅ transactions.amount, txn_type, category, is_recurring, confidence_score
  ✅ transactions.txn_timestamp  (used for time-window aggregations)
  ✅ budget_profiles.avg_monthly_surplus, expense_volatility, baseline_expense
  ✅ accounts.current_balance  (used as available_balance proxy)
  ✅ users.monthly_income, income_type, risk_profile
  ✅ goals.target_amount, current_amount, deadline, priority, goal_type
  ✅ transaction_patterns.avg_amount, std_amount (behavioral consistency)
  ✅ financial_health_ratings.score  (latest rating per user)
  ⚠  is_anomalous  → DERIVED: amount > 3× median for that user
  ⚠  anomaly_score → DERIVED: z-score of transaction amount
  ⚠  monthly_surplus → DERIVED: income − avg_monthly_expenses (per window)
  ⚠  available_balance → accounts.current_balance (direct proxy)
  ⚠  cat_method  → NOT required for goal prediction (dropped)

Feature Groups:
  A (5)  — Goal: target, remaining, time, required rate, progress
  B (7)  — Capacity: income, surplus, volatility, balance, safety, rate, ratio
  C (7)  — Behaviour: expenses, vol_ratio, anomalies, recurring, discretionary, freq, hvt
  D (3)  — Drift: category slope for Dining / Shopping / Entertainment
  E (3)  — Stability: contribution streak, missed months, behavioral consistency
  F (3)  — Health: health score, spend acceleration, income stability
"""
from __future__ import annotations

import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import date, datetime, timedelta

import numpy as np

# ── Canonical feature name list (order is the contract between builder + model) ─
FEATURE_NAMES = [
    # A — Goal
    "log_target_amount",        # 0  log1p(target_amount)
    "log_remaining_amount",     # 1  log1p(remaining)
    "months_left",              # 2  days_to_deadline / 30.44
    "monthly_required",         # 3  remaining / months_left
    "progress_pct",             # 4  current / target
    # B — Capacity
    "monthly_income",           # 5  users.monthly_income
    "avg_monthly_surplus",      # 6  budget_profiles or derived
    "expense_volatility",       # 7  budget_profiles.expense_volatility
    "current_balance",          # 8  sum(accounts.current_balance)
    "safe_surplus",             # 9  avg_surplus × 0.85
    "savings_rate",             # 10 safe_surplus / monthly_income
    "feasibility_ratio",        # 11 safe_surplus / monthly_required
    # C — Transaction Behaviour
    "avg_monthly_expenses",     # 12 debit_sum_3m / 3
    "expense_volatility_ratio", # 13 exp_volatility / avg_monthly_expenses
    "anomaly_count_3m",         # 14 DERIVED: amount > 3×median  (last 90 days)
    "recurring_expense_ratio",  # 15 recurring_txns / total_txns (last 90 days)
    "discretionary_ratio",      # 16 (Dining+Shopping+Entertainment) / debit_3m
    "txn_frequency",            # 17 txn_count_3m / 3
    "high_value_txn_count",     # 18 txns above 90th percentile (last 90 days)
    # D — Category Drift (normalised slope over 6-month window)
    "dining_slope",             # 19 DERIVED: linear slope Dining spend (norm)
    "shopping_slope",           # 20 DERIVED: linear slope Shopping spend (norm)
    "entertainment_slope",      # 21 DERIVED: linear slope Entertainment spend (norm)
    # E — Stability & Momentum
    "contribution_streak",      # 22 DERIVED: consecutive months surplus >= required
    "missed_saving_months",     # 23 DERIVED: months where surplus < required (12m)
    "behavioral_consistency",   # 24 DERIVED: 1 − CV from transaction_patterns
    # F — Health & Macro
    "health_score",             # 25 financial_health_ratings.score / 100
    "debit_ratio_3m_6m",        # 26 DERIVED: debit_3m / (debit_6m/2) (acceleration)
    "income_stability",         # 27 DERIVED: 1.0 salaried / 0.7 self-emp / 0.6 freelance
]

DISCRETIONARY_CATS = {"Food & Dining", "Shopping", "Entertainment"}
SAFETY_FACTOR      = 0.85   # conservative multiplier on surplus


# ────────────────────────────────────────────────────────────────────────────
# Helper: linear slope
# ────────────────────────────────────────────────────────────────────────────
def _slope(series: list[float]) -> float:
    """OLS slope of a series; returns 0 if too short."""
    n = len(series)
    if n < 2:
        return 0.0
    x  = list(range(n))
    xm = sum(x) / n
    ym = sum(series) / n
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, series))
    den = sum((xi - xm) ** 2 for xi in x) + 1e-9
    return num / den


# ────────────────────────────────────────────────────────────────────────────
# Main feature builder
# ────────────────────────────────────────────────────────────────────────────
def build_feature_vector(db, user_id: int, goal) -> dict:
    """
    Extract the full 28-feature vector for one user × goal pair.
    Returns an ordered dict keyed by FEATURE_NAMES.
    All DB queries are read-only; no schema mutations.
    """
    from sqlalchemy import func as F
    from app.models import Transaction, Account, BudgetProfile
    from app.models.financial_health_rating import FinancialHealthRating
    from app.models.transaction_pattern import TransactionPattern
    from app.models.user import User
    from app.models.enums import TxnType, IncomeType

    today = date.today()
    now   = datetime.utcnow()
    c3m   = now - timedelta(days=90)
    c6m   = now - timedelta(days=180)
    c12m  = now - timedelta(days=365)

    # ── User ─────────────────────────────────────────────────────────────────
    user           = db.query(User).filter(User.user_id == user_id).first()
    monthly_income = float(user.monthly_income or 0) if user else 0.0

    # ── A. Goal ───────────────────────────────────────────────────────────────
    target    = float(goal.target_amount  or 0)
    current   = float(goal.current_amount or 0)
    remaining = max(target - current, 0.0)

    months_left = 12.0
    if goal.deadline:
        days_left   = (goal.deadline - today).days
        months_left = max(days_left / 30.44, 0.01)

    monthly_required = remaining / months_left if months_left > 0 else remaining

    # ── B. Financial Capacity ─────────────────────────────────────────────────
    bp = (db.query(BudgetProfile)
          .filter(BudgetProfile.user_id == user_id)
          .first())

    avg_surplus    = float(bp.avg_monthly_surplus if bp else 0.0)
    exp_volatility = float(bp.expense_volatility  if bp else 0.0)

    # Derive surplus from live transactions if budget profile is blank
    debit_3m = float(
        db.query(F.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id,
                Transaction.txn_type == TxnType.DEBIT,
                Transaction.txn_timestamp >= c3m)
        .scalar() or 0.0
    )
    avg_monthly_expenses = debit_3m / 3.0

    if avg_surplus == 0.0 and monthly_income > 0:
        avg_surplus = max(monthly_income - avg_monthly_expenses, 0.0)

    safe_surplus      = avg_surplus * SAFETY_FACTOR
    savings_rate      = safe_surplus / monthly_income if monthly_income > 0 else 0.0
    feasibility_ratio = safe_surplus / max(monthly_required, 1.0)

    total_balance = float(
        db.query(F.sum(Account.current_balance))
        .filter(Account.user_id == user_id)
        .scalar() or 0.0
    )

    # ── C. Transaction Behaviour ──────────────────────────────────────────────
    debit_6m = float(
        db.query(F.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id,
                Transaction.txn_type == TxnType.DEBIT,
                Transaction.txn_timestamp >= c6m)
        .scalar() or 0.0
    )

    # Anomaly proxy: transactions with amount > 3× user's 3-month median
    amt_rows   = db.query(Transaction.amount).filter(
        Transaction.user_id == user_id,
        Transaction.txn_type == TxnType.DEBIT,
        Transaction.txn_timestamp >= c3m,
    ).all()
    amounts_3m = [float(r[0]) for r in amt_rows]
    median_amt = float(np.median(amounts_3m)) if amounts_3m else 1.0
    anomaly_threshold = median_amt * 3.0

    anomaly_count_3m = sum(1 for a in amounts_3m if a > anomaly_threshold)

    total_debits_count = len(amounts_3m) or 1
    recurring_count = int(
        db.query(F.count(Transaction.txn_id))
        .filter(Transaction.user_id == user_id,
                Transaction.is_recurring == True,
                Transaction.txn_timestamp >= c3m)
        .scalar() or 0
    )
    recurring_ratio = recurring_count / total_debits_count

    disc_sum = float(
        db.query(F.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id,
                Transaction.txn_type == TxnType.DEBIT,
                Transaction.category.in_(list(DISCRETIONARY_CATS)),
                Transaction.txn_timestamp >= c3m)
        .scalar() or 0.0
    )
    discretionary_ratio = disc_sum / max(debit_3m, 1.0)

    txn_frequency    = total_debits_count / 3.0
    p90              = float(np.percentile(amounts_3m, 90)) if amounts_3m else 0.0
    high_value_count = sum(1 for a in amounts_3m if a > p90)

    exp_vol_ratio = exp_volatility / max(avg_monthly_expenses, 1.0)

    # ── D. Category Drift ─────────────────────────────────────────────────────
    def _cat_slope(cat: str) -> float:
        monthly: list[float] = []
        for i in range(5, -1, -1):   # oldest → newest
            s = now - timedelta(days=30 * (i + 1))
            e = now - timedelta(days=30 * i)
            v = float(
                db.query(F.sum(Transaction.amount))
                .filter(Transaction.user_id == user_id,
                        Transaction.txn_type == TxnType.DEBIT,
                        Transaction.category == cat,
                        Transaction.txn_timestamp >= s,
                        Transaction.txn_timestamp < e)
                .scalar() or 0.0
            )
            monthly.append(v)
        raw_slope = _slope(monthly)
        return raw_slope / max(avg_monthly_expenses, 1.0)   # normalise

    dining_slope        = _cat_slope("Food & Dining")
    shopping_slope      = _cat_slope("Shopping")
    entertainment_slope = _cat_slope("Entertainment")

    # ── E. Stability & Momentum ───────────────────────────────────────────────
    contribution_streak  = 0
    missed_saving_months = 0
    _streak_cur          = 0

    for i in range(11, -1, -1):   # 12 months, oldest first
        s   = now - timedelta(days=30 * (i + 1))
        e   = now - timedelta(days=30 * i)
        cr  = float(db.query(F.sum(Transaction.amount))
                    .filter(Transaction.user_id == user_id,
                            Transaction.txn_type == TxnType.CREDIT,
                            Transaction.txn_timestamp >= s,
                            Transaction.txn_timestamp < e)
                    .scalar() or 0.0)
        ex  = float(db.query(F.sum(Transaction.amount))
                    .filter(Transaction.user_id == user_id,
                            Transaction.txn_type == TxnType.DEBIT,
                            Transaction.txn_timestamp >= s,
                            Transaction.txn_timestamp < e)
                    .scalar() or 0.0)
        net = cr - ex
        if net >= monthly_required:
            _streak_cur += 1
            contribution_streak = _streak_cur
        else:
            missed_saving_months += 1
            _streak_cur = 0

    # Behavioral consistency from transaction_patterns
    tps = db.query(TransactionPattern).filter(
        TransactionPattern.user_id == user_id).all()

    if tps:
        cvs = [p.std_amount / max(p.avg_amount, 1.0) for p in tps if p.avg_amount > 0]
        behavioral_consistency = 1.0 - min(float(np.mean(cvs)) if cvs else 0.5, 1.0)
    elif len(amounts_3m) >= 5:
        cv = float(np.std(amounts_3m)) / (float(np.mean(amounts_3m)) + 1e-9)
        behavioral_consistency = 1.0 - min(cv, 1.0)
    else:
        behavioral_consistency = 0.5

    # ── F. Health & Macro ─────────────────────────────────────────────────────
    latest_hr = (db.query(FinancialHealthRating)
                 .filter(FinancialHealthRating.user_id == user_id)
                 .order_by(FinancialHealthRating.created_at.desc())
                 .first())
    health_score = float(latest_hr.score / 100.0) if latest_hr else 0.5

    # Spend acceleration: if debit_3m > debit_6m/2 spend is rising
    debit_ratio_3m_6m = (debit_3m / max(debit_6m / 2, 1.0)) if debit_6m else 1.0

    income_stability = 1.0
    if user:
        if user.income_type == IncomeType.SELF_EMPLOYED:
            income_stability = 0.7
        elif str(user.income_type).upper().endswith("FREELANCER"):
            income_stability = 0.6

    # ── Assemble ─────────────────────────────────────────────────────────────
    return {
        "log_target_amount":        math.log1p(target),
        "log_remaining_amount":     math.log1p(remaining),
        "months_left":              months_left,
        "monthly_required":         monthly_required,
        "progress_pct":             current / max(target, 1.0),
        "monthly_income":           monthly_income,
        "avg_monthly_surplus":      avg_surplus,
        "expense_volatility":       exp_volatility,
        "current_balance":          total_balance,
        "safe_surplus":             safe_surplus,
        "savings_rate":             savings_rate,
        "feasibility_ratio":        feasibility_ratio,
        "avg_monthly_expenses":     avg_monthly_expenses,
        "expense_volatility_ratio": exp_vol_ratio,
        "anomaly_count_3m":         float(anomaly_count_3m),
        "recurring_expense_ratio":  recurring_ratio,
        "discretionary_ratio":      discretionary_ratio,
        "txn_frequency":            txn_frequency,
        "high_value_txn_count":     float(high_value_count),
        "dining_slope":             dining_slope,
        "shopping_slope":           shopping_slope,
        "entertainment_slope":      entertainment_slope,
        "contribution_streak":      float(contribution_streak),
        "missed_saving_months":     float(missed_saving_months),
        "behavioral_consistency":   behavioral_consistency,
        "health_score":             health_score,
        "debit_ratio_3m_6m":        float(debit_ratio_3m_6m),
        "income_stability":         income_stability,
    }
