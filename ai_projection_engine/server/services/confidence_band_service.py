"""
ai_projection_engine/server/services/confidence_band_service.py
===============================================================
Thin caching layer on top of the probabilistic forecast service.

The snapshot is stored in the *forecast_snapshots* table and served
from there when still fresh (within FORECAST_CACHE_TTL_MINUTES).
A forced recompute invalidates the cache.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

from server.core.config import settings
from server.core.database import ForecastSnapshot
from server.services.probabilistic_forecast_service import run_probabilistic_forecast


# ── Public API ─────────────────────────────────────────────────────────────────

def get_or_create_forecast_snapshot(db: Session, user_id: int) -> Dict:
    """
    Return the latest forecast snapshot for *user_id* in the current month.

    Cache logic:
      • If a snapshot exists and is younger than FORECAST_CACHE_TTL_MINUTES → serve it.
      • Otherwise run a full Monte Carlo recompute and store the new snapshot.
    """
    current_month = datetime.now().strftime("%Y-%m")

    existing: ForecastSnapshot | None = (
        db.query(ForecastSnapshot)
        .filter_by(user_id=user_id, month_year=current_month)
        .first()
    )

    if existing:
        age_minutes = (datetime.utcnow() - existing.computed_at).total_seconds() / 60.0
        if age_minutes <= settings.FORECAST_CACHE_TTL_MINUTES:
            return _snapshot_to_dict(existing, from_cache=True)

    # Cache miss or stale → recompute
    forecast = run_probabilistic_forecast(db, user_id)
    snapshot = _upsert_snapshot(db, user_id, current_month, forecast)
    db.commit()
    return _snapshot_to_dict(snapshot, from_cache=False)


def invalidate_snapshot(db: Session, user_id: int) -> None:
    """Delete the cached snapshot for the current month (triggers recompute next call)."""
    current_month = datetime.now().strftime("%Y-%m")
    existing = (
        db.query(ForecastSnapshot)
        .filter_by(user_id=user_id, month_year=current_month)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _upsert_snapshot(
    db: Session,
    user_id: int,
    month_year: str,
    forecast: Dict,
) -> ForecastSnapshot:
    proj_spend = forecast.get("projected_month_spend", {})
    proj_balance = forecast.get("projected_balance_at_month_end", {})
    cat_bd = forecast.get("category_breakdown", {})

    existing = (
        db.query(ForecastSnapshot)
        .filter_by(user_id=user_id, month_year=month_year)
        .first()
    )

    if existing:
        existing.computed_at = datetime.utcnow()
        existing.band_lower_25 = proj_spend.get("lower_p25")
        existing.band_median_50 = proj_spend.get("median_p50")
        existing.band_upper_90 = proj_spend.get("upper_p90")
        existing.balance_lower = proj_balance.get("lower")
        existing.balance_median = proj_balance.get("median")
        existing.balance_upper = proj_balance.get("upper")
        existing.depletion_risk_flag = forecast.get("depletion_risk_flag", False)
        existing.depletion_risk_date = forecast.get("depletion_risk_date")
        existing.category_breakdown = cat_bd
        return existing

    snap = ForecastSnapshot(
        user_id=user_id,
        month_year=month_year,
        computed_at=datetime.utcnow(),
        band_lower_25=proj_spend.get("lower_p25"),
        band_median_50=proj_spend.get("median_p50"),
        band_upper_90=proj_spend.get("upper_p90"),
        balance_lower=proj_balance.get("lower"),
        balance_median=proj_balance.get("median"),
        balance_upper=proj_balance.get("upper"),
        depletion_risk_flag=forecast.get("depletion_risk_flag", False),
        depletion_risk_date=forecast.get("depletion_risk_date"),
    )
    snap.category_breakdown = cat_bd
    db.add(snap)
    return snap


def _snapshot_to_dict(snap: ForecastSnapshot, from_cache: bool = True) -> Dict:
    return {
        "user_id": snap.user_id,
        "month_year": snap.month_year,
        "computed_at": snap.computed_at.isoformat(),
        "from_cache": from_cache,
        "projected_month_spend": {
            "lower_p25": snap.band_lower_25,
            "median_p50": snap.band_median_50,
            "upper_p90": snap.band_upper_90,
        },
        "projected_balance_at_month_end": {
            "lower": snap.balance_lower,
            "median": snap.balance_median,
            "upper": snap.balance_upper,
        },
        "depletion_risk_flag": snap.depletion_risk_flag,
        "depletion_risk_date": snap.depletion_risk_date,
        "category_breakdown": snap.category_breakdown,
    }
