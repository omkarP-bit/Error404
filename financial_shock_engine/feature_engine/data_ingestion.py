"""
financial_shock_engine/feature_engine/data_ingestion.py
=======================================================
Step 1 — Data Ingestion Layer.

Fetches all required raw data for a user from the shared SQLite DB.
Returns a typed RawUserData dict — NO ML logic here, just clean SQL.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry-point
# ─────────────────────────────────────────────────────────────────────────────

def fetch_user_data(db: Session, user_id: int) -> dict[str, Any]:
    """
    Fetch all raw data needed by the shock engine for *user_id*.

    Returns
    -------
    {
        user_profile      : dict
        accounts          : list[dict]
        transactions_6m   : pd.DataFrame   (6 months of DEBIT txns)
        current_month_txns: pd.DataFrame   (current month DEBIT txns)
        goals             : list[dict]
        budget_profile    : dict | None
        txn_patterns      : list[dict]
        health_rating     : dict | None
    }
    """
    today = date.today()
    six_months_ago = today - timedelta(days=182)
    month_start    = today.replace(day=1)

    user     = _fetch_user(db, user_id)
    accounts = _fetch_accounts(db, user_id)
    txns_6m  = _fetch_transactions(db, user_id, since=six_months_ago)
    txns_cm  = txns_6m[txns_6m["txn_date"] >= pd.Timestamp(month_start)]
    goals    = _fetch_goals(db, user_id)
    budget   = _fetch_budget_profile(db, user_id)
    patterns = _fetch_patterns(db, user_id)
    health   = _fetch_health_rating(db, user_id)

    logger.info(
        "Ingested data for user=%d | txns_6m=%d | txns_cm=%d | goals=%d",
        user_id, len(txns_6m), len(txns_cm), len(goals),
    )

    return {
        "user_profile":       user,
        "accounts":           accounts,
        "transactions_6m":    txns_6m,
        "current_month_txns": txns_cm,
        "goals":              goals,
        "budget_profile":     budget,
        "txn_patterns":       patterns,
        "health_rating":      health,
        "snapshot_date":      today.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_user(db: Session, user_id: int) -> dict:
    row = db.execute(
        text("""
            SELECT user_id, name, email, monthly_income, risk_profile, income_type
            FROM users
            WHERE user_id = :uid
        """),
        {"uid": user_id},
    ).mappings().first()
    if not row:
        raise ValueError(f"User {user_id} not found in database.")
    return dict(row)


def _fetch_accounts(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT account_id, institution_name, account_type, current_balance
            FROM accounts
            WHERE user_id = :uid
        """),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _fetch_transactions(
    db: Session, user_id: int, since: date
) -> pd.DataFrame:
    rows = db.execute(
        text("""
            SELECT
                txn_id,
                amount,
                category,
                subcategory,
                txn_timestamp,
                txn_type,
                is_recurring,
                payment_mode,
                balance_after_txn
            FROM transactions
            WHERE user_id = :uid
              AND lower(txn_type) = 'debit'
              AND date(txn_timestamp) >= :since
            ORDER BY txn_timestamp ASC
        """),
        {"uid": user_id, "since": since.isoformat()},
    ).mappings().all()

    if not rows:
        return pd.DataFrame(columns=[
            "txn_id", "amount", "category", "subcategory",
            "txn_date", "txn_type", "is_recurring",
            "payment_mode", "balance_after_txn",
        ])

    df = pd.DataFrame([dict(r) for r in rows])
    df["txn_date"] = pd.to_datetime(df["txn_timestamp"]).dt.normalize()
    df["amount"]   = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["category"] = df["category"].fillna("Uncategorised")
    return df


def _fetch_goals(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT goal_id, goal_name, goal_type, priority,
                   target_amount, current_amount, deadline, status,
                   feasibility_score
            FROM goals
            WHERE user_id = :uid
              AND lower(status) = 'active'
            ORDER BY priority ASC
        """),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _fetch_budget_profile(db: Session, user_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT profile_id, needs_ratio, wants_ratio, savings_ratio,
                   baseline_expense, expense_volatility,
                   avg_monthly_surplus, safe_investable_amount
            FROM budget_profiles
            WHERE user_id = :uid
            LIMIT 1
        """),
        {"uid": user_id},
    ).mappings().first()
    return dict(row) if row else None


def _fetch_patterns(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT pattern_id, category, avg_amount, std_amount,
                   txn_count, typical_weekdays
            FROM transaction_patterns
            WHERE user_id = :uid
        """),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _fetch_health_rating(db: Session, user_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT overall_score, savings_score, spending_score,
                   debt_score, investment_score, rating_label
            FROM financial_health_ratings
            WHERE user_id = :uid
            ORDER BY rowid DESC
            LIMIT 1
        """),
        {"uid": user_id},
    ).mappings().first()
    return dict(row) if row else None
