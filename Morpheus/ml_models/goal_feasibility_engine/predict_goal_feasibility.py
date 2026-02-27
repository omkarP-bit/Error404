"""
ml_models/goal_feasibility_engine/predict_goal_feasibility.py
==============================================================
Orchestrator — public API entry point for the Goal Feasibility Engine v3.0.

Pipeline (10 steps):
  1  Fetch goal from DB
  2  Build FinancialContext    (feature_builder)
  3  Forecast surplus          (surplus_forecaster)
  4  Multi-goal allocation     (allocation_optimizer)
  5  Behavioral constraints    (behavioral_constraint_model)
  6  Monte Carlo simulation    (feasibility_simulator) — 750 runs
  7  Generate explanation      (explanation_generator)
  8  Persist to existing DB columns: feasibility_score, feasibility_note, health_tag
  9  Audit log to ml_model_runs
  10 Return structured response dict

No new DB columns are created or required.
Existing columns used:
  goals.feasibility_score  → probability (float 0-1)
  goals.feasibility_note   → human-readable summary text
  goals.health_tag         → On Track / Tight / Behind / At Risk

Public functions:
  predict_goal_feasibility(db, user_id, goal_id) -> dict
  predict_bulk(db, user_id)                       -> list[dict]
"""
from __future__ import annotations

import time
from datetime import datetime


