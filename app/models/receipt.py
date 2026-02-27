"""
app/models/receipt.py
=====================
RECEIPTS table — OCR-extracted receipt data linked to transactions.
"""
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Float, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id:      Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    txn_id:          Mapped[int]           = mapped_column(
        ForeignKey("transactions.txn_id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    extracted_items: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    total_amount:    Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    amount_matched:  Mapped[bool]          = mapped_column(Boolean, default=False)
    ocr_confidence:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at:      Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    transaction: Mapped["Transaction"] = relationship("Transaction")

    def __repr__(self) -> str:
        return f"<Receipt id={self.receipt_id} matched={self.amount_matched}>"
