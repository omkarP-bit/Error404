"""
Multi-Goal Priority Allocation Engine

Distributes available surplus among goals by priority weights.
Handles normalization if any priority group is missing.

High → 50%
Medium → 30%
Low → 20%

If a priority group is missing, redistributes its weight proportionally.

Input: List[Goal]
Output: Dict[goal_id, contribution]
"""
from typing import List, Dict

def allocate_surplus(goals: List[dict], total_surplus: float) -> Dict[int, float]:
    # Priority weights
    weights = {1: 0.5, 2: 0.3, 3: 0.2}
    present = {g['priority'] for g in goals}
    active_weights = {p: w for p, w in weights.items() if p in present}
    total_weight = sum(active_weights.values())
    normalized = {p: w / total_weight for p, w in active_weights.items()}
    # Group goals by priority
    grouped = {p: [g for g in goals if g['priority'] == p] for p in active_weights}
    # Distribute surplus
    allocation = {}
    for p, group in grouped.items():
        group_surplus = total_surplus * normalized[p]
        if group:
            per_goal = group_surplus / len(group)
            for g in group:
                allocation[g['goal_id']] = round(per_goal, 2)
    return allocation
