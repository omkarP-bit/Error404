"""
ai_projection_engine/server/routes/insights_routes.py
======================================================
REST endpoints for Mistral LLM-generated financial insights.

GET /insights/{user_id}
    → 3-4 sentence ₹-only plain-English financial summary
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from server.core.database import get_db
from server.services.llm_insight_service import get_llm_insights

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get(
    "/{user_id}",
    summary="Mistral LLM-generated simplified financial insights",
    response_description=(
        "Plain-English 3-4 sentence financial insight using only ₹ amounts. "
        "No percentages, no jargon."
    ),
)
def get_insights(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Generates a personalised financial insight using Mistral LLM.

    The insight:
    - Uses only ₹ amounts (never percentages or ratios)
    - Is written in plain everyday language (suitable for non-finance users)
    - Mentions specific spending categories and ₹ figures
    - Is 3-4 sentences maximum

    If Mistral API is unavailable, a template-based fallback is returned.

    Response also includes `supporting_data` with:
    - `top_spending_categories`
    - `over_budget_categories`
    - `saving_potential` (₹)
    - `depletion_risk` (bool)
    """
    try:
        data = get_llm_insights(db, user_id)
        return {"status": "success", "data": data}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
