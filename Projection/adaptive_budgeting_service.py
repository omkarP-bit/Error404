"""
ai_projection_engine/server/services/adaptive_budgeting_service.py
===================================================================
Computes and persists adaptive category budgets for the current month.

Formula (per category):
  AdaptiveBudget = 0.50 × Median(last 3 months spend)
                 + 0.30 × EMA(last 30 days spend)
                 + 0.20 × CurrentMonthPaceAdjustment

The budget is dynamic: it auto-adjusts to actual user behaviour
and does NOT use static limits.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from constants import (
    ADAPTIVE_BUDGET_WEIGHTS,
    DISCRETIONARY_EXPENSE_CATEGORIES,
    FIXED_EXPENSE_CATEGORIES,
)
from database import AdaptiveBudget
from feature_engineering import build_all_features


# ── Budget Formula ─────────────────────────────────────────────────────────────

def _apply_formula(median_3m: float, ema_30d: float, current_pace: float) -> float:
    """
    Core adaptive budget formula.
    All three inputs are expressed in ₹ (monthly equivalent).
    """
    w = ADAPTIVE_BUDGET_WEIGHTS
    return (
        w["median_3m"] * median_3m
        + w["ema_30d"] * ema_30d
        + w["pace_adj"] * current_pace
    )


# ── Main Service ───────────────────────────────────────────────────────────────

def get_adaptive_budgets(db: Session, user_id: int) -> List[Dict]:
    """
    Compute adaptive budgets for every spending category active this month.
    Results are upserted to the *adaptive_budgets* table and returned as a list.

    Returned dict keys per category:
      category, month_year, median_spend_3m, ema_30d, current_month_pace,
      adaptive_budget, actual_spend_so_far, budget_remaining,
      is_over_budget, is_fixed_expense, is_discretionary
    """
    features = build_all_features(db, user_id)
    current_month = features["current_month"]

    if not features["has_data"]:
        return []

    median_3m = features["median_3m_spend"]
    ema_30d = features["ema_30d"]
    pace = features["current_month_pace"]
    df = features["df"]

    all_categories = set(median_3m) | set(ema_30d) | set(pace)
    budgets: List[Dict] = []

    for cat in sorted(all_categories):
        m3 = median_3m.get(cat, 0.0)
        e30 = ema_30d.get(cat, m3)      # Fallback: use median if no recent data
        p = pace.get(cat, m3)            # Fallback: use median if month just started

        adaptive = round(_apply_formula(m3, e30, p), 2)

        # Actual spend so far this month for this category
        cur_spend = float(
            df[
                (df["month_year"] == current_month) & (df["category"] == cat)
            ]["amount"].sum()
        )

        record = {
            "user_id": user_id,
            "category": cat,
            "month_year": current_month,
            "median_spend_3m": round(m3, 2),
            "ema_30d": round(e30, 2),
            "current_month_pace": round(p, 2),
            "adaptive_budget": adaptive,
            "actual_spend_so_far": round(cur_spend, 2),
            "budget_remaining": round(max(adaptive - cur_spend, 0.0), 2),
            "is_over_budget": cur_spend > adaptive,
            "is_fixed_expense": cat in FIXED_EXPENSE_CATEGORIES,
            "is_discretionary": cat in DISCRETIONARY_EXPENSE_CATEGORIES,
        }
        budgets.append(record)
        _upsert_budget(db, record)

    db.commit()

    # Sort: over-budget first, then by adaptive_budget descending
    budgets.sort(key=lambda x: (-int(x["is_over_budget"]), -x["adaptive_budget"]))
    return budgets


# ── DB Upsert ──────────────────────────────────────────────────────────────────

def _upsert_budget(db: Session, record: Dict) -> None:
    existing = (
        db.query(AdaptiveBudget)
        .filter_by(
            user_id=record["user_id"],
            category=record["category"],
            month_year=record["month_year"],
        )
        .first()
    )
    if existing:
        existing.median_spend_3m = record["median_spend_3m"]
        existing.ema_30d = record["ema_30d"]
        existing.current_month_pace = record["current_month_pace"]
        existing.adaptive_budget = record["adaptive_budget"]
        existing.actual_spend_so_far = record["actual_spend_so_far"]
        existing.updated_at = datetime.utcnow()
    else:
        db.add(
            AdaptiveBudget(
                user_id=record["user_id"],
                category=record["category"],
                month_year=record["month_year"],
                median_spend_3m=record["median_spend_3m"],
                ema_30d=record["ema_30d"],
                current_month_pace=record["current_month_pace"],
                adaptive_budget=record["adaptive_budget"],
                actual_spend_so_far=record["actual_spend_so_far"],
            )
        )
