"""
ai_projection_engine/server/main.py
====================================
FastAPI application entry point for the Adaptive Financial Projection Engine.

Standalone microservice — no imports from the main Morpheus project.
Exposes:
  GET  /forecast/{user_id}
  GET  /forecast/{user_id}/fresh
  GET  /forecast/{user_id}/adaptive-budgets
  GET  /savings-opportunities/{user_id}
  GET  /insights/{user_id}
  POST /recompute/{user_id}

Runs on port 8001 by default (configurable via PORT env var).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pathlib import Path

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

from config import settings
from database import get_db, init_projection_tables
from forecast_routes import router as forecast_router
from insights_routes import router as insights_router
from savings_routes import router as savings_router
from transaction_routes import router as transaction_router
from shock_routes import router as shock_router
from adaptive_budgeting_service import get_adaptive_budgets
from confidence_band_service import invalidate_snapshot
from probabilistic_forecast_service import run_probabilistic_forecast
from savings_opportunity_service import get_savings_opportunities

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create new DB tables on startup, cleanup on shutdown."""
    logger.info("⚙  Initialising projection tables …")
    init_projection_tables()
    logger.info("✅ Projection tables ready.")
    yield
    logger.info("🔌 Projection engine shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Standalone AI microservice for adaptive budgeting, probabilistic "
        "expenditure forecasting, confidence bands, savings opportunity detection, "
        "and Mistral LLM-powered plain-English financial insights."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS (Flutter mobile app friendly) ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ──────────────────────────────────────────────────────────
app.include_router(forecast_router)
app.include_router(savings_router)
app.include_router(insights_router)
app.include_router(transaction_router)
app.include_router(shock_router)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="Root — redirect to API docs", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"], summary="Service health check")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/ui", response_class=HTMLResponse, tags=["UI"], summary="Interactive test dashboard", include_in_schema=False)
def ui_dashboard(request: Request):
    return _templates.TemplateResponse("dashboard.html", {"request": request})


# ── Recompute Endpoint ────────────────────────────────────────────────────────

@app.post(
    "/recompute/{user_id}",
    tags=["Recompute"],
    summary="Trigger full projection recompute for a user",
    response_description=(
        "Recomputes adaptive budgets, forecast, and savings opportunities "
        "for the given user. Invalidates any existing snapshot cache."
    ),
)
def recompute(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Force-recomputes all projections for *user_id*:
    1. Invalidates cached forecast snapshot.
    2. Re-runs Monte Carlo forecast.
    3. Recalculates adaptive budgets.
    4. Refreshes savings opportunity matrix.

    Call this endpoint after:
    - A bulk transaction import
    - Manual transaction correction
    - Account balance update
    """
    try:
        invalidate_snapshot(db, user_id)
        forecast = run_probabilistic_forecast(db, user_id)
        budgets = get_adaptive_budgets(db, user_id)
        savings = get_savings_opportunities(db, user_id)

        return {
            "status": "success",
            "user_id": user_id,
            "message": "Projections recomputed successfully.",
            "summary": {
                "forecast_month": forecast.get("month_year"),
                "categories_budgeted": len(budgets),
                "savings_opportunities_found": len(savings.get("opportunities", [])),
                "depletion_risk": forecast.get("depletion_risk_flag", False),
                "projected_balance_median": (
                    forecast.get("projected_balance_at_month_end", {}).get("median")
                ),
            },
        }
    except Exception as exc:
        logger.exception("Recompute failed for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


# ── Exception Handler ─────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):  # noqa: ANN001
    logger.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": str(exc)},
    )


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
