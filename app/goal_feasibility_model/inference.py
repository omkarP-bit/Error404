"""
ml_models/goal_feasibility_model/inference.py
==============================================
Public API for the Goal Probability Engine.

Primary entrypoint  : run_goal_assessment(db, user_id, goal_id)
Bulk entrypoint     : run_bulk_assessment(db, user_id)
Model retrain       : retrain_model()
Legacy compat       : assess_goal_feasibility(...) — kept for old router calls
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_models.goal_feasibility_model.probability_engine import (
    goal_probability_engine, GoalProbabilityEngine
)
from ml_models.goal_feasibility_model.model import GoalProbabilityModel


def run_goal_assessment(db, user_id: int, goal_id: int) -> dict:
    """Full 10-step Goal Probability Engine pipeline for one goal."""
    return goal_probability_engine.run(db, user_id, goal_id)


def run_bulk_assessment(db, user_id: int) -> list[dict]:
    """Assess all active goals for a user in one call."""
    return goal_probability_engine.run_bulk(db, user_id)


def retrain_model() -> dict:
    """Force re-train the HistGBT classifier on a fresh synthetic dataset."""
    import ml_models.goal_feasibility_model.probability_engine as pe
    pe._model = None   # reset singleton
    m = GoalProbabilityModel()
    report = m.train(verbose=True)
    pe._model = m
    return report


# ── Legacy backward-compat shim (old router still calls this) ─────────────────
def assess_goal_feasibility(
    monthly_surplus: float,
    expense_volatility: float,
    target_amount: float,
    deadline_months: int,
) -> dict:
    """
    Backward-compatible wrapper.
    Uses heuristic formula (no DB required).
    """
    monthly_required  = target_amount / max(deadline_months, 1)
    safe_surplus      = monthly_surplus * 0.85
    feasibility_ratio = safe_surplus / max(monthly_required, 1)
    prob = max(0.05, min(0.95, 0.15 + 0.55 * feasibility_ratio))
    pct  = int(prob * 100)

    if feasibility_ratio >= 1.5:
        interp = "High feasibility — on track"
    elif feasibility_ratio >= 1.0:
        interp = "Moderate feasibility — achievable with discipline"
    elif feasibility_ratio >= 0.7:
        interp = "Low feasibility — behind schedule"
    else:
        interp = "At risk — significant changes needed"

    return {
        "feasibility_score":   pct,
        "probability":         round(prob, 4),
        "interpretation":      interp,
        "feasibility_ratio":   round(feasibility_ratio, 3),
        "monthly_required":    round(monthly_required, 2),
        "safe_surplus":        round(safe_surplus, 2),
    }


if __name__ == "__main__":
    result = assess_goal_feasibility(
        monthly_surplus=50000, expense_volatility=8000,
        target_amount=300000, deadline_months=8
    )
    print(result)

