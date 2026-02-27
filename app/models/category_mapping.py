"""
app/models/category_mapping.py
================================
CATEGORY_MAPPINGS table — per-user merchant→category overrides.
Used by the categorisation model as the highest-priority lookup.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MappingSource


class CategoryMapping(Base):
    __tablename__ = "category_mappings"

    # ── Primary Key ───────────────────────────────────────────
    mapping_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Keys ─────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    merchant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("merchants.merchant_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ── Category Override ─────────────────────────────────────
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # ── Source ────────────────────────────────────────────────
    source: Mapped[MappingSource] = mapped_column(
        SQLEnum(MappingSource), default=MappingSource.USER
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="category_mappings")
    merchant: Mapped[Optional["Merchant"]] = relationship(
        "Merchant", back_populates="category_mappings"
    )

    def __repr__(self) -> str:
        return (
            f"<CategoryMapping id={self.mapping_id} "
            f"category={self.category!r} "
            f"confidence={self.confidence:.2f}>"
        )
