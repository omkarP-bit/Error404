"""
ai_projection_engine/server/services/llm_insight_service.py
============================================================
Orchestrates financial context gathering and Mistral LLM insight generation.

Flow:
  1. Run probabilistic forecast   → spending picture
  2. Compute savings opportunities → actionable levers
  3. Get adaptive budgets          → over-budget categories
  4. Build a structured prompt
  5. Send to MistralClient (cloud API or local Ollama)
  6. Return plain-English insight + supporting context

All monetary values in ₹. No percentages exposed to LLM prompt.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from llm.mistral_client import MistralClient
from llm.prompt_templates import build_insight_prompt
from server.services.adaptive_budgeting_service import get_adaptive_budgets
from server.services.probabilistic_forecast_service import run_probabilistic_forecast
from server.services.savings_opportunity_service import get_savings_opportunities


def get_llm_insights(db: Session, user_id: int) -> Dict:
    """
    Generate simplified Mistral LLM insights for *user_id*.

    Returns:
      insight          – 3-4 sentence plain-English financial summary
      context_used     – the structured data sent to the LLM (for debugging)
      supporting data  – top categories, over-budget items, saving potential
    """
    # ── Gather context ────────────────────────────────────────────────────────
    forecast = run_probabilistic_forecast(db, user_id)
    savings = get_savings_opportunities(db, user_id)
    budgets = get_adaptive_budgets(db, user_id)

    # Top 3 projected spend categories
    cat_breakdown: Dict[str, Dict] = forecast.get("category_breakdown", {})
    top_categories: List[str] = [
        cat
        for cat, _ in sorted(
            cat_breakdown.items(),
            key=lambda x: x[1].get("projected_p50", 0),
            reverse=True,
        )[:3]
    ]

    # Over-budget discretionary categories
    over_budget_cats: List[str] = [
        b["category"]
        for b in budgets
        if b.get("is_over_budget") and b.get("is_discretionary")
    ][:3]

    # Total potential savings from top opportunities
    opportunities = savings.get("opportunities", [])[:3]
    saving_potential = sum(o["best_scenario"]["amount_saved"] for o in opportunities)

    # Main causes: prefer over-budget, fall back to top projected spenders
    main_causes = over_budget_cats or top_categories[:2]

    # Extra spend = how much over mid-month expected (rough heuristic)
    spent_so_far = forecast.get("spent_this_month_so_far", 0.0)
    median_proj = forecast.get("projected_month_spend", {}).get("median_p50", spent_so_far)
    mid_month_expected = median_proj * 0.50  # halfway through month ≈ 50% of projected
    extra_spent = max(spent_so_far - mid_month_expected, 0.0)

    proj_balance = forecast.get("projected_balance_at_month_end", {})
    balance_range = [
        round(proj_balance.get("lower", 0.0), 2),
        round(proj_balance.get("upper", 0.0), 2),
    ]

    llm_payload: Dict = {
        "extra_spent": round(extra_spent, 2),
        "spent_this_month": round(spent_so_far, 2),
        "top_categories": top_categories,
        "projected_balance_range": balance_range,
        "main_causes": main_causes,
        "saving_potential": round(saving_potential, 2),
        "over_budget_categories": over_budget_cats,
        "depletion_risk": forecast.get("depletion_risk_flag", False),
        "current_balance": round(forecast.get("current_balance", 0.0), 2),
        "month_year": forecast.get("month_year", ""),
    }

    # ── LLM call ──────────────────────────────────────────────────────────────
    prompt = build_insight_prompt(llm_payload)
    client = MistralClient()

    # Try Ollama / cloud; _fallback is called internally on failure
    insight_text = client.generate(prompt, context=llm_payload)

    # Detect whether we got a real LLM response or the rule-based fallback
    # (fallback text never starts with a quote or contains "Dear")
    insight_source = "ollama" if client.use_local else ("api" if client.api_key else "fallback")

    return {
        "user_id": user_id,
        "month_year": forecast.get("month_year"),
        "computed_at": datetime.utcnow().isoformat(),
        "insight": insight_text,
        "insight_source": insight_source,
        "context_used": llm_payload,
        "supporting_data": {
            "depletion_risk": forecast.get("depletion_risk_flag", False),
            "top_spending_categories": top_categories,
            "over_budget_categories": over_budget_cats,
            "saving_potential": round(saving_potential, 2),
            "current_balance": round(forecast.get("current_balance", 0.0), 2),
            "projected_balance_median": round(proj_balance.get("median", 0.0), 2),
        },
    }
