# Dockerfile для AIOS v22.0.0 (Fly.io Deployment)
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для тяжелых ML-библиотек (Torch, Qiskit, ChromaDB)
RUN apt-get update && apt-get install -y \
    gcc g++ build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всего исходного кода
COPY . .

# Права на исполнение скриптов
RUN chmod +x scripts/*.py scripts/*.sh

# Открываем порт для Fly.io HTTP-роутера
EXPOSE 8000

# Точка входа в систему
CMD ["bash", "scripts/fly_entrypoint.sh"]
