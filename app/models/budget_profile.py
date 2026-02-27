"""
app/models/budget_profile.py
=============================
BUDGET_PROFILES table — single per-user holistic budget profile.
Tracks income allocation ratios and surplus estimates.
"""
from datetime import datetime
from sqlalchemy import Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BudgetProfile(Base):
    __tablename__ = "budget_profiles"

    profile_id:            Mapped[int]   = mapped_column(primary_key=True, autoincrement=True)
    user_id:               Mapped[int]   = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    needs_ratio:           Mapped[float] = mapped_column(Float, default=0.50)
    wants_ratio:           Mapped[float] = mapped_column(Float, default=0.30)
    savings_ratio:         Mapped[float] = mapped_column(Float, default=0.20)
    baseline_expense:      Mapped[float] = mapped_column(Float, default=0.0)
    expense_volatility:    Mapped[float] = mapped_column(Float, default=0.0)
    avg_monthly_surplus:   Mapped[float] = mapped_column(Float, default=0.0)
    safe_investable_amount:Mapped[float] = mapped_column(Float, default=0.0)
    created_at:            Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at:            Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (f"<BudgetProfile user={self.user_id} "
                f"needs={self.needs_ratio} wants={self.wants_ratio} savings={self.savings_ratio}>")
