"""
ai_projection_engine/llm/prompt_templates.py
============================================
Prompt construction for Mistral LLM insight generation.

Design rules mirrored from spec:
  • ₹ amounts only — no percentages
  • Mention specific category names
  • Keep prompts under ~300 tokens for fast inference
  • Build context sentence-by-sentence so the LLM has clear structure
"""

from __future__ import annotations

from typing import Dict, List


# ── Main Insight Prompt ────────────────────────────────────────────────────────

def build_insight_prompt(context: Dict) -> str:
    """
    Build the user-facing LLM prompt from the structured financial context dict.

    Expected context keys:
      extra_spent             (float)  – how much over mid-month expected spend
      top_categories          (list)   – top 3 spending categories by projected spend
      projected_balance_range (list)   – [lower ₹, upper ₹] at month end
      main_causes             (list)   – categories driving the extra spend
      saving_potential        (float)  – total ₹ saveable from best scenarios
      over_budget_categories  (list)   – categories that exceeded adaptive budget
      depletion_risk          (bool)   – whether balance may run out
      current_balance         (float)  – today's account balance
      month_year              (str)    – "YYYY-MM"
    """
    extra: float = context.get("extra_spent", 0.0)
    top_cats: List[str] = context.get("top_categories", [])
    bal_range: List[float] = context.get("projected_balance_range", [0.0, 0.0])
    causes: List[str] = context.get("main_causes", [])
    saving: float = context.get("saving_potential", 0.0)
    over_budget: List[str] = context.get("over_budget_categories", [])
    depletion: bool = context.get("depletion_risk", False)
    current_bal: float = context.get("current_balance", 0.0)

    lines: List[str] = []

    # Sentence 1 — spending summary
    if extra > 500:
        causes_str = " and ".join(causes) if causes else "various categories"
        lines.append(
            f"The user spent about ₹{extra:,.0f} more than their usual mid-month pattern, "
            f"mainly on {causes_str}."
        )
    else:
        cats_str = ", ".join(top_cats) if top_cats else "various categories"
        lines.append(
            f"The user's top spending areas this month are {cats_str}, "
            f"which appear to be tracking close to normal levels."
        )

    # Sentence 2 — over-budget alert
    if over_budget:
        ob_str = ", ".join(over_budget)
        lines.append(
            f"They have exceeded their usual budget in {ob_str} so far this month."
        )

    # Sentence 3 — balance projection
    bal_lo, bal_hi = bal_range[0], bal_range[1] if len(bal_range) > 1 else bal_range[0]
    if bal_lo >= 0 and bal_hi >= 0:
        lines.append(
            f"By month end, their remaining balance is expected to be "
            f"between ₹{bal_lo:,.0f} and ₹{bal_hi:,.0f}."
        )
    elif depletion:
        lines.append(
            f"Their current balance of ₹{current_bal:,.0f} may run short before "
            f"the month ends if spending continues at this pace."
        )

    # Sentence 4 — savings recommendation
    if saving > 200:
        lines.append(
            f"Reducing non-essential spending by about ₹{saving:,.0f} this month "
            f"could help maintain their planned savings."
        )

    paragraph = " ".join(lines)

    return (
        f"{paragraph}\n\n"
        "Using only the above information, write a 3-4 sentence, warm and friendly "
        "financial insight for this user. "
        "Use only ₹ amounts. No percentages. No jargon. "
        "Mention specific category names and amounts."
    )


# ── Budget Alert Prompt ────────────────────────────────────────────────────────

def build_budget_alert_prompt(category: str, budget: float, actual: float) -> str:
    """
    Short prompt for a single-category over-budget alert.
    Used by future alert notification features.
    """
    over_by = actual - budget
    return (
        f"The user spent ₹{actual:,.0f} on {category} this month, "
        f"which is ₹{over_by:,.0f} more than their usual spending of ₹{budget:,.0f}. "
        "Write 2 sentences of friendly advice on managing these expenses. "
        "Use only ₹ amounts, no percentages."
    )


# ── Depletion Risk Prompt ──────────────────────────────────────────────────────

def build_depletion_prompt(
    current_balance: float,
    avg_daily_spend: float,
    days_remaining: int,
    depletion_date: str,
) -> str:
    """Prompt for mid-month money depletion risk warnings."""
    estimated_spend = round(avg_daily_spend * days_remaining, 2)
    return (
        f"The user currently has ₹{current_balance:,.0f} in their account. "
        f"Their daily spending averages ₹{avg_daily_spend:,.0f}. "
        f"If this continues, they may run low on funds around {depletion_date}. "
        f"Estimated remaining spend for the month is ₹{estimated_spend:,.0f}. "
        "Write 2-3 sentences of gentle, practical advice to avoid running short. "
        "Use only ₹ amounts, no percentages."
    )
