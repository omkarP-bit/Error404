"""
app/routers/investment.py
==========================
Routes for:
  GET  /investment-test        — UI test page
  POST /api/investment/assess  — Assess investment readiness
  POST /api/retrain/investment — Re-train the model
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import User

router     = APIRouter(prefix="/investment-test", tags=["Investment"])
api_router = APIRouter(prefix="/api", tags=["Investment API"])
templates  = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def investment_test_page(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).limit(10).all()
    return templates.TemplateResponse("investment_test.html", {
        "request": request,
        "users":   users,
        "result":  None,
    })


@api_router.post("/investment/assess")
async def assess_investment(
    savings_ratio:           float = Form(...),
    surplus_consistency:     float = Form(...),
    emergency_fund_coverage: float = Form(...),
    income_stability:        float = Form(...),
    risk_profile:            str   = Form("moderate"),
):
    """Assess whether a user is ready to invest."""
    try:
        from ml_models.investment_readiness_model.inference import assess_investment_readiness
        result = assess_investment_readiness(
            savings_ratio           = savings_ratio,
            surplus_consistency     = surplus_consistency,
            emergency_fund_coverage = emergency_fund_coverage,
            income_stability        = income_stability,
            risk_profile            = risk_profile,
        )
        return JSONResponse({"success": True, "result": result})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/investment/assess-user")
async def assess_user_investment(user_id: int = Form(1), db: Session = Depends(get_db)):
    """Auto-derive all metrics from a user's transaction history and assess readiness."""
    try:
        from ml_models.investment_readiness_model.inference import assess_investment_readiness
        from app.models import Transaction, TxnType
        from sqlalchemy import func

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return JSONResponse({"success": False, "error": "User not found"}, status_code=404)

        # Derive metrics
        avg_income  = db.query(func.avg(Transaction.amount)).filter(
            Transaction.user_id == user_id, Transaction.txn_type == TxnType.CREDIT
        ).scalar() or 1.0

        avg_expense = db.query(func.avg(Transaction.amount)).filter(
            Transaction.user_id == user_id, Transaction.txn_type == TxnType.DEBIT
        ).scalar() or 0.0

        avg_surplus = db.query(func.avg(Transaction.monthly_surplus)).filter(
            Transaction.user_id == user_id
        ).scalar() or 0.0

        volatility = db.query(func.avg(Transaction.expense_volatility)).filter(
            Transaction.user_id == user_id
        ).scalar() or 1.0

        balance = db.query(func.max(Transaction.balance_after_txn)).filter(
            Transaction.user_id == user_id
        ).scalar() or 0.0

        savings_ratio           = min(max(avg_surplus / max(avg_income, 1), 0), 1)
        surplus_consistency     = max(1 - volatility / max(avg_surplus * 12, 1), 0)
        emergency_fund_coverage = min(balance / max(avg_expense * 6, 1), 5.0)
        income_stability        = max(1 - volatility / max(avg_income, 1), 0)

        result = assess_investment_readiness(
            savings_ratio           = float(savings_ratio),
            surplus_consistency     = float(surplus_consistency),
            emergency_fund_coverage = float(emergency_fund_coverage),
            income_stability        = float(income_stability),
            risk_profile            = user.risk_profile.value,
        )
        result["derived_metrics"] = {
            "avg_income":            round(float(avg_income), 2),
            "avg_surplus":           round(float(avg_surplus), 2),
            "savings_ratio":         round(float(savings_ratio), 4),
            "emergency_fund_coverage": round(float(emergency_fund_coverage), 2),
        }
        return JSONResponse({"success": True, "result": result})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/retrain/investment")
async def retrain_investment():
    from ml_models.investment_readiness_model.inference import retrain_model
    report = retrain_model()
    return JSONResponse({"success": True, "report": report})
