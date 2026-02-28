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
from app.engines.goal_timeline_simulator import simulate_goal_timeline

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


@api_router.get("/goals/list")
async def list_user_goals(
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    """
    Fetch all active goals for a user with timeline simulation data.
    
    Returns:
        {
            'success': true,
            'goals': [
                {
                    'goal_id': int,
                    'goal_name': str,
                    'goal_type': str,
                    'target_amount': float,
                    'current_amount': float,
                    'monthly_contribution': float,
                    'deadline': date,
                    'progress_pct': float,
                    'timeline': {
                        'months_to_target': int,
                        'months_to_deadline': int,
                        'delta_months': int,
                        'status': 'on_time|early|late|impossible',
                        'feasibility_pct': float,
                    },
                    'feasibility_score': Optional[float],
                    'health_tag': Optional[str],
                }
            ]
        }
    """
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return JSONResponse({"success": False, "error": "User not found"}, status_code=404)
        
        goals = db.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.status == "active"
        ).all()
        
        goals_payload = []
        for goal in goals:
            timeline = simulate_goal_timeline(goal)
            
            goals_payload.append({
                "goal_id": goal.goal_id,
                "goal_name": goal.goal_name,
                "goal_type": goal.goal_type,
                "target_amount": round(goal.target_amount, 2),
                "current_amount": round(goal.current_amount, 2),
                "monthly_contribution": round(goal.monthly_contribution, 2),
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "priority": goal.priority,
                "progress_pct": goal.progress_pct,
                "timeline": timeline,
                "feasibility_score": round(goal.feasibility_score, 2) if goal.feasibility_score else None,
                "health_tag": goal.health_tag,
                "feasibility_note": goal.feasibility_note,
            })
        
        # Sort by priority (1=High first) then by deadline
        goals_payload.sort(key=lambda g: (g["priority"], g["deadline"] or "9999-12-31"))
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "total": len(goals_payload),
            "goals": goals_payload,
        })
    except Exception as exc:
        import traceback
        return JSONResponse({
            "success": False,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }, status_code=500)


@api_router.post("/goals/create")
async def create_goal(
    user_id: int = Form(1),
    goal_name: str = Form(...),
    goal_type: str = Form(...),
    target_amount: float = Form(...),
    current_saved: float = Form(0.0),
    monthly_contribution: float = Form(None),
    deadline: str = Form(None),
    priority: int = Form(2),
    db: Session = Depends(get_db),
):
    """
    Create a new goal for a user.
    
    Now supports auto-calculation of monthly SIP based on current_saved.
    
    Parameters:
        user_id: int
        goal_name: str (e.g., "Emergency Fund")
        goal_type: str (e.g., "emergency_fund", "retirement", "short_term")
        target_amount: float
        current_saved: float (how much already saved, used for SIP calculation)
        monthly_contribution: float or None (if None, will be calculated)
        deadline: str or None (YYYY-MM-DD format, required if calculating SIP)
        priority: int (1=High, 2=Medium, 3=Low)
    
    Returns:
        {
            'success': true,
            'goal_id': int,
            'monthly_contribution': float (actual/calculated),
            'sip_calculated': bool,
            'message': 'Goal created successfully'
        }
    """
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return JSONResponse({"success": False, "error": "User not found"}, status_code=404)
        
        from datetime import datetime
        deadline_date = None
        sip_calculated = False
        final_sip = monthly_contribution or 0.0
        
        if deadline:
            try:
                deadline_date = datetime.fromisoformat(deadline).date()
            except:
                return JSONResponse(
                    {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"},
                    status_code=400
                )
        
        # If monthly_contribution not provided, calculate it
        if monthly_contribution is None and deadline_date:
            from app.engines.sip_calculator import calculate_required_sip
            from app.engines.goal_timeline_simulator import get_expected_return
            
            annual_return = get_expected_return(goal_type)
            calc_result = calculate_required_sip(
                target_amount=target_amount,
                current_saved=current_saved,
                deadline_date=deadline_date,
                expected_annual_return=annual_return,
            )
            final_sip = calc_result['required_monthly_sip']
            sip_calculated = True
        elif monthly_contribution is None:
            return JSONResponse(
                {
                    "success": False,
                    "error": "Either monthly_contribution or deadline must be provided for SIP calculation",
                },
                status_code=400,
            )
        
        # Create the new goal
        new_goal = Goal(
            user_id=user_id,
            goal_name=goal_name,
            goal_type=goal_type,
            target_amount=target_amount,
            current_amount=current_saved,  # Set to current_saved
            monthly_contribution=final_sip,
            deadline=deadline_date,
            priority=priority,
            status="active",
        )
        
        db.add(new_goal)
        db.flush()  # Flush to get the ID
        
        # Check if emergency fund exists, if not and this isn't one, create it
        if goal_type and 'emergency' not in goal_type.lower():
            emergency_exists = db.query(Goal).filter(
                Goal.user_id == user_id,
                Goal.goal_type.ilike('%emergency%'),
                Goal.status == 'active',
            ).first()
            
            if not emergency_exists:
                # Auto-create emergency fund
                from app.models import Account
                accounts = db.query(Account).filter(Account.user_id == user_id).all()
                total_balance = sum(acc.balance for acc in accounts) if accounts else 0
                
                # Default target: 3 months of expenses or 50k
                emergency_target = max(150000.0, total_balance * 0.5)  # 3x monthly avg or 50% of current balance
                
                emergency_fund = Goal(
                    user_id=user_id,
                    goal_name="Emergency Fund",
                    goal_type="emergency_fund",
                    target_amount=emergency_target,
                    current_amount=0.0,
                    monthly_contribution=0.0,  # Will be allocated by priority engine
                    priority=1,  # Highest priority
                    status="active",
                )
                db.add(emergency_fund)
        
        db.commit()
        db.refresh(new_goal)
        
        return JSONResponse({
            "success": True,
            "goal_id": new_goal.goal_id,
            "monthly_contribution": round(final_sip, 2),
            "sip_calculated": sip_calculated,
            "message": "Goal created successfully",
        })
    except Exception as exc:
        db.rollback()
        import traceback
        return JSONResponse({
            "success": False,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }, status_code=500)

