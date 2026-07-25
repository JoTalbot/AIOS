FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl sqlite3 build-essential &&     rm -rf /var/lib/apt/lists/* && apt-get clean

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir -r requirements.txt gunicorn

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
COPY Makefile VERSION ./
COPY .env.example ./
COPY ROADMAP_NEXT.md EXECUTIVE_SUMMARY.md ./

RUN useradd -m -u 1000 aios &&     mkdir -p /app/logs /app/data /app/backups /app/export &&     chown -R aios:aios /app

EXPOSE 8000 8080 8471
USER aios
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

CMD ["gunicorn", "run_rest_api:app", "--bind", "0.0.0.0:8000",      "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker",      "--access-logfile", "-", "--error-logfile", "-"]
