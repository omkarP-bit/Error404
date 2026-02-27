"""
ai_projection_engine/server/routes/forecast_routes.py
======================================================
REST endpoints for probabilistic forecast and adaptive budgets.

GET  /forecast/{user_id}
     → Confidence-band forecast (cached, TTL-based)

GET  /forecast/{user_id}/fresh
     → Force recompute (bypass cache)

GET  /forecast/{user_id}/adaptive-budgets
     → Per-category adaptive budgets for current month
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from server.core.database import get_db
from server.services.adaptive_budgeting_service import get_adaptive_budgets
from server.services.confidence_band_service import get_or_create_forecast_snapshot
from server.services.probabilistic_forecast_service import run_probabilistic_forecast

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get(
    "/{user_id}",
    summary="Probabilistic forecast with P25 / P50 / P90 confidence bands",
    response_description="Projected month-end spend, balance bands, and depletion risk.",
)
def get_forecast(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns cached (or freshly computed) Monte Carlo forecast:
    - `projected_month_spend` → lower / median / upper bands
    - `projected_balance_at_month_end` → balance confidence bands
    - `depletion_risk_flag` → True if balance may fall below safe threshold
    - `category_breakdown` → per-category P25/P50/P90 spend projection
    - `from_cache` → whether this result was served from the snapshot cache
    """
    try:
        data = get_or_create_forecast_snapshot(db, user_id)
        return {"status": "success", "data": data}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get(
    "/{user_id}/fresh",
    summary="Force-recompute forecast (bypasses cache)",
    response_description="Fresh Monte Carlo forecast result.",
)
def get_forecast_fresh(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Runs a full Monte Carlo simulation regardless of cache state.
    Use this after bulk transaction imports or manual recalibration.
    """
    try:
        data = run_probabilistic_forecast(db, user_id)
        return {"status": "success", "data": data}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get(
    "/{user_id}/adaptive-budgets",
    summary="Adaptive category budgets for the current month",
    response_description=(
        "Per-category adaptive budgets, actual spend so far, and over-budget flags."
    ),
)
def get_budgets(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Computes and returns adaptive budgets using the formula:
    `AdaptiveBudget = 0.50 × Median(3m) + 0.30 × EMA(30d) + 0.20 × CurrentPace`

    Each item includes:
    - `adaptive_budget`     → computed ₹ budget for the category
    - `actual_spend_so_far` → spent so far this month
    - `budget_remaining`    → headroom left
    - `is_over_budget`      → True if already over adaptive limit
    - `is_discretionary`    → whether the category can be reduced
    """
    try:
        budgets = get_adaptive_budgets(db, user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "count": len(budgets),
            "data": budgets,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
