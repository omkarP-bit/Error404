"""
app/main.py
===========
FastAPI application entry point.

Registers all routers, mounts static files, and wires up templates.
On startup: creates DB tables and (optionally) runs seed if DB is empty.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup."""
    Base.metadata.create_all(bind=engine)
    print(f"✅  Database tables ready — {settings.DATABASE_URL}")
    yield
    print("👋  Application shutting down")


# ── App Instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = "Personal Finance Manager with AI Insights — Hackathon Edition",
    lifespan    = lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ── Static Files ──────────────────────────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Templates ─────────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routers import dashboard, categorization, anomaly, goal, investment, transactions

app.include_router(dashboard.router)
app.include_router(dashboard.api_router)
app.include_router(categorization.router)
app.include_router(categorization.api_router)
app.include_router(anomaly.router)
app.include_router(anomaly.api_router)
app.include_router(goal.router)
app.include_router(goal.api_router)
app.include_router(investment.router)
app.include_router(investment.api_router)
app.include_router(transactions.router)


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status":  "ok",
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
