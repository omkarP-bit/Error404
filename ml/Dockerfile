# Optimized multi-stage build
FROM python:3.11-slim as deps
WORKDIR /app

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt \
    && find /root/.local -name '*.pyc' -delete \
    && find /root/.local -name '__pycache__' -delete

FROM python:3.11-slim as runner
WORKDIR /app

# Copy installed packages
COPY --from=deps /root/.local /root/.local

# Copy application code
COPY src/ ./src/

# Set environment
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["python", "src/api/main.py"]
