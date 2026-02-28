"""
app/models/goal.py
==================
GOALS table — user financial goals with progress tracking.
Not in core ER diagram but required by seed data spec (5 goals/user).
"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Float, Integer, Date, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import GoalStatus


class Goal(Base):
    __tablename__ = "goals"

    # ── Primary Key ───────────────────────────────────────────
    goal_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ───────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Goal Details ──────────────────────────────────────────
    goal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1=High 2=Med 3=Low
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0.0)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    monthly_contribution: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[GoalStatus] = mapped_column(
        SQLEnum(GoalStatus), default=GoalStatus.ACTIVE
    )
    # ── ML Outputs ────────────────────────────────────────────
    feasibility_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feasibility_note: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    health_tag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="goals")

    @property
    def progress_pct(self) -> float:
        if self.target_amount == 0:
            return 0.0
        return round(min(self.current_amount / self.target_amount * 100, 100), 2)

    def __repr__(self) -> str:
        return (
            f"<Goal id={self.goal_id} "
            f"name={self.goal_name!r} "
            f"progress={self.progress_pct}%>"
        )
