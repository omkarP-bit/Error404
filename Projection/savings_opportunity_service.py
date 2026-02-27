"""
ai_projection_engine/server/services/savings_opportunity_service.py
====================================================================
Counterfactual savings simulation per discretionary spending category.

For each discretionary category in the current month:
  • Simulate 5 / 10 / 15 / 20% reduction scenarios.
  • Compute the ₹ amount saved and projected balance improvement.
  • Never suggest reducing fixed expenses (Rent, EMI, Insurance, …).
  • Never suggest > 25% reduction (configurable via MAX_REDUCTION_PCT).

Also evaluates goal impact:
  • Computes total monthly goal requirement for all active goals.
  • Checks whether the potential savings cover goal contributions.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from constants import (
    DISCRETIONARY_EXPENSE_CATEGORIES,
    FIXED_EXPENSE_CATEGORIES,
    MIN_CATEGORY_SPEND_FOR_SAVINGS,
    SAVINGS_REDUCTION_SCENARIOS,
)
from database import SavingsOpportunity
from probabilistic_forecast_service import (
    get_user_current_balance,
    run_probabilistic_forecast,
)
from feature_engineering import build_all_features


# ── Main Service ───────────────────────────────────────────────────────────────

def get_savings_opportunities(db: Session, user_id: int) -> Dict:
    """
    Compute savings opportunities for *user_id* and persist to DB.

    Returns a Flutter-ready JSON dict with:
      • opportunities  – per-category simulation results
      • goal_impact    – feasibility of goals given potential savings
      • summary        – aggregate numbers
    """
    features = build_all_features(db, user_id)
    current_month = features["current_month"]
    current_balance = get_user_current_balance(db, user_id)

    if not features["has_data"]:
        return {
            "user_id": user_id,
            "month_year": current_month,
            "message": "Insufficient transaction history to compute savings opportunities.",
            "opportunities": [],
            "goal_impact": {},
            "total_potential_monthly_savings": 0.0,
        }

    # Run forecast once to get projected balance
    forecast = run_probabilistic_forecast(db, user_id)
    proj_balance_median = (
        forecast.get("projected_balance_at_month_end", {}).get("median", current_balance)
    )

    df = features["df"]
    cur_month_df = df[df["month_year"] == current_month]

    opportunities: List[Dict] = []
    total_savings_potential = 0.0

    for cat in sorted(cur_month_df["category"].dropna().unique()):
        cat = str(cat)

        # Skip fixed expenses — never suggest cutting these
        if cat in FIXED_EXPENSE_CATEGORIES:
            continue

        is_discretionary = cat in DISCRETIONARY_EXPENSE_CATEGORIES
        cat_spend = float(cur_month_df[cur_month_df["category"] == cat]["amount"].sum())

        if cat_spend < MIN_CATEGORY_SPEND_FOR_SAVINGS:
            continue  # Negligible spend — skip

        scenarios = _build_scenarios(cat, cat_spend)
        if not scenarios:
            continue

        # Best practical scenario: 10% (or first available)
        best = scenarios.get("reduction_10pct") or list(scenarios.values())[0]
        total_savings_potential += best["amount_saved"]

        opp = {
            "category": cat,
            "is_discretionary": is_discretionary,
            "current_spend_this_month": round(cat_spend, 2),
            "scenarios": scenarios,
            "best_scenario": {
                "reduction_pct": best["reduction_percentage"],
                "amount_saved": round(best["amount_saved"], 2),
                "balance_improvement": round(best["projected_balance_improvement"], 2),
            },
            "insight": (
                f"If {cat} reduced by ₹{best['amount_saved']:,.0f}, "
                f"month-end balance improves by ₹{best['projected_balance_improvement']:,.0f}"
            ),
        }
        opportunities.append(opp)
        _upsert_opportunity(db, user_id, current_month, cat, is_discretionary, cat_spend, scenarios)

    db.commit()

    # Sort by best saving potential (highest first)
    opportunities.sort(key=lambda x: x["best_scenario"]["amount_saved"], reverse=True)

    goal_impact = _compute_goal_impact(db, user_id, total_savings_potential)

    return {
        "user_id": user_id,
        "month_year": current_month,
        "computed_at": datetime.utcnow().isoformat(),
        "current_balance": round(current_balance, 2),
        "projected_balance_median": round(proj_balance_median, 2),
        "total_potential_monthly_savings": round(total_savings_potential, 2),
        "opportunities": opportunities,
        "goal_impact": goal_impact,
    }


# ── Scenario Builder ───────────────────────────────────────────────────────────

def _build_scenarios(category: str, current_spend: float) -> Dict[str, Dict]:
    """Build reduction scenario dict for one category."""
    from config import settings

    scenarios: Dict[str, Dict] = {}
    for pct in SAVINGS_REDUCTION_SCENARIOS:
        if pct > settings.MAX_REDUCTION_PCT:
            continue
        reduction_amt = round(current_spend * pct / 100.0, 2)
        key = f"reduction_{int(pct)}pct"
        scenarios[key] = {
            "reduction_percentage": pct,
            "amount_saved": reduction_amt,
            "projected_balance_improvement": reduction_amt,   # 1-for-1 improvement
            "description": (
                f"Reduce {category} by ₹{reduction_amt:,.0f} "
                f"→ balance improves by ₹{reduction_amt:,.0f}"
            ),
        }
    return scenarios


# ── Goal Impact Evaluation ─────────────────────────────────────────────────────

def _compute_goal_impact(db: Session, user_id: int, savings_potential: float) -> Dict:
    """
    Compare achievable savings against monthly goal requirements.
    Uses existing *goals* table (READ-ONLY).
    """
    rows = db.execute(
        text("""
            SELECT goal_name, target_amount, current_amount, deadline, priority
            FROM goals
            WHERE user_id = :uid AND status = 'active'
            ORDER BY priority ASC
        """),
        {"uid": user_id},
    ).fetchall()

    if not rows:
        return {"goals_evaluated": 0, "message": "No active goals found."}

    goal_details: List[Dict] = []
    for row in rows:
        goal_name, target, current_amt, deadline, priority = row
        remaining = max(float(target) - float(current_amt or 0), 0.0)

        # Monthly contribution required
        monthly_needed = _monthly_needed(remaining, deadline)

        goal_details.append({
            "goal_name": goal_name,
            "remaining_amount": round(remaining, 2),
            "monthly_contribution_needed": round(monthly_needed, 2),
            "feasible_with_savings": savings_potential >= monthly_needed,
        })

    total_needed = sum(g["monthly_contribution_needed"] for g in goal_details)
    shortfall = max(total_needed - savings_potential, 0.0)

    return {
        "goals_evaluated": len(goal_details),
        "total_monthly_goal_requirement": round(total_needed, 2),
        "achievable_savings_this_month": round(savings_potential, 2),
        "shortfall_for_goals": round(shortfall, 2),
        "goal_feasibility_flag": shortfall == 0.0,
        "goals": goal_details,
    }


def _monthly_needed(remaining: float, deadline) -> float:
    """Rough monthly contribution needed to reach a goal by deadline."""
    if not deadline:
        return remaining / 12.0
    try:
        if isinstance(deadline, str):
            deadline_date = date.fromisoformat(deadline)
        else:
            deadline_date = deadline
        today = date.today()
        months_left = max(
            (deadline_date.year - today.year) * 12
            + (deadline_date.month - today.month),
            1,
        )
        return remaining / months_left
    except Exception:
        return remaining / 12.0


# ── DB Upsert ──────────────────────────────────────────────────────────────────

def _upsert_opportunity(
    db: Session,
    user_id: int,
    month_year: str,
    category: str,
    is_discretionary: bool,
    current_spend: float,
    scenarios: Dict,
) -> None:
    def _val(scenario_key: str, field: str) -> float:
        return scenarios.get(scenario_key, {}).get(field, 0.0)

    kwargs = dict(
        is_discretionary=is_discretionary,
        current_spend=current_spend,
        saving_5pct=_val("reduction_5pct", "amount_saved"),
        saving_10pct=_val("reduction_10pct", "amount_saved"),
        saving_15pct=_val("reduction_15pct", "amount_saved"),
        saving_20pct=_val("reduction_20pct", "amount_saved"),
        balance_impact_5pct=_val("reduction_5pct", "projected_balance_improvement"),
        balance_impact_10pct=_val("reduction_10pct", "projected_balance_improvement"),
        balance_impact_15pct=_val("reduction_15pct", "projected_balance_improvement"),
        balance_impact_20pct=_val("reduction_20pct", "projected_balance_improvement"),
    )

    existing = (
        db.query(SavingsOpportunity)
        .filter_by(user_id=user_id, category=category, month_year=month_year)
        .first()
    )

    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
    else:
        db.add(
            SavingsOpportunity(
                user_id=user_id,
                category=category,
                month_year=month_year,
                **kwargs,
            )
        )
