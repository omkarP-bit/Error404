"""
ai_projection_engine/jobs/nightly_recompute.py
===============================================
Nightly batch job that refreshes all projections for every user in the DB.

Designed to run via cron, Windows Task Scheduler, or a container scheduler.
Can also be triggered manually:
  python jobs/nightly_recompute.py

Schedule recommendation: 00:05 daily (5 minutes after midnight).
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

# ── Path setup (must come before project imports) ────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from server.core.database import SessionLocal, init_projection_tables
from server.services.adaptive_budgeting_service import get_adaptive_budgets
from server.services.confidence_band_service import invalidate_snapshot
from server.services.probabilistic_forecast_service import run_probabilistic_forecast
from server.services.savings_opportunity_service import get_savings_opportunities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [NIGHTLY]  %(levelname)s  %(message)s",
)
logger = logging.getLogger("nightly_recompute")


# ── Job ───────────────────────────────────────────────────────────────────────

def get_all_user_ids() -> List[int]:
    """Fetch all user IDs from the database."""
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT user_id FROM users ORDER BY user_id")).fetchall()
        return [row[0] for row in rows]
    finally:
        db.close()


def recompute_for_user(user_id: int) -> dict:
    """
    Full recompute for one user.
    Returns a summary dict for logging.
    """
    db = SessionLocal()
    try:
        # 1. Invalidate snapshot cache
        invalidate_snapshot(db, user_id)

        # 2. Fresh Monte Carlo forecast
        t0 = time.perf_counter()
        forecast = run_probabilistic_forecast(db, user_id)
        forecast_ms = int((time.perf_counter() - t0) * 1000)

        # 3. Adaptive budgets
        budgets = get_adaptive_budgets(db, user_id)

        # 4. Savings opportunities
        savings = get_savings_opportunities(db, user_id)

        return {
            "user_id": user_id,
            "status": "ok",
            "forecast_ms": forecast_ms,
            "categories": len(budgets),
            "opportunities": len(savings.get("opportunities", [])),
            "depletion_risk": forecast.get("depletion_risk_flag", False),
            "projected_balance_median": (
                forecast.get("projected_balance_at_month_end", {}).get("median")
            ),
        }
    except Exception as exc:
        logger.error("Recompute failed for user %s: %s", user_id, exc)
        return {"user_id": user_id, "status": "error", "error": str(exc)}
    finally:
        db.close()


def run_nightly_job() -> None:
    started_at = datetime.now().isoformat()
    logger.info("=== Nightly recompute started at %s ===", started_at)

    # Ensure tables exist
    init_projection_tables()

    user_ids = get_all_user_ids()
    logger.info("Found %d users to process.", len(user_ids))

    success, failed = 0, 0
    for uid in user_ids:
        result = recompute_for_user(uid)
        if result["status"] == "ok":
            logger.info(
                "✅ user_id=%s  categories=%s  opportunities=%s  "
                "depletion=%s  forecast_ms=%sms",
                result["user_id"],
                result["categories"],
                result["opportunities"],
                result["depletion_risk"],
                result["forecast_ms"],
            )
            success += 1
        else:
            logger.error("❌ user_id=%s  error=%s", result["user_id"], result.get("error"))
            failed += 1

    finished_at = datetime.now().isoformat()
    logger.info(
        "=== Nightly recompute finished at %s — success: %d, failed: %d ===",
        finished_at, success, failed,
    )


if __name__ == "__main__":
    run_nightly_job()
