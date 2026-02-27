"""
financial_shock_engine/simulations/monte_carlo.py
==================================================
Step 4 & 5 — Probabilistic Shock Simulation + Shock Capacity Calculation.

Runs 1000 vectorized scenarios simulating:
  • Daily spending variability (based on historical std)
  • Random unexpected expense shocks (₹1k–₹50k)
  • Goal contributions
  • Recurring fixed expenses

Then calculates:
  shock_capacity_amount  (₹ you can safely absorb)
  safe_shock_limit       (95% of simulations remain positive)
  risk_threshold         (50% of simulations start breaking)
  failure_threshold      (balance < 0 or goals missed)
  resilience_label       (Safe / Moderate / Fragile / Critical)
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from configs.settings import (
    MONTE_CARLO_SIMULATIONS,
    SAFETY_BUFFER_RATIO,
)

logger = logging.getLogger(__name__)

RNG = np.random.default_rng(seed=42)   # reproducible but varied per session


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_shock_simulation(features: dict, projection: dict) -> dict[str, Any]:
    """
    Execute Monte Carlo simulation and compute shock absorption capacity.

    Returns
    -------
    {
        shock_capacity_amount  : float   (₹ safely absorbable)
        safe_shock_limit       : float   (₹ — 95% scenarios stay positive)
        risk_threshold         : float   (₹ — 50% scenarios start breaking)
        failure_threshold      : float   (₹ — 10% scenarios fail)
        projected_end_balance  : float   (median simulated end balance)
        confidence_band_low    : float
        confidence_band_high   : float
        depletion_risk_flag    : bool
        resilience_label       : str
        resilience_score       : int     (0–100)
        simulation_count       : int
    }
    """
    n = MONTE_CARLO_SIMULATIONS

    # ── Simulation parameters ─────────────────────────────────────────────────
    liquid_balance   = features["liquid_balance"]
    mean_daily       = features["mean_daily_spend"]
    std_daily        = features["std_daily_spend"]
    days_remaining   = features["days_remaining"]
    goals_monthly    = features["goals_monthly_total_required"]
    monthly_income   = features["monthly_income"]
    recurring_daily  = _estimate_recurring_daily(features)

    if mean_daily == 0.0:
        mean_daily = features.get("burn_rate", features.get("avg_monthly_expense", 30000) / 30)
    if std_daily == 0.0:
        std_daily  = mean_daily * 0.30   # assume 30% volatility as fallback

    # Ensure positive std for sampling
    std_daily = max(std_daily, mean_daily * 0.05)

    # ── Run simulations (fully vectorized) ────────────────────────────────────
    # Shape: (n_simulations, days_remaining)
    daily_spend_sim = RNG.normal(
        loc=mean_daily,
        scale=std_daily,
        size=(n, days_remaining),
    ).clip(min=0.0)

    # Add one-time shock (only some days)
    # Randomly inject event spending on ~15% of days
    event_mask   = RNG.random(size=(n, days_remaining)) < 0.15
    event_shocks = RNG.uniform(500, 5000, size=(n, days_remaining)) * event_mask
    daily_spend_sim += event_shocks

    # Cumulative spend over remaining days
    total_remaining_spend = daily_spend_sim.sum(axis=1)   # shape: (n,)

    # Final balance for each simulation (before any external shock)
    # Include goals contribution and recurring expenses
    base_end_balance = (
        liquid_balance
        - total_remaining_spend
        - goals_monthly          # goal contribution this month
        - recurring_daily * days_remaining
    )

    # ── Shock injection analysis ───────────────────────────────────────────────
    # Test a range of shock amounts to find capacity thresholds
    shock_range = np.linspace(0, liquid_balance * 0.8, 500)  # ₹0 to 80% of balance
    survival_rates = _compute_survival_rates(base_end_balance, shock_range, liquid_balance)

    safe_shock   = _find_shock_at_survival(shock_range, survival_rates, target=0.95)
    risk_shock   = _find_shock_at_survival(shock_range, survival_rates, target=0.50)
    fail_shock   = _find_shock_at_survival(shock_range, survival_rates, target=0.10)

    # ── Shock Capacity (Step 5 formula) ───────────────────────────────────────
    proj_median_balance = float(np.median(base_end_balance))
    mandatory_remaining = _mandatory_remaining(features)
    safety_buffer       = proj_median_balance * SAFETY_BUFFER_RATIO

    shock_capacity = max(
        proj_median_balance
        - mandatory_remaining
        - goals_monthly
        - safety_buffer,
        0.0,
    )

    # Use the more conservative of formula vs Monte Carlo safe threshold
    shock_capacity = min(shock_capacity, safe_shock)

    # ── Depletion risk ────────────────────────────────────────────────────────
    depletion_risk = float(np.mean(base_end_balance < 0)) > 0.20   # >20% sims deplete

    # ── Resilience score (0–100) ──────────────────────────────────────────────
    resilience_score = _compute_resilience_score(features, shock_capacity, proj_median_balance)
    resilience_label = _resilience_label(resilience_score)

    logger.info(
        "Simulation done | capacity=₹%.0f | safe=₹%.0f | score=%d | label=%s",
        shock_capacity, safe_shock, resilience_score, resilience_label,
    )

    return {
        "shock_capacity_amount":  round(shock_capacity, 2),
        "safe_shock_limit":       round(safe_shock, 2),
        "risk_threshold":         round(risk_shock, 2),
        "failure_threshold":      round(fail_shock, 2),
        "projected_end_balance":  round(proj_median_balance, 2),
        "confidence_band_low":    round(float(np.percentile(base_end_balance, 10)), 2),
        "confidence_band_high":   round(float(np.percentile(base_end_balance, 90)), 2),
        "depletion_risk_flag":    depletion_risk,
        "resilience_label":       resilience_label,
        "resilience_score":       resilience_score,
        "simulation_count":       n,
        "mandatory_remaining":    round(mandatory_remaining, 2),
        "safety_buffer_applied":  round(safety_buffer, 2),
    }


def simulate_with_shock(
    features: dict,
    shock_amount: float,
) -> dict[str, Any]:
    """
    Re-run simulation with a specific shock amount applied today.
    Used by goal-impact analysis.
    """
    adjusted_features = features.copy()
    adjusted_features["liquid_balance"] = max(
        features["liquid_balance"] - shock_amount, 0.0
    )
    projection = {}  # not used here
    result = run_shock_simulation(adjusted_features, projection)
    result["shock_applied"] = shock_amount
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_survival_rates(
    base_balances: np.ndarray,
    shock_range: np.ndarray,
    liquid_balance: float,
) -> np.ndarray:
    """For each shock ₹ amount, compute fraction of simulations that survive (balance > 0)."""
    # (n_simulations, n_shocks) — subtract each shock from each simulation's end balance
    after_shock = base_balances[:, None] - shock_range[None, :]   # broadcasting
    return (after_shock > 0).mean(axis=0)   # shape: (n_shocks,)


def _find_shock_at_survival(
    shock_range: np.ndarray,
    survival_rates: np.ndarray,
    target: float,
) -> float:
    """Find the largest shock amount where survival_rate >= target."""
    mask = survival_rates >= target
    if not mask.any():
        return 0.0
    return float(shock_range[mask].max())


def _estimate_recurring_daily(features: dict) -> float:
    """Estimate daily recurring expense from feature data."""
    avg_monthly = features.get("avg_monthly_expense", 0.0)
    recurring_ratio = features.get("recurring_ratio", 0.35)
    return (avg_monthly * recurring_ratio) / 30.0


def _mandatory_remaining(features: dict) -> float:
    """Estimate mandatory (fixed) spend for remaining days."""
    days_remaining = features.get("days_remaining", 1)
    avg_monthly    = features.get("avg_monthly_expense", 0.0)
    recurring_ratio = features.get("recurring_ratio", 0.35)
    fixed_cats     = ["Rent", "Utilities", "Healthcare", "Finance"]

    cat_spend = features.get("category_spend_cm", {})
    fixed_so_far = sum(cat_spend.get(c, 0.0) for c in fixed_cats)
    days_in_month = features.get("days_in_month", 30)

    # Estimate remaining fixed spend proportionally
    daily_fixed = (avg_monthly * recurring_ratio) / days_in_month
    return daily_fixed * days_remaining


def _compute_resilience_score(
    features: dict,
    shock_capacity: float,
    proj_balance: float,
) -> int:
    """
    Score 0–100 based on:
      40pts — shock_capacity / monthly_income ratio
      30pts — low expense_volatility
      20pts — days_to_depletion > 30
      10pts — safe_surplus > 0
    """
    income    = max(features.get("monthly_income", 1), 1)
    vol       = features.get("expense_volatility", 0.5)
    dtd       = features.get("days_to_depletion", 0)
    surplus   = features.get("safe_surplus", 0)

    cap_score = min(shock_capacity / income, 1.0) * 40
    vol_score = max(0, 1.0 - min(vol, 1.0)) * 30
    dtd_score = min(dtd / 60, 1.0) * 20
    sur_score = 10.0 if surplus > 0 else 0.0

    return int(round(cap_score + vol_score + dtd_score + sur_score))


def _resilience_label(score: int) -> str:
    if score >= 75:
        return "Safe"
    if score >= 50:
        return "Moderate"
    if score >= 25:
        return "Fragile"
    return "Critical"
