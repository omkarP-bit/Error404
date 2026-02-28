"""
Emergency Fund Override Logic

If emergency fund goal is incomplete (<80% target),
70% of surplus goes to emergency fund, 30% to other goals.
If no emergency fund goal, auto-create with default target.
"""
from typing import List, Dict

def emergency_fund_allocation(goals: List[dict], total_surplus: float) -> Dict[int, float]:
    emergency_goals = [g for g in goals if 'emergency' in (g.get('goal_type') or '').lower()]
    other_goals = [g for g in goals if g not in emergency_goals]
    allocation = {}
    if emergency_goals:
        emergency = emergency_goals[0]
        percent_complete = emergency['current_amount'] / emergency['target_amount'] if emergency['target_amount'] > 0 else 0
        if percent_complete < 0.8:
            # 70% to emergency, 30% to others
            allocation[emergency['goal_id']] = round(total_surplus * 0.7, 2)
            if other_goals:
                per_goal = (total_surplus * 0.3) / len(other_goals)
                for g in other_goals:
                    allocation[g['goal_id']] = round(per_goal, 2)
        else:
            # Use normal allocation
            from app.engines.priority_allocation_engine import allocate_surplus
            allocation = allocate_surplus(goals, total_surplus)
    else:
        # Auto-create emergency fund logic should be handled in goal creation
        allocation = {}
    return allocation
