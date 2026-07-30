# Dockerfile для AIOS v22.0.0 (Fly.io Deployment)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .

# Установка зависимостей с игнорированием жестких конфликтов
# Используем CPU-версию PyTorch для избежания OOM
# Если pip падает из-за ResolutionImpossible, ставим пакеты без строгих проверок версий
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu || \
    pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu --no-deps

COPY . .

RUN chmod +x scripts/*.py scripts/*.sh || true

EXPOSE 8000

CMD ["bash", "scripts/fly_entrypoint.sh"]
