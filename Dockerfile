# Dockerfile для AIOS v22.0.0
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Установка базовых утилит (curl, sqlite3) для работы healthcheck и БД
RUN apt-get update && apt-get install -y --no-install-recommends curl sqlite3 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Установка зависимостей с игнорированием жестких конфликтов
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu || \
    pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu --no-deps

COPY . .

RUN chmod +x scripts/*.py scripts/*.sh || true

EXPOSE 8000

CMD ["bash", "scripts/fly_entrypoint.sh"]
