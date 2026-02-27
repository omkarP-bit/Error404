"""
app/models/merchant.py
======================
MERCHANTS table — normalised merchant registry with default category.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    # ── Primary Key ───────────────────────────────────────────
    merchant_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Merchant Info ─────────────────────────────────────────
    raw_name: Mapped[str] = mapped_column(String(500), nullable=False)
    clean_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    default_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # ── Relationships ─────────────────────────────────────────
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="merchant"
    )
    category_mappings: Mapped[List["CategoryMapping"]] = relationship(
        "CategoryMapping", back_populates="merchant"
    )

    def __repr__(self) -> str:
        return f"<Merchant id={self.merchant_id} name={self.clean_name!r}>"
