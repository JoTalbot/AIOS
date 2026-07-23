# AIOS Production Dockerfile — multi-stage build (v9.3.1)
# Final image: ~150MB vs ~400MB single-stage

# ------------------------------------------------------------------
# Stage 1: build dependencies
# ------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt pyproject.toml ./

# Install build deps, compile everything into a wheel cache
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt && \
    pip wheel --no-cache-dir --wheel-dir=/wheels gunicorn

# ------------------------------------------------------------------
# Stage 2: minimal runtime
# ------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Only curl + sqlite3 (no build-essential = −200MB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl sqlite3 && \
    rm -rf /var/lib/apt/lists/* && apt-get clean

WORKDIR /app

# Copy pre-built wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl && \
    rm -rf /wheels

# Copy only what the runtime needs
COPY aios_core/ ./aios_core/
COPY aios_mcp/ ./aios_mcp/
COPY aios_cli/ ./aios_cli/
COPY sdk/ ./sdk/
COPY platforms/ ./platforms/
COPY docs/ ./docs/
COPY policies/ ./policies/
COPY constitution/ ./constitution/
COPY deploy/ ./deploy/
COPY tools/ ./tools/
COPY aios_cli.py aios_cli_admin.py demo.py monitor.py ./
COPY run_*.py ./
COPY Makefile ./
COPY ai*_config.yaml* ./
COPY .env.example 2>/dev/null || true
COPY VERSION ROADMAP_NEXT.md EXECUTIVE_SUMMARY.md ./

# Create non-root user + required directories
RUN useradd -m -u 1000 aios && \
    mkdir -p /app/logs /app/data /app/backups /app/export && \
    chown -R aios:aios /app

# Health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

EXPOSE 8000 8080 8471

USER aios
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Default: REST API
CMD ["gunicorn", "run_rest_api:app", "--bind", "0.0.0.0:8000", \
     "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-logfile", "-", "--error-logfile", "-"]
