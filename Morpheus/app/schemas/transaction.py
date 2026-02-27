"""
app/schemas/transaction.py
===========================
Pydantic schemas for Transaction API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    user_id:         int
    account_id:      int
    amount:          float = Field(..., gt=0)
    txn_type:        str   = "debit"
    raw_description: str
    payment_mode:    str   = "UPI"


class TransactionOut(BaseModel):
    txn_id:           int
    user_id:          int
    account_id:       int
    merchant_id:      Optional[int]
    # Expose the merchant's raw_name (from MERCHANTS table) so
    # the Flutter client can display the correct merchant label.
    raw_name:         Optional[str] = None
    amount:           float
    txn_type:         str
    category:         Optional[str]
    subcategory:      Optional[str]
    confidence_score: Optional[float]
    user_verified:    bool
    payment_mode:     Optional[str]
    txn_timestamp:    datetime

    model_config = {"from_attributes": True}


class CategoryConfirmRequest(BaseModel):
    txn_id:                int
    corrected_category:    str
    corrected_subcategory: str = ""
    user_id:               Optional[int] = None
