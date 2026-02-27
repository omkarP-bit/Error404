"""
app/models/transaction_pattern.py
===================================
TRANSACTION_PATTERNS table — ML-derived behavioural summaries per category.
"""
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TransactionPattern(Base):
    __tablename__ = "transaction_patterns"

    pattern_id:           Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    user_id:              Mapped[int]           = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    category:             Mapped[str]           = mapped_column(String(100), nullable=False)
    avg_amount:           Mapped[float]         = mapped_column(Float, default=0.0)
    std_amount:           Mapped[float]         = mapped_column(Float, default=0.0)
    typical_weekdays:     Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)   # [0,1,4,5,6]
    typical_merchant_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)   # [1,2,3]
    txn_count:            Mapped[int]           = mapped_column(Integer, default=0)
    created_at:           Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    updated_at:           Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<TransactionPattern category={self.category!r} avg={self.avg_amount}>"
