"""
ml_models/goal_feasibility_model/counterfactual.py
===================================================
Counterfactual Simulation Engine.

For each simulation scenario, the engine:
  1. Clones the current feature vector
  2. Applies the scenario modification
  3. Re-runs the probability model
  4. Computes the delta in probability and deadline shift

Scenarios supported:
  • Reduce a spending category by X%  (affects discretionary_ratio, cat_slope)
  • Increase monthly contribution by ₹N  (affects feasibility_ratio, safe_surplus)
  • Reduce anomalous transactions (affects anomaly_count_3m)
  • Improve behavioral consistency  (affects behavioral_consistency, volatility)

Timeline shift formula:
  saved_per_month_delta = safe_surplus_new − safe_surplus_old
  months_saved = remaining_amount / safe_surplus_new − remaining_amount / safe_surplus_old

Output:
  [
    {
      "scenario":           "Reduce Food & Dining by 20%",
      "new_probability":    0.81,
      "prob_delta":        +0.06,
      "new_feasibility_ratio": 1.42,
      "months_earlier":    1.3,
      "monthly_savings_gain": 1800.0,
      "actionable_tip":    "Cut Swiggy orders from 8×/month to 6×/month"
    },
    ...
  ]
"""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ml_models.goal_feasibility_model.model import GoalProbabilityModel


# ── Scenario definitions ───────────────────────────────────────────────────────
DEFAULT_SCENARIOS = [
    {"type": "reduce_category", "category": "Food & Dining",   "reduction": 0.20},
    {"type": "reduce_category", "category": "Shopping",        "reduction": 0.15},
    {"type": "reduce_category", "category": "Entertainment",   "reduction": 0.25},
    {"type": "increase_contribution", "amount": 5000},
    {"type": "increase_contribution", "amount": 10000},
    {"type": "reduce_anomalies"},
]

CATEGORY_TO_SLOPE_FEATURE = {
    "Food & Dining":  "dining_slope",
    "Shopping":       "shopping_slope",
    "Entertainment":  "entertainment_slope",
}


def simulate_counterfactuals(
    model: "GoalProbabilityModel",
    feature_dict: dict,
    base_probability: float,
    scenarios: list[dict] | None = None,
) -> list[dict]:
    """
    Run all scenarios and return those that improve probability by >= 2pp.

    Parameters
    ----------
    model            : fitted GoalProbabilityModel
    feature_dict     : original feature dict (raw, unscaled)
    base_probability : original prediction
    scenarios        : override DEFAULT_SCENARIOS if provided
    """
    scenarios = scenarios or DEFAULT_SCENARIOS
    results   = []

    for scenario in scenarios:
        try:
            result = _run_scenario(model, feature_dict, base_probability, scenario)
            if result and result["prob_delta"] >= 0.01:   # only meaningful improvements
                results.append(result)
        except Exception:
            continue

    # Sort by impact descending
    results.sort(key=lambda x: -x["prob_delta"])
    return results[:4]   # return top-4 scenarios


def _run_scenario(
    model: "GoalProbabilityModel",
    feat: dict,
    base_prob: float,
    scenario: dict,
) -> dict | None:
    """Apply one scenario and measure the probability change."""
    new_feat = copy.deepcopy(feat)

    stype = scenario["type"]
    remaining   = feat.get("log_remaining_amount", 0)
    monthly_req = feat.get("monthly_required", 1.0)
    months_left = feat.get("months_left", 12.0)
    avg_expenses = feat.get("avg_monthly_expenses", 1.0)

    if stype == "reduce_category":
        cat       = scenario["category"]
        reduction = scenario["reduction"]  # e.g. 0.20 → 20%
        slope_feat = CATEGORY_TO_SLOPE_FEATURE.get(cat)

        # Monthly saving from reduction
        # Estimate category spend from discretionary_ratio × avg_expenses
        disc_ratio    = feat.get("discretionary_ratio", 0.25)
        cat_spend_est = avg_expenses * disc_ratio / 3   # rough per-category estimate
        monthly_gain  = cat_spend_est * reduction

        # Update features: lower discretionary ratio, reduce slope, raise surplus
        new_feat["discretionary_ratio"]  = max(
            feat.get("discretionary_ratio", 0) * (1 - reduction / 3), 0.0
        )
        if slope_feat:
            new_feat[slope_feat] = min(feat.get(slope_feat, 0) * (1 - reduction), 0.0)

        new_feat["avg_monthly_surplus"]  = feat.get("avg_monthly_surplus", 0) + monthly_gain
        new_feat["safe_surplus"]         = new_feat["avg_monthly_surplus"] * 0.85
        new_feat["savings_rate"]         = (
            new_feat["safe_surplus"] / max(feat.get("monthly_income", 1), 1)
        )
        new_feat["feasibility_ratio"]    = (
            new_feat["safe_surplus"] / max(monthly_req, 1)
        )

        scenario_label = f"Reduce {cat} by {int(reduction*100)}%"
        tip = f"Save ₹{monthly_gain:,.0f}/month by cutting {cat} spend by {int(reduction*100)}%"

    elif stype == "increase_contribution":
        add_amount  = float(scenario["amount"])
        monthly_gain = add_amount

        new_feat["avg_monthly_surplus"] = feat.get("avg_monthly_surplus", 0) + add_amount
        new_feat["safe_surplus"]        = new_feat["avg_monthly_surplus"] * 0.85
        new_feat["savings_rate"]        = (
            new_feat["safe_surplus"] / max(feat.get("monthly_income", 1), 1)
        )
        new_feat["feasibility_ratio"]   = (
            new_feat["safe_surplus"] / max(monthly_req, 1)
        )

        scenario_label = f"Add ₹{add_amount:,.0f}/month to savings"
        tip = f"Set up a ₹{add_amount:,.0f} SIP or recurring transfer"

    elif stype == "reduce_anomalies":
        new_feat["anomaly_count_3m"]     = max(feat.get("anomaly_count_3m", 0) * 0.5, 0)
        new_feat["expense_volatility"]   = feat.get("expense_volatility", 0) * 0.8
        new_feat["expense_volatility_ratio"] = feat.get("expense_volatility_ratio", 0) * 0.8
        new_feat["behavioral_consistency"] = min(
            feat.get("behavioral_consistency", 0.5) + 0.15, 1.0
        )
        monthly_gain = 0.0
        scenario_label = "Reduce impulsive/unusual purchases"
        tip = "Avoid high-value unplanned purchases; set a ₹5,000 impulse-buy limit"

    else:
        return None

    # Recompute probability under new features
    new_prob, _ = model.predict_proba(new_feat)
    prob_delta  = round(new_prob - base_prob, 4)

    # Timeline shift: months_earlier
    old_safe   = feat.get("safe_surplus", 1.0)
    new_safe   = new_feat.get("safe_surplus", old_safe)
    import math
    rem_raw    = math.expm1(feat.get("log_remaining_amount", 0))   # undo log1p
    old_months = rem_raw / max(old_safe, 1)
    new_months = rem_raw / max(new_safe, 1)
    months_earlier = round(max(old_months - new_months, 0.0), 1)

    return {
        "scenario":              scenario_label,
        "new_probability":       round(new_prob, 4),
        "prob_delta":            prob_delta,
        "new_feasibility_ratio": round(new_feat.get("feasibility_ratio", 0), 3),
        "months_earlier":        months_earlier,
        "monthly_savings_gain":  round(monthly_gain if stype != "reduce_anomalies" else 0, 2),
        "actionable_tip":        tip,
    }
