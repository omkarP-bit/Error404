"""
app/routers/anomaly.py
=======================
Routes for:
  GET  /anomaly-test         -- UI page
  POST /api/anomaly/scan     -- Scan a user's live DB transactions for anomalies
  POST /api/retrain/anomaly  -- Re-train the IsolationForest model
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import User, Alert

router     = APIRouter(prefix="/anomaly-test", tags=["Anomaly"])
api_router = APIRouter(prefix="/api", tags=["Anomaly API"])
templates  = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def anomaly_test_page(request: Request, db: Session = Depends(get_db)):
    users  = db.query(User).limit(10).all()
    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse("anomaly_test.html", {
        "request": request,
        "users":   users,
        "alerts":  alerts,
    })


@api_router.post("/anomaly/scan")
async def anomaly_scan(
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Scan a user's live DB transactions through the IsolationForest.
    Clears stale OPEN anomaly alerts, inserts fresh ones.
    Returns every transaction (normal + anomaly) with anomaly_score and severity.
    """
    try:
        from ml_models.anomaly_detection_model.inference import scan_user_from_db
        results   = scan_user_from_db(db_session=db, user_id=user_id if user_id > 0 else None)
        anomalies = [r for r in results if r["is_anomaly"]]
        return JSONResponse({
            "success":         True,
            "total_scanned":   len(results),
            "total_anomalies": len(anomalies),
            "transactions":    results,
        })
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/retrain/anomaly")
async def retrain_anomaly():
    """Re-train IsolationForest on the CSV dataset (baseline recalibration)."""
    try:
        from ml_models.anomaly_detection_model.inference import retrain_model
        report = retrain_model()
        return JSONResponse({"success": True, "report": report})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/anomaly/dismiss")
async def anomaly_dismiss(
    txn_ids: str = Form(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Dismiss (delete) Alert records for the given txn_ids.
    Does NOT delete the underlying Transaction — only removes the anomaly flag.
    """
    try:
        ids = [int(x.strip()) for x in txn_ids.split(",") if x.strip()]
        if not ids:
            return JSONResponse({"success": False, "error": "No txn_ids provided"}, status_code=400)
        deleted = (
            db.query(Alert)
            .filter(Alert.txn_id.in_(ids), Alert.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return JSONResponse({"success": True, "dismissed": deleted})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)

