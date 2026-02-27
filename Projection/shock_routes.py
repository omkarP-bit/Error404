"""
server/routes/shock_routes.py
==============================
Shock Absorption Engine endpoints — mounted on the existing projection engine server (port 8001).

  GET  /shock-engine/{user_id}                  → Shock capacity + resilience
  GET  /shock-engine/{user_id}/goal-impact       → Goal delay simulations
  GET  /shock-engine/{user_id}/savings-insights  → Savings opportunities
  GET  /shock-engine/{user_id}/insight           → Mistral LLM explanation
  POST /shock-engine/{user_id}/simulate          → Custom shock amount
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from shock_service import (
    get_shock_capacity,
    get_goal_impact,
    get_savings_insights,
    get_llm_insight,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shock-engine", tags=["Shock Absorption Engine"])


def _ok(data: dict) -> dict:
    return {"success": True, "data": data}


@router.get("/{user_id}", summary="Shock absorption capacity")
def shock_capacity(user_id: int, db: Session = Depends(get_db)):
    try:
        return _ok(get_shock_capacity(db, user_id))
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error("shock_capacity user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(500, "Shock capacity computation failed.")


@router.get("/{user_id}/goal-impact", summary="Goal delay simulation")
def goal_impact(
    user_id: int,
    shocks: Optional[str] = Query(
        default=None,
        description="Comma-separated ₹ amounts e.g. 5000,10000,25000",
    ),
    db: Session = Depends(get_db),
):
    try:
        shock_list = [float(s.strip()) for s in shocks.split(",") if s.strip()] if shocks else None
        return _ok(get_goal_impact(db, user_id, shock_amounts=shock_list))
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error("goal_impact user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(500, "Goal impact simulation failed.")


@router.get("/{user_id}/savings-insights", summary="Savings opportunities")
def savings_insights(user_id: int, db: Session = Depends(get_db)):
    try:
        return _ok(get_savings_insights(db, user_id))
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error("savings_insights user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(500, "Savings insight failed.")


@router.get("/{user_id}/insight", summary="Mistral LLM shock insight")
def llm_insight(user_id: int, db: Session = Depends(get_db)):
    try:
        return _ok(get_llm_insight(db, user_id))
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error("llm_insight user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(500, "LLM insight failed.")


@router.post("/{user_id}/simulate", summary="Simulate a specific shock amount")
def custom_simulate(
    user_id: int,
    shock_amount: float = Query(..., description="Shock amount in ₹", gt=0),
    db: Session = Depends(get_db),
):
    try:
        return _ok(get_goal_impact(db, user_id, shock_amounts=[shock_amount]))
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error("custom_simulate user=%d: %s", user_id, e, exc_info=True)
        raise HTTPException(500, "Custom simulation failed.")
