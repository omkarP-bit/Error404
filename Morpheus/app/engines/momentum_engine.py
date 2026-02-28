"""
app/engines/momentum_engine.py
==============================
Behavioral gamification engine for savings streak & consistency scoring.

Tracks:
- Monthly contribution activity (contributed or missed)
- Consecutive months streak
- Consistency percentage
- Score calculation with rewards & penalties

Score = min(100, streakScore + consistencyScore - penalty)

Where:
- streakScore = min(40, streakMonths * 10)
- consistencyScore = consistencyPct * 0.5  (max 50)
- penalty = missedMonths * 10
"""

from datetime import datetime, date, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func


def calculate_streak_and_score(
    db: Session,
    user_id: int,
    lookback_months: int = 12,
) -> Dict[str, any]:
    """
    Calculate user's saving streak, consistency, and score.
    
    Args:
        db: Database session
        user_id: User ID
        lookback_months: How many past months to analyze (default: last 12 months)
    
    Returns:
        {
            'streak_months': int,            # Consecutive months with contribution
            'streak_days': int,              # Streak in days (approximation)
            'consistency_pct': float,        # % of months with contribution
            'total_months_analyzed': int,    # How many months looked at
            'months_contributed': int,       # Months with contribution > 0
            'months_missed': int,            # Months with contribution = 0
            'streak_score': float,           # 0-40 (streak component)
            'consistency_score': float,      # 0-50 (consistency component)
            'penalty': float,                # Missed months penalty
            'score': float,                  # Final score 0-100
            'activity_last_7_months': List[Dict],  # Last 7 months breakdown
        }
    """
    from app.models import SavingsActivity
    
    now = date.today()
    lookback_start = now - timedelta(days=lookback_months * 30)
    
    # Get all activity for this user in lookback period
    activities = db.query(SavingsActivity).filter(
        SavingsActivity.user_id == user_id,
        SavingsActivity.month_key >= lookback_start.strftime("%Y-%m"),
    ).order_by(SavingsActivity.month_key.desc()).all()
    
    if not activities:
        return {
            'streak_months': 0,
            'streak_days': 0,
            'consistency_pct': 0.0,
            'total_months_analyzed': 0,
            'months_contributed': 0,
            'months_missed': 0,
            'streak_score': 0.0,
            'consistency_score': 0.0,
            'penalty': 0.0,
            'score': 0.0,
            'activity_last_7_months': [],
        }
    
    # Calculate streak (consecutive months from most recent backwards)
    streak_months = 0
    for activity in activities:
        if activity.contributed == 1:
            streak_months += 1
        else:
            break
    
    # Calculate consistency
    total_analyzed = len(activities)
    months_contributed = sum(1 for a in activities if a.contributed == 1)
    months_missed = total_analyzed - months_contributed
    consistency_pct = (months_contributed / total_analyzed * 100) if total_analyzed > 0 else 0
    
    # Calculate scores
    streak_score = min(40, streak_months * 10)
    consistency_score = (consistency_pct / 100) * 50  # max 50
    penalty = months_missed * 10
    
    # Final score
    score = max(0, min(100, streak_score + consistency_score - penalty))
    
    # Last 7 months activity breakdown
    last_7_activity = []
    for i in range(min(7, total_analyzed)):
        activity = activities[i]
        last_7_activity.append({
            'month_key': activity.month_key,
            'contributed': activity.contributed == 1,
            'total_sip_amount': float(activity.total_sip_amount or 0),
        })
    
    return {
        'streak_months': streak_months,
        'streak_days': streak_months * 30,  # Approximation
        'consistency_pct': round(consistency_pct, 2),
        'total_months_analyzed': total_analyzed,
        'months_contributed': months_contributed,
        'months_missed': months_missed,
        'streak_score': round(streak_score, 2),
        'consistency_score': round(consistency_score, 2),
        'penalty': round(penalty, 2),
        'score': round(score, 2),
        'activity_last_7_months': last_7_activity,
    }


def record_monthly_activity(
    db: Session,
    user_id: int,
    month_key: str,  # "2026-02"
    total_sip_amount: float,
) -> bool:
    """
    Record SIP contribution activity for a month.
    
    Args:
        db: Database session
        user_id: User ID
        month_key: Month in "YYYY-MM" format
        total_sip_amount: Total SIP contributed this month
    
    Returns:
        True if recorded successfully
    """
    from app.models import SavingsActivity
    
    try:
        # Check if existing
        existing = db.query(SavingsActivity).filter(
            SavingsActivity.user_id == user_id,
            SavingsActivity.month_key == month_key,
        ).first()
        
        contributed = 1 if total_sip_amount > 0 else 0
        
        if existing:
            existing.contributed = contributed
            existing.total_sip_amount = total_sip_amount
        else:
            activity = SavingsActivity(
                user_id=user_id,
                month_key=month_key,
                contributed=contributed,
                total_sip_amount=total_sip_amount,
                missed=1 - contributed,
            )
            db.add(activity)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error recording activity: {e}")
        return False