def predict_goal_feasibility(db, user_id: int, goal_id: int) -> dict:
    """
    Run the full 10-step pipeline for one user × goal.

    Returns a structured dict containing:
      goal metadata, probability, health_tag, risk_level,
      savings_plan (required/feasible/recommended),
      timeline (original vs realistic),
      capacity (income/expenses/surplus/liquidity),
      top_negative_drivers, top_positive_drivers,
      top_impact_transactions,
      counterfactuals,
      simulation_stats,
      feasibility_note (full text),
      feature_snapshot (legacy compat),
      model_source, model_version, data_sufficiency
    """
    from app.models.goal import Goal
    from ml_models.goal_feasibility_engine.feature_builder import build_financial_context
    from ml_models.goal_feasibility_engine.surplus_forecaster import forecast_surplus
    from ml_models.goal_feasibility_engine.behavioral_constraint_model import compute_feasible_saving
    from ml_models.goal_feasibility_engine.allocation_optimizer import allocate_goals
    from ml_models.goal_feasibility_engine.feasibility_simulator import run_simulation
    from ml_models.goal_feasibility_engine.explanation_generator import generate_explanation

    t0 = time.monotonic()

    # ── Step 1: Fetch goal ────────────────────────────────────────────────────
    goal = db.query(Goal).filter(
        Goal.goal_id == goal_id, Goal.user_id == user_id
    ).first()
    if not goal:
        return {"error": f"Goal {goal_id} not found for user {user_id}"}

    # ── Step 2: Build financial context ──────────────────────────────────────
    ctx = build_financial_context(db, user_id, goal)

    # ── Step 3: Forecast surplus ──────────────────────────────────────────────
    forecast = forecast_surplus(ctx)

    # ── Step 4: Multi-goal allocation ─────────────────────────────────────────
    all_goals      = ctx["all_active_goals"]
    max_pool       = forecast["stable_surplus"] * 0.70
    allocations    = allocate_goals(all_goals, max_pool)
    alloc_frac     = allocations.get(
        goal_id,
        1.0 / max(len(all_goals), 1),
    )

    # ── Step 5: Behavioral constraints ───────────────────────────────────────
    constraint = compute_feasible_saving(ctx, forecast, alloc_frac)

    # ── Step 6: Monte Carlo simulation ───────────────────────────────────────
    simulation = run_simulation(
        current_amount       = ctx["current_amount"],
        target_amount        = ctx["target_amount"],
        months_left          = ctx["months_left"],
        predicted_surplus    = forecast["predicted_surplus"],
        surplus_std          = forecast["surplus_std"],
        max_feasible_monthly = constraint["feasible_monthly"],
        allocated_monthly    = constraint["recommended_monthly"],
        income_stability     = ctx["income_stability"],
    )

    # ── Step 7: Generate explanation ──────────────────────────────────────────
    explanation = generate_explanation(ctx, forecast, constraint, simulation, alloc_frac)

    probability     = simulation["probability"]
    probability_pct = f"{probability * 100:.0f}%"
    health_tag      = explanation["health_tag"]
    latency_ms      = int((time.monotonic() - t0) * 1000)

    # ── Step 8: Persist to existing DB columns ────────────────────────────────
    try:
        goal.feasibility_score = probability
        goal.feasibility_note  = explanation["feasibility_note"][:1990]  # String(2000)
        goal.health_tag        = health_tag
        db.commit()
    except Exception:
        db.rollback()

    # ── Step 9: Audit log ─────────────────────────────────────────────────────
    try:
        from app.models.ml_model_run import MLModelRun
        log = MLModelRun(
            model_name    = "goal_feasibility_engine",
            model_version = "3.0.0",
            confidence    = probability,
            latency_ms    = latency_ms,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()

    # ── Step 10: Return full structured response ──────────────────────────────
    return {
        # Identity
        "goal_id":      goal_id,
        "goal_name":    ctx["goal_name"],
        "goal_type":    ctx["goal_type"],
        "priority":     ctx["priority"],
        "progress_pct": round(ctx["progress_pct"], 1),
        # Core outputs
        "probability":     probability,
        "probability_pct": probability_pct,
        "health_tag":      health_tag,
        "risk_level":      constraint["risk_level"],
        # Three-tier savings plan
        "savings_plan": explanation["savings_plan"],
        # Timeline (original vs realistic)
        "timeline":     explanation["timeline"],
        # Capacity breakdown
        "capacity": {
            "monthly_income":          ctx["monthly_income"],
            "predicted_expenses":      forecast["predicted_expenses"],
            "predicted_surplus":       forecast["predicted_surplus"],
            "stable_surplus":          forecast["stable_surplus"],
            "feasible_saving":         constraint["feasible_monthly"],
            "liquidity_ok":            constraint["liquidity_ok"],
            "buffer_months":           constraint["buffer_months"],
            "expense_volatility_pct":  round(ctx["expense_volatility_factor"] * 100, 1),
            "confidence_lower":        forecast["confidence_lower"],
            "confidence_upper":        forecast["confidence_upper"],
        },
        # Explanation
        "top_negative_drivers":    explanation["top_negative_drivers"],
        "top_positive_drivers":    explanation["top_positive_drivers"],
        "top_impact_transactions": _top_transactions(db, user_id),
        "counterfactuals":         explanation["counterfactuals"],
        "category_impact_summary": {
            "dining_monthly":        round(ctx.get("dining_monthly",        0), 0),
            "shopping_monthly":      round(ctx.get("shopping_monthly",      0), 0),
            "entertainment_monthly": round(ctx.get("entertainment_monthly", 0), 0),
            "discretionary_total":   round(ctx.get("discretionary_monthly", 0), 0),
        },
        # Simulation stats
        "simulation_stats": {
            "n_simulations":              simulation["n_simulations"],
            "pct_5th":                    simulation["pct_5th"],
            "pct_50th":                   simulation["pct_50th"],
            "pct_95th":                   simulation["pct_95th"],
            "expected_completion_months": simulation["expected_completion_months"],
        },
        # Text summary
        "feasibility_note": explanation["feasibility_note"],
        # Metadata
        "data_sufficiency": "full" if ctx["has_enough_data"] else "limited",
        "model_source":     "monte_carlo_simulator",
        "model_version":    "3.0.0",
        # Legacy compatibility: existing template reads feature_snapshot
        "feature_snapshot": {
            "months_left":       ctx["months_left"],
            "monthly_required":  ctx["required_monthly_raw"],
            "safe_surplus":      forecast["stable_surplus"],
            "feasibility_ratio": (
                constraint["feasible_monthly"] / max(ctx["required_monthly_raw"], 1.0)
            ),
            "health_score":      simulation["probability"],
            "contribution_streak": ctx["contribution_streak"],
        },
    }


def predict_bulk(db, user_id: int) -> list:
    """
    Assess all active goals for a user and return a list of result dicts,
    each enriched with top-level bulk summary fields for the UI table.
    """
    from app.models.goal import Goal
    from app.models.enums import GoalStatus

    goals = (
        db.query(Goal)
        .filter(Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE)
        .order_by(Goal.priority.asc())
        .all()
    )

    results = []
    for goal in goals:
        result = predict_goal_feasibility(db, user_id, goal.goal_id)
        if "error" not in result:
            # Hoist convenience fields to top level for bulk table rendering
            result["monthly_required"]    = result["savings_plan"]["required_monthly"]
            result["monthly_feasible"]    = result["savings_plan"]["feasible_monthly"]
            result["months_left"]         = result["timeline"]["months_left"]
            result["realistic_months"]    = result["timeline"]["realistic_months"]
            result["delay_months"]        = result["timeline"]["delay_months"]
            result["top_counterfactual"]  = (
                result["counterfactuals"][0]["scenario"]
                if result["counterfactuals"] else None
            )
            results.append(result)

    return results


# ── Internal helpers ──────────────────────────────────────────────────────────

def _top_transactions(db, user_id: int, limit: int = 5) -> list:
    """Return the top discretionary transactions in the last 90 days by amount."""
    from datetime import timedelta
    from app.models.transaction import Transaction
    from app.models.enums import TxnType
    from app.models.merchant import Merchant

    cutoff    = datetime.utcnow() - timedelta(days=90)
    DISC_CATS = [
        "Food & Dining", "Shopping", "Entertainment",
        "Dining", "Restaurants", "Cafe",
    ]

    txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id        == user_id,
            Transaction.txn_type       == TxnType.DEBIT,
            Transaction.category.in_(DISC_CATS),
            Transaction.txn_timestamp  >= cutoff,
        )
        .order_by(Transaction.amount.desc())
        .limit(limit)
        .all()
    )

    out = []
    for t in txns:
        merchant_name = ""
        if t.merchant_id:
            m = db.query(Merchant).filter(
                Merchant.merchant_id == t.merchant_id
            ).first()
            merchant_name = m.clean_name if m else ""
        out.append({
            "merchant":    merchant_name or t.raw_description or "Unknown",
            "category":    t.category or "—",
            "amount":      float(t.amount),
            "date":        t.txn_timestamp.strftime("%d %b %Y"),
            "impact_score": round(float(t.amount) / 10000.0, 3),
        })
    return out
