"""
server/shock_engine/shock_service.py
=====================================
Orchestrates the full shock capacity pipeline.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from data_ingestion import fetch_user_data
from feature_builder import build_features
from monte_carlo import run_simulation, simulate_with_shock

logger = logging.getLogger(__name__)

DISCRETIONARY = ["Food & Dining", "Shopping", "Entertainment", "Travel", "Groceries"]
_MAX_SAVE_RATIO = 0.30


def get_shock_capacity(db: Session, user_id: int) -> dict[str, Any]:
    t0       = time.perf_counter()
    raw      = fetch_user_data(db, user_id)
    features = build_features(raw)
    sim      = run_simulation(features)
    elapsed  = round((time.perf_counter() - t0) * 1000, 1)

    return {
        "user_id":               user_id,
        "user_name":             raw["user_profile"].get("name", ""),
        "computed_at":           datetime.utcnow().isoformat(),
        "elapsed_ms":            elapsed,
        # Core shock outputs
        "shock_capacity":        sim["shock_capacity_amount"],
        "safe_shock_limit":      sim["safe_shock_limit"],
        "risk_threshold":        sim["risk_threshold"],
        "failure_threshold":     sim["failure_threshold"],
        "resilience_label":      sim["resilience_label"],
        "resilience_score":      sim["resilience_score"],
        "depletion_risk":        sim["depletion_risk_flag"],
        # Balance
        "current_balance":       features["liquid_balance"],
        "projected_end_balance": sim["projected_end_balance"],
        "confidence_band_low":   sim["confidence_band_low"],
        "confidence_band_high":  sim["confidence_band_high"],
        # Spend
        "current_month_spend":   features["current_month_spend"],
        "projected_month_spend": features["projected_month_spend"],
        "monthly_income":        features["monthly_income"],
        "monthly_surplus":       features["monthly_surplus"],
        "burn_rate_daily":       features["burn_rate"],
        "days_to_depletion":     features["days_to_depletion"],
        # Behavioral
        "expense_volatility":    features["expense_volatility"],
        "top_categories":        features["top_categories_6m"],
        "discretionary_ratio":   features["discretionary_ratio"],
        "trend_slope":           features["trend_slope"],
        # Meta
        "has_sufficient_data":   features["has_sufficient_data"],
        "data_months":           features["data_months_available"],
    }


def get_goal_impact(
    db: Session, user_id: int, shock_amounts: list[float] | None = None
) -> dict[str, Any]:
    from datetime import date
    shocks   = shock_amounts or [5_000, 10_000, 20_000, 50_000]
    raw      = fetch_user_data(db, user_id)
    features = build_features(raw)
    goals    = features.get("goal_details", [])

    disc_monthly = features["avg_monthly_expense"] * features["discretionary_ratio"]

    # Baseline MC run — gives us the safe/risk thresholds without any shock applied
    baseline     = run_simulation(features)
    safe_limit   = baseline["safe_shock_limit"]   # shock where 95 % of sims survive
    risk_limit   = baseline["risk_threshold"]     # shock where 50 % of sims survive

    # Monthly free cash after ALL expenses AND goal contributions
    monthly_free = max(
        features["monthly_income"]
        - features["avg_monthly_expense"]
        - features["goals_monthly_total_required"],
        0.0,
    )

    today     = date.today()
    scenarios = []

    for shock in shocks:
        sim_after = simulate_with_shock(features, shock)

        # Excess shock beyond the safe limit is what drives goal delays.
        # The user must divert `monthly_free` cash each month to rebuild
        # the excess — during that recovery window goal contributions pause.
        excess            = max(shock - safe_limit, 0.0)
        months_to_recover = (excess / monthly_free) if (monthly_free > 0 and excess > 0) else 0.0

        impacts = []
        for g in goals:
            mn    = g["monthly_need"]
            delay = int(round(months_to_recover))

            if delay == 0:
                gap, risk = 0.0, "None"
                new_date  = _add_months(today, g["months_left"]).isoformat()
            else:
                # Monthly shortfall = excess spread over recovery period
                gap      = min(mn, excess / max(months_to_recover, 1))
                risk     = (
                    "Low"      if delay <= 1 else
                    "Medium"   if delay <= 3 else
                    "High"     if delay <= 6 else
                    "Critical"
                )
                new_date = _add_months(today, g["months_left"] + delay).isoformat()

            max_sug = disc_monthly * _MAX_SAVE_RATIO
            sug_cut = min(gap, max_sug)
            cat_top = _top_disc_cat(features)
            suggestion = (
                f"Reduce {cat_top} by ₹{sug_cut:,.0f}/month to protect '{g['goal_name']}'"
                if sug_cut > 200 else None
            )

            impacts.append({**g, "impact_level": risk, "delay_in_months": delay,
                            "contribution_gap": round(gap, 2),
                            "new_completion_date": new_date, "suggestion": suggestion})

        # Depletion risk: True when the shock exceeds the 50 % survival threshold
        # (i.e. more than half of MC simulations show the user's finances under stress)
        scenarios.append({
            "shock_amount":        shock,
            "balance_after_shock": round(sim_after["projected_end_balance"], 2),
            "resilience_after":    sim_after["resilience_label"],
            "depletion_risk":      shock > risk_limit,
            "goal_impacts":        impacts,
        })

    return {
        "user_id": user_id, "computed_at": datetime.utcnow().isoformat(),
        "monthly_income": features["monthly_income"],
        "current_balance": features["liquid_balance"],
        "goals_count": len(goals),
        "shock_scenarios": scenarios,
    }


def get_savings_insights(db: Session, user_id: int) -> dict[str, Any]:
    raw      = fetch_user_data(db, user_id)
    features = build_features(raw)
    patterns = raw["txn_patterns"]
    cat_spend = features.get("category_spend_cm", {})
    cat_vol   = features.get("cat_volatility", {})
    opps      = []

    for cat in DISCRETIONARY:
        spent = cat_spend.get(cat, 0.0)
        if spent < 500:
            continue
        pat     = next((p for p in patterns if p["category"] == cat), None)
        base    = pat["avg_amount"] * pat["txn_count"] if pat else spent * 0.70
        over    = max(spent - base, 0.0)
        max_sav = spent * _MAX_SAVE_RATIO
        save    = min(over if over > 0 else max_sav * 0.5, max_sav)
        if save < 200:
            continue
        vol = cat_vol.get(cat, 0.0)
        conf = "High" if vol > 0.5 or (spent > 0 and over / spent > 0.3) else ("Medium" if vol > 0.2 else "Low")
        opps.append({
            "category": cat, "current_spend": round(spent, 2),
            "baseline_spend": round(base, 2), "save_amount": round(save, 2),
            "confidence": conf,
            "insight": f"Reducing {cat} by ₹{save:,.0f} could improve your shock resilience.",
        })

    # Weekend spike alert
    wknd_r = features.get("weekend_spend_ratio", 0.0)
    if wknd_r > 0.45:
        excess = features["current_month_spend"] * wknd_r * 0.25
        if excess > 500:
            opps.append({
                "category": "Weekend Spending",
                "current_spend": round(features["current_month_spend"] * wknd_r, 2),
                "baseline_spend": round(features["current_month_spend"] * 0.30, 2),
                "save_amount": round(excess, 2), "confidence": "Medium",
                "insight": f"High weekend spending is reducing your shock resilience by ₹{excess:,.0f} this month.",
            })

    opps.sort(key=lambda x: x["save_amount"], reverse=True)
    top = opps[:5]
    total = sum(o["save_amount"] for o in top)

    return {
        "user_id": user_id, "computed_at": datetime.utcnow().isoformat(),
        "total_monthly_saveable": round(total, 2),
        "opportunities": top,
        "top_risk_categories": [o["category"] for o in top[:3]],
        "current_balance": features["liquid_balance"],
        "monthly_income":  features["monthly_income"],
    }


def get_llm_insight(db: Session, user_id: int) -> dict[str, Any]:
    shock   = get_shock_capacity(db, user_id)
    savings = get_savings_insights(db, user_id)

    context = {
        "shock_capacity":         shock["shock_capacity"],
        "safe_shock_limit":       shock["safe_shock_limit"],
        "resilience_label":       shock["resilience_label"],
        "resilience_score":       shock["resilience_score"],
        "current_balance":        shock["current_balance"],
        "projected_end_balance":  shock["projected_end_balance"],
        "current_month_spend":    shock["current_month_spend"],
        "monthly_income":         shock["monthly_income"],
        "top_risk_categories":    savings["top_risk_categories"],
        "depletion_risk":         shock["depletion_risk"],
        "expense_volatility":     shock["expense_volatility"],
        "total_monthly_saveable": savings["total_monthly_saveable"],
    }

    from mistral_client import MistralClient
    from llm_prompts import build_shock_prompt

    prompt  = build_shock_prompt(context)
    client  = MistralClient()
    insight = client.generate(prompt, context=context)
    source  = "ollama" if client.use_local else ("api" if client.api_key else "fallback")

    return {
        "user_id": user_id, "computed_at": datetime.utcnow().isoformat(),
        "insight": insight, "insight_source": source,
        "shock_summary": shock, "savings_summary": savings,
    }


def _top_disc_cat(features):
    cs = features.get("category_spend_cm", {})
    disc = {k: v for k, v in cs.items() if k in DISCRETIONARY}
    return max(disc, key=disc.get) if disc else "discretionary spending"


def _add_months(d, months):
    import calendar
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    from datetime import date as date_cls
    return date_cls(y, m, day)
