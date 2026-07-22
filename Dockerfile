# AIOS — Production Dockerfile (v9.1.0 - fixed healthcheck & deps)
FROM python:3.12-slim

WORKDIR /app

# System dependencies + curl for healthcheck, sqlite3 for debugging
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for caching
COPY requirements.txt .
COPY pyproject.toml .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy the entire project
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 aios && \
    mkdir -p /app/logs /app/data && \
    chown -R aios:aios /app

# Create .env example if missing
RUN if [ ! -f .env.example ]; then echo "AIOS_API_KEYS={\"local\":{\"subject\":\"local\",\"roles\":[\"admin\"]}}" > .env.example; fi

# Expose ports: 8000 REST, 8471 MCP, 8080 Dashboard, 9090 Metrics
EXPOSE 8000 8471 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: run REST API
USER aios
CMD ["python", "run_rest_api.py", "--host", "0.0.0.0", "--port", "8000", "--db", "./aios.sqlite"]
