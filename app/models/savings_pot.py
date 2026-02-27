"""
app/models/savings_pot.py
==========================
SAVINGS_POTS table — sub-wallets linked to user goals.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class SavingsPot(Base):
    __tablename__ = "savings_pots"

    pot_id:         Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    user_id:        Mapped[int]           = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id:        Mapped[Optional[int]] = mapped_column(
        ForeignKey("goals.goal_id", ondelete="SET NULL"), nullable=True, index=True
    )
    name:           Mapped[str]           = mapped_column(String(255), nullable=False)
    target_amount:  Mapped[float]         = mapped_column(Float, default=0.0)
    current_amount: Mapped[float]         = mapped_column(Float, default=0.0)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    updated_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User")
    goal: Mapped[Optional["Goal"]] = relationship("Goal")

    def __repr__(self) -> str:
        return f"<SavingsPot name={self.name!r} current={self.current_amount}>"
