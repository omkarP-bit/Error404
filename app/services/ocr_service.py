"""
app/services/ocr_service.py
============================
OCR Receipt Ingestion Service using pytesseract.
"""

import io
from typing import Optional


def extract_from_image(image_bytes: bytes) -> dict:
    """
    Extract transaction data from a receipt image using OCR.
    Returns dict with: merchant, amount, date, raw_text, error.
    """
    try:
        import pytesseract
        from PIL import Image
        import re
        import os

        # Use TESSERACT_CMD from settings
        from app.config import settings
        tess_cmd = settings.TESSERACT_CMD
        if tess_cmd and tess_cmd != "tesseract":
            pytesseract.pytesseract.tesseract_cmd = tess_cmd

        image     = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        raw_text  = pytesseract.image_to_string(image)

        merchant, amount, txn_date = _parse_receipt(raw_text)

        return {
            "merchant":   merchant,
            "amount":     amount,
            "date":       txn_date,
            "raw_text":   raw_text[:1000],
            "error":      None,
        }
    except ImportError:
        return {
            "merchant": "Unknown",
            "amount":   0.0,
            "date":     None,
            "raw_text": "",
            "error":    "pytesseract not installed. Run: pip install pytesseract pillow",
        }
    except Exception as exc:
        msg = str(exc)
        if "tesseract is not installed" in msg or "not in your PATH" in msg:
            return {
                "merchant": "Unknown",
                "amount":   0.0,
                "date":     None,
                "raw_text": "",
                "error":    (
                    "Tesseract OCR binary not found. "
                    "Download from https://github.com/UB-Mannheim/tesseract/wiki "
                    "then set TESSERACT_CMD in .env to its full path."
                ),
            }
        return {
            "merchant": "Unknown",
            "amount":   0.0,
            "date":     None,
            "raw_text": "",
            "error":    msg,
        }


def _parse_receipt(text: str) -> tuple[str, float, Optional[str]]:
    """Heuristic extraction from OCR text."""
    import re

    lines  = [l.strip() for l in text.splitlines() if l.strip()]
    merchant = lines[0][:100] if lines else "Unknown"

    # Extract amount: look for ₹, Rs., Total, Amount patterns
    amount = 0.0
    amount_patterns = [
        r"(?:total|amount|rs\.?|₹)\s*[:\s]*([0-9,]+\.?[0-9]*)",
        r"([0-9]{2,}[.,][0-9]{2})\s*(?:total|rs|₹)?",
    ]
    for pat in amount_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
                if amount > 1:
                    break
            except ValueError:
                continue

    # Extract date
    txn_date = None
    date_pat = r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
    match = re.search(date_pat, text)
    if match:
        txn_date = match.group(1)

    return merchant, amount, txn_date
