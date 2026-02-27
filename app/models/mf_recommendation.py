"""
app/models/mf_recommendation.py
=================================
MF_RECOMMENDATIONS table — personalised fund recommendations per user.
"""
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MFRecommendation(Base):
    __tablename__ = "mf_recommendations"

    recommendation_id:  Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    user_id:            Mapped[int]           = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id:      Mapped[int]           = mapped_column(
        ForeignKey("mf_instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating_id:          Mapped[Optional[int]] = mapped_column(
        ForeignKey("financial_health_ratings.rating_id", ondelete="SET NULL"), nullable=True
    )
    expected_cagr_low:  Mapped[float]         = mapped_column(Float, nullable=False)
    expected_cagr_high: Mapped[float]         = mapped_column(Float, nullable=False)
    reason:             Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    hard_gates_snapshot:Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at:         Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    user:       Mapped["User"]                         = relationship("User")
    instrument: Mapped["MFInstrument"]                 = relationship("MFInstrument", back_populates="recommendations")
    rating:     Mapped[Optional["FinancialHealthRating"]] = relationship("FinancialHealthRating", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<MFRecommendation user={self.user_id} instrument={self.instrument_id}>"
