"""
ml_models/categorization_model/inference.py
============================================
High-level inference interface for the Categorisation model.
Integrates OCR, PDF parsing, DB feedback loop, and audit logging.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import io
import json
from datetime import datetime
from typing import Optional

import pandas as pd

from ml_models.categorization_model.model import CategorizationModel

# Lazy model singleton
_model: Optional[CategorizationModel] = None


def _get_model() -> CategorizationModel:
    global _model
    if _model is None:
        _model = CategorizationModel()
        if _model.is_trained():
            _model.load()
        else:
            print("⚠️  Model not trained — training now …")
            _model.train(verbose=False)
    return _model


def categorize_transaction(
    raw_description: str,
    amount: float,
    merchant_name: str = "",
    txn_type: str = "debit",
    payment_mode: str = "UPI",
    month: int = 1,
    day_of_week: int = 0,
    hour: int = 12,
    is_recurring: int = 0,
    user_mappings: Optional[dict] = None,
) -> dict:
    """
    Main entry point: categorise a single transaction.
    Returns full prediction dict including confidence + confirmation flag.
    """
    model = _get_model()
    return model.predict_single(
        text_input    = raw_description,
        amount        = amount,
        merchant_name = merchant_name,
        txn_type      = txn_type,
        payment_mode  = payment_mode,
        month         = month,
        day_of_week   = day_of_week,
        hour          = hour,
        is_recurring  = is_recurring,
        user_mappings = user_mappings,
    )


def categorize_from_ocr(image_bytes: bytes) -> dict:
    """
    Ingest a receipt image via OCR, extract text, then categorise.
    Requires pytesseract + Tesseract installed.
    """
    try:
        import pytesseract
        from PIL import Image
        # Set tesseract binary path from settings / .env
        try:
            from app.config import settings
            tess_cmd = settings.TESSERACT_CMD
            if tess_cmd and tess_cmd != "tesseract":
                pytesseract.pytesseract.tesseract_cmd = tess_cmd
        except Exception:
            import os
            tess_cmd = os.getenv("TESSERACT_CMD", "tesseract")
            if tess_cmd != "tesseract":
                pytesseract.pytesseract.tesseract_cmd = tess_cmd
        image = Image.open(io.BytesIO(image_bytes))
        text  = pytesseract.image_to_string(image)
    except Exception as exc:
        return {"error": f"OCR failed: {exc}", "raw_text": ""}

    # Extract merchant, amount, description from OCR text
    import re
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    merchant = lines[0][:100] if lines else "Unknown"

    # Try to find a better merchant name (skip lines that look like dates/numbers)
    for line in lines[:5]:
        if not re.match(r'^[\d\W]+$', line) and len(line) > 2:
            merchant = line[:100]
            break

    # Extract amount — try Total/Amount labels first, then any price-like number
    amount = 0.0
    amount_patterns = [
        r'(?:total|grand total|amount|net amount|rs\.?|₹)\s*[:\s]*([\d,]+\.?\d*)',
        r'([\d,]{2,}\.[\d]{2})\s*$',
        r'([\d,]{3,})',
    ]
    for pat in amount_patterns:
        for line in reversed(lines):          # totals usually near the bottom
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                try:
                    v = float(m.group(1).replace(',', ''))
                    if v > 1:
                        amount = v
                        break
                except ValueError:
                    continue
        if amount > 0:
            break

    raw_description = ' '.join(lines[:3])[:200]   # first 3 lines as description

    result = categorize_transaction(
        raw_description=raw_description,
        amount=amount,
        merchant_name=merchant,
    )
    result["ocr_text"]       = text[:500]
    result["ocr_merchant"]   = merchant
    result["ocr_amount"]     = amount
    result["ocr_description"] = raw_description
    result["source"]         = "ocr"
    return result


def categorize_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Parse a bank statement PDF, extract rows, categorise each transaction.
    Requires pdfplumber.
    """
    try:
        import pdfplumber
        results = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or all(c is None for c in row):
                            continue
                        row_text = " ".join(str(c) for c in row if c)
                        amount = 0.0
                        for tok in row_text.replace(",", "").split():
                            try:
                                v = float(tok.strip("₹$Rs.-"))
                                if v > 1:
                                    amount = v
                                    break
                            except ValueError:
                                continue

                        result = categorize_transaction(
                            raw_description = row_text[:200],
                            amount          = amount,
                            merchant_name   = row_text.split()[0] if row_text.split() else "",
                        )
                        result["pdf_row"] = row_text[:200]
                        result["source"]  = "pdf"
                        results.append(result)
        return results
    except Exception as exc:
        return [{"error": f"PDF parsing failed: {exc}", "source": "pdf"}]


def categorize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Batch categorise a full DataFrame from CSV upload."""
    model = _get_model()
    return model.predict_batch(df)


def retrain_model() -> dict:
    """Force re-train from latest CSV data."""
    global _model
    _model = CategorizationModel()
    return _model.train(verbose=True)


if __name__ == "__main__":
    result = categorize_transaction(
        raw_description="SWIGGY ORDER 4521",
        amount=350.0,
        merchant_name="Swiggy",
        txn_type="debit",
        payment_mode="UPI",
        month=3,
        day_of_week=5,
        hour=20,
    )
    print(json.dumps(result, indent=2))
