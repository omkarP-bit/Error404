"""
financial_shock_engine/llm/prompt_templates.py
===============================================
Prompt builders for the Shock Engine LLM insight generator.
All prompts are structured narrative paragraphs — NOT JSON.
"""
from __future__ import annotations

from typing import Any


def build_shock_insight_prompt(context: dict[str, Any]) -> str:
    """
    Build the main shock capacity explanation prompt.

    Context keys expected:
        shock_capacity, safe_shock_limit, risk_threshold,
        resilience_label, resilience_score,
        current_balance, projected_end_balance,
        current_month_spend, monthly_income,
        top_risk_categories, depletion_risk,
        expense_volatility, total_monthly_saveable
    """
    capacity     = context.get("shock_capacity", 0.0)
    safe         = context.get("safe_shock_limit", 0.0)
    risk         = context.get("risk_threshold", 0.0)
    label        = context.get("resilience_label", "Moderate")
    score        = context.get("resilience_score", 50)
    cur_bal      = context.get("current_balance", 0.0)
    proj_bal     = context.get("projected_end_balance", 0.0)
    spent        = context.get("current_month_spend", 0.0)
    income       = context.get("monthly_income", 0.0)
    top_cats     = context.get("top_risk_categories", [])
    depletion    = context.get("depletion_risk", False)
    savings_pot  = context.get("total_monthly_saveable", 0.0)

    lines = []

    lines.append(
        f"The user's financial resilience is classified as '{label}' "
        f"with a score of {score}/100."
    )
    lines.append(
        f"They can safely absorb an unexpected expense of up to ₹{capacity:,.0f} "
        f"this month without missing goals. Expenses above ₹{risk:,.0f} start to create risk."
    )
    lines.append(
        f"Their current balance is ₹{cur_bal:,.0f}, with a projected end-of-month "
        f"balance of ₹{proj_bal:,.0f}. Monthly income is ₹{income:,.0f}."
    )
    if top_cats:
        lines.append(
            f"The highest risk spending categories are: {', '.join(top_cats)}."
        )
    if depletion:
        lines.append(
            "There is a risk of balance depletion before month end if spending continues at this rate."
        )
    if savings_pot > 0:
        lines.append(
            f"Cutting discretionary spending by ₹{savings_pot:,.0f} this month "
            f"would significantly improve their shock buffer."
        )

    paragraph = " ".join(lines)

    return (
        f"{paragraph}\n\n"
        "Write a 3-4 sentence warm, friendly explanation of this financial situation for the user. "
        "Use only ₹ amounts. Mention specific categories. No jargon. Be encouraging and practical."
    )


def build_goal_impact_prompt(context: dict[str, Any]) -> str:
    """Prompt for goal-impact explanation after a shock."""
    shock       = context.get("shock_amount", 0.0)
    goal_name   = context.get("goal_name", "your goal")
    delay       = context.get("delay_in_months", 0)
    suggestion  = context.get("suggestion", "")
    bal_after   = context.get("balance_after_shock", 0.0)

    lines = [
        f"If the user faces an unexpected expense of ₹{shock:,.0f}, "
        f"their account balance would drop to approximately ₹{bal_after:,.0f}.",
    ]
    if delay > 0:
        lines.append(
            f"This would delay '{goal_name}' by approximately {delay} month(s)."
        )
    if suggestion:
        lines.append(suggestion)

    return (
        " ".join(lines) + "\n\n"
        "Write 2-3 sentences explaining this to the user in a warm and practical way. "
        "Use only ₹ amounts. Mention specific goal names. Be encouraging."
    )


def build_savings_opportunity_prompt(context: dict[str, Any]) -> str:
    """Prompt for savings opportunity explanation."""
    total    = context.get("total_monthly_saveable", 0.0)
    opps     = context.get("opportunities", [])
    top_cats = context.get("top_risk_categories", [])

    lines = [f"The user has a savings opportunity of ₹{total:,.0f} per month."]

    for opp in opps[:3]:
        lines.append(
            f"In {opp['category']}, they currently spend ₹{opp['current_spend']:,.0f} "
            f"and could reduce this by ₹{opp['save_amount']:,.0f}."
        )

    return (
        " ".join(lines) + "\n\n"
        "Write 3-4 sentences summarising these savings opportunities in a friendly, motivating way. "
        "Use only ₹ amounts. Be specific about categories and amounts. No jargon."
    )
