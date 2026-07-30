# Dockerfile для AIOS v22.0.0 (Fly.io Deployment - Ultimate Lightweight Version)
FROM python:3.11-slim

# Отключаем буферизацию вывода Python
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Копируем только requirements.txt для начала
COPY requirements.txt .

# Устанавливаем зависимости из готовых бинарников (.whl).
# Мы не ставим C++ компиляторы (gcc) через apt, так как используем --only-binary для критичных пакетов.
# Качаем легкий CPU-only PyTorch.
RUN pip install --upgrade pip && \
    pip install -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Копируем исходный код
COPY . .

# Права на запуск
RUN chmod +x scripts/*.py scripts/*.sh || true

# Порт
EXPOSE 8000

# Запуск
CMD ["bash", "scripts/fly_entrypoint.sh"]
