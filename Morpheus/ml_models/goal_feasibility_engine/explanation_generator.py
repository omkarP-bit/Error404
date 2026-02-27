"""
ml_models/goal_feasibility_engine/explanation_generator.py
===========================================================
Generates human-readable, financially realistic insights.

Outputs:
  savings_plan          — required / feasible / recommended monthly (3-tier)
  timeline              — original vs realistic, delay months
  top_positive_drivers  — what's working in favour
  top_negative_drivers  — what's dragging feasibility down
  counterfactuals       — "if you do X, probability improves by Y"
  health_tag            — On Track / Tight / Behind / At Risk
  feasibility_note      — multi-line human-readable summary

Anti-naive rules enforced:
  - Required vs Feasible gap is ALWAYS shown when feasible < required
  - Realistic timeline is computed and shown when there is meaningful delay
  - Suggestions are capacity-bounded (never "save 90% of income")
  - All monetary figures are in INR (₹)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


def generate_explanation(
    ctx:        dict,
    forecast:   dict,
    constraint: dict,
    simulation: dict,
    allocation_fraction: float,
) -> dict:
    """
    Build the full explanation + health tag + feasibility note.

    Parameters
    ----------
    ctx               FinancialContext from feature_builder.
    forecast          Surplus forecast from surplus_forecaster.
    constraint        Saving constraints from behavioral_constraint_model.
    simulation        Monte Carlo results from feasibility_simulator.
    allocation_fraction  This goal's fraction of total feasible saving pool.
    """
    required    = ctx["required_monthly_raw"]
    feasible    = constraint["feasible_monthly"]
    recommended = constraint["recommended_monthly"]
    allocated   = feasible * (allocation_fraction if allocation_fraction else 1.0)
    months_left = ctx["months_left"]
    remaining   = ctx["remaining_amount"]
    prob        = simulation["probability"]

    today = date.today()

    # ── Timeline recalibration ────────────────────────────────────────────────
    if feasible > 0 and feasible < required:
        realistic_months = remaining / feasible
        delay_months     = max(realistic_months - months_left, 0.0)
    else:
        realistic_months = months_left
        delay_months     = 0.0

    realistic_date       = today + timedelta(days=realistic_months * 30.44)
    original_date        = today + timedelta(days=months_left     * 30.44)
    realistic_completion = realistic_date.strftime("%b %Y")
    original_completion  = original_date.strftime("%b %Y")

    # ── Positive drivers ──────────────────────────────────────────────────────
    pos = []
    if ctx["contribution_streak"] >= 2:
        pos.append(f"{ctx['contribution_streak']}-month consistent saving streak")
    if constraint["buffer_months"] >= 2.0:
        pos.append(f"Healthy liquidity buffer ({constraint['buffer_months']:.1f} months)")
    if ctx["income_stability"] >= 0.90:
        pos.append("Stable salaried income reduces income risk")
    if ctx["progress_pct"] >= 25:
        pos.append(f"Already {ctx['progress_pct']:.0f}% of goal achieved")
    if forecast["predicted_surplus"] >= required:
        pos.append("Monthly surplus exceeds the required saving rate")
    if ctx["anomaly_count_3m"] == 0:
        pos.append("No anomalous high-value transactions in past 3 months")

    # ── Negative drivers ──────────────────────────────────────────────────────
    neg = []
    if ctx["expense_volatility_factor"] > 0.30:
        neg.append(
            f"High expense volatility ({ctx['expense_volatility_factor'] * 100:.0f}%) "
            f"reduces reliable surplus"
        )
    if ctx["discretionary_ratio"] > 0.35:
        neg.append(
            f"Discretionary spend is {ctx['discretionary_ratio'] * 100:.0f}% of "
            f"expenses — significant room to cut"
        )
    if ctx["missed_saving_months"] >= 3:
        neg.append(
            f"Savings target was missed in {ctx['missed_saving_months']} of the "
            f"last 6 months"
        )
    if ctx["anomaly_count_3m"] >= 3:
        neg.append(
            f"{ctx['anomaly_count_3m']} high-value anomaly transactions detected "
            f"in past 3 months"
        )
    if ctx["num_competing_goals"] >= 2:
        neg.append(
            f"{ctx['num_competing_goals']} competing active goals reduce your "
            f"monthly allocation"
        )
    if not constraint["liquidity_ok"]:
        neg.append(
            f"Liquidity buffer is only {constraint['buffer_months']:.1f} months "
            f"(below 1.5-month safe threshold)"
        )
    if ctx["lifestyle_drift"] > 0.02:
        neg.append("Discretionary spending shows an upward trend")
    if feasible < required * 0.60:
        neg.append(
            f"Feasible saving (INR {feasible:,.0f}) is well below "
            f"mathematical requirement (INR {required:,.0f})"
        )

    # ── Health tag ────────────────────────────────────────────────────────────
    if feasible <= 0:
        health_tag = "At Risk"
    else:
        ratio = feasible / max(required, 1.0)
        if ratio >= 1.20:
            health_tag = "On Track"
        elif ratio >= 0.80:
            health_tag = "Tight"
        elif ratio >= 0.50:
            health_tag = "Behind"
        else:
            health_tag = "At Risk"

    # ── Counterfactuals ───────────────────────────────────────────────────────
    cf = []

    # CF1: Reduce dining by 20%
    dining = ctx.get("dining_monthly", 0.0)
    if dining > 500:
        saved      = dining * 0.20
        new_feas   = min(
            (forecast["predicted_surplus"] + saved) * 0.70,
            constraint["max_feasible_saving"] + saved * 0.60,
        )
        prob_gain  = min((saved / max(required, 1)) * 0.30, 0.15)
        mo_earlier = round(saved / max(required, 1) * months_left * 0.5, 1)
        cf.append({
            "scenario":             f"Cut dining by 20% (save ~INR {saved:,.0f}/mo)",
            "new_feasible_monthly": round(new_feas, 0),
            "probability_delta":    round(prob_gain, 3),
            "months_earlier":       mo_earlier,
        })

    # CF2: Cut all discretionary by 15%
    disc = ctx.get("discretionary_monthly", 0.0)
    if disc > 1000:
        saved2     = disc * 0.15
        new_feas2  = (forecast["predicted_surplus"] + saved2) * 0.70
        prob_gain2 = min((saved2 / max(required, 1)) * 0.35, 0.18)
        cf.append({
            "scenario":             f"Cut discretionary by 15% (save ~INR {saved2:,.0f}/mo)",
            "new_feasible_monthly": round(new_feas2, 0),
            "probability_delta":    round(prob_gain2, 3),
            "months_earlier":       round(saved2 / max(required, 1) * months_left * 0.5, 1),
        })

    # CF3: Extend deadline by 6 months (only relevant if significantly delayed)
    if delay_months > 3:
        ext_months  = months_left + 6
        new_req     = remaining / ext_months
        prob_gain3  = min(0.12, abs(new_req - required) / max(required, 1) * 0.5)
        cf.append({
            "scenario":              "Extend goal deadline by 6 months",
            "new_required_monthly":  round(new_req, 0),
            "probability_delta":     round(prob_gain3, 3),
            "months_earlier":        -6,
        })

    # CF4: Increase income by 10%
    if ctx["monthly_income"] > 0:
        new_surplus4 = max(ctx["monthly_income"] * 1.10 - forecast["predicted_expenses"], 0)
        new_feas4    = new_surplus4 * 0.70
        prob_gain4   = min(0.10, new_feas4 / max(required, 1) * 0.10)
        cf.append({
            "scenario":             "Increase monthly income by 10%",
            "new_feasible_monthly": round(new_feas4, 0),
            "probability_delta":    round(prob_gain4, 3),
            "months_earlier":       round(months_left * 0.08, 1),
        })

    # ── Human-readable feasibility note ──────────────────────────────────────
    lines = []
    if not ctx["has_enough_data"]:
        lines.append(
            "Note: Limited transaction history — estimates will improve "
            "with 2+ months of activity."
        )
        lines.append("")

    lines.append(
        f"{prob * 100:.0f}% probability to achieve '{ctx['goal_name']}' "
        f"by {original_completion}  [{health_tag}]"
    )
    lines.append("")
    lines.append(f"Required monthly:    INR {required:,.0f}  (mathematical minimum)")
    lines.append(f"Feasible monthly:    INR {feasible:,.0f}  (capacity-constrained estimate)")
    lines.append(f"Recommended monthly: INR {recommended:,.0f}  (risk-adjusted safe allocation)")

    if delay_months > 1:
        lines.append("")
        lines.append(
            f"At your current financial capacity, this goal will realistically "
            f"take {realistic_months:.0f} months instead of {months_left:.0f} months "
            f"— a delay of approximately {delay_months:.0f} months."
        )
        lines.append(f"Realistic completion: {realistic_completion}")

    if neg:
        lines.append("")
        lines.append("Key concerns:")
        for n in neg[:4]:
            lines.append(f"  - {n}")

    if pos:
        lines.append("")
        lines.append("Working in your favour:")
        for p in pos[:3]:
            lines.append(f"  + {p}")

    feasibility_note = "\n".join(lines)

    return {
        "health_tag":       health_tag,
        "feasibility_note": feasibility_note,
        "savings_plan": {
            "required_monthly":    round(required,    2),
            "feasible_monthly":    round(feasible,    2),
            "recommended_monthly": round(recommended, 2),
            "allocated_monthly":   round(allocated,   2),
        },
        "timeline": {
            "months_left":           round(months_left,       1),
            "original_completion":   original_completion,
            "realistic_months":      round(realistic_months,  1),
            "delay_months":          round(delay_months,      1),
            "realistic_completion":  realistic_completion,
            "on_schedule":           delay_months < 1.0,
        },
        "top_positive_drivers": [
            {"human_label": p, "shap_value":  0.10} for p in pos[:3]
        ],
        "top_negative_drivers": [
            {"human_label": n, "shap_value": -0.10} for n in neg[:3]
        ],
        "counterfactuals": cf[:4],
        "risk_level":       constraint["risk_level"],
    }
