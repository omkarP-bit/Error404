"""
ai_projection_engine/server/routes/transaction_routes.py
=========================================================
Endpoint to add a new transaction directly to the main finance.db.
This writes to the shared `transactions` table (read-write).

POST /transactions
    → Inserts a new transaction and returns the fresh forecast impact.
GET  /transactions/{user_id}/recent
    → Last N transactions for a user (for live feed in UI).
GET  /transactions/{user_id}/categories
    → Distinct categories currently in the DB for this user.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.core.database import get_db
from server.services.confidence_band_service import invalidate_snapshot

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class TransactionIn(BaseModel):
    user_id: int = Field(..., gt=0)
    account_id: int = Field(default=1, gt=0)
    amount: float = Field(..., gt=0, description="Positive amount in ₹")
    txn_type: str = Field(default="DEBIT", description="DEBIT or CREDIT")
    category: str = Field(default="Uncategorised", max_length=100)
    subcategory: Optional[str] = Field(default=None, max_length=100)
    raw_description: Optional[str] = Field(default=None, max_length=500)
    payment_mode: Optional[str] = Field(default=None, max_length=50)
    is_recurring: bool = Field(default=False)
    txn_timestamp: Optional[datetime] = Field(
        default=None,
        description="ISO datetime; defaults to now if omitted",
    )

    @validator("txn_type")
    def normalise_type(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in {"DEBIT", "CREDIT", "TRANSFER"}:
            raise ValueError("txn_type must be DEBIT, CREDIT, or TRANSFER")
        return v


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_account_ids(db: Session, user_id: int) -> List[int]:
    rows = db.execute(
        text("SELECT account_id FROM accounts WHERE user_id = :uid ORDER BY account_id"),
        {"uid": user_id},
    ).fetchall()
    return [r[0] for r in rows]


def _get_latest_balance(db: Session, account_id: int) -> float:
    row = db.execute(
        text("SELECT current_balance FROM accounts WHERE account_id = :aid"),
        {"aid": account_id},
    ).fetchone()
    return float(row[0]) if row else 0.0


def _update_account_balance(
    db: Session, account_id: int, delta: float, txn_type: str
) -> float:
    """Adjust account balance and return the new balance."""
    current = _get_latest_balance(db, account_id)
    if txn_type == "DEBIT":
        new_bal = current - delta
    elif txn_type == "CREDIT":
        new_bal = current + delta
    else:
        new_bal = current  # TRANSFER — don't adjust here

    db.execute(
        text("UPDATE accounts SET current_balance = :bal WHERE account_id = :aid"),
        {"bal": round(new_bal, 2), "aid": account_id},
    )
    return round(new_bal, 2)


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a new transaction and get updated forecast impact",
)
def add_transaction(
    payload: TransactionIn,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Inserts a transaction into the shared `transactions` table.
    - Updates the account balance.
    - Invalidates the forecast cache so the next /forecast call reflects the new data.
    - Returns the inserted transaction ID + quick spend summary.
    """
    # Verify account belongs to user
    valid_accounts = _get_account_ids(db, payload.user_id)
    if not valid_accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No accounts found for user_id={payload.user_id}",
        )
    account_id = payload.account_id if payload.account_id in valid_accounts else valid_accounts[0]

    ts = payload.txn_timestamp or datetime.now()
    new_balance = _update_account_balance(db, account_id, payload.amount, payload.txn_type)

    result = db.execute(
        text("""
            INSERT INTO transactions
                (user_id, account_id, amount, txn_type, category, subcategory,
                 raw_description, payment_mode, is_recurring, user_verified,
                 balance_after_txn, txn_timestamp)
            VALUES
                (:user_id, :account_id, :amount, :txn_type, :category, :subcategory,
                 :raw_description, :payment_mode, :is_recurring, 0,
                 :balance_after_txn, :txn_timestamp)
        """),
        {
            "user_id": payload.user_id,
            "account_id": account_id,
            "amount": round(payload.amount, 2),
            "txn_type": payload.txn_type,
            "category": payload.category,
            "subcategory": payload.subcategory,
            "raw_description": payload.raw_description,
            "payment_mode": payload.payment_mode,
            "is_recurring": int(payload.is_recurring),
            "balance_after_txn": new_balance,
            "txn_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S.%f"),
        },
    )
    db.commit()
    txn_id = result.lastrowid

    # Invalidate forecast cache so next /forecast gives fresh numbers
    try:
        invalidate_snapshot(db, payload.user_id)
    except Exception:
        pass  # Don't fail the insert if cache invalidation errors

    # Quick spend-so-far summary for the response
    cur_month = ts.strftime("%Y-%m")
    row = db.execute(
        text("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE user_id = :uid
              AND lower(txn_type) = 'debit'
              AND strftime('%Y-%m', txn_timestamp) = :month
        """),
        {"uid": payload.user_id, "month": cur_month},
    ).fetchone()
    spent_this_month = float(row[0]) if row else 0.0

    return {
        "status": "created",
        "txn_id": txn_id,
        "message": f"Transaction #{txn_id} added. Forecast cache invalidated.",
        "account_balance_after": new_balance,
        "spent_this_month_so_far": round(spent_this_month, 2),
        "month_year": cur_month,
        "transaction": {
            "txn_id": txn_id,
            "user_id": payload.user_id,
            "amount": round(payload.amount, 2),
            "txn_type": payload.txn_type,
            "category": payload.category,
            "raw_description": payload.raw_description,
            "txn_timestamp": ts.isoformat(),
            "is_recurring": payload.is_recurring,
        },
    }


@router.get(
    "/{user_id}/recent",
    summary="Fetch the most recent transactions for a user",
)
def get_recent_transactions(
    user_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    rows = db.execute(
        text("""
            SELECT txn_id, amount, txn_type, category, raw_description,
                   txn_timestamp, is_recurring, balance_after_txn
            FROM transactions
            WHERE user_id = :uid
            ORDER BY txn_timestamp DESC
            LIMIT :lim
        """),
        {"uid": user_id, "lim": limit},
    ).fetchall()

    transactions = [
        {
            "txn_id": r[0],
            "amount": r[1],
            "txn_type": r[2],
            "category": r[3] or "Uncategorised",
            "description": r[4] or "",
            "txn_timestamp": str(r[5]),
            "is_recurring": bool(r[6]),
            "balance_after": r[7],
        }
        for r in rows
    ]
    return {"status": "success", "user_id": user_id, "transactions": transactions}


@router.get(
    "/{user_id}/categories",
    summary="Get distinct categories for a user (for dropdown population)",
)
def get_categories(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    rows = db.execute(
        text("""
            SELECT DISTINCT category
            FROM transactions
            WHERE user_id = :uid AND category IS NOT NULL
            ORDER BY category
        """),
        {"uid": user_id},
    ).fetchall()
    categories = [r[0] for r in rows if r[0]]
    return {"status": "success", "categories": categories}
