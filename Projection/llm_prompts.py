"""
server/shock_engine/llm_prompts.py
====================================
Prompt builder for the Financial Shock Absorption Engine LLM insight.
"""
from __future__ import annotations
from typing import Any


def build_shock_prompt(ctx: dict[str, Any]) -> str:
    cap      = ctx.get("shock_capacity", 0.0)
    safe     = ctx.get("safe_shock_limit", 0.0)
    label    = ctx.get("resilience_label", "Moderate")
    bal      = ctx.get("current_balance", 0.0)
    proj     = ctx.get("projected_end_balance", 0.0)
    spent    = ctx.get("current_month_spend", 0.0)
    income   = ctx.get("monthly_income", 0.0)
    cats     = ctx.get("top_risk_categories", [])
    depl     = ctx.get("depletion_risk", False)
    saveable = ctx.get("total_monthly_saveable", 0.0)

    lines = []

    lines.append(
        f"The user has a current balance of ₹{bal:,.0f} and has spent ₹{spent:,.0f} this month "
        f"out of a monthly income of ₹{income:,.0f}."
    )
    lines.append(
        f"Their financial resilience is rated as '{label}'. "
        f"They can safely absorb an unexpected expense of up to ₹{safe:,.0f} without risking their goals. "
        f"Their overall shock absorption capacity is ₹{cap:,.0f}."
    )
    if cats:
        lines.append(f"The highest-risk spending categories are: {', '.join(cats)}.")
    if depl:
        lines.append("There is a risk of balance depletion before month end if spending continues at this pace.")
    else:
        lines.append(f"By month end, their balance is projected to be around ₹{proj:,.0f}.")
    if saveable > 200:
        lines.append(f"They could save up to ₹{saveable:,.0f}/month by reducing discretionary spending.")

    paragraph = " ".join(lines)
    return (
        f"{paragraph}\n\n"
        "Using only the above, write 3-4 warm, friendly sentences explaining the user's financial shock resilience. "
        "Use only ₹ amounts. No percentages. Mention specific amounts and categories. Be encouraging."
    )


def build_shock_fallback(ctx: dict[str, Any]) -> str:
    cap      = float(ctx.get("shock_capacity", 0.0) or 0.0)
    safe     = float(ctx.get("safe_shock_limit", 0.0) or 0.0)
    label    = ctx.get("resilience_label", "Moderate")
    bal      = float(ctx.get("current_balance", 0.0) or 0.0)
    proj     = float(ctx.get("projected_end_balance", 0.0) or 0.0)
    cats     = ctx.get("top_risk_categories", []) or []
    depl     = bool(ctx.get("depletion_risk", False))
    saveable = float(ctx.get("total_monthly_saveable", 0.0) or 0.0)
    spent    = float(ctx.get("current_month_spend", 0.0) or 0.0)

    parts = []

    # Sentence 1 — resilience summary
    if label in ("Safe", "Moderate"):
        parts.append(
            f"Your financial resilience is {label} — you can comfortably absorb an unexpected expense "
            f"of up to ₹{safe:,.0f} without affecting your savings goals."
        )
    else:
        parts.append(
            f"Your resilience is currently {label}. An unexpected expense above ₹{safe:,.0f} "
            f"could put pressure on your monthly balance."
        )

    # Sentence 2 — spending/balance picture
    if spent > 0:
        cat_str = ", ".join(cats[:2]) if cats else "a few categories"
        parts.append(
            f"You've spent ₹{spent:,.0f} so far this month, with the most going to {cat_str}."
        )

    # Sentence 3 — depletion or projection
    if depl:
        parts.append(
            "Your spending pace suggests your balance could run short before month end — "
            "consider pausing non-essential purchases."
        )
    elif proj > 0:
        parts.append(f"Your balance is projected to be around ₹{proj:,.0f} by month end.")

    # Sentence 4 — savings tip
    if saveable > 200:
        tip_cat = cats[0] if cats else "discretionary spending"
        parts.append(
            f"Trimming {tip_cat} by around ₹{saveable:,.0f}/month would meaningfully boost your shock buffer."
        )

    return " ".join(parts) if parts else (
        f"Your current balance is ₹{bal:,.0f}. Keep tracking your expenses to build financial resilience."
    )
