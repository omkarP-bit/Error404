"""
app/models/financial_health_rating.py
======================================
FINANCIAL_HEALTH_RATINGS table — periodic financial health snapshots with chained history.
"""
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class FinancialHealthRating(Base):
    __tablename__ = "financial_health_ratings"

    rating_id:        Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    user_id:          Mapped[int]           = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    score:            Mapped[float]         = mapped_column(Float, nullable=False)
    rating_label:     Mapped[str]           = mapped_column(String(50), nullable=False)   # Excellent/Good/Fair/Poor
    prev_rating_id:   Mapped[Optional[int]] = mapped_column(
        ForeignKey("financial_health_ratings.rating_id", ondelete="SET NULL"), nullable=True
    )
    rating_delta:     Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    improvement_tips: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    window_months:    Mapped[int]           = mapped_column(Integer, default=3)
    created_at:       Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    user:        Mapped["User"] = relationship("User")
    prev_rating: Mapped[Optional["FinancialHealthRating"]] = relationship(
        "FinancialHealthRating", remote_side="FinancialHealthRating.rating_id"
    )
    recommendations: Mapped[list["MFRecommendation"]] = relationship(
        "MFRecommendation", back_populates="rating"
    )

    def __repr__(self) -> str:
        return f"<FinancialHealthRating id={self.rating_id} score={self.score} label={self.rating_label!r}>"
