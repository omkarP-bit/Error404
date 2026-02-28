"""
app/engines/sip_calculator.py
=============================
SIP (Systematic Investment Plan) calculator.

Given:
- target_amount
- current_saved
- deadline (months)
- expected_return

Calculates required monthly SIP to reach target.
"""

from datetime import datetime, date
from typing import Dict


def calculate_required_sip(
    target_amount: float,
    current_saved: float,
    deadline_date: date,
    expected_annual_return: float = 0.10,
) -> Dict[str, float]:
    """
    Calculate required monthly SIP to reach target by deadline.
    
    Uses Future Value of Annuity formula adjusted for compound interest:
    FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]
    
    Rearranged for PMT:
    PMT = (FV - PV*(1+r)^n) / [((1+r)^n - 1) / r]
    
    Args:
        target_amount: Target goal amount
        current_saved: Already saved amount
        deadline_date: Target deadline date
        expected_annual_return: Expected annual return rate (default 10%)
    
    Returns:
        {
            'required_monthly_sip': float,
            'months_remaining': int,
            'total_contribution_needed': float,
            'investment_growth_expected': float,
        }
    """
    now = datetime.utcnow().date()
    
    # Calculate months remaining
    months_remaining = max(1, (deadline_date.year - now.year) * 12 + (deadline_date.month - now.month))
    
    # Monthly return rate
    monthly_return = (1 + expected_annual_return) ** (1 / 12) - 1
    
    # Amount still needed
    amount_needed = target_amount - current_saved
    
    if amount_needed <= 0:
        # Already saved enough
        return {
            'required_monthly_sip': 0.0,
            'months_remaining': months_remaining,
            'total_contribution_needed': 0.0,
            'investment_growth_expected': 0.0,
        }
    
    # Future value of current savings
    fv_current = current_saved * ((1 + monthly_return) ** months_remaining)
    
    # Remaining amount to be covered by SIP
    remaining_fv = target_amount - fv_current
    
    if remaining_fv <= 0:
        # Current savings + returns will exceed target
        return {
            'required_monthly_sip': 0.0,
            'months_remaining': months_remaining,
            'total_contribution_needed': 0.0,
            'investment_growth_expected': round(fv_current - current_saved, 2),
        }
    
    # Calculate required monthly SIP
    if monthly_return == 0:
        # No returns case
        required_sip = remaining_fv / months_remaining
    else:
        # FV annuity formula
        numerator = remaining_fv
        denominator = (((1 + monthly_return) ** months_remaining) - 1) / monthly_return
        required_sip = numerator / denominator
    
    # Total contribution from SIP
    total_sip_contribution = required_sip * months_remaining
    
    # Expected growth from investments
    investment_growth = target_amount - current_saved - total_sip_contribution
    
    return {
        'required_monthly_sip': max(0.0, round(required_sip, 2)),
        'months_remaining': months_remaining,
        'total_contribution_needed': round(total_sip_contribution, 2),
        'investment_growth_expected': round(max(0.0, investment_growth), 2),
    }
