"""
financial_shock_engine/server/routes/shock_routes.py
=====================================================
All REST API endpoints for the Financial Shock Absorption Engine.

Endpoints:
  GET /shock-engine/{user_id}                  → Shock capacity
  GET /shock-engine/{user_id}/goal-impact      → Goal impact scenarios
  GET /shock-engine/{user_id}/savings-insights → Savings opportunities
  GET /shock-engine/{user_id}/insight          → LLM-generated full insight
  POST /shock-engine/{user_id}/simulate        → Custom shock simulation
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from configs.database import get_db
from server.services.shock_capacity_service import get_shock_capacity
from server.services.goal_impact_service import get_goal_impact
from server.services.savings_insight_service import get_savings_insights
from llm.insight_orchestrator import generate_shock_insight, generate_savings_insight

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shock-engine", tags=["Shock Engine"])


# ── Helper ────────────────────────────────────────────────────────────────────

def _wrap(data: dict, success: bool = True) -> dict:
    return {"success": success, "data": data}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{user_id}", summary="Get shock absorption capacity")
def shock_capacity(user_id: int, db: Session = Depends(get_db)):
    """
    Returns shock capacity, resilience label, Monte Carlo balance projections,
    and behavioral signals for a user.
    """
    try:
        result = get_shock_capacity(db, user_id)
        return _wrap(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("shock_capacity error user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Shock capacity computation failed.")


@router.get("/{user_id}/goal-impact", summary="Simulate goal impact after shock")
def goal_impact(
    user_id: int,
    shocks: Optional[str] = Query(
        default=None,
        description="Comma-separated shock amounts in ₹ (e.g. 5000,10000,25000)",
        examples={"default": {"value": "5000,10000,25000"}},
    ),
    db: Session = Depends(get_db),
):
    """
    Simulate how different unexpected expense shocks affect each active goal.
    Provide ?shocks=5000,10000,25000 to test custom amounts.
    """
    try:
        shock_list = None
        if shocks:
            shock_list = [float(s.strip()) for s in shocks.split(",") if s.strip()]
        result = get_goal_impact(db, user_id, shock_amounts=shock_list)
        return _wrap(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("goal_impact error user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Goal impact simulation failed.")


@router.get("/{user_id}/savings-insights", summary="Get savings opportunities")
def savings_insights(user_id: int, db: Session = Depends(get_db)):
    """
    Analyse discretionary spending and return ranked, realistic savings opportunities.
    Capped at 30% of discretionary spend per category.
    """
    try:
        result = get_savings_insights(db, user_id)
        return _wrap(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("savings_insights error user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Savings insight computation failed.")


@router.get("/{user_id}/insight", summary="Get LLM-generated full insight")
def full_insight(user_id: int, db: Session = Depends(get_db)):
    """
    Combines shock capacity + savings analysis → calls Mistral (local Ollama or API)
    → returns a human-readable financial explanation with supporting data.
    """
    try:
        shock   = get_shock_capacity(db, user_id)
        savings = get_savings_insights(db, user_id)
        llm     = generate_shock_insight(shock, savings)

        return _wrap({
            "user_id":        user_id,
            "computed_at":    llm["computed_at"],
            "insight":        llm["insight"],
            "insight_source": llm["insight_source"],
            "shock_summary": {
                "shock_capacity":      shock["shock_capacity"],
                "safe_shock_limit":    shock["safe_shock_limit"],
                "resilience_label":    shock["resilience_label"],
                "resilience_score":    shock["resilience_score"],
                "depletion_risk":      shock["depletion_risk"],
                "current_balance":     shock["current_balance"],
                "projected_end_balance": shock["projected_end_balance"],
                "top_categories":      shock["top_categories"],
            },
            "savings_summary": {
                "total_monthly_saveable": savings["total_monthly_saveable"],
                "top_risk_categories":   savings["top_risk_categories"],
                "opportunities":         savings["opportunities"],
            },
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("full_insight error user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Insight generation failed.")


@router.post("/{user_id}/simulate", summary="Simulate a specific shock amount")
def custom_simulate(
    user_id: int,
    shock_amount: float = Query(..., description="Custom shock amount in ₹", gt=0),
    db: Session = Depends(get_db),
):
    """
    Test exactly what happens to goals and balance if a specific expense hits today.
    """
    try:
        result = get_goal_impact(db, user_id, shock_amounts=[shock_amount])
        return _wrap(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("custom_simulate error user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Custom simulation failed.")
