"""
ai_projection_engine/server/core/config.py
==========================================
Central configuration for the Adaptive Financial Projection Engine.
All settings are loaded from environment variables or a local .env file.
No dependency on the main project's config.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Path Resolution ────────────────────────────────────────────────────────────
# server/core/config.py  →  ../../.. = ai_projection_engine/
ENGINE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# Main project root: e:/Morpheus/
PROJECT_ROOT: Path = ENGINE_DIR.parent


class Settings(BaseSettings):
    # ── App Identity ─────────────────────────────────────────────────────────
    APP_NAME: str = "Adaptive Financial Projection & Savings Insight Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # ── Database ──────────────────────────────────────────────────────────────
    # Points to the main project's finance.db (read existing tables).
    # Override via PROJECTION_DB_URL env var for Docker / remote setups.
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT}/data/finance.db"

    # ── Monte Carlo Simulation ────────────────────────────────────────────────
    MC_SIMULATIONS: int = 1000          # Number of simulation paths
    MC_REMAINING_DAYS_CAP: int = 31     # Safety cap for remaining days

    # ── Mistral LLM ────────────────────────────────────────────────────────────
    MISTRAL_API_KEY: str = ""                                    # Cloud API key
    MISTRAL_MODEL: str = "mistral-small-latest"                  # Cloud model
    MISTRAL_USE_LOCAL: bool = False                              # True → Ollama
    MISTRAL_LOCAL_URL: str = "http://localhost:11434"            # Ollama endpoint
    MISTRAL_LOCAL_MODEL: str = "mistral"                         # Ollama model name

    # ── Forecast Caching ──────────────────────────────────────────────────────
    FORECAST_CACHE_TTL_MINUTES: int = 60   # Re-use snapshot if younger than this

    # ── Historical Data Thresholds ────────────────────────────────────────────
    MIN_DAYS_FOR_ML_MODEL: int = 30        # Fall back to heuristic if < 30 days
    LOOKBACK_MONTHS: int = 6              # Months of history to analyse

    # ── Outlier Detection ─────────────────────────────────────────────────────
    ANOMALY_IQR_MULTIPLIER: float = 2.0   # IQR fence multiplier
    OUTLIER_WEIGHT: float = 0.25          # Down-weight outliers by this factor

    # ── Savings Engine ────────────────────────────────────────────────────────
    MAX_REDUCTION_PCT: float = 25.0       # Never suggest more than 25% cut

    model_config = SettingsConfigDict(
        env_file=str(ENGINE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
