"""
ml_models/goal_feasibility_model/test_ui.py
============================================
Console test harness for Goal Feasibility model.
Run: python ml_models/goal_feasibility_model/test_ui.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_models.goal_feasibility_model.inference import assess_goal_feasibility, retrain_model
from ml_models.goal_feasibility_model.model import GoalFeasibilityModel


TEST_GOALS = [
    # (name, monthly_surplus, expense_volatility, target_amount, deadline_months)
    ("Emergency Fund",      25000,  3000,  150000,  6),
    ("Home Down Payment",   50000,  8000, 1500000, 36),
    ("Europe Vacation",     40000,  6000,  200000,  8),
    ("Child Education",     30000,  5000, 2000000, 60),
    ("Startup Capital",     15000, 12000,  500000, 18),
    ("Retirement Corpus",  100000, 10000, 5000000, 240),
    ("Laptop Upgrade",      20000,  2000,   80000,  5),
    ("Wedding Fund",        35000,  7000,  600000, 24),
]


def run_console_test():
    print("=" * 70)
    print("  GOAL FEASIBILITY MODEL — Console Test")
    print("=" * 70)

    m = GoalFeasibilityModel()
    if not m.is_trained():
        print("\n🔄  Training model …")
        retrain_model()
    else:
        print("\n✅  Pre-trained model found")

    print(f"\n{'Goal':<22} {'Target':>12} {'Deadline':>10} {'Surplus':>12} {'Score':>8}  Interpretation")
    print("-" * 95)

    for name, surplus, vol, target, months in TEST_GOALS:
        result = assess_goal_feasibility(surplus, vol, target, months)
        score  = result["feasibility_score"]
        interp = result["interpretation"].split("—")[0].strip()
        bar    = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(
            f"{name:<22} ₹{target:>10,.0f}  {months:>6}mo  "
            f"₹{surplus:>9,.0f}/mo  {score:>6.1f}  {interp}"
        )
        print(f"  [{bar}] {score:.1f}/100")
        print()

    print("\n✅  Test complete.")


if __name__ == "__main__":
    run_console_test()
