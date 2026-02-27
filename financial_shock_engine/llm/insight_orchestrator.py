"""
financial_shock_engine/llm/insight_orchestrator.py
===================================================
Orchestrates LLM insight generation for the shock engine.
Combines shock data + savings data + goal data → single LLM call → structured output.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from llm.mistral_client import MistralClient
from llm.prompt_templates import (
    build_shock_insight_prompt,
    build_savings_opportunity_prompt,
)

logger = logging.getLogger(__name__)


def generate_shock_insight(
    shock_result: dict[str, Any],
    savings_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a complete LLM insight combining shock capacity + savings opportunities.
    Falls back gracefully if LLM is unavailable.
    """
    # Build merged context for prompt + fallback
    context = {
        "shock_capacity":          shock_result.get("shock_capacity", 0.0),
        "safe_shock_limit":        shock_result.get("safe_shock_limit", 0.0),
        "risk_threshold":          shock_result.get("risk_threshold", 0.0),
        "resilience_label":        shock_result.get("resilience_label", "Moderate"),
        "resilience_score":        shock_result.get("resilience_score", 50),
        "current_balance":         shock_result.get("current_balance", 0.0),
        "projected_end_balance":   shock_result.get("projected_end_balance", 0.0),
        "current_month_spend":     shock_result.get("current_month_spend", 0.0),
        "monthly_income":          shock_result.get("monthly_income", 0.0),
        "top_risk_categories":     savings_result.get("top_risk_categories", shock_result.get("top_categories", [])),
        "depletion_risk":          shock_result.get("depletion_risk", False),
        "expense_volatility":      shock_result.get("expense_volatility", 0.0),
        "total_monthly_saveable":  savings_result.get("total_monthly_saveable", 0.0),
    }

    prompt = build_shock_insight_prompt(context)
    client = MistralClient()
    insight_text = client.generate(prompt, context=context)

    insight_source = "ollama" if client.use_local else ("api" if client.api_key else "fallback")

    return {
        "insight":        insight_text,
        "insight_source": insight_source,
        "computed_at":    datetime.utcnow().isoformat(),
    }


def generate_savings_insight(savings_result: dict[str, Any]) -> str:
    """Generate a natural language summary of savings opportunities."""
    context = {
        "total_monthly_saveable": savings_result.get("total_monthly_saveable", 0.0),
        "opportunities":          savings_result.get("opportunities", []),
        "top_risk_categories":    savings_result.get("top_risk_categories", []),
    }
    prompt = build_savings_opportunity_prompt(context)
    client = MistralClient()
    return client.generate(prompt, context=context)
