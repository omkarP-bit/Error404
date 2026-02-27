"""
ml_models/goal_feasibility_engine/behavioral_constraint_model.py
=================================================================
Computes the MAXIMUM REALISTIC monthly saving the user can sustain,
enforcing four behavioral-realism constraints:

  1. Cap at 70% of predicted surplus
     (humans don't allocate their entire surplus to savings)

  2. Cap at historical median savings
     (what they've ACTUALLY managed; not what math says they could)

  3. Volatility-adjusted stable surplus
     (high-volatility spenders save less reliably)

  4. Minimum liquidity buffer enforcement
     (never save aggressively when liquid reserves are thin)

Design rule: The system must NEVER suggest saving more than is realistically
achievable. Outputs that require "save 90% of income" or "save ₹50,000 with
₹12,000 surplus" are strictly prohibited.

Output dict:
  max_feasible_saving   — total feasible monthly saving across ALL goals
  feasible_monthly      — this goal's share (after allocation)
  recommended_monthly   — risk-adjusted, safer figure (85% of feasible × stability)
  liquidity_ok          — bool: buffer >= 1.5 months essential expenses
  buffer_months         — current liquidity in months of essential spend
  risk_level            — low / medium / high / critical
  bound_70pct           — Bound 1 value (diagnostic)
  bound_historical      — Bound 2 value (diagnostic)
  bound_volatility      — Bound 3 value (diagnostic)
"""
from __future__ import annotations


def compute_feasible_saving(
    ctx: dict,
    forecast: dict,
    goal_allocation_fraction: float = 1.0,
) -> dict:
    """
    Parameters
    ----------
    ctx
        FinancialContext from feature_builder.
    forecast
        Surplus forecast from surplus_forecaster.
    goal_allocation_fraction
        Fraction of the total feasible saving pool allocated to THIS goal
        (provided by allocation_optimizer; defaults to 1.0 for single-goal users).
    """
    predicted_surplus = forecast["predicted_surplus"]
    stable_surplus    = forecast["stable_surplus"]
    exp_vol_factor    = ctx["expense_volatility_factor"]
    hist_median       = ctx["historical_median_savings"]
    total_balance     = ctx["total_balance"]
    avg_essential     = ctx["avg_essential_monthly"]
    required_monthly  = ctx["required_monthly_raw"]
    income_stability  = ctx["income_stability"]

    # ── Bound 1: 70% of predicted surplus ────────────────────────────────────
    bound_70 = predicted_surplus * 0.70

    # ── Bound 2: Historical median savings ───────────────────────────────────
    # If no savings history exists, fall back to Bound 1 (don't penalise new users)
    bound_hist = hist_median if hist_median > 0 else bound_70

    # ── Bound 3: Volatility-adjusted stable surplus ───────────────────────────
    # High volatility (> 30%) erodes reliable saving capacity
    vol_penalty  = min(exp_vol_factor * 0.50, 0.50)   # cap penalty at 50%
    bound_vol    = stable_surplus * (1.0 - vol_penalty)

    # ── Bound 4: Liquidity buffer enforcement ─────────────────────────────────
    BUFFER_THRESHOLD = 1.5   # months of essential expenses required as buffer
    buffer_months    = total_balance / max(avg_essential, 1.0)
    liquidity_ok     = buffer_months >= BUFFER_THRESHOLD

    if not liquidity_ok:
        if buffer_months < 0.5:
            # Critically low buffer — must build reserves, cannot save for goals
            bound_liquidity = 0.0
        else:
            # Partial saving allowed, but heavily reduced to help rebuild buffer
            bound_liquidity = bound_70 * 0.40
    else:
        bound_liquidity = bound_70   # no liquidity constraint

    # ── Max feasible (all goals combined) ─────────────────────────────────────
    max_feasible_all = max(
        min(bound_70, bound_hist, bound_vol, bound_liquidity),
        0.0,
    )

    # ── This goal's allocation ────────────────────────────────────────────────
    feasible_monthly = max_feasible_all * goal_allocation_fraction

    # ── Recommended: risk-adjusted safer allocation ───────────────────────────
    # income_stability < 1 → income disruptions possible → be more conservative
    recommended_monthly = max(feasible_monthly * income_stability * 0.85, 0.0)

    # ── Risk level ────────────────────────────────────────────────────────────
    if required_monthly <= 0:
        risk_level = "low"
    else:
        ratio = feasible_monthly / required_monthly
        if ratio >= 1.20:
            risk_level = "low"
        elif ratio >= 0.80:
            risk_level = "medium"
        elif ratio >= 0.50:
            risk_level = "high"
        else:
            risk_level = "critical"

    return {
        "max_feasible_saving":  round(max_feasible_all,      2),
        "feasible_monthly":     round(feasible_monthly,      2),
        "recommended_monthly":  round(recommended_monthly,   2),
        "liquidity_ok":         liquidity_ok,
        "buffer_months":        round(buffer_months,         2),
        "risk_level":           risk_level,
        # Diagnostics (useful for debugging / API response)
        "bound_70pct":          round(bound_70,   2),
        "bound_historical":     round(bound_hist, 2),
        "bound_volatility":     round(bound_vol,  2),
    }
