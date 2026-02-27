"""
ml_models/goal_feasibility_engine/
===================================
Capacity-Constrained Goal Feasibility Engine v3.0

Architecture:
  feature_builder.py          — Aggregate all financial context from live DB
  surplus_forecaster.py       — Predict future surplus via robust statistics
  behavioral_constraint_model.py — Compute max realistic saving (not theoretical)
  allocation_optimizer.py     — Priority-aware multi-goal allocation
  feasibility_simulator.py    — Monte Carlo probability (750 simulations)
  explanation_generator.py    — Human-readable insights & counterfactuals
  predict_goal_feasibility.py — Orchestrator / public API entry point

Key design principles (NON-NEGOTIABLE):
  - Never assume 100% surplus can be allocated
  - Never assume perfect monthly discipline
  - Never use static or dropdown probabilities
  - Always respect: surplus, volatility, liquidity, behavior, competing goals
"""
from ml_models.goal_feasibility_engine.predict_goal_feasibility import (
    predict_goal_feasibility,
    predict_bulk,
)

__all__ = ["predict_goal_feasibility", "predict_bulk"]
