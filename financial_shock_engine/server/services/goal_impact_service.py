"""
financial_shock_engine/server/services/goal_impact_service.py
=============================================================
Step 6 — Goal Impact Analyzer.

For each active goal, simulates what happens after a shock:
  • delay_in_months        — how many months behind deadline
  • reduced_contribution   — how much less per month the user can contribute
  • contribution_gap       — total gap to fill
  • risk_level             — Low / Medium / High / Critical

Constraints enforced:
  • Suggested savings adjustments ≤ historical discretionary spend capacity
  • Realistic timelines only
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from feature_engine.data_ingestion import fetch_user_data
from feature_engine.feature_builder import build_features
from simulations.monte_carlo import simulate_with_shock

logger = logging.getLogger(__name__)

# Default shock amounts to simulate (₹)
_DEFAULT_SHOCK_AMOUNTS: list[float] = [5_000, 10_000, 20_000, 50_000]


def get_goal_impact(
    db: Session,
    user_id: int,
    shock_amounts: list[float] | None = None,
) -> dict[str, Any]:
    """
    Compute goal feasibility impact for one or more shock amounts.
    """
    shocks = shock_amounts or _DEFAULT_SHOCK_AMOUNTS

    raw      = fetch_user_data(db, user_id)
    features = build_features(raw)
    goals    = features.get("goal_details", [])
    monthly_income = features.get("monthly_income", 0.0)

    # Discretionary spend cap for realistic suggestions
    disc_ratio   = features.get("discretionary_ratio", 0.25)
    avg_expense  = features.get("avg_monthly_expense", 0.0)
    disc_monthly = avg_expense * disc_ratio

    results = []

    for shock in shocks:
        sim_after = simulate_with_shock(features, shock)
        balance_after = sim_after["projected_end_balance"]
        surplus_after = balance_after - features.get("goals_monthly_total_required", 0)

        goal_impacts = []
        for g in goals:
            impact = _compute_single_goal_impact(
                g, shock, surplus_after, disc_monthly, features
            )
            goal_impacts.append(impact)

        results.append({
            "shock_amount":         shock,
            "balance_after_shock":  round(balance_after, 2),
            "resilience_after":     sim_after["resilience_label"],
            "depletion_risk":       sim_after["depletion_risk_flag"],
            "goal_impacts":         goal_impacts,
            "total_delay_risk":     sum(g["delay_in_months"] for g in goal_impacts),
        })

    return {
        "user_id":     user_id,
        "computed_at": datetime.utcnow().isoformat(),
        "monthly_income": monthly_income,
        "current_balance": features["liquid_balance"],
        "goals_count":  len(goals),
        "shock_scenarios": results,
    }


def _compute_single_goal_impact(
    goal: dict,
    shock_amount: float,
    surplus_after_shock: float,
    disc_monthly: float,
    features: dict,
) -> dict:
    """Compute the impact on a single goal given a specific shock."""
    monthly_need    = goal["monthly_need"]
    remaining       = goal["remaining"]
    months_left     = goal["months_left"]
    today           = date.today()

    # Available for this goal after shock
    available_for_goal = max(surplus_after_shock, 0.0)

    if available_for_goal >= monthly_need:
        # Goal fully on track even after shock
        return {
            **goal,
            "impact_level":       "None",
            "delay_in_months":    0,
            "reduced_contribution": 0.0,
            "contribution_gap":   0.0,
            "new_completion_date": _add_months(today, months_left).isoformat(),
            "suggestion":         None,
        }

    contribution_gap     = monthly_need - available_for_goal
    reduced_contribution = max(available_for_goal, 0.0)

    if reduced_contribution <= 0:
        delay = months_left + int(remaining / max(monthly_need, 1))
    else:
        new_months = int(remaining / reduced_contribution) if reduced_contribution > 0 else months_left * 3
        delay = max(new_months - months_left, 0)

    # Risk level
    if delay == 0:
        risk = "Low"
    elif delay <= 2:
        risk = "Medium"
    elif delay <= 6:
        risk = "High"
    else:
        risk = "Critical"

    # Realistic suggestion: capped at 30% of discretionary
    max_suggestable = disc_monthly * 0.30
    suggested_cut = min(contribution_gap, max_suggestable)

    suggestion = None
    if suggested_cut > 200:
        top_disc_cat = _top_discretionary_category(features)
        suggestion = (
            f"Reduce {top_disc_cat} by ₹{suggested_cut:,.0f}/month to stay on track "
            f"with '{goal['goal_name']}'"
        )

    return {
        **goal,
        "impact_level":          risk,
        "delay_in_months":       delay,
        "reduced_contribution":  round(reduced_contribution, 2),
        "contribution_gap":      round(contribution_gap, 2),
        "new_completion_date":   _add_months(today, months_left + delay).isoformat(),
        "suggestion":            suggestion,
    }


def _top_discretionary_category(features: dict) -> str:
    from configs.settings import DISCRETIONARY_CATEGORIES
    cat_spend = features.get("category_spend_cm", {})
    disc_spend = {k: v for k, v in cat_spend.items() if k in DISCRETIONARY_CATEGORIES}
    if disc_spend:
        return max(disc_spend, key=disc_spend.get)
    return "discretionary spending"


def _add_months(d: date, months: int) -> date:
    import calendar
    month = d.month - 1 + months
    year  = d.year + month // 12
    month = month % 12 + 1
    day   = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
