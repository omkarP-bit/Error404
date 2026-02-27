"""
app/services/pdf_service.py
============================
Bank Statement PDF Ingestion using pdfplumber.
"""

import io
import re
from typing import Optional


def extract_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Parse a bank statement PDF and extract transaction rows.
    Returns list of dicts: {date, description, amount, txn_type, raw_row}
    """
    try:
        import pdfplumber

        transactions = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Try table extraction first
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            parsed = _parse_table_row(row)
                            if parsed:
                                parsed["page"] = page_num + 1
                                transactions.append(parsed)
                else:
                    # Fallback: raw text line parsing
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        parsed = _parse_text_line(line)
                        if parsed:
                            parsed["page"] = page_num + 1
                            transactions.append(parsed)

        return transactions if transactions else [{"error": "No transactions found in PDF"}]

    except ImportError:
        return [{"error": "pdfplumber not installed. Run: pip install pdfplumber"}]
    except Exception as exc:
        return [{"error": str(exc)}]


def _parse_table_row(row: list) -> Optional[dict]:
    """Parse a table row into a transaction dict."""
    row_str = " ".join(str(c) for c in row if c)
    if not row_str.strip():
        return None

    amount   = _extract_amount(row_str)
    if amount <= 0:
        return None

    txn_type = "credit" if _is_credit(row_str) else "debit"
    date_str = _extract_date(row_str)
    desc     = _extract_description(row)

    return {
        "date":        date_str,
        "description": desc[:200],
        "amount":      amount,
        "txn_type":    txn_type,
        "raw_row":     row_str[:300],
    }


def _parse_text_line(line: str) -> Optional[dict]:
    """Parse a freeform text line."""
    amount = _extract_amount(line)
    if amount <= 0:
        return None
    return {
        "date":        _extract_date(line),
        "description": line[:200],
        "amount":      amount,
        "txn_type":    "credit" if _is_credit(line) else "debit",
        "raw_row":     line[:300],
    }


def _extract_amount(text: str) -> float:
    patterns = [
        r"₹\s*([0-9,]+\.?[0-9]*)",
        r"Rs\.?\s*([0-9,]+\.?[0-9]*)",
        r"\b([0-9]{2,},[0-9]{3}(?:\.[0-9]{2})?)\b",
        r"\b([0-9]+\.[0-9]{2})\b",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                if val > 1:
                    return val
            except ValueError:
                continue
    return 0.0


def _is_credit(text: str) -> bool:
    credit_keywords = ["cr", "credit", "deposit", "salary", "refund", "interest"]
    return any(kw in text.lower() for kw in credit_keywords)


def _extract_date(text: str) -> Optional[str]:
    match = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text)
    return match.group(1) if match else None


def _extract_description(row: list) -> str:
    """Extract the longest non-numeric cell as description."""
    candidates = [
        str(c) for c in row if c and not str(c).replace(",","").replace(".","").isdigit()
    ]
    return max(candidates, key=len) if candidates else ""
