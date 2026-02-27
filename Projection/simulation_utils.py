"""
ai_projection_engine/server/utils/simulation_utils.py
======================================================
Monte Carlo simulation utilities for probabilistic expenditure forecasting.

Design decisions:
  • Gamma distribution is used per-category (right-skewed, non-negative).
  • Method-of-moments fallback when scipy fit diverges.
  • NumPy's default_rng for reproducible, vectorised simulation.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats


# ── Distribution Fitting ───────────────────────────────────────────────────────

def fit_gamma_distribution(amounts: np.ndarray) -> Tuple[float, float, float]:
    """
    Fit a Gamma(shape, loc=0, scale) distribution to positive daily spend amounts.
    Falls back to method-of-moments if scipy MLE fails.

    Returns: (shape, loc, scale)
    """
    amounts = amounts[amounts > 0]

    if len(amounts) < 3:
        # Degenerate: use mean as single-parameter exponential proxy
        mean = float(amounts.mean()) if len(amounts) > 0 else 10.0
        return 1.0, 0.0, mean

    try:
        shape, loc, scale = stats.gamma.fit(amounts, floc=0)
        # Guard against degenerate fits
        if not (np.isfinite(shape) and np.isfinite(scale) and shape > 0 and scale > 0):
            raise ValueError("Degenerate gamma fit")
        return float(shape), float(loc), float(scale)
    except Exception:
        # Method-of-moments fallback
        mean = float(amounts.mean())
        std = float(amounts.std()) if amounts.std() > 0 else mean * 0.3
        if std == 0 or mean == 0:
            return 1.0, 0.0, max(mean, 0.01)
        shape = (mean / std) ** 2
        scale = (std ** 2) / mean
        return max(shape, 0.1), 0.0, max(scale, 0.01)


# ── Core Simulation ────────────────────────────────────────────────────────────

def simulate_remaining_days(
    daily_amounts: np.ndarray,
    remaining_days: int,
    n_simulations: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """
    Monte Carlo: simulate total spend over *remaining_days* for *n_simulations* paths.

    Returns array of shape (n_simulations,) with total projected spend.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    if len(daily_amounts) == 0 or remaining_days <= 0:
        return np.zeros(n_simulations)

    shape, loc, scale = fit_gamma_distribution(daily_amounts)

    # (n_simulations × remaining_days) daily draws, summed across days
    draws = rng.gamma(
        shape=shape,
        scale=scale,
        size=(n_simulations, remaining_days),
    )
    return draws.sum(axis=1)


def simulate_category_forecast(
    df: pd.DataFrame,
    category: str,
    remaining_days: int,
    n_simulations: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """
    Monte Carlo forecast for a single category.
    Uses historical daily amounts (all available months) to fit the distribution.
    """
    cat_df = df[df["category"] == category]
    if cat_df.empty:
        return np.zeros(n_simulations)

    daily_amounts = cat_df.groupby("date")["amount"].sum().values
    return simulate_remaining_days(daily_amounts, remaining_days, n_simulations, rng)


# ── Result Analysis ────────────────────────────────────────────────────────────

def compute_percentiles(simulation_results: np.ndarray) -> Dict[str, float]:
    """Compute P25 / P50 / P90 from a simulation output array."""
    if len(simulation_results) == 0:
        return {"p25": 0.0, "p50": 0.0, "p90": 0.0}
    return {
        "p25": float(np.percentile(simulation_results, 25)),
        "p50": float(np.percentile(simulation_results, 50)),
        "p90": float(np.percentile(simulation_results, 90)),
    }


# ── Calendar Helpers ───────────────────────────────────────────────────────────

def get_remaining_days_in_month() -> int:
    """Number of calendar days remaining in the current month (inclusive of today)."""
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    return days_in_month - now.day + 1


def estimate_depletion_date(
    current_balance: float,
    avg_daily_spend: float,
) -> Optional[str]:
    """
    Estimate the date the account balance would reach ≈ ₹0
    given the current average daily spend.

    Returns ISO date string if depletion is expected within the current month,
    otherwise None.
    """
    if avg_daily_spend <= 0 or current_balance <= 0:
        return None

    days_to_depletion = int(current_balance / avg_daily_spend)
    depletion_dt = datetime.now() + timedelta(days=days_to_depletion)
    now = datetime.now()

    if depletion_dt.year == now.year and depletion_dt.month == now.month:
        return depletion_dt.strftime("%Y-%m-%d")
    return None
