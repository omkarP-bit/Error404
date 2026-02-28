"""
app/routers/dashboard.py
========================
Main dashboard route — aggregated financial overview.
"""

from datetime import datetime, timedelta
import math
from collections import defaultdict

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pathlib import Path

from app.database import get_db
from app.models import User, Transaction, Alert, Goal, Budget, SavingsPot, TxnType, AlertStatus
from app.models.enums import BudgetPeriod

router     = APIRouter()
templates  = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
api_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard API"])


def _get_period_start(now: datetime, period: BudgetPeriod) -> datetime:
    """Return the datetime representing the start of the budget period."""
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == BudgetPeriod.WEEKLY:
        return base - timedelta(days=base.weekday())

    if period == BudgetPeriod.QUARTERLY:
        quarter = (base.month - 1) // 3
        month = quarter * 3 + 1
        return base.replace(month=month, day=1)

    if period == BudgetPeriod.YEARLY:
        return base.replace(month=1, day=1)

    # Default: monthly
    return base.replace(day=1)


def _month_start_offset(base: datetime, months_back: int) -> datetime:
    """Return the first day of the month offset by `months_back`."""
    year = base.year
    month = base.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return base.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _score_label(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Watch"


@api_router.get("/summary")
def dashboard_summary(user_id: int = 1, db: Session = Depends(get_db)):
    """Return aggregated dashboard metrics for the Flutter client."""
    user_exists = db.query(User.user_id).filter(User.user_id == user_id).first()
    if not user_exists:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_type == TxnType.CREDIT,
            Transaction.txn_timestamp >= month_start,
        )
        .scalar()
        or 0.0
    )

    expense = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_type == TxnType.DEBIT,
            Transaction.txn_timestamp >= month_start,
        )
        .scalar()
        or 0.0
    )

    net = float(income) - float(expense)
    savings_rate = round((net / income) * 100, 2) if income else 0.0

    budgets = (
        db.query(Budget)
        .filter(Budget.user_id == user_id, Budget.is_active == True)
        .order_by(Budget.limit_amount.desc())
        .all()
    )

    budgets_payload = []
    for budget in budgets:
        period_start = _get_period_start(now, budget.period)
        spent = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.txn_type == TxnType.DEBIT,
                Transaction.category == budget.category,
                Transaction.txn_timestamp >= period_start,
            )
            .scalar()
            or 0.0
        )
        spent = float(spent)
        remaining = budget.limit_amount - spent
        utilisation = 0.0
        if budget.limit_amount:
            utilisation = min(spent / budget.limit_amount * 100, 999)

        budgets_payload.append({
            "budget_id": budget.budget_id,
            "category": budget.category,
            "period": budget.period.value,
            "limit_amount": round(budget.limit_amount, 2),
            "spent_amount": round(spent, 2),
            "remaining_amount": round(remaining, 2),
            "utilisation_pct": round(utilisation, 2),
        })

    emergency_goal_amount = (
        db.query(func.coalesce(func.sum(Goal.current_amount), 0.0))
        .filter(
            Goal.user_id == user_id,
            or_(
                Goal.goal_name.ilike("%emergency%"),
                Goal.goal_type.ilike("%emergency%"),
            ),
        )
        .scalar()
        or 0.0
    )

    emergency_pot_amount = (
        db.query(func.coalesce(func.sum(SavingsPot.current_amount), 0.0))
        .filter(
            SavingsPot.user_id == user_id,
            SavingsPot.name.ilike("%emergency%"),
        )
        .scalar()
        or 0.0
    )

    emergency_fund_balance = float(emergency_goal_amount) + float(emergency_pot_amount)

    emi_spend = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_type == TxnType.DEBIT,
            Transaction.txn_timestamp >= month_start,
            or_(
                Transaction.category.ilike("%emi%"),
                Transaction.category.ilike("%loan%"),
                Transaction.subcategory.ilike("%emi%"),
                Transaction.raw_description.ilike("%emi%"),
            ),
        )
        .scalar()
        or 0.0
    )

    income_history_start = _month_start_offset(month_start, 5)
    income_rows = (
        db.query(Transaction.txn_timestamp, Transaction.amount)
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_type == TxnType.CREDIT,
            Transaction.txn_timestamp >= income_history_start,
        )
        .all()
    )

    income_by_month = defaultdict(float)
    for txn_ts, amount in income_rows:
        label = txn_ts.strftime("%Y-%m")
        income_by_month[label] += float(amount or 0.0)

    income_history = []
    income_values = []
    for offset in range(5, -1, -1):
        month_point = _month_start_offset(month_start, offset)
        label = month_point.strftime("%Y-%m")
        amount = round(income_by_month.get(label, 0.0), 2)
        income_history.append({"month": label, "amount": amount})
        income_values.append(amount)

    income_cv_pct = 0.0
    if income_values:
        avg_income = sum(income_values) / len(income_values)
        if avg_income > 0:
            variance = sum((val - avg_income) ** 2 for val in income_values) / len(income_values)
            std_dev = math.sqrt(variance)
            income_cv_pct = min((std_dev / avg_income) * 100.0, 1000.0)
        else:
            income_cv_pct = 100.0

    savings_rate_pct = savings_rate
    expense_ratio_pct = round((float(expense) / float(income)) * 100, 2) if income else 100.0
    savings_score = _clamp(savings_rate_pct)
    expense_control_score = _clamp(100.0 - expense_ratio_pct)

    monthly_expense_value = float(expense) if expense else 0.0
    emergency_months = (
        emergency_fund_balance / monthly_expense_value if monthly_expense_value > 0 else 0.0
    )
    emergency_score = _clamp((emergency_months / 6.0) * 100.0)

    emi_ratio_pct = (
        round((float(emi_spend) / float(income)) * 100, 2)
        if income
        else (100.0 if emi_spend else 0.0)
    )
    debt_health_score = _clamp(100.0 - emi_ratio_pct)
    income_stability_score = _clamp(100.0 - min(income_cv_pct, 100.0))

    financial_stability_score = round(
        savings_score * 0.30
        + expense_control_score * 0.20
        + emergency_score * 0.20
        + debt_health_score * 0.15
        + income_stability_score * 0.15,
        2,
    )

    financial_components = {
        "savings_rate": {
            "weight": 0.30,
            "value_pct": round(savings_rate_pct, 2),
            "score": round(savings_score, 2),
            "direction": "higher_is_better",
        },
        "expense_control": {
            "weight": 0.20,
            "value_pct": round(expense_ratio_pct, 2),
            "score": round(expense_control_score, 2),
            "direction": "lower_is_better",
        },
        "emergency_fund": {
            "weight": 0.20,
            "value_months": round(emergency_months, 2),
            "score": round(emergency_score, 2),
            "direction": "higher_is_better",
        },
        "debt_health": {
            "weight": 0.15,
            "value_pct": round(emi_ratio_pct, 2),
            "score": round(debt_health_score, 2),
            "direction": "lower_is_better",
        },
        "income_stability": {
            "weight": 0.15,
            "value_pct": round(income_cv_pct, 2),
            "score": round(income_stability_score, 2),
            "direction": "lower_is_better",
        },
    }

    metrics_payload = {
        "monthly_income": round(float(income), 2),
        "monthly_expense": round(float(expense), 2),
        "monthly_savings": round(net, 2),
        "savings_rate_pct": round(savings_rate_pct, 2),
        "expense_ratio_pct": round(expense_ratio_pct, 2),
        "emergency_fund_balance": round(emergency_fund_balance, 2),
        "emergency_months": round(emergency_months, 2),
        "emi_obligations": round(float(emi_spend), 2),
        "emi_ratio_pct": round(emi_ratio_pct, 2),
        "income_cv_pct": round(income_cv_pct, 2),
        "income_history": income_history,
    }

    financial_payload = {
        "score": financial_stability_score,
        "label": _score_label(financial_stability_score),
        "components": financial_components,
        "metrics": metrics_payload,
    }

        # ── Momentum / Streak Engine ─────────────────────────────
        from app.models.savings_activity import SavingsActivity
        from app.engines.momentum_streak_engine import calculate_streak_score
        # Get last 7 months of savings activity
        streak_activities = (
            db.query(SavingsActivity)
            .filter(SavingsActivity.user_id == user_id)
            .order_by(SavingsActivity.month_key.desc())
            .limit(7)
            .all()
        )
        streak_activity_dicts = [
            {
                "month_key": sa.month_key,
                "contributed": sa.contributed,
                "missed": sa.missed,
                "total_sip_amount": sa.total_sip_amount,
            }
            for sa in reversed(streak_activities)
        ]
        streak_metrics = calculate_streak_score(streak_activity_dicts)

    return {
        "success": True,
        "user_id": user_id,
        "timeframe": {
            "month_start": month_start.isoformat(),
            "generated_at": now.isoformat(),
        },
        "summary": {
            "income_vs_expense": {
                "income": round(float(income), 2),
                "expense": round(float(expense), 2),
                "net": round(net, 2),
            },
            "savings_rate": savings_rate,
            "budgets": budgets_payload,
            "financial_stability": financial_payload,
                "streak_metrics": streak_metrics,
        },
    }


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
