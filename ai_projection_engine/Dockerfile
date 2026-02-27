# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Adaptive Financial Projection & Savings Insight Engine
# Multi-stage build: slim production image (~200 MB)
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (needed for scipy wheel)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Production ───────────────────────────────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="Morpheus Finance Team"
LABEL description="Adaptive Financial Projection & Savings Insight Engine"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source code
COPY server/ ./server/
COPY llm/    ./llm/
COPY jobs/   ./jobs/
COPY models/ ./models/

# ── Environment defaults (override at runtime) ────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8001 \
    HOST=0.0.0.0 \
    # Point to mounted DB volume in production:
    DATABASE_URL=sqlite:////data/finance.db \
    MISTRAL_USE_LOCAL=False \
    MISTRAL_API_KEY="" \
    FORECAST_CACHE_TTL_MINUTES=60

# ── Volume for persistent SQLite DB ──────────────────────────────────────────
VOLUME ["/data"]

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health').raise_for_status()"

CMD ["python", "-m", "uvicorn", "server.main:app", \
     "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
