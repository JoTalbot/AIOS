# AIOS production image; keep this synchronized with VERSION and pyproject.toml.
FROM python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3

ARG AIOS_VERSION=19.9.0
LABEL org.opencontainers.image.title="AIOS" \
      org.opencontainers.image.version="${AIOS_VERSION}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache

WORKDIR /app

# curl is used by operators; sqlite3 is used for database diagnostics.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./

# Pin pip too: an unbounded installer upgrade makes otherwise locked builds drift.
RUN python -m pip install --upgrade pip==26.2.1 setuptools==84.0.0 wheel==0.46.3 \
    && python -m pip install -r requirements.lock \
       --extra-index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --upgrade setuptools==84.0.0 wheel==0.46.3 \
    && python -m pip check

COPY . .

# Debian's built-in unprivileged identity. Runtime state is mounted separately.
USER 65534:65534

EXPOSE 8000

# One foreground workload per container. P2P and commercial jobs are Compose services.
CMD ["python", "run_rest_api.py", "--host", "0.0.0.0", "--port", "8000", "--db", "/app/data/aios.sqlite"]
