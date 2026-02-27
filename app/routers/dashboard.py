"""
app/routers/dashboard.py
========================
Main dashboard route — aggregated financial overview.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path

from app.database import get_db
from app.models import User, Transaction, Alert, Goal, Budget, TxnType, AlertStatus

router     = APIRouter()
templates  = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: int = 1, db: Session = Depends(get_db)):
    """
    Render the main fintech dashboard for a given user.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        users = db.query(User).limit(10).all()
        return templates.TemplateResponse(
            "user_select.html",
            {"request": request, "users": users},
        )

    # ── Aggregates ─────────────────────────────────────────────────────────
    total_txns = db.query(func.count(Transaction.txn_id)).filter(
        Transaction.user_id == user_id
    ).scalar() or 0

    total_debit = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.txn_type == TxnType.DEBIT,
    ).scalar() or 0.0

    total_credit = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.txn_type == TxnType.CREDIT,
    ).scalar() or 0.0

    open_alerts = db.query(func.count(Alert.alert_id)).filter(
        Alert.user_id == user_id,
        Alert.status  == AlertStatus.OPEN,
    ).scalar() or 0

    recent_txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.txn_timestamp.desc())
        .limit(10)
        .all()
    )

    goals = db.query(Goal).filter(Goal.user_id == user_id).all()
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()

    # ── Category spend breakdown ───────────────────────────────────────────
    cat_spend = (
        db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
        .filter(Transaction.user_id == user_id, Transaction.txn_type == TxnType.DEBIT)
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(8)
        .all()
    )

    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == user_id, Alert.status == AlertStatus.OPEN)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse("dashboard.html", {
        "request":      request,
        "user":         user,
        "total_txns":   total_txns,
        "total_debit":  round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "net_balance":  round(total_credit - total_debit, 2),
        "open_alerts":  open_alerts,
        "recent_txns":  recent_txns,
        "goals":        goals,
        "budgets":      budgets,
        "cat_spend":    cat_spend,
        "alerts":       alerts,
        "all_users":    db.query(User).all(),
    })
