"""
app/models/ml_model_run.py
===========================
ML_MODEL_RUNS table — records every ML inference for auditability and retraining.
"""
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MLModelRun(Base):
    __tablename__ = "ml_model_runs"

    run_id:          Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    txn_id:          Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.txn_id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_name:      Mapped[str]           = mapped_column(String(100), nullable=False)
    model_version:   Mapped[str]           = mapped_column(String(50),  nullable=False)
    input_text:      Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top5_categories: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    latency_ms:      Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at:      Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")

    def __repr__(self) -> str:
        return f"<MLModelRun model={self.model_name!r} confidence={self.confidence}>"
