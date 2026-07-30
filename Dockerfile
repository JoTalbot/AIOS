# Dockerfile для AIOS v22.0.0 (Fly.io Deployment)
FROM python:3.11-slim

# Отключаем интерактивные диалоги apt и буферизацию вывода Python
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Установка системных зависимостей (только необходимое)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    curl \
    cmake \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Сначала копируем только requirements, чтобы кэшировать слой установки
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости.
# Важно: указываем extra-index-url для скачивания CPU-версии PyTorch, 
# что экономит ~2.5 ГБ места и спасает Fly.io Builder от зависания (OOM).
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Копирование всего исходного кода
COPY . .

# Права на исполнение скриптов
RUN chmod +x scripts/*.py scripts/*.sh || true

# Открываем порт для Fly.io HTTP-роутера
EXPOSE 8000

# Точка входа в систему
CMD ["bash", "scripts/fly_entrypoint.sh"]
