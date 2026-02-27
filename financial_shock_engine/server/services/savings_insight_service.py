"""
financial_shock_engine/server/services/savings_insight_service.py
=================================================================
Smart Savings Opportunity Engine (behavior-aware, realistic).

Rules enforced:
  • Only targets discretionary categories (Dining, Shopping, Entertainment, etc.)
  • Suggestions capped at 30% of category's monthly spend
  • Pattern-aware: uses transaction_patterns for cluster detection
  • Trend-aware: flags accelerating spend categories

Generates insights like:
  "Reducing Food & Dining by ₹2,100/month protects your goal timeline"
  "High weekend spending is reducing shock resilience"
  "Subscription cluster detected — ₹1,500 potentially redundant"
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from feature_engine.data_ingestion import fetch_user_data
from feature_engine.feature_builder import build_features
from configs.settings import (
    DISCRETIONARY_CATEGORIES,
    MAX_SAVINGS_SUGGESTION_RATIO,
)

logger = logging.getLogger(__name__)


def get_savings_insights(db: Session, user_id: int) -> dict[str, Any]:
    """
    Analyse discretionary spending and return ranked savings opportunities.
    """
    raw      = fetch_user_data(db, user_id)
    features = build_features(raw)
    patterns = raw["txn_patterns"]

    cat_spend    = features.get("category_spend_cm", {})
    cat_vol      = features.get("cat_volatility", {})
    trend_slope  = features.get("trend_slope", 0.0)
    weekend_ratio = features.get("weekend_spend_ratio", 0.0)
    monthly_income = features.get("monthly_income", 0.0)

    opportunities = []

    # ── 1. Category-level savings ─────────────────────────────────────────────
    for cat in DISCRETIONARY_CATEGORIES:
        spent = cat_spend.get(cat, 0.0)
        if spent < 500:
            continue

        max_save = spent * MAX_SAVINGS_SUGGESTION_RATIO
        vol      = cat_vol.get(cat, 0.0)

        # Pattern baseline for this category
        pattern = _pattern_for(cat, patterns)
        baseline = pattern["avg_amount"] * pattern["txn_count"] if pattern else spent * 0.7
        over_baseline = max(spent - baseline, 0.0)

        save_amount = min(over_baseline if over_baseline > 0 else max_save * 0.5, max_save)
        if save_amount < 200:
            continue

        reason = _spending_reason(cat, spent, baseline, vol, trend_slope)
        opportunities.append({
            "category":       cat,
            "current_spend":  round(spent, 2),
            "baseline_spend": round(baseline, 2),
            "save_amount":    round(save_amount, 2),
            "confidence":     _confidence(vol, over_baseline, spent),
            "reason":         reason,
            "insight":        f"Reducing {cat} by ₹{save_amount:,.0f} could improve your shock resilience.",
        })

    # ── 2. Weekend overspend alert ────────────────────────────────────────────
    if weekend_ratio > 0.45:
        weekend_excess = features["current_month_spend"] * weekend_ratio * 0.25
        if weekend_excess > 500:
            opportunities.append({
                "category":       "Weekend Spending",
                "current_spend":  round(features["current_month_spend"] * weekend_ratio, 2),
                "baseline_spend": round(features["current_month_spend"] * 0.30, 2),
                "save_amount":    round(weekend_excess, 2),
                "confidence":     "Medium",
                "reason":         "Weekend spending is significantly higher than weekdays",
                "insight":        f"High weekend spending is reducing your shock resilience by ₹{weekend_excess:,.0f} this month.",
            })

    # ── 3. Subscription cluster detection ────────────────────────────────────
    sub_cluster = _detect_subscription_cluster(raw["transactions_6m"])
    if sub_cluster["detected"] and sub_cluster["monthly_value"] > 300:
        opportunities.append({
            "category":       "Subscriptions",
            "current_spend":  round(sub_cluster["monthly_value"], 2),
            "baseline_spend": round(sub_cluster["monthly_value"] * 0.5, 2),
            "save_amount":    round(sub_cluster["monthly_value"] * 0.4, 2),
            "confidence":     "High",
            "reason":         f"Detected {sub_cluster['count']} recurring small transactions that may include unused subscriptions",
            "insight":        f"Subscription cluster worth ₹{sub_cluster['monthly_value']:,.0f}/month detected — reviewing these could free up ₹{sub_cluster['monthly_value']*0.4:,.0f}.",
        })

    # ── 4. Trend alert ────────────────────────────────────────────────────────
    if trend_slope > 2000:
        accelerating = [
            cat for cat, vol in cat_vol.items()
            if vol > 0.4 and cat_spend.get(cat, 0) > 1000
        ]
        for cat in accelerating[:2]:
            opportunities.append({
                "category":       cat,
                "current_spend":  round(cat_spend.get(cat, 0), 2),
                "baseline_spend": round(cat_spend.get(cat, 0) * 0.7, 2),
                "save_amount":    round(cat_spend.get(cat, 0) * 0.20, 2),
                "confidence":     "Medium",
                "reason":         f"Spending in {cat} has been accelerating month over month",
                "insight":        f"{cat} spending is trending upward — curbing it now could prevent ₹{cat_spend.get(cat,0)*0.20:,.0f} in future overruns.",
            })

    # Sort by save_amount desc, take top 5
    opportunities.sort(key=lambda x: x["save_amount"], reverse=True)
    top_opps = opportunities[:5]

    total_saveable = sum(o["save_amount"] for o in top_opps)

    return {
        "user_id":              user_id,
        "computed_at":          datetime.utcnow().isoformat(),
        "total_monthly_saveable": round(total_saveable, 2),
        "opportunities":        top_opps,
        "top_risk_categories":  [o["category"] for o in top_opps[:3]],
        "resilience_boost":     f"Saving ₹{total_saveable:,.0f}/month would add ~{int(total_saveable/30)} days to your depletion buffer.",
        "current_balance":      features["liquid_balance"],
        "monthly_income":       features["monthly_income"],
    }


# ─────────────────────────────────────────────────────────────────────────────

def _pattern_for(category: str, patterns: list[dict]) -> dict | None:
    for p in patterns:
        if p["category"] == category:
            return p
    return None


def _confidence(vol: float, over_baseline: float, spent: float) -> str:
    if vol > 0.5 or (spent > 0 and over_baseline / spent > 0.3):
        return "High"
    if vol > 0.2:
        return "Medium"
    return "Low"


def _spending_reason(
    cat: str, spent: float, baseline: float, vol: float, trend: float
) -> str:
    if spent > baseline * 1.4:
        return f"Spending in {cat} is significantly above your 6-month average"
    if vol > 0.5:
        return f"{cat} spending is highly irregular this month"
    if trend > 1500:
        return f"{cat} costs have been rising steadily"
    return f"{cat} has some discretionary room based on your patterns"


def _detect_subscription_cluster(txns_6m) -> dict:
    """
    Detect clusters of recurring small transactions (₹100–₹2000) that appear monthly.
    """
    import pandas as pd
    if txns_6m is None or (hasattr(txns_6m, "empty") and txns_6m.empty):
        return {"detected": False, "count": 0, "monthly_value": 0.0}

    try:
        small = txns_6m[(txns_6m["amount"] >= 100) & (txns_6m["amount"] <= 2000)]
        if small.empty:
            return {"detected": False, "count": 0, "monthly_value": 0.0}

        # Group by description/merchant similarity — use amount clustering as proxy
        amount_counts = small.groupby(small["amount"].round(-1))["amount"].count()
        recurring_amounts = amount_counts[amount_counts >= 2]   # appears ≥2 times

        if recurring_amounts.empty:
            return {"detected": False, "count": 0, "monthly_value": 0.0}

        total_monthly = float(recurring_amounts.index.to_series().sum())
        count = len(recurring_amounts)

        return {"detected": True, "count": count, "monthly_value": total_monthly}
    except Exception:
        return {"detected": False, "count": 0, "monthly_value": 0.0}
