"""
app/models/audit_log.py
=======================
AUDIT_LOGS table — immutable event trail for every state change.
Stores old/new JSON snapshots for full auditability.
"""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ActorType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    # ── Primary Key ───────────────────────────────────────────
    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Actor ─────────────────────────────────────────────────
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_type: Mapped[ActorType] = mapped_column(
        SQLEnum(ActorType), default=ActorType.USER
    )

    # ── Action ────────────────────────────────────────────────
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── State Snapshot ────────────────────────────────────────
    old_value: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # ── Relationships ─────────────────────────────────────────
    actor: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs",
        foreign_keys=[actor_id],
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.log_id} "
            f"action={self.action!r} "
            f"resource={self.resource_type}/{self.resource_id}>"
        )
