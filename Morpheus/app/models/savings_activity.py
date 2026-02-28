"""
app/models/savings_activity.py
==============================
Tracks monthly SIP/savings activity for streak & momentum calculation.
"""

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SavingsActivity(Base):
    __tablename__ = "savings_activity"

    # ── Primary Key ───────────────────────────────────────────
    activity_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ───────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Activity Data ─────────────────────────────────────────
    month_key: Mapped[str] = mapped_column(
        String(7),  # Format: "YYYY-MM"
        nullable=False,
        index=True,
    )
    contributed: Mapped[int] = mapped_column(Integer, default=0)  # 1 if any contribution, 0 if none
    missed: Mapped[int] = mapped_column(Integer, default=0)  # 1 if missed payment
    total_sip_amount: Mapped[float] = mapped_column(Float, default=0.0)  # Total SIP amount in month

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<SavingsActivity id={self.activity_id} "
            f"user={self.user_id} "
            f"month={self.month_key} "
            f"contributed={self.contributed}>"
        )
