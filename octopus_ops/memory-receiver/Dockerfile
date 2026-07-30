FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    OCTOPUS_MEMORY_POOL=/data/memory_pool \
    OCTOPUS_REPLICATION_NONCE_DIR=/data/nonces \
    OCTOPUS_MEMORY_INDEX=/data/index.jsonl \
    OCTOPUS_REPLICATION_MAX_SKEW_SECONDS=300
COPY app.py /app/app.py
VOLUME ["/data"]
EXPOSE 8080
CMD ["python", "/app/app.py"]
