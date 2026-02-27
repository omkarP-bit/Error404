"""
app/routers/goal.py
====================
Routes for the Goal Feasibility Engine v3.0 — Capacity-Constrained Simulation.

  GET  /goal-test                    — UI test page
  POST /api/goal/assess              — Full Monte Carlo pipeline (750 sims)
  POST /api/goal/assess-bulk         — Assess all active goals for a user
  POST /api/goal/counterfactuals     — Scenario simulation only (fast path)
  POST /api/goal/update-progress     — Update current_amount, re-assess
  POST /api/goal/assess-legacy       — Heuristic only (no DB, backward compat)
  POST /api/retrain/goal             — Retrain old HistGBT model (legacy)

Engine (new): ml_models/goal_feasibility_engine/predict_goal_feasibility.py
  - feature_builder         : 6-month DB aggregation
  - surplus_forecaster      : trimmed-mean expense forecast
  - behavioral_constraint   : min(70%×surplus, hist_median, vol_adjusted)
  - allocation_optimizer    : priority-weighted multi-goal LP
  - feasibility_simulator   : Monte Carlo 750 scenarios
  - explanation_generator   : 3-tier savings plan + timeline recalibration
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import User, Goal

router     = APIRouter(prefix="/goal-test", tags=["Goal"])
api_router = APIRouter(prefix="/api", tags=["Goal API"])
templates  = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


# ── UI Route ───────────────────────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
async def goal_test_page(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).limit(10).all()
    goals = db.query(Goal).limit(20).all()
    return templates.TemplateResponse("goal_test.html", {
        "request": request,
        "users":   users,
        "goals":   goals,
        "result":  None,
    })


# ── API Routes ──────────────────────────────────────────────────────────────────────
@api_router.post("/goal/assess")
async def assess_single_goal(
    user_id: int = Form(1),
    goal_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Full 10-step Goal Probability Engine pipeline.

    Returns:
      probability         — 0.0–1.0
      probability_pct     — "78%"
      health_tag          — On Track / Tight / Behind / At Risk
      feasibility_note    — human-readable summary
      top_negative_drivers / top_positive_drivers  (SHAP-style)
      top_impact_transactions                      (attribution)
      category_impact_summary                      (drift per category)
      counterfactuals                              ("if Dining −20%…")
      feature_snapshot                             (key metrics)
    """
    try:
        from ml_models.goal_feasibility_engine.predict_goal_feasibility import (
            predict_goal_feasibility,
        )
        result = predict_goal_feasibility(db=db, user_id=user_id, goal_id=goal_id)
        if "error" in result:
            return JSONResponse({"success": False, "error": result["error"]},
                                status_code=404)
        return JSONResponse({"success": True, "result": result})
    except Exception as exc:
        import traceback
        return JSONResponse({"success": False, "error": str(exc),
                             "trace": traceback.format_exc()}, status_code=500)


@api_router.post("/goal/assess-bulk")
async def assess_goals_bulk(
    user_id: int = Form(1),
    db: Session = Depends(get_db),
):
    """
    Assess all active goals for a user.
    Updates feasibility_score, feasibility_note and health_tag on each Goal row.
    Returns a summary list ordered by probability ascending (most at-risk first).
    """
    try:
        from ml_models.goal_feasibility_engine.predict_goal_feasibility import predict_bulk
        results = predict_bulk(db=db, user_id=user_id)
        if not results:
            return JSONResponse({"success": True, "results": [],
                                 "message": "No active goals found"})
        # Sort: lowest probability first (most at-risk first)
        results.sort(key=lambda r: r.get("probability", 0.5))
        summary = [
            {
                "goal_id":           r.get("goal_id"),
                "goal_name":         r.get("goal_name"),
                "goal_type":         r.get("goal_type"),
                "probability_pct":   r.get("probability_pct"),
                "health_tag":        r.get("health_tag"),
                "risk_level":        r.get("risk_level"),
                "months_left":       r.get("months_left"),
                "monthly_required":  r.get("monthly_required"),
                "monthly_feasible":  r.get("monthly_feasible"),
                "delay_months":      r.get("delay_months"),
                "top_counterfactual": r.get("top_counterfactual"),
                "error":             r.get("error"),
            }
            for r in results
        ]
        return JSONResponse({"success": True, "results": summary,
                             "total": len(summary)})
    except Exception as exc:
        import traceback
        return JSONResponse({"success": False, "error": str(exc),
                             "trace": traceback.format_exc()}, status_code=500)


@api_router.post("/goal/counterfactuals")
async def get_counterfactuals(
    user_id: int = Form(1),
    goal_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Scenario simulation only — faster than full assess.
    Returns counterfactual scenarios with prob delta and timeline shift.
    """
    try:
        from ml_models.goal_feasibility_model.probability_engine import (
            goal_probability_engine, _get_model, _heuristic_probability
        )
        from ml_models.goal_feasibility_model.feature_builder import build_feature_vector
        from ml_models.goal_feasibility_model.counterfactual import simulate_counterfactuals
        from app.models.goal import Goal

        goal = db.query(Goal).filter(
            Goal.goal_id == goal_id, Goal.user_id == user_id
        ).first()
        if not goal:
            return JSONResponse({"success": False, "error": "Goal not found"}, status_code=404)

        feat        = build_feature_vector(db, user_id, goal)
        model       = _get_model()
        base_prob, _ = model.predict_proba(feat)
        scenarios   = simulate_counterfactuals(model, feat, base_prob)

        return JSONResponse({
            "success":          True,
            "goal_id":          goal_id,
            "base_probability": round(base_prob, 4),
            "counterfactuals":  scenarios,
        })
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/goal/update-progress")
async def update_goal_progress(
    user_id:        int   = Form(1),
    goal_id:        int   = Form(...),
    current_amount: float = Form(...),
    db: Session = Depends(get_db),
):
    """
    Update goal.current_amount and immediately re-run the probability engine.
    Persists the updated feasibility_score and health_tag.
    """
    try:
        from app.models.goal import Goal

        goal = db.query(Goal).filter(
            Goal.goal_id == goal_id, Goal.user_id == user_id
        ).first()
        if not goal:
            return JSONResponse({"success": False, "error": "Goal not found"}, status_code=404)

        goal.current_amount = current_amount
        db.commit()

        from ml_models.goal_feasibility_engine.predict_goal_feasibility import (
            predict_goal_feasibility,
        )
        result = predict_goal_feasibility(db=db, user_id=user_id, goal_id=goal_id)
        return JSONResponse({"success": True, "result": result})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


# ── Legacy endpoint (backward compat) ────────────────────────────────────────────
@api_router.post("/goal/assess-legacy")
async def assess_goal_legacy(
    monthly_surplus:    float = Form(...),
    expense_volatility: float = Form(...),
    target_amount:      float = Form(...),
    deadline_months:    int   = Form(...),
):
    """Heuristic-only assess (no DB). Kept for demo/testing convenience."""
    try:
        from ml_models.goal_feasibility_model.inference import assess_goal_feasibility
        result = assess_goal_feasibility(
            monthly_surplus    = monthly_surplus,
            expense_volatility = expense_volatility,
            target_amount      = target_amount,
            deadline_months    = deadline_months,
        )
        return JSONResponse({"success": True, "result": result})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/retrain/goal")
async def retrain_goal(
    db: Session = Depends(get_db),
):
    """
    Force re-train the HistGradientBoosting goal probability model.
    Regenerates synthetic dataset + re-fits model + saves artifacts.
    """
    try:
        from ml_models.goal_feasibility_model.inference import retrain_model
        report = retrain_model()
        return JSONResponse({"success": True, "report": report})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
