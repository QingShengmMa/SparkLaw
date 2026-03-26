# =============================================================
# SparkLaw — Backend Dockerfile
# Multi-stage build · python:3.11-slim · non-root user
# =============================================================

# ── Stage 1: dependency builder ──────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build-time system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ───────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="SparkLaw Backend"
LABEL org.opencontainers.image.description="Chinese Legal AI Backend — FastAPI + LangGraph"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd --gid 1001 sparklaw \
    && useradd --uid 1001 --gid sparklaw --shell /bin/bash --create-home sparklaw

# Copy application source
COPY app/ ./app/
COPY app/main.py ./main.py 2>/dev/null || true

# Create directories and set ownership
RUN mkdir -p logs data && chown -R sparklaw:sparklaw /app

USER sparklaw

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
