"""
ai_projection_engine/server/core/database.py
============================================
Database connectivity for the Projection Engine.

READ-ONLY access to existing core tables:
  users, transactions, accounts, goals

NEW tables created here (never modifies existing schema):
  forecast_snapshots, adaptive_budgets, savings_opportunities, behavior_profiles
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings


# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    """Enable foreign-keys + WAL for every new SQLite connection."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


# ── Declarative Base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All NEW projection tables inherit from this base."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# NEW OPTIONAL TABLES  (read about them in NEW_TABLES.md)
# ══════════════════════════════════════════════════════════════════════════════

class ForecastSnapshot(Base):
    """
    Stores the latest Monte Carlo forecast result per user per calendar month.
    Acts as a cache so repeat API calls are fast.
    """
    __tablename__ = "forecast_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    month_year = Column(String(7), nullable=False)        # e.g. "2026-02"
    computed_at = Column(DateTime, default=datetime.utcnow)

    # ── Projected month-end spend confidence bands ─────────────
    band_lower_25 = Column(Float, nullable=True)            # P25
    band_median_50 = Column(Float, nullable=True)           # P50
    band_upper_90 = Column(Float, nullable=True)            # P90

    # ── Projected end-of-month account balance ─────────────────
    balance_lower = Column(Float, nullable=True)
    balance_median = Column(Float, nullable=True)
    balance_upper = Column(Float, nullable=True)

    # ── Depletion risk ─────────────────────────────────────────
    depletion_risk_flag = Column(Boolean, default=False)
    depletion_risk_date = Column(String(20), nullable=True)

    # ── Per-category breakdown (stored as JSON text) ───────────
    _category_breakdown_raw = Column("category_breakdown", Text, nullable=True)

    @property
    def category_breakdown(self):
        if self._category_breakdown_raw:
            return json.loads(self._category_breakdown_raw)
        return {}

    @category_breakdown.setter
    def category_breakdown(self, value):
        self._category_breakdown_raw = json.dumps(value) if value else None

    __table_args__ = (
        UniqueConstraint("user_id", "month_year", name="uq_forecast_user_month"),
    )


class AdaptiveBudget(Base):
    """
    Stores computed adaptive budget per user, category, and calendar month.
    Updated on every recompute / nightly job.
    """
    __tablename__ = "adaptive_budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(String(100), nullable=False)
    month_year = Column(String(7), nullable=False)

    # Formula inputs
    median_spend_3m = Column(Float, nullable=True)
    ema_30d = Column(Float, nullable=True)
    current_month_pace = Column(Float, nullable=True)

    # Formula output
    adaptive_budget = Column(Float, nullable=False)

    # Actual vs budget tracking
    actual_spend_so_far = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "category", "month_year",
            name="uq_adaptive_user_cat_month",
        ),
    )


class SavingsOpportunity(Base):
    """
    Stores counterfactual savings simulations per discretionary category.
    Updated on every recompute / nightly job.
    """
    __tablename__ = "savings_opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(String(100), nullable=False)
    month_year = Column(String(7), nullable=False)
    is_discretionary = Column(Boolean, default=True)

    current_spend = Column(Float, nullable=False)

    # Amount saved at each reduction scenario
    saving_5pct = Column(Float, nullable=True)
    saving_10pct = Column(Float, nullable=True)
    saving_15pct = Column(Float, nullable=True)
    saving_20pct = Column(Float, nullable=True)

    # Projected balance improvement at each scenario
    balance_impact_5pct = Column(Float, nullable=True)
    balance_impact_10pct = Column(Float, nullable=True)
    balance_impact_15pct = Column(Float, nullable=True)
    balance_impact_20pct = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "category", "month_year",
            name="uq_savings_user_cat_month",
        ),
    )


class BehaviorProfile(Base):
    """
    Aggregated spending behaviour metrics per user.
    One row per user, overwritten on every nightly recompute.
    """
    __tablename__ = "behavior_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)

    avg_daily_spend = Column(Float, nullable=True)
    mid_month_burn_rate = Column(Float, nullable=True)
    spend_volatility = Column(Float, nullable=True)
    discretionary_ratio = Column(Float, nullable=True)
    fixed_ratio = Column(Float, nullable=True)
    weekend_spending_multiplier = Column(Float, nullable=True)
    recurring_expense_count = Column(Integer, default=0)
    data_days_available = Column(Integer, default=0)

    computed_at = Column(DateTime, default=datetime.utcnow)


# ── Session Factory ────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a scoped session and guarantees cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_projection_tables() -> None:
    """
    Create all new projection tables if they do not already exist.
    Safe to call on every startup — does NOT modify existing tables.
    """
    Base.metadata.create_all(bind=engine)
