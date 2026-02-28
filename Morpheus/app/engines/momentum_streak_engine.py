"""
Momentum / Streak Engine

Calculates streak, consistency, penalty, and score for goal contributions.
Reads from savings_activity table.
"""
from typing import List, Dict

def calculate_streak_score(activity: List[Dict]) -> Dict:
    streak_months = 0
    consistency_pct = 0.0
    missed_months = 0
    total_sip_amount = 0.0
    months = len(activity)
    contributed_months = 0
    # Calculate streak (consecutive months ending now)
    for entry in reversed(activity):
        if entry.get('contributed', 0) == 1:
            streak_months += 1
        else:
            break
    # Consistency: % of months contributed
    for entry in activity:
        if entry.get('contributed', 0) == 1:
            contributed_months += 1
        if entry.get('missed', 0) == 1:
            missed_months += 1
        total_sip_amount += entry.get('total_sip_amount', 0.0)
    consistency_pct = (contributed_months / months) * 100 if months > 0 else 0.0
    # Score formula
    streakScore = min(40, streak_months * 10)
    consistencyScore = consistency_pct * 0.5
    penalty = missed_months * 10
    score = max(0, min(100, streakScore + consistencyScore - penalty))
    return {
        'streak_months': streak_months,
        'streak_days': streak_months * 30,
        'consistency_pct': round(consistency_pct, 2),
        'score': round(score, 2),
        'total_sip_amount': round(total_sip_amount, 2),
        'missed_months': missed_months,
    }
