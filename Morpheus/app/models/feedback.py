"""
app/models/feedback.py
======================
USER_FEEDBACK table — user corrections to ML categorisations.
Creates or updates a CATEGORY_MAPPINGS record via analytics engine.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FeedbackSource


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    # ── Primary Key ───────────────────────────────────────────
    feedback_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ───────────────────────────────────────────
    txn_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.txn_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one feedback per transaction
        index=True,
    )

    # ── Corrected Labels ──────────────────────────────────────
    corrected_category: Mapped[str] = mapped_column(String(100), nullable=False)
    corrected_subcategory: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # ── Metadata ──────────────────────────────────────────────
    source: Mapped[FeedbackSource] = mapped_column(
        SQLEnum(FeedbackSource), default=FeedbackSource.USER_UI
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # ── Relationships ─────────────────────────────────────────
    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="feedback"
    )

    def __repr__(self) -> str:
        return (
            f"<UserFeedback id={self.feedback_id} "
            f"category={self.corrected_category!r}>"
        )
