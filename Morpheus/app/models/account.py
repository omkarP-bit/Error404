"""
app/models/account.py
=====================
ACCOUNTS table — financial accounts owned by a user.
"""

from datetime import datetime
from typing import List

from sqlalchemy import String, Float, Enum as SQLEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AccountType


class Account(Base):
    __tablename__ = "accounts"

    # ── Primary Key ───────────────────────────────────────────
    account_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ───────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Account Details ───────────────────────────────────────
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(AccountType), default=AccountType.SAVINGS
    )
    current_balance: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="account"
    )

    def __repr__(self) -> str:
        return (
            f"<Account id={self.account_id} "
            f"type={self.account_type} "
            f"balance={self.current_balance}>"
        )
