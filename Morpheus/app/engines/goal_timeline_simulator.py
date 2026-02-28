"""
app/engines/goal_timeline_simulator.py
======================================
Timeline simulation engine for goals.

Simulates actual goal progress using:
- monthly_contribution (actual SIP amount)
- Expected return by goal type
- Correct compounding logic

Outputs:
- months_to_target (when goal is reached at current SIP)
- months_to_deadline (months remaining until deadline)
- delta_months (positive=ahead, negative=behind, zero=on-time)
- feasibility (achievable within deadline)
"""

from datetime import datetime, date
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models import Goal


# Expected annual returns by goal type
EXPECTED_RETURNS = {
    "emergency_fund": 0.06,      # 6%
    "retirement": 0.13,           # 13%
    "long_term": 0.12,            # 12%
    "short_term": 0.08,           # 8%
    "custom": 0.11,               # 11% default
}


def get_expected_return(goal_type: Optional[str]) -> float:
    """Get annual return rate for goal type."""
    if not goal_type:
        return EXPECTED_RETURNS["custom"]
    goal_type_lower = goal_type.lower().strip()
    return EXPECTED_RETURNS.get(goal_type_lower, EXPECTED_RETURNS["custom"])


def simulate_goal_timeline(goal: Goal) -> Dict:
    """
    Simulate goal timeline using correct compounding logic.
    
    Returns:
        {
            'months_to_target': int,         # Months to reach target at current SIP
            'months_to_deadline': int,       # Months until deadline
            'delta_months': int,             # delta = months_to_target - months_to_deadline
            'status': 'on_time|early|late',  # Feasibility status
            'feasibility_pct': float,        # Probability of hitting deadline (0-100)
            'runway_months': Optional[int],  # Emergency fund coverage in months
        }
    """
    now = datetime.utcnow().date()
    
    if not goal.deadline:
        return {
            'months_to_target': 9999,
            'months_to_deadline': 9999,
            'delta_months': 0,
            'status': 'on_time',
            'feasibility_pct': 50.0,
            'runway_months': None,
        }
    
    # Calculate months until deadline
    deadline = goal.deadline
    months_to_deadline = (deadline.year - now.year) * 12 + (deadline.month - now.month)
    months_to_deadline = max(0, months_to_deadline)
    
    # If no SIP set, goal is impossible
    if goal.monthly_contribution <= 0:
        return {
            'months_to_target': 99999,
            'months_to_deadline': months_to_deadline,
            'delta_months': 99999,
            'status': 'impossible',
            'feasibility_pct': 0.0,
            'runway_months': None,
        }
    
    # Simulate month-by-month compounding
    balance = float(goal.current_amount)
    target = float(goal.target_amount)
    monthly_contribution = float(goal.monthly_contribution)
    annual_return = get_expected_return(goal.goal_type)
    monthly_return = (1 + annual_return) ** (1/12) - 1
    
    months_to_target = 0
    max_months = 1200  # Safety cap: 100 years
    
    while balance < target and months_to_target < max_months:
        # Apply return first, then contribution
        balance = balance * (1 + monthly_return)
        balance += monthly_contribution
        months_to_target += 1
    
    if months_to_target >= max_months:
        # Unrealistic (shouldn't happen with reasonable SIP)
        return {
            'months_to_target': max_months,
            'months_to_deadline': months_to_deadline,
            'delta_months': max_months - months_to_deadline,
            'status': 'impossible',
            'feasibility_pct': 0.0,
            'runway_months': None,
        }
    
    # Determine status
    delta = months_to_target - months_to_deadline
    
    if delta <= 0:
        status = 'early' if delta < 0 else 'on_time'
        feasibility = 85.0 + (min(-delta, 12) / 12) * 15  # Higher feasibility if ahead
    else:
        status = 'late'
        feasibility = max(0.0, 85.0 - (delta / 6.0))  # Reduces by ~14% per month behind
    
    feasibility = min(100.0, max(0.0, feasibility))
    
    # For emergency fund goals, compute runway (months of expenses covered)
    runway_months = None
    if goal.goal_type and 'emergency' in goal.goal_type.lower():
        # Estimate monthly expense as target / 6 (6 months target coverage)
        estimated_monthly_expense = target / 6.0
        if estimated_monthly_expense > 0:
            runway_months = round(balance / estimated_monthly_expense, 1)
    
    return {
        'months_to_target': months_to_target,
        'months_to_deadline': months_to_deadline,
        'delta_months': delta,
        'status': status,
        'feasibility_pct': round(feasibility, 2),
        'runway_months': runway_months,
    }
