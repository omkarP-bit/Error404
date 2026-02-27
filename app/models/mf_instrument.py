"""
app/models/mf_instrument.py
============================
MF_INSTRUMENTS table — mutual fund / investment instrument catalogue.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Float, Date, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import RiskProfile


class MFInstrument(Base):
    __tablename__ = "mf_instruments"

    instrument_id:    Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    fund_category_id: Mapped[int]           = mapped_column(
        ForeignKey("fund_categories.fund_category_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name:             Mapped[str]           = mapped_column(String(255), nullable=False)
    isin:             Mapped[str]           = mapped_column(String(20),  nullable=False, unique=True)
    risk_level:       Mapped[RiskProfile]   = mapped_column(SQLEnum(RiskProfile), nullable=False)
    cagr_1y:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cagr_3y:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cagr_5y:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sip_minimum:      Mapped[float]         = mapped_column(Float, default=500.0)
    nav:              Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nav_date:         Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at:       Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    fund_category:   Mapped["FundCategory"] = relationship("FundCategory", back_populates="instruments")
    recommendations: Mapped[list["MFRecommendation"]] = relationship("MFRecommendation", back_populates="instrument")
    watchlist_entries: Mapped[list["MFWatchlist"]] = relationship("MFWatchlist", back_populates="instrument")

    def __repr__(self) -> str:
        return f"<MFInstrument name={self.name!r} isin={self.isin!r}>"
