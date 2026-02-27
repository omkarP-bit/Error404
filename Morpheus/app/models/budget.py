"""
app/models/budget.py
====================
BUDGETS table — per-user category spending limits.
3 budget profiles per user as per spec.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BudgetPeriod


class Budget(Base):
    __tablename__ = "budgets"

    # ── Primary Key ───────────────────────────────────────────
    budget_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ───────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Budget Details ────────────────────────────────────────
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    limit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    spent_amount: Mapped[float] = mapped_column(Float, default=0.0)
    period: Mapped[BudgetPeriod] = mapped_column(
        SQLEnum(BudgetPeriod), default=BudgetPeriod.MONTHLY
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="budgets")

    @property
    def utilisation_pct(self) -> float:
        if self.limit_amount == 0:
            return 0.0
        return round(min(self.spent_amount / self.limit_amount * 100, 999), 2)

    def __repr__(self) -> str:
        return (
            f"<Budget id={self.budget_id} "
            f"category={self.category!r} "
            f"limit={self.limit_amount}>"
        )
