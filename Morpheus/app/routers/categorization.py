"""
app/routers/categorization.py
==============================
Routes for:
  GET  /categorization-test             -- UI test page
  POST /api/categorize                   -- Categorise (DB lookup first, NLP fallback, no DB insert)
  POST /api/categorize/confirm           -- User confirms/corrects a category (updates DB mapping)
  POST /api/categorize/add-transaction   -- Explicitly save categorised transaction to DB
  POST /api/categorize/ocr               -- Upload receipt image -> OCR -> autofill fields
  POST /api/retrain/categorize           -- Re-train the SVC model
"""

import io
import re
from typing import Optional

from fastapi import APIRouter, Request, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import User
from app.config import settings
from app.services.categorization_service import categorization_service

router     = APIRouter(prefix="/categorization-test", tags=["Categorization"])
api_router = APIRouter(prefix="/api", tags=["Categorization API"])
templates  = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


# ---------------------------------------------------------------------------
# UI Route
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
async def cat_test_page(request: Request, db: Session = Depends(get_db)):
    """Render the Categorisation test UI."""
    users = db.query(User).limit(10).all()
    return templates.TemplateResponse("categorization_test.html", {
        "request": request,
        "users":   users,
        "result":  None,
    })


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@api_router.post("/categorize")
async def categorize_api(
    raw_description: str   = Form(...),
    amount:          float = Form(...),
    merchant_name:   str   = Form(""),
    txn_type:        str   = Form("debit"),
    payment_mode:    str   = Form("UPI"),
    user_id:         int   = Form(1),
    account_id:      int   = Form(1),
    db: Session = Depends(get_db),
):
    """
    Stage 1: DB merchant lookup (instant, confidence=1.0).
    Stage 2: SentenceTransformer + SVC fallback.
    Does NOT insert to DB — call /add-transaction to persist.
    Returns needs_confirmation=True when confidence < 0.85.
    """
    try:
        result = categorization_service.categorize(
            db=db,
            user_id=user_id,
            raw_description=raw_description,
            merchant_name=merchant_name,
            amount=amount,
            txn_type=txn_type,
            payment_mode=payment_mode,
            account_id=account_id,
            insert_to_db=False,   # user decides via Add Transaction button
        )
        return JSONResponse({"success": True, "result": result})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/categorize/add-transaction")
async def add_transaction(
    raw_description: str   = Form(...),
    amount:          float = Form(...),
    merchant_name:   str   = Form(""),
    txn_type:        str   = Form("debit"),
    payment_mode:    str   = Form("UPI"),
    user_id:         int   = Form(1),
    account_id:      int   = Form(1),
    category:        str   = Form(...),
    subcategory:     str   = Form(""),
    db: Session = Depends(get_db),
):
    """
    Insert the categorised transaction into the DB.
    Also upserts CategoryMapping so next categorisation hits Stage 1.
    """
    try:
        from app.services.categorization_service import normalize_merchant
        from app.models import Merchant
        norm = normalize_merchant(merchant_name or raw_description)
        txn, merchant_id = categorization_service._insert_transaction(
            db, user_id, account_id, amount, txn_type,
            raw_description, merchant_name, payment_mode,
            category, subcategory,
            1.0,   # user-confirmed confidence
            norm, None,
        )
        # Upsert CategoryMapping so Stage 1 hits immediately next time
        if txn and txn.merchant_id:
            categorization_service._upsert_mapping(
                db, user_id, txn.merchant_id, category, subcategory
            )
            # Also update the merchant's global default so Stage 1
            # hits even for other users who haven't set a preference yet
            m = db.query(Merchant).filter(
                Merchant.merchant_id == txn.merchant_id
            ).first()
            if m:
                m.default_category = category
            db.commit()   # ← persist both the mapping and the merchant update
        return JSONResponse({
            "success":     True,
            "txn_id":      txn.txn_id if txn else None,
            "merchant_id": txn.merchant_id if txn else None,
            "category":    category,
            "message":     f"Transaction #{txn.txn_id} saved and merchant mapping updated."
        })
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/categorize/confirm")
async def confirm_category(
    txn_id:                int = Form(...),
    corrected_category:    str = Form(...),
    corrected_subcategory: str = Form(""),
    user_id:               int = Form(1),
    db: Session = Depends(get_db),
):
    """User confirms / corrects a category -- updates DB mapping for future predictions."""
    try:
        result = categorization_service.confirm_category(
            db=db,
            txn_id=txn_id,
            corrected_category=corrected_category,
            corrected_subcategory=corrected_subcategory,
            user_id=user_id,
        )
        return JSONResponse({"success": True, **result})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/categorize/ocr")
