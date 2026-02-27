"""
app/models/user.py
==================
USERS table — core identity and profile.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Float, Enum as SQLEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IncomeType, RiskProfile, KYCStatus


class User(Base):
    __tablename__ = "users"

    # ── Primary Key ───────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Identity ──────────────────────────────────────────────
    auth_uid: Mapped[str] = mapped_column(
        String(36),
        default=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Financial Profile ─────────────────────────────────────
    monthly_income: Mapped[float] = mapped_column(Float, default=0.0)
    income_type: Mapped[IncomeType] = mapped_column(
        SQLEnum(IncomeType), default=IncomeType.SALARIED
    )
    risk_profile: Mapped[RiskProfile] = mapped_column(
        SQLEnum(RiskProfile), default=RiskProfile.MODERATE
    )
    kyc_status: Mapped[KYCStatus] = mapped_column(
        SQLEnum(KYCStatus), default=KYCStatus.PENDING
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────
    accounts: Mapped[List["Account"]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user"
    )
    category_mappings: Mapped[List["CategoryMapping"]] = relationship(
        "CategoryMapping", back_populates="user", cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="user"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="actor",
        foreign_keys="[AuditLog.actor_id]",
    )
    goals: Mapped[List["Goal"]] = relationship(
        "Goal", back_populates="user", cascade="all, delete-orphan"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.user_id} name={self.name!r}>"
