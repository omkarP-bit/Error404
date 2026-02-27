"""
ai_projection_engine/server/routes/savings_routes.py
=====================================================
REST endpoints for savings opportunity analysis.

GET /savings-opportunities/{user_id}
    → Per-category ₹ savings simulations + goal impact evaluation
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from server.core.database import get_db
from server.services.savings_opportunity_service import get_savings_opportunities

router = APIRouter(prefix="/savings-opportunities", tags=["Savings"])


@router.get(
    "/{user_id}",
    summary="Realistic savings opportunities per discretionary category",
    response_description=(
        "Counterfactual ₹ savings simulations for 5/10/15/20% spend reductions "
        "plus goal feasibility impact."
    ),
)
def get_savings(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Counterfactual savings analysis:

    - Simulates 5%, 10%, 15%, 20% spend reductions on each discretionary category.
    - Outputs actual **₹ amounts** — no percentages in the response.
    - Fixed expenses (Rent, EMI, Insurance, …) are never included.
    - Reductions are capped at 25% to keep suggestions realistic.

    Each opportunity includes:
    - `current_spend_this_month`     → actual spend in current month
    - `scenarios`                    → reduction scenarios with ₹ impact
    - `best_scenario`                → recommended reduction (10% by default)
    - `insight`                      → one-line ₹-based summary string

    Also returns `goal_impact`:
    - Monthly goal contribution requirements vs achievable savings
    - `goal_feasibility_flag` → True if savings can cover all goals
    """
    try:
        data = get_savings_opportunities(db, user_id)
        return {"status": "success", "data": data}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
