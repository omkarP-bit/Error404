"""
financial_shock_engine/tests/test_shock_engine.py
==================================================
Validation tests for the Shock Engine pipeline.

Tests:
  1. DB connectivity
  2. Feature builder outputs (types, ranges)
  3. Budget projector (EWMA sanity)
  4. Monte Carlo simulation outputs
  5. Shock capacity > 0 for valid user
  6. Goal impact with sparse data (< 2 months)
  7. Savings insight capping (≤ 30% of spend)
  8. API endpoint responses (requires server running)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
import numpy as np
import pandas as pd

from configs.database import SessionLocal, ping_db
from configs.settings import MAX_SAVINGS_SUGGESTION_RATIO


# ── 1. DB connectivity ─────────────────────────────────────────────────────────

def test_db_ping():
    assert ping_db(), "Database must be reachable"


# ── 2. Feature builder ─────────────────────────────────────────────────────────

def test_feature_builder_types():
    from feature_engine.data_ingestion import fetch_user_data
    from feature_engine.feature_builder import build_features

    db = SessionLocal()
    try:
        raw = fetch_user_data(db, 1)
        feats = build_features(raw)

        assert isinstance(feats["monthly_income"], float)
        assert isinstance(feats["avg_monthly_expense"], float)
        assert isinstance(feats["expense_volatility"], float)
        assert isinstance(feats["liquid_balance"], float)
        assert isinstance(feats["burn_rate"], float)
        assert isinstance(feats["top_categories_6m"], list)
        assert 0.0 <= feats["expense_volatility"] < 100.0
        assert feats["days_remaining"] >= 0
    finally:
        db.close()


def test_feature_builder_sparse_data():
    """Engine must not crash with empty transaction DataFrame."""
    from feature_engine.feature_builder import build_features

    raw = {
        "transactions_6m":    pd.DataFrame(),
        "current_month_txns": pd.DataFrame(),
        "user_profile":       {"monthly_income": 50000, "risk_profile": "MODERATE"},
        "accounts":           [{"current_balance": 100000}],
        "goals":              [],
        "budget_profile":     None,
        "txn_patterns":       [],
        "snapshot_date":      "2026-02-27",
    }
    feats = build_features(raw)
    assert feats["monthly_income"] == 50000.0
    assert feats["liquid_balance"] == 100000.0
    assert feats["expense_volatility"] == 0.0


# ── 3. Budget projector ────────────────────────────────────────────────────────

def test_budget_projector_heuristic():
    """Heuristic fallback must return valid balance."""
    from feature_engine.budget_projector import project_month_balance

    feats = {
        "has_sufficient_data": False,
        "avg_monthly_expense": 30000.0,
        "liquid_balance": 80000.0,
        "days_remaining": 10,
        "std_daily_spend": 500.0,
        "burn_rate": 1200.0,
        "mean_daily_spend": 0.0,
        "expense_volatility": 0.2,
        "days_passed": 20,
    }
    proj = project_month_balance(feats)
    assert proj["projection_method"] == "heuristic_fallback"
    assert isinstance(proj["projected_end_month_balance"], float)


def test_budget_projector_ewma():
    """EWMA blend must produce a positive estimate for normal spending."""
    from feature_engine.budget_projector import project_month_balance

    feats = {
        "has_sufficient_data": True,
        "avg_monthly_expense": 40000.0,
        "liquid_balance": 120000.0,
        "days_remaining": 5,
        "std_daily_spend": 300.0,
        "burn_rate": 1400.0,
        "mean_daily_spend": 1333.0,
        "expense_volatility": 0.15,
        "days_passed": 26,
    }
    proj = project_month_balance(feats)
    assert proj["projection_method"] == "ewma_mad_blend"
    assert proj["daily_spend_estimate"] > 0
    assert proj["confidence_band_low"] <= proj["projected_end_month_balance"]


# ── 4. Monte Carlo simulation ──────────────────────────────────────────────────

def test_monte_carlo_outputs():
    from simulations.monte_carlo import run_shock_simulation

    feats = {
        "liquid_balance": 100000.0,
        "mean_daily_spend": 1500.0,
        "std_daily_spend": 400.0,
        "days_remaining": 8,
        "goals_monthly_total_required": 5000.0,
        "monthly_income": 120000.0,
        "recurring_ratio": 0.35,
        "avg_monthly_expense": 50000.0,
        "days_in_month": 28,
        "category_spend_cm": {},
        "safe_surplus": 10000.0,
        "expense_volatility": 0.25,
        "days_to_depletion": 45.0,
        "burn_rate": 1500.0,
    }
    result = run_shock_simulation(feats, {})

    assert result["shock_capacity_amount"] >= 0.0
    assert result["safe_shock_limit"] >= 0.0
    assert result["resilience_label"] in ("Safe", "Moderate", "Fragile", "Critical")
    assert 0 <= result["resilience_score"] <= 100
    assert result["simulation_count"] == 1000
    assert result["confidence_band_low"] <= result["projected_end_balance"]


# ── 5. Shock capacity for real user ───────────────────────────────────────────

def test_shock_capacity_real_user():
    from server.services.shock_capacity_service import get_shock_capacity

    db = SessionLocal()
    try:
        result = get_shock_capacity(db, 1)
        assert result["shock_capacity"] >= 0.0
        assert result["resilience_label"] in ("Safe", "Moderate", "Fragile", "Critical")
        assert result["current_balance"] > 0.0
        assert result["monthly_income"] > 0.0
        print(f"\n  ✓ Shock Capacity: ₹{result['shock_capacity']:,.0f}")
        print(f"  ✓ Resilience: {result['resilience_label']} ({result['resilience_score']}/100)")
        print(f"  ✓ Balance: ₹{result['current_balance']:,.0f}")
    finally:
        db.close()


# ── 6. Goal impact ─────────────────────────────────────────────────────────────

def test_goal_impact_simulation():
    from server.services.goal_impact_service import get_goal_impact

    db = SessionLocal()
    try:
        result = get_goal_impact(db, 1, shock_amounts=[10000.0, 25000.0])
        assert len(result["shock_scenarios"]) == 2
        for scenario in result["shock_scenarios"]:
            assert scenario["shock_amount"] > 0
            assert scenario["resilience_after"] in ("Safe", "Moderate", "Fragile", "Critical")
            for gi in scenario["goal_impacts"]:
                assert gi["delay_in_months"] >= 0
    finally:
        db.close()


# ── 7. Savings capping ────────────────────────────────────────────────────────

def test_savings_capping():
    """No suggested saving should exceed 30% of category spend."""
    from server.services.savings_insight_service import get_savings_insights

    db = SessionLocal()
    try:
        result = get_savings_insights(db, 1)
        for opp in result["opportunities"]:
            if opp["current_spend"] > 0:
                ratio = opp["save_amount"] / opp["current_spend"]
                assert ratio <= MAX_SAVINGS_SUGGESTION_RATIO + 0.01, (
                    f"{opp['category']}: save_amount {opp['save_amount']} "
                    f"> 30% of {opp['current_spend']}"
                )
    finally:
        db.close()


# ── 8. LLM fallback always produces non-empty string ──────────────────────────

def test_llm_fallback_with_real_context():
    from llm.mistral_client import MistralClient

    ctx = {
        "shock_capacity": 18500.0,
        "safe_shock_limit": 12000.0,
        "resilience_label": "Moderate",
        "current_balance": 95000.0,
        "top_risk_categories": ["Food & Dining", "Shopping"],
        "depletion_risk": False,
        "total_monthly_saveable": 3200.0,
        "expense_volatility": 0.3,
    }
    client = MistralClient()
    result = client._fallback(ctx)
    assert isinstance(result, str)
    assert len(result) > 20
    assert "₹" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
