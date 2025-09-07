# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# System deps (tzdata is useful for logs); keep image slim
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*

# Copy requirement spec first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (excluding via .dockerignore)
COPY ctt_viewer/ ctt_viewer/
COPY parser/ parser/
COPY static/ static/
COPY font/ font/
COPY app.py README.md ./

# Default env (can be overridden)
ENV HOST=0.0.0.0 \
    PORT=5001 \
    ENABLE_COMPRESSION=1

# Data directory is mounted at runtime
VOLUME ["/app/data"]

EXPOSE 5001

# Run via module entry; no extra gunicorn dependency required
CMD ["python", "-m", "ctt_viewer"]

