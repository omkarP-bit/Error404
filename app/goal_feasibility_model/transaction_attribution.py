"""
ml_models/goal_feasibility_model/transaction_attribution.py
=============================================================
Transaction Attribution Engine.

Maps negative feature drivers → spending categories → actual transactions.

Algorithm:
  1. Identify which negative driver features relate to spending categories
     (dining_slope → "Food & Dining", shopping_slope → "Shopping", etc.)
  2. For non-category features (volatility, anomaly_count), fetch top
     high-impact transactions by amount × recency weight.
  3. Rank transactions by: impact_score = amount × recency_weight
     where recency_weight = exp(−days_ago / 30)  (exponential decay)
  4. Return top-N transactions with category impact summary.

Output shape:
  {
    "top_impact_transactions": [
      {
        "txn_id": 123,
        "merchant": "Swiggy",
        "amount": 1250.0,
        "category": "Food & Dining",
        "date": "2026-02-15",
        "impact_score": 0.87,
        "reason": "Rising dining trend"
      }, ...
    ],
    "category_impact_summary": {
      "Food & Dining": {
        "monthly_drift": 890.0,
        "share_of_expenses": 0.18,
        "impact": "negative",
        "reason": "Increasing trend over last 6 months"
      }, ...
    }
  }
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional


# ── Feature → category mapping ────────────────────────────────────────────────
FEATURE_TO_CATEGORY: dict[str, str] = {
    "dining_slope":           "Food & Dining",
    "shopping_slope":         "Shopping",
    "entertainment_slope":    "Entertainment",
    "discretionary_ratio":    None,   # all three discretionary categories
}

SLOPE_FEATURES = {"dining_slope", "shopping_slope", "entertainment_slope"}


def attribute_transactions(
    db,
    user_id: int,
    negative_drivers: list[dict],
    feature_dict: dict,
    top_n: int = 5,
) -> dict:
    """
    Map negative feature drivers to real transactions and category summaries.

    Parameters
    ----------
    db               : SQLAlchemy session
    user_id          : user whose transactions to query
    negative_drivers : output from explainer.explain()["top_negative"]
    feature_dict     : full feature dict (for context)
    top_n            : max transactions to return
    """
    from sqlalchemy import func as F
    from app.models import Transaction
    from app.models.merchant import Merchant
    from app.models.enums import TxnType

    now    = datetime.utcnow()
    c3m    = now - timedelta(days=90)
    c6m    = now - timedelta(days=180)

    # ── Step 1: Collect categories to investigate ─────────────────────────────
    target_categories: set[str] = set()

    for driver in negative_drivers:
        feat = driver["feature"]
        if feat in FEATURE_TO_CATEGORY:
            cat = FEATURE_TO_CATEGORY[feat]
            if cat:
                target_categories.add(cat)
            else:
                # discretionary_ratio → all three
                target_categories.update({"Food & Dining", "Shopping", "Entertainment"})
        elif feat in {"anomaly_count_3m", "high_value_txn_count", "expense_volatility_ratio"}:
            target_categories.add("_anomaly")   # special marker

    if not target_categories:
        # Default: fetch top spends across all categories
        target_categories.add("_all")

    # ── Step 2: Fetch candidate transactions ──────────────────────────────────
    txn_query = (
        db.query(Transaction)
        .filter(
            Transaction.user_id   == user_id,
            Transaction.txn_type  == TxnType.DEBIT,
            Transaction.txn_timestamp >= c3m,
        )
    )

    if "_anomaly" in target_categories:
        # Pull all debits in 3m; we'll filter anomalies in Python
        all_txns = txn_query.order_by(Transaction.amount.desc()).limit(200).all()
        amounts  = [float(t.amount) for t in all_txns]
        p90      = float(sorted(amounts)[-len(amounts) // 10]) if amounts else 0
        candidate_txns = [t for t in all_txns if float(t.amount) >= p90]
    elif "_all" in target_categories:
        candidate_txns = txn_query.order_by(Transaction.amount.desc()).limit(100).all()
    else:
        candidate_txns = txn_query.filter(
            Transaction.category.in_(list(target_categories))
        ).order_by(Transaction.amount.desc()).limit(100).all()

    # ── Step 3: Score transactions by amount × recency ────────────────────────
    scored: list[dict] = []
    for txn in candidate_txns:
        days_ago       = (now - txn.txn_timestamp).days
        recency_weight = math.exp(-days_ago / 30.0)
        impact_score   = float(txn.amount) * recency_weight / max(feature_dict.get("avg_monthly_expenses", 1), 1)

        # Resolve merchant name
        merchant_name = ""
        if txn.merchant_id:
            m = db.query(Merchant).filter(Merchant.merchant_id == txn.merchant_id).first()
            merchant_name = m.clean_name if m else ""
        if not merchant_name and txn.raw_description:
            merchant_name = txn.raw_description[:40]

        scored.append({
            "txn_id":       txn.txn_id,
            "merchant":     merchant_name.title(),
            "amount":       round(float(txn.amount), 2),
            "category":     txn.category or "Uncategorized",
            "date":         txn.txn_timestamp.strftime("%Y-%m-%d"),
            "impact_score": round(impact_score, 4),
            "reason":       _reason_for_driver(negative_drivers, txn.category),
        })

    scored.sort(key=lambda x: -x["impact_score"])
    top_txns = scored[:top_n]

    # ── Step 4: Category impact summary ───────────────────────────────────────
    avg_expenses = max(feature_dict.get("avg_monthly_expenses", 1.0), 1.0)
    cat_summary: dict[str, dict] = {}

    for cat in (target_categories - {"_anomaly", "_all"}):
        # Monthly spend for last 6 months
        monthly: list[float] = []
        for i in range(5, -1, -1):
            s = now - timedelta(days=30 * (i + 1))
            e = now - timedelta(days=30 * i)
            v = float(
                db.query(F.sum(Transaction.amount))
                .filter(Transaction.user_id == user_id,
                        Transaction.txn_type == TxnType.DEBIT,
                        Transaction.category == cat,
                        Transaction.txn_timestamp >= s,
                        Transaction.txn_timestamp < e)
                .scalar() or 0.0
            )
            monthly.append(v)

        from ml_models.goal_feasibility_model.feature_builder import _slope
        drift  = _slope(monthly)
        recent = monthly[-1] if monthly else 0.0

        cat_summary[cat] = {
            "monthly_drift":      round(drift, 2),
            "recent_monthly_spend": round(recent, 2),
            "share_of_expenses":  round(recent / avg_expenses, 4),
            "impact":             "negative" if drift > 0 else "stable",
            "reason": (
                f"Increasing trend: +₹{drift:.0f}/month"
                if drift > 50
                else "Stable spending in this category"
            ),
        }

    return {
        "top_impact_transactions": top_txns,
        "category_impact_summary": cat_summary,
    }


def _reason_for_driver(drivers: list[dict], category: Optional[str]) -> str:
    """Map a transaction category back to the most relevant driver reason."""
    cat_to_feature = {
        "Food & Dining":  "Rising dining expenses trend",
        "Shopping":       "Rising shopping expenses trend",
        "Entertainment":  "Rising entertainment expenses trend",
    }
    if category in cat_to_feature:
        return cat_to_feature[category]
    for d in drivers:
        if "volatil" in d["feature"]:
            return "Unusual high-value transaction"
        if "anomaly" in d["feature"]:
            return "Anomalous spending pattern"
    return "High-impact expense"
