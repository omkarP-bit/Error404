"""
financial_shock_engine/configs/settings.py
==========================================
Central configuration — reads from .env in project root.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "FSE_DATABASE_URL",
    os.getenv("DATABASE_URL", f"sqlite:///{_ROOT.parent}/data/finance.db"),
)

# ── Server ────────────────────────────────────────────────────────────────────
HOST: str = os.getenv("FSE_HOST", "0.0.0.0")
PORT: int = int(os.getenv("FSE_PORT", "8002"))
DEBUG: bool = os.getenv("FSE_DEBUG", "True").lower() == "true"

# ── LLM ───────────────────────────────────────────────────────────────────────
MISTRAL_USE_LOCAL: bool = os.getenv("MISTRAL_USE_LOCAL", "True").lower() == "true"
MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_LOCAL_URL: str = os.getenv("MISTRAL_LOCAL_URL", "http://localhost:11434")
MISTRAL_LOCAL_MODEL: str = os.getenv("MISTRAL_LOCAL_MODEL", "mistral:latest")
MISTRAL_TIMEOUT: float = float(os.getenv("MISTRAL_TIMEOUT", "90"))

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS: int = int(os.getenv("FSE_CACHE_TTL", "900"))   # 15 min

# ── Simulation ────────────────────────────────────────────────────────────────
MONTE_CARLO_SIMULATIONS: int = int(os.getenv("FSE_MC_SIMS", "1000"))
SAFETY_BUFFER_RATIO: float = float(os.getenv("FSE_SAFETY_BUFFER", "0.30"))
MAX_SAVINGS_SUGGESTION_RATIO: float = float(os.getenv("FSE_MAX_SAVINGS_RATIO", "0.30"))

# ── Financial Thresholds ──────────────────────────────────────────────────────
MIN_DATA_MONTHS: int = 2          # minimum months of txn history for full model
FALLBACK_HEURISTIC_MONTHS: int = 1  # fallback if sparse data

# ── Discretionary Categories (used for savings capping) ──────────────────────
DISCRETIONARY_CATEGORIES: list[str] = [
    "Food & Dining",
    "Shopping",
    "Entertainment",
    "Travel",
    "Groceries",
]

FIXED_CATEGORIES: list[str] = [
    "Rent",
    "Utilities",
    "Healthcare",
    "Transport",
    "Finance",
    "Investments",
]