async def ocr_upload(
    file:       UploadFile = File(...),
    user_id:    int = Form(1),
    account_id: int = Form(1),
    db: Session = Depends(get_db),
):
    """
    OCR a receipt image — extracts merchant/amount/description and runs
    the categorisation pipeline. Does NOT insert to DB.
    Returns ocr_merchant, ocr_amount, ocr_description for form autofill
    plus the full categorisation result (category, confidence, pipeline_step).
    """
    image_bytes = await file.read()
    try:
        ocr_data = _run_ocr(image_bytes)
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"OCR failed: {exc}"}, status_code=500)

    result = categorization_service.categorize(
        db=db,
        user_id=user_id,
        raw_description=ocr_data.get("description", ""),
        merchant_name=ocr_data.get("merchant", ""),
        amount=ocr_data.get("amount", 0.0),
        txn_type="debit",
        payment_mode="OCR",
        account_id=account_id,
        insert_to_db=False,
        receipt_items=ocr_data.get("items", ""),          # str fallback
        items=ocr_data.get("items_list", []),             # list[str] for item-level embedding
    )
    result["ocr_merchant"]    = ocr_data.get("merchant", "")
    result["ocr_amount"]      = ocr_data.get("amount", 0.0)
    result["ocr_description"] = ocr_data.get("description", "")
    result["ocr_items"]       = ocr_data.get("items_list", [])
    result["receipt_json"]    = ocr_data.get("receipt_json", {})
    return JSONResponse({"success": True, "result": result})


@api_router.post("/retrain/categorize")
async def retrain_cat():
    """Force re-train the SVC categorisation model."""
    try:
        categorization_service._svc_model = None
        from ml_models.categorization_model.train import train_model
        report = train_model()
        return JSONResponse({"success": True, "report": str(report)})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@api_router.post("/retrain/gradient-boost")
async def retrain_gradient_boost_endpoint(
    user_id: int = Form(1),
    db: Session = Depends(get_db),
):
    """
    Force re-train the HistGradientBoosting (Option A) classifier.
    Wipes the saved artifact and trains fresh from high-confidence DB transactions.
    Requires >= 30 verified/high-confidence transactions.
    """
    try:
        from app.services.categorization_service import retrain_gradient_boost
        ok = retrain_gradient_boost(db)
        if ok:
            return JSONResponse({"success": True, "message": "Gradient boost model trained and saved."})
        return JSONResponse({"success": False, "message": "Not enough labeled data (need >= 30 transactions)."})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_ocr(image_bytes: bytes) -> dict:
    """
    Run Tesseract OCR on image bytes.
    Returns:
      merchant    – best guess at store/sender name
      amount      – largest 'Total' value found
      description – full receipt text (all lines) for NLP
      items       – only the line-item product/food name lines
    """
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    img  = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(img)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # ── Merchant: first alphabetic, non-date line in top 8 ────────────────
    merchant = ""
    _skip_re = re.compile(
        r'^(date|time|invoice|bill\s*no|gstin|phone|address|table|order\s*no|receipt)',
        re.IGNORECASE,
    )
    for line in lines[:8]:
        if re.search(r"[A-Za-z]", line) and not re.match(r"^\d", line) and not _skip_re.match(line):
            merchant = line
            break

    # ── Amount: scan bottom-up for Total / Grand Total / Amount Due ───────
    amount = 0.0
    _amt_re = re.compile(
        r"(?:total|grand\s*total|amount\s*due|amount\s*paid|net\s*amount)[^\d]*([0-9,]+\.?\d*)",
        re.IGNORECASE,
    )
    for line in reversed(lines):
        m = _amt_re.search(line)
        if m:
            try:
                amount = float(m.group(1).replace(",", ""))
                break
            except ValueError:
                pass
    # Fallback: last bare decimal number
    if amount == 0.0:
        for line in reversed(lines):
            m = re.search(r"([0-9,]+\.\d{2})\s*$", line)
            if m:
                try:
                    amount = float(m.group(1).replace(",", ""))
                    break
                except ValueError:
                    pass

    # ── Item lines: lines that look like product / food names ─────────────
    # Keep lines that have letters but are NOT purely metadata
    _meta_re = re.compile(
        r'^(date|time|gstin|phone|address|table|order|receipt|invoice|cashier'
        r'|server|subtotal|sub total|discount|tax|cgst|sgst|igst|vat|total'
        r'|grand|amount|cash|change|balance|tip|thank|welcome|visit|www|http)',
        re.IGNORECASE,
    )
    item_lines = [
        ln for ln in lines
        if re.search(r'[A-Za-z]', ln)
        and not _meta_re.match(ln)
        and not re.match(r'^\d{1,2}[/\-]\d{1,2}', ln)   # skip date-like lines
    ]

    # ── Build structured receipt output ──────────────────────────────────────
    # Full receipt text (NLP uses all lines)
    description  = " | ".join(lines)
    # Space-joined item string (backward compat for receipt_items param)
    items_str    = " ".join(item_lines[:20])
    # Structured list for per-item embedding (Step 2)
    items_list   = item_lines[:20]

    receipt_json = {
        "merchant": merchant,
        "items":    items_list,
        "total":    amount,
    }

    return {
        "merchant":     merchant,
        "amount":       amount,
        "description":  description,
        "items":        items_str,        # str  — legacy receipt_items
        "items_list":   items_list,       # list[str] — item-level embedding
        "receipt_json": receipt_json,     # structured JSON
    }

