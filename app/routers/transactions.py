"""
app/routers/transactions.py
============================
RESTful transaction management API.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Transaction, User, TxnType
from app.schemas import TransactionCreate, TransactionOut, CategoryConfirmRequest
from app.services.analytics_engine import analytics_engine

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("/")
def list_transactions(
    user_id: int = 1,
    limit:   int = 20,
    offset:  int = 0,
    db: Session = Depends(get_db),
):
    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.txn_timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(func.count(Transaction.txn_id)).filter(
        Transaction.user_id == user_id
    ).scalar()
    return {"total": total, "transactions": [TransactionOut.model_validate(t) for t in txns]}


@router.post("/")
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    txn = analytics_engine.ingest_transaction(
        db,
        user_id         = payload.user_id,
        account_id      = payload.account_id,
        amount          = payload.amount,
        txn_type        = payload.txn_type,
        raw_description = payload.raw_description,
        payment_mode    = payload.payment_mode,
    )
    return TransactionOut.model_validate(txn)


@router.post("/confirm-category")
def confirm_category(payload: CategoryConfirmRequest, db: Session = Depends(get_db)):
    try:
        fb = analytics_engine.confirm_category(
            db,
            txn_id               = payload.txn_id,
            corrected_category   = payload.corrected_category,
            corrected_subcategory= payload.corrected_subcategory,
            user_id              = payload.user_id,
        )
        return {"success": True, "feedback_id": fb.feedback_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{txn_id}")
def get_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.txn_id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionOut.model_validate(txn)
