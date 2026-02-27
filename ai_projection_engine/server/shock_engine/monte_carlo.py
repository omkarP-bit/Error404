"""
server/shock_engine/monte_carlo.py
===================================
Vectorized Monte Carlo shock simulation (1000 scenarios).
Computes shock absorption capacity, resilience score, and depletion risk.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_N_SIMS         = 1000
_SAFETY_BUFFER  = 0.30
RNG             = np.random.default_rng(seed=42)


def run_simulation(features: dict) -> dict[str, Any]:
    liquid    = features["liquid_balance"]
    mean_d    = features.get("mean_daily_spend", 0.0) or features.get("burn_rate", 0.0)
    std_d     = features.get("std_daily_spend", 0.0)
    days_r    = max(features.get("days_remaining", 1), 1)
    goals_m   = features.get("goals_monthly_total_required", 0.0)
    recur_r   = features.get("recurring_ratio", 0.35)
    avg_exp   = features.get("avg_monthly_expense", 0.0)

    if mean_d == 0.0:
        mean_d = avg_exp / 30.0
    std_d = max(std_d, mean_d * 0.10)

    # Daily spend matrix: (N_SIMS x days_remaining)
    daily_sim = RNG.normal(mean_d, std_d, (1000, days_r)).clip(min=0.0)

    # Random event shocks on ~15% of days
    events = RNG.random((1000, days_r)) < 0.15
    daily_sim += RNG.uniform(500, 5000, (1000, days_r)) * events

    # Recurring daily cost
    recur_daily = (avg_exp * recur_r) / 30.0
    total_spend = daily_sim.sum(axis=1) + recur_daily * days_r

    # End-of-month balance per simulation (subtract goals contribution too)
    base_end = liquid - total_spend - goals_m

    # ── Shock capacity thresholds ──────────────────────────────────────────────
    shock_range   = np.linspace(0, liquid * 0.85, 600)
    after_shock   = base_end[:, None] - shock_range[None, :]
    survival      = (after_shock > 0).mean(axis=0)

    safe_shock    = _at_survival(shock_range, survival, 0.95)
    risk_shock    = _at_survival(shock_range, survival, 0.50)
    fail_shock    = _at_survival(shock_range, survival, 0.10)

    # ── Formula-based capacity (Step 5 spec) ──────────────────────────────────
    proj_median    = float(np.median(base_end))
    days_in_month  = features.get("days_in_month", 30)
    fixed_daily    = (avg_exp * 0.40) / days_in_month
    mandatory_rem  = fixed_daily * days_r
    safety_buf     = proj_median * _SAFETY_BUFFER

    shock_capacity = max(proj_median - mandatory_rem - goals_m - safety_buf, 0.0)
    shock_capacity = min(shock_capacity, safe_shock)

    depletion_risk = float(np.mean(base_end < 0)) > 0.20

    score = _resilience_score(features, shock_capacity, proj_median)
    label = _resilience_label(score)

    return {
        "shock_capacity_amount":  round(shock_capacity, 2),
        "safe_shock_limit":       round(safe_shock, 2),
        "risk_threshold":         round(risk_shock, 2),
        "failure_threshold":      round(fail_shock, 2),
        "projected_end_balance":  round(proj_median, 2),
        "confidence_band_low":    round(float(np.percentile(base_end, 10)), 2),
        "confidence_band_high":   round(float(np.percentile(base_end, 90)), 2),
        "depletion_risk_flag":    depletion_risk,
        "resilience_label":       label,
        "resilience_score":       score,
        "mandatory_remaining":    round(mandatory_rem, 2),
        "safety_buffer_applied":  round(max(safety_buf, 0), 2),
    }


def simulate_with_shock(features: dict, shock_amount: float) -> dict:
    adj        = features.copy()
    new_liquid = max(features["liquid_balance"] - shock_amount, 0.0)
    adj["liquid_balance"] = new_liquid
    # Recalculate days-to-depletion so _resilience_score reflects the new balance
    burn = features.get("burn_rate", 0.0)
    adj["days_to_depletion"] = new_liquid / burn if burn > 0 else 9999.0
    r = run_simulation(adj)
    r["shock_applied"] = shock_amount
    return r


def _at_survival(shock_range, survival, target):
    mask = survival >= target
    return float(shock_range[mask].max()) if mask.any() else 0.0


def _resilience_score(features, capacity, proj_balance):
    income  = max(features.get("monthly_income", 1), 1)
    vol     = features.get("expense_volatility", 0.5)
    dtd     = features.get("days_to_depletion", 0)
    surplus = features.get("safe_surplus", 0)
    cap_s   = min(capacity / income, 1.0) * 40
    vol_s   = max(0, 1.0 - min(vol, 1.0)) * 30
    dtd_s   = min(dtd / 60, 1.0) * 20
    sur_s   = 10.0 if surplus > 0 else 0.0
    return int(round(cap_s + vol_s + dtd_s + sur_s))


def _resilience_label(score):
    if score >= 75: return "Safe"
    if score >= 50: return "Moderate"
    if score >= 25: return "Fragile"
    return "Critical"
