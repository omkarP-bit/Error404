"""
financial_shock_engine/server/services/shock_capacity_service.py
=================================================================
Step 4+5 Orchestrator — Shock Capacity end-to-end pipeline.

Flow:
  1. Ingest raw data
  2. Build features
  3. Project budget (EWMA)
  4. Run Monte Carlo simulation
  5. Return structured ShockResult
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from feature_engine.data_ingestion import fetch_user_data
from feature_engine.feature_builder import build_features
from feature_engine.budget_projector import project_month_balance
from simulations.monte_carlo import run_shock_simulation

logger = logging.getLogger(__name__)


def get_shock_capacity(db: Session, user_id: int) -> dict[str, Any]:
    """
    Full shock capacity computation for a user.

    Returns the complete ShockResult dict ready to be serialized as API response.
    """
    t0 = time.perf_counter()

    # ── Pipeline ──────────────────────────────────────────────────────────────
    raw        = fetch_user_data(db, user_id)
    features   = build_features(raw)
    projection = project_month_balance(features)
    simulation = run_shock_simulation(features, projection)

    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    logger.info("Shock capacity computed for user=%d in %dms", user_id, elapsed)

    return {
        "user_id":     user_id,
        "user_name":   raw["user_profile"].get("name", ""),
        "computed_at": datetime.utcnow().isoformat(),
        "elapsed_ms":  elapsed,

        # ── Core output ────────────────────────────────────────────────────────
        "shock_capacity":         simulation["shock_capacity_amount"],
        "safe_shock_limit":       simulation["safe_shock_limit"],
        "risk_threshold":         simulation["risk_threshold"],
        "failure_threshold":      simulation["failure_threshold"],
        "resilience_label":       simulation["resilience_label"],
        "resilience_score":       simulation["resilience_score"],
        "depletion_risk":         simulation["depletion_risk_flag"],

        # ── Balance projections ────────────────────────────────────────────────
        "current_balance":        features["liquid_balance"],
        "projected_end_balance":  simulation["projected_end_balance"],
        "confidence_band_low":    simulation["confidence_band_low"],
        "confidence_band_high":   simulation["confidence_band_high"],

        # ── Spend summary ─────────────────────────────────────────────────────
        "current_month_spend":    features["current_month_spend"],
        "projected_month_spend":  features["projected_month_spend"],
        "monthly_income":         features["monthly_income"],
        "monthly_surplus":        features["monthly_surplus"],
        "burn_rate_daily":        features["burn_rate"],
        "days_to_depletion":      features["days_to_depletion"],

        # ── Behavioral signals ────────────────────────────────────────────────
        "expense_volatility":     features["expense_volatility"],
        "top_categories":         features["top_categories_6m"],
        "discretionary_ratio":    features["discretionary_ratio"],
        "trend_slope":            features["trend_slope"],

        # ── Meta ───────────────────────────────────────────────────────────────
        "has_sufficient_data":    features["has_sufficient_data"],
        "data_months":            features["data_months_available"],
        "projection_method":      projection["projection_method"],
        "simulation_count":       simulation["simulation_count"],
    }
