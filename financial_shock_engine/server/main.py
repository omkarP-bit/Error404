"""
financial_shock_engine/server/main.py
======================================
FastAPI application entry-point for the Financial Shock Absorption Engine.
Runs on port 8002. Shares the same SQLite DB as the main app.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# ── sys.path: ensure project root is importable ───────────────────────────────
_ENGINE_ROOT = Path(__file__).resolve().parent.parent
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from configs import settings
from configs.database import ping_db
from server.routes.shock_routes import router as shock_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-5s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Financial Shock Absorption Engine",
    description=(
        "AI-driven microservice that calculates how much unexpected expense "
        "a user can safely absorb without breaking savings goals or causing balance depletion."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Templates ─────────────────────────────────────────────────────────────────
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(shock_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui")


@app.get("/ui", include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health", tags=["Health"])
def health():
    db_ok = ping_db()
    return JSONResponse({
        "status": "ok" if db_ok else "degraded",
        "db_ok":  db_ok,
        "version": "1.0.0",
        "port": settings.PORT,
    })


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    logger.info("⚡ Financial Shock Absorption Engine starting on port %d", settings.PORT)
    if ping_db():
        logger.info("✅ Database connection verified.")
    else:
        logger.warning("⚠️  Database ping failed — check DATABASE_URL.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
