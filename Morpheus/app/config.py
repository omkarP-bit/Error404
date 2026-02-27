"""
app/config.py
=============
Central configuration using Pydantic-Settings.
Reads from environment variables / .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # ── App Identity ─────────────────────────────────────────
    APP_NAME: str = "Personal Finance Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/finance.db"

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY: str = "super-secret-key-change-in-production-2024"

    # ── ML / Data Paths ───────────────────────────────────────
    DATASET_PATH: str = str(BASE_DIR / "data" / "finance_ml_dataset.csv")
    MODEL_SAVE_DIR: str = str(BASE_DIR / "ml_models")

    # ── ML Thresholds ─────────────────────────────────────────
    CONFIDENCE_THRESHOLD: float = 0.85         # Below this → ask user
    ANOMALY_CONTAMINATION: float = 0.05        # ~5% anomalies expected
    ANOMALY_ALERT_THRESHOLD: float = -0.1      # IsolationForest score cut-off

    # ── OCR ──────────────────────────────────────────────────
    TESSERACT_CMD: str = "tesseract"

    # ── Pagination ────────────────────────────────────────────
    PAGE_SIZE: int = 20

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Singleton settings instance
settings = Settings()

# Ensure data and model directories exist at import time
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "ml_models" / "categorization_model" / "artifacts").mkdir(
    parents=True, exist_ok=True
)
(BASE_DIR / "ml_models" / "anomaly_detection_model" / "artifacts").mkdir(
    parents=True, exist_ok=True
)
(BASE_DIR / "ml_models" / "goal_feasibility_model" / "artifacts").mkdir(
    parents=True, exist_ok=True
)
(BASE_DIR / "ml_models" / "investment_readiness_model" / "artifacts").mkdir(
    parents=True, exist_ok=True
)
