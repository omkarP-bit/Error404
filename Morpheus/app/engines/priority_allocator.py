"""
app/engines/priority_allocator.py
==================================
Multi-goal priority allocation engine.

Distributes available surplus across goals based on priority weights,
with proportional redistribution if any priority group is empty.

Principle:
- High priority: 50%
- Medium priority: 30%
- Low priority: 20%

If a priority level has no goals, redistribute proportionally.
"""

from typing import List, Dict, Optional
from app.models import Goal


# Priority level weights (before normalization)
BASE_WEIGHTS = {
    1: 0.50,  # High
    2: 0.30,  # Medium
    3: 0.20,  # Low
}


def allocate_surplus_to_goals(
    goals: List[Goal],
    available_monthly_surplus: float,
    emergency_fund_goal: Optional[Goal] = None,
) -> Dict[int, float]:
    """
    Allocate available monthly surplus across goals based on priority.
    
    Special rule: Emergency fund override.
    If emergency fund incomplete (current < 80% of target):
        70% of surplus → Emergency fund
        30% of surplus → Other goals (distributed by priority)
    
    Args:
        goals: List of active Goal objects
        available_monthly_surplus: Monthly amount available to distribute
        emergency_fund_goal: Emergency fund goal object (optional)
    
    Returns:
        {
            goal_id: monthly_contribution,
            ...
        }
    
    Example:
        allocation = allocate_surplus_to_goals(
            goals=[goal1, goal2, goal3],
            available_monthly_surplus=5000,
            emergency_fund_goal=goal1
        )
        # {1: 3500, 2: 1000, 3: 500}
    """
    allocation = {}
    
    if not goals or available_monthly_surplus <= 0:
        return allocation
    
    # Check emergency fund status
    emergency_incomplete = False
    if emergency_fund_goal:
        if emergency_fund_goal.target_amount > 0:
            completion_pct = emergency_fund_goal.current_amount / emergency_fund_goal.target_amount
            emergency_incomplete = completion_pct < 0.80
    
    # Split surplus if emergency fund incomplete
    if emergency_incomplete and emergency_fund_goal:
        emergency_allocation = available_monthly_surplus * 0.70
        other_surplus = available_monthly_surplus * 0.30
        
        allocation[emergency_fund_goal.goal_id] = round(emergency_allocation, 2)
        available_monthly_surplus = other_surplus
        goals = [g for g in goals if g.goal_id != emergency_fund_goal.goal_id]
    
    if not goals or available_monthly_surplus <= 0:
        return allocation
    
    # Group goals by priority
    priority_groups = {1: [], 2: [], 3: []}
    for goal in goals:
        priority = goal.priority if goal.priority in [1, 2, 3] else 2
        priority_groups[priority].append(goal)
    
    # Calculate active weights (only for priorities with goals)
    active_weights = {}
    total_weight = 0
    
    for priority, weight in BASE_WEIGHTS.items():
        if priority_groups[priority]:  # Only if group has goals
            active_weights[priority] = weight
            total_weight += weight
    
    # Normalize weights if some priority groups are empty
    if total_weight == 0:
        return allocation  # No goals
    
    normalized_weights = {p: w / total_weight for p, w in active_weights.items()}
    
    # Allocate to each priority group
    for priority, weight in normalized_weights.items():
        group_allocation = available_monthly_surplus * weight
        group_goals = priority_groups[priority]
        
        if group_goals:
            # Distribute equally among goals in this priority
            per_goal = group_allocation / len(group_goals)
            
            for goal in group_goals:
                allocation[goal.goal_id] = round(per_goal, 2)
    
    return allocation


def validate_allocation(
    allocation: Dict[int, float],
    available_monthly_surplus: float,
    tolerance: float = 0.01,
) -> bool:
    """
    Validate that allocation doesn't exceed available surplus.
    
    Args:
        allocation: {goal_id: contribution} map
        available_monthly_surplus: Total available
        tolerance: Rounding tolerance (default 0.01)
    
    Returns:
        True if valid, False otherwise
    """
    total_allocated = sum(allocation.values())
    return total_allocated <= (available_monthly_surplus + tolerance)
