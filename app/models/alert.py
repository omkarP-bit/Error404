"""
app/models/alert.py
===================
ALERTS table — system-generated financial alerts for users.
Triggered by anomaly detection or threshold breaches.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AlertType, AlertSeverity, AlertStatus


class Alert(Base):
    __tablename__ = "alerts"

    # ── Primary Key ───────────────────────────────────────────
    alert_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Keys ─────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    txn_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.txn_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Alert Metadata ────────────────────────────────────────
    alert_type: Mapped[AlertType] = mapped_column(
        SQLEnum(AlertType), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity), default=AlertSeverity.MEDIUM
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus), default=AlertStatus.OPEN
    )
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="alerts")
    transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction", back_populates="alerts"
    )

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.alert_id} "
            f"type={self.alert_type} "
            f"severity={self.severity}>"
        )
