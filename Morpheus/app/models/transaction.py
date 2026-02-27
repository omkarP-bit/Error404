"""
app/models/transaction.py
=========================
TRANSACTIONS table — the core financial event record.
Indexed on: user_id, txn_timestamp, merchant_id, category, amount.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Float,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TxnType


class Transaction(Base):
    __tablename__ = "transactions"

    # ── Primary Key ───────────────────────────────────────────
    txn_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Keys ─────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False
    )
    merchant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("merchants.merchant_id", ondelete="SET NULL"), nullable=True
    )

    # ── Financial Data ────────────────────────────────────────
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    txn_type: Mapped[TxnType] = mapped_column(
        SQLEnum(TxnType), default=TxnType.DEBIT, nullable=False
    )

    # ── Categorisation ────────────────────────────────────────
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    payment_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ── Status ────────────────────────────────────────────────
    user_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    balance_after_txn: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    txn_timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    merchant: Mapped[Optional["Merchant"]] = relationship(
        "Merchant", back_populates="transactions"
    )
    feedback: Mapped[Optional["UserFeedback"]] = relationship(
        "UserFeedback", back_populates="transaction", uselist=False
    )
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="transaction")

    # ── Composite Indexes ─────────────────────────────────────
    __table_args__ = (
        Index("ix_txn_user_id", "user_id"),
        Index("ix_txn_timestamp", "txn_timestamp"),
        Index("ix_txn_merchant_id", "merchant_id"),
        Index("ix_txn_category", "category"),
        Index("ix_txn_amount", "amount"),
        Index("ix_txn_user_ts", "user_id", "txn_timestamp"),
    )

    # Convenience attribute for API responses — exposes the linked
    # merchant's raw_name so clients don't need a separate join.
    @property
    def raw_name(self) -> Optional[str]:  # type: ignore[override]
        merchant = getattr(self, "merchant", None)
        return getattr(merchant, "raw_name", None) if merchant is not None else None

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.txn_id} "
            f"amount={self.amount} "
            f"category={self.category!r}>"
        )
