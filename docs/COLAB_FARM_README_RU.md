# AIOS Colab Farm — Документация

Ферма бесплатных GPU-сессий Google Colab, интегрированная с AIOS на VPS.
Позволяет обучать ML-модели, LoRA-адаптеры, строить RAG-индексы и скрапить
данные **без нагрузки на основной сервер**, используя бесплатные GPU T4.

---

## Архитектура

```
┌────────────────────────────  VPS  (167.233.95.7)  ────────────────────────────┐
│                                                                              │
│  aios_colab_cli.py  ── единое управление всей фермой                          │
│        │                                                                     │
│        ├── aios_core/colab/          ── реестр сервисов + кластер + планировщик│
│        ├── aios_core/quant/          ── сбор данных 5 бирж + ML-инференс       │
│        ├── aios_core/rag/            ── индекс эмбеддингов (ChromaDB)          │
│        ├── aios_core/scraping/       ── задания и приём результатов скрапинга  │
│        └── run_*.py  (systemd-демоны) ── heartbeat, сбор данных, ML-инференс   │
│                                                                              │
│  data/.colab_services.json  ── реестр живых Colab-сервисов (URL туннелей)      │
│  data/quant/                ── рыночные данные + модели + сигналы              │
│  data/rag/corpus.jsonl      ── корпус для эмбеддингов                         │
│  chroma_db/                 ── векторный индекс                               │
└──────────────────────────────────────────────────────────────────────────────┘
        ▲                                                                     ▲
        │ cloudflared-туннель (trycloudflare)                                  │ модели/индексы
        ▼                                                                     ▼
┌──────────────────────────  Google Colab (T4 GPU)  ──────────────────────────┐
│  docs/AIOS_Colab_*.ipynb  — ноутбуки обучения/построения                    │
│  colab_automation_runner.py — авто-запуск ноутбука + вочдог активности      │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Принцип:** ноутбук поднимает сервис на локальном порту → cloudflared даёт
публичный URL → VPS регистрирует его в реестре → сервис доступен AIOS
(LLM-балансировщик, RAG, ML-инференс).

---

## Быстрый старт

### Управление фермой (CLI)
```bash
cd /root/AIOS
/opt/aios/.venv/bin/python aios_colab_cli.py status                 # сводка
/opt/aios/.venv/bin/python aios_colab_cli.py services list          # сервисы
/opt/aios/.venv/bin/python aios_colab_cli.py nodes list             # ноды кластера
/opt/aios/.venv/bin/python aios_colab_cli.py rag search "запрос"    # RAG-поиск
/opt/aios/.venv/bin/python aios_colab_cli.py rag ask "вопрос"       # RAG + локальная LLM (Ollama)
/opt/aios/.venv/bin/python aios_colab_cli.py ml signal              # ML-сигналы
/opt/aios/.venv/bin/python aios_colab_cli.py ml momentum            # топ-моментум (консультирующие)
/opt/aios/.venv/bin/python aios_colab_cli.py data collect --symbols BTC ETH
```

### Демоны (systemd, уже запущены)
| Сервис | Назначение |
|---|---|
| `aios-colab-heartbeat` | мониторинг живых Colab-сервисов |
| `aios-market-data` | сбор OHLCV/стаканов с 5 бирж (каждые 15 мин) |
| `aios-quant-ml-inference` | ML-прогноз направления по активам (каждые 10 мин) |

---

## Этапы и артефакты

### 1. Реестр Colab-сервисов
`aios_core/colab/` — `colab_registry.py`, `service_discovery.py`, `cluster.py`, `scheduler.py`
`scripts/register_colab_service.py` — регистрация сервиса
```bash
python scripts/register_colab_service.py register quant_ml https://abc.trycloudflare.com
```

### 2. Quant ML Engine
`aios_core/quant/` — сбор данных + инференс. Ноутбуки:
- `docs/AIOS_Colab_Quant_ML_Training.ipynb` — XGBoost/LightGBM/CatBoost/LSTM
- `docs/AIOS_Colab_Quant_RL_Training.ipynb` — RL-агент (Stable-Baselines3)
- `docs/AIOS_Colab_Quant_Clustering.ipynb` — кластеризация/аномалии 24 активов

Перенос обученных моделей на VPS:
```bash
python scripts/import_colab_models.py --src <папка моделей> --extract
```

### 3. LoRA Fine-Tuning
- `docs/AIOS_Colab_LoRA_FineTune.ipynb` — Unsloth, Qwen2.5-7B / Llama-3.1-8B
- `docs/AIOS_Colab_GGUF_Quantize.ipynb` — GGUF/AWQ
- `scripts/export_lora_dataset.py` — сбор датасета (`data/finetune/lora_commercial.jsonl`)

### 4. RAG и эмбеддинги
- `aios_core/rag/index_builder.py` — построение корпуса (`data/rag/corpus.jsonl`)
- `aios_core/rag/embeddings_store.py` — ChromaDB-поиск
- `docs/AIOS_Colab_Embeddings_Build.ipynb` — эмбеддинги на GPU (bge-m3/nomic)
- `scripts/import_colab_index.py` — импорт индекса из Colab

Построение локального индекса (ONNX, CPU):
```bash
python scripts/build_local_embedding_index.py --chunk-size 200
```

### 5. Скрапинг
- `aios_core/scraping/job_spec.py`, `result_ingest.py`
- `scripts/dispatch_colab_scrape.py` — создать/выполнить задание
- `docs/AIOS_Colab_Scraper_Farm.ipynb` — скрапинг с чистых IP Google

### 6. Multi-Node Cluster
`aios_core/colab/cluster.py`, `scheduler.py` — ноды по ролям + планировщик задач.

---

## Запуск ноутбука в Colab автоматически

```bash
# LLM-ноутбук
COLAB_SERVICE_KIND=llm /opt/aios/.venv/bin/python scripts/colab_automation_runner.py
# Scraper-ноутбук
COLAB_SERVICE_KIND=scraper COLAB_NODE_ID=colab-node-1 \
  /opt/aios/.venv/bin/python scripts/colab_automation_runner.py
```

Ноутбук выбирается по `COLAB_SERVICE_KIND` (см. `NOTEBOOK_MAP` в runner).
Туннель регистрируется в реестре автоматически.

---

## Безопасность
- `.env`, `data/.llm_keys.json`, `data/.colab_services.json`, `chroma_db/`,
  `data/quant`, `data/rag` — в `.gitignore`, не коммитятся.
- ML-сигналы **консультирующие** — автоторговля отключена.
- Туннели trycloudflare публичны — не выводить секреты в логи сервисов.
