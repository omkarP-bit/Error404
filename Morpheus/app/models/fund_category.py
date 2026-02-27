"""
app/models/fund_category.py
============================
FUND_CATEGORIES table — mutual fund / investment category registry.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class FundCategory(Base):
    __tablename__ = "fund_categories"

    fund_category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name:             Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description:      Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at:       Mapped[datetime] = mapped_column(DateTime, default=func.now())

    instruments: Mapped[List["MFInstrument"]] = relationship(
        "MFInstrument", back_populates="fund_category"
    )

    def __repr__(self) -> str:
        return f"<FundCategory name={self.name!r}>"
