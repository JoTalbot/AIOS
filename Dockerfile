# AIOS production image; application version is defined in VERSION
FROM python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3

ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Установка базовых утилит (curl, sqlite3) для работы healthcheck и БД
RUN apt-get update && apt-get install -y --no-install-recommends curl sqlite3 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./

# Install the exact validated production environment; fail closed on conflicts.
RUN pip install --upgrade pip && \
    pip install -r requirements.lock --extra-index-url https://download.pytorch.org/whl/cpu

COPY . .

RUN chmod +x scripts/*.py scripts/*.sh || true

EXPOSE 8000

CMD ["bash", "scripts/fly_entrypoint.sh"]
