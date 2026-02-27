"""
ml_models/goal_feasibility_engine/feasibility_simulator.py
===========================================================
Monte Carlo Feasibility Simulator — the core probability engine.

Design (NON-NEGOTIABLE):
  - Does NOT use predefined probabilities
  - Does NOT use lookup tables or static thresholds
  - Generates N_SIMULATIONS independent surplus scenarios
  - Simulates month-by-month goal accumulation for each scenario
  - probability = successful_simulations / N_SIMULATIONS

Each simulation:
  1. For each month until deadline:
     a. Sample surplus from Normal(predicted_surplus, surplus_std)
     b. Apply income disruption if income_stability < 1.0
     c. Cap contribution at 70% of sampled surplus (behavioral cap)
     d. Further cap at max_feasible_monthly (constraint-based cap)
     e. Add contribution to running balance
  2. If balance >= target before deadline: success

Outputs:
  probability               — P(goal achieved by deadline)
  pct_5th / pct_50th / pct_95th  — distribution of final balances
  expected_completion_months — median months to completion
  shortfall_fraction        — average deficit in failing runs (0–1)
  n_simulations             — for transparency
"""
from __future__ import annotations

import numpy as np

N_SIMULATIONS  = 750
BEHAVIORAL_CAP = 0.70   # max fraction of any month's surplus to contribute


def run_simulation(
    current_amount:       float,
    target_amount:        float,
    months_left:          float,
    predicted_surplus:    float,
    surplus_std:          float,
    max_feasible_monthly: float,
    allocated_monthly:    float,
    income_stability:     float = 1.0,
    random_seed:          int   = 42,
) -> dict:
    """
    Monte Carlo simulation of goal achievement probability.

    Parameters
    ----------
    current_amount       Current saved amount toward the goal.
    target_amount        Goal target amount.
    months_left          Months until the goal deadline.
    predicted_surplus    Expected monthly surplus (mean of distribution).
    surplus_std          Standard deviation of monthly surplus.
    max_feasible_monthly Max contribution per month (from behavioral_constraint_model).
    allocated_monthly    Target contribution for this goal specifically.
    income_stability     1.0 = salaried, <1.0 = variable income.
    random_seed          For reproducibility.
    """
    rng       = np.random.default_rng(random_seed)
    n_months  = max(int(np.ceil(months_left)), 1)

    # The actual monthly contribution target is the lower of all constraints
    monthly_target = min(allocated_monthly, max_feasible_monthly)

    success_count        = 0
    final_balances       = []
    completion_months_ls = []

    for _ in range(N_SIMULATIONS):
        balance   = current_amount
        completed = False

        for month in range(n_months):
            # Sample surplus for this month
            sampled_surplus = float(
                rng.normal(predicted_surplus, max(surplus_std, predicted_surplus * 0.05))
            )
            sampled_surplus = max(sampled_surplus, 0.0)

            # Income disruption: variable-income users occasionally earn much less
            if income_stability < 1.0:
                disruption_prob = 1.0 - income_stability
                if rng.random() < disruption_prob:
                    sampled_surplus *= float(rng.uniform(0.15, 0.65))

            # Behavioral cap: never contribute more than 70% of this month's surplus
            max_this_month = sampled_surplus * BEHAVIORAL_CAP

            # Actual contribution: most restrictive of all caps
            contribution = max(
                min(monthly_target, max_this_month, max_feasible_monthly),
                0.0,
            )

            balance += contribution

            if balance >= target_amount:
                success_count += 1
                completion_months_ls.append(month + 1)
                completed = True
                break

        final_balances.append(balance)
        if not completed:
            completion_months_ls.append(n_months)   # did not complete in time

    probability = success_count / N_SIMULATIONS
    arr         = np.array(final_balances, dtype=float)

    # Average shortfall in failing simulations (as fraction of target)
    failed        = [b for b in final_balances if b < target_amount]
    avg_shortfall = (
        (target_amount - float(np.mean(failed))) / max(target_amount, 1.0)
        if failed else 0.0
    )

    return {
        "probability":                round(float(probability),                   4),
        "pct_5th":                    round(float(np.percentile(arr,  5)),         2),
        "pct_50th":                   round(float(np.percentile(arr, 50)),         2),
        "pct_95th":                   round(float(np.percentile(arr, 95)),         2),
        "expected_completion_months": round(float(np.median(completion_months_ls)), 1),
        "shortfall_fraction":         round(float(avg_shortfall),                  3),
        "n_simulations":              N_SIMULATIONS,
    }
