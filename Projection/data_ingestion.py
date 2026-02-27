"""
server/shock_engine/data_ingestion.py
======================================
Fetches raw data needed by the Financial Shock Absorption Engine.
Uses the same shared SQLite DB as the rest of the projection engine.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def fetch_user_data(db: Session, user_id: int) -> dict[str, Any]:
    today          = date.today()
    six_months_ago = today - timedelta(days=182)
    month_start    = today.replace(day=1)

    user     = _fetch_user(db, user_id)
    accounts = _fetch_accounts(db, user_id)
    txns_6m  = _fetch_transactions(db, user_id, since=six_months_ago)
    txns_cm  = txns_6m[txns_6m["txn_date"] >= pd.Timestamp(month_start)].copy() if not txns_6m.empty else txns_6m.copy()
    goals    = _fetch_goals(db, user_id)
    budget   = _fetch_budget_profile(db, user_id)
    patterns = _fetch_patterns(db, user_id)

    logger.info("FSE ingested user=%d | 6m_txns=%d | cm_txns=%d | goals=%d",
                user_id, len(txns_6m), len(txns_cm), len(goals))

    return {
        "user_profile":       user,
        "accounts":           accounts,
        "transactions_6m":    txns_6m,
        "current_month_txns": txns_cm,
        "goals":              goals,
        "budget_profile":     budget,
        "txn_patterns":       patterns,
        "snapshot_date":      today.isoformat(),
    }


def _fetch_user(db: Session, user_id: int) -> dict:
    row = db.execute(
        text("SELECT user_id, name, email, monthly_income, risk_profile FROM users WHERE user_id=:uid"),
        {"uid": user_id},
    ).mappings().first()
    if not row:
        raise ValueError(f"User {user_id} not found.")
    return dict(row)


def _fetch_accounts(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        text("SELECT account_id, institution_name, account_type, current_balance FROM accounts WHERE user_id=:uid"),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _fetch_transactions(db: Session, user_id: int, since: date) -> pd.DataFrame:
    rows = db.execute(
        text("""
            SELECT txn_id, amount, category, subcategory,
                   txn_timestamp, txn_type, is_recurring,
                   payment_mode, balance_after_txn
            FROM transactions
            WHERE user_id=:uid AND lower(txn_type)='debit'
              AND date(txn_timestamp) >= :since
            ORDER BY txn_timestamp ASC
        """),
        {"uid": user_id, "since": since.isoformat()},
    ).mappings().all()

    if not rows:
        return pd.DataFrame(columns=["txn_id","amount","category","subcategory",
                                     "txn_date","txn_type","is_recurring",
                                     "payment_mode","balance_after_txn"])
    df = pd.DataFrame([dict(r) for r in rows])
    df["txn_date"] = pd.to_datetime(df["txn_timestamp"]).dt.normalize()
    df["amount"]   = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["category"] = df["category"].fillna("Uncategorised")
    return df


def _fetch_goals(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT goal_id, goal_name, goal_type, priority,
                   target_amount, current_amount, deadline, status
            FROM goals WHERE user_id=:uid AND lower(status)='active'
            ORDER BY priority ASC
        """),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _fetch_budget_profile(db: Session, user_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT needs_ratio, wants_ratio, savings_ratio,
                   baseline_expense, expense_volatility,
                   avg_monthly_surplus, safe_investable_amount
            FROM budget_profiles WHERE user_id=:uid LIMIT 1
        """),
        {"uid": user_id},
    ).mappings().first()
    return dict(row) if row else None


def _fetch_patterns(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        text("SELECT category, avg_amount, std_amount, txn_count FROM transaction_patterns WHERE user_id=:uid"),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]
