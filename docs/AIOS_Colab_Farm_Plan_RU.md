# План расширения AIOS «Colab-Ферма» (Quant ML, LLM Training, RAG, Scraping)

> Документ-план. Кодирование НЕ начато — сначала согласуем этапы.
> Целевое размещение: **VPS `167.233.95.7`, репозиторий `/root/AIOS`**.
> Версия плана: v1.0 · Дата: 2026-08-10

---

## 0. Что уже есть (факт по серверу)

| Компонент | Файл | Статус |
|---|---|---|
| Автозапуск Colab + туннель | `scripts/colab_automation_runner.py` | ✅ работает (CDP 9222, вочдог) |
| Регистрация LLM в балансировщике | `scripts/register_colab_llm.py` | ✅ пишет в `data/.llm_keys.json` + `.env` |
| Регистрация Whisper | `scripts/register_colab_whisper.py` | ✅ |
| LLM-ноутбук (vLLM + Qwen2.5-Coder) | `docs/AIOS_Google_Colab_LLM_Coding.ipynb` | ✅ 4 ячейки |
| Whisper-ноутбук | `docs/AIOS_Google_Colab_Whisper_Transcriber.ipynb` | ✅ |
| Интеграция с LLMBalancer | `aios_core/llm_balancer.py` → `_query_colab_llm()` | ✅ читает `COLAB_LLM_URL` |
| Квант-трейдинг (база) | `aios_core/quant_trading_engine.py`, `swarm_quant_backtester.py` | ✅ есть |
| «Quantum ML» модули | `aios_core/quantum_ml*.py` и др. | ⚠️ есть, требуется ревизия |

**Вывод:** ядро Colab-интеграции уже построено. Новые разделы плана — это **расширение паттерна** «ноутбук → cloudflared → регистрация в AIOS» на новые сценарии.

---

## 1. Архитектурный принцип (единый паттерн)

Все новые модули должны следовать уже принятому в проекте паттерну:

```
[Colab GPU]  ── vLLM/Ollama/Torch  ──►  localhost:8xxx  ──►  cloudflared  ──►  https://*.trycloudflare.com
        ▲                                                                              │
        │  colab_automation_runner.py (Chrome CDP 9222)                               ▼
        └────────────────────────── извлекает URL туннеля ──► register_*.py ──► data/*.json + .env
```

**Ключевые решения, которых нужно придерживаться:**
- Каждый сервис в Colab поднимается на **своём порту** и пробрасывается **своим туннелем** → уникальный URL.
- Регистрация сервиса → отдельный JSON-конфиг + запись в `.env` + точка регистрации в `LLMBalancer` / новом `ColabServiceRegistry`.
- Единый «Activity Keeper» уже реализован в `colab_automation_runner.py` — переиспользуем, не дублируем.
- Все модели скачиваются в Colab (HuggingFace), **на VPS не ставим тяжёлые фреймворки** (только клиенты/инференс).

---

## 2. Этапы реализации

### ЭТАП 1 — Фундамент: единый реестр Colab-сервисов

**Проблема сегодня:** `register_colab_llm.py` знает только один сервис `colab_llm`. Для фермы нужно управлять N сервисами (LLM, Whisper, Quant-ML, Embeddings, RAG, Cluster).

**Артефакты:**
1. `aios_core/colab/colab_registry.py` — единый реестр:
   - CRUD записей сервисов в `data/.colab_services.json` (`{name, kind, base_url, model, status, heartbeat, registered_at}`).
   - `heartbeat`-обновление (сервис жив, если VPS может его пинговать).
   - Health-check: `GET /v1/models`, `GET /health` и т.п.
2. `scripts/register_colab_service.py` — универсальный CLI: `register_colab_service.py <kind> <url> [model]` (заменяет оба старых регистратора, остаётся обратная совместимость).
3. `aios_core/colab/service_discovery.py` — поиск живого сервиса по `kind` для использования из других модулей (LLMBalancer, embeddings, quant engine).
4. Миграция существующих вызовов `register_colab_llm`/`register_colab_whisper` на новый реестр.

**Результат этапа:** один источник правды о всех Colab-сервисах; старые LLM/Whisper продолжат работать.

---

### ЭТАП 2 — Quant ML Engine (раздел 1 плана)

**Цель:** обучение предсказательных моделей + RL-агентов + кластеризации на биржевых данных, без нагрузки на VPS.

**Артефакты:**

1. **Сбор данных (на VPS, лёгкий):**
   - `aios_core/quant/data_collector.py` — сбор тиков/свечей/глубины стакана с 5 бирж:
     - **Binance, Bybit, OKX, Kraken** — публичные REST/WS API (без ключей).
     - **Uniswap V3** — через The Graph / Subgraph API (пулы, ликвидность, swaps).
   - `scripts/run_market_data_collector.py --daemon --interval 300` — фоновый сборчик (по образцу существующих `run_*.py` демонов).
   - Хранение: `data/quant/<SYMBOL>/<EXCHANGE>/` (parquet/csv), ротация и дедупликация.
   - Выгрузка на Colab: датасет упаковывается в `data/quant/export/latest.tar.gz` или публикуется, Colab-ноутбук его качает.

2. **Колаб-ноутбуки обучения (GPU):**
   - `docs/AIOS_Colab_Quant_ML_Training.ipynb`:
     - Фичи: OHLCV, объём, глубина стакана, индикаторы (EMA, RSI, MACD, VWAP), производные.
     - Модели: **XGBoost, LightGBM, CatBoost** (табличные) + **LSTM/Transformer** (последовательности, PyTorch).
     - Кросс-валидация по времени (не рандомная), метрики (MAE, direction accuracy, Sharpe).
     - Сохранение моделей → `model.onnx`/`.joblib` → **облако (HF Hub / R2)**, т.к. VPS их забирает.
   - `docs/AIOS_Colab_Quant_RL_Training.ipynb`:
     - **FinRL / Stable-Baselines3** — среда-симулятор биржи, обучение агента (PPO/DQN) на исторических данных.
     - Валидация на вне-выборке, метрики риск-доходности (Sharpe, max drawdown).
     - Экспорт весов → облако → VPS.
   - `docs/AIOS_Colab_Quant_Clustering.ipynb`:
     - Кластеризация (KMeans/DBSCAN) и детектор аномалий (Isolation Forest / autoencoder) по 24 активам.
     - Корреляционная матрица 24×24, поиск следов маркет-мейкеров по аномальным объёмам.
     - Экспорт профилей кластеров → JSON в облако.

3. **Инференс на VPS (лёгкий):**
   - `aios_core/quant/ml_predictor.py` — подтягивает обученные модели из облака, делает предсказания в реальном времени на данных `data/quant/`.
   - Интеграция с `quant_trading_engine.py` (сигналы от ML-моделей как один из источников).
   - Опционально: `aios_core/colab/quant_ml_inference.py` — если модель можно держать в Colab-сервисе, то запросы идут через туннель.

---

### ЭТАП 3 — LoRA Fine-Tuning персональных моделей (раздел 3)

**Цель:** обучить собственные LoRA-адаптеры (Llama-3.1-8B / Qwen2.5-7B) на базе фриланс-заказов, шаблонах и ответах.

**Артефакты:**
1. `docs/AIOS_Colab_LoRA_FineTune.ipynb` (Unsloth / PEFT):
   - Сборка датасета: `data/lora/<task>/` (Freelancehunt-заказы, шаблоны предложений, коммерческие ответы, юридические договоры).
   - Инструкция-формат (chat template), LoRA (r/lora_alpha/target_modules), Unsloth для скорости на T4.
   - Обучение → слияние → сохранение LoRA-адаптера → публикация в **HF Hub / R2**.
2. `scripts/export_lora_dataset.py` — конвертация сырых данных AIOS в формат датасета.
3. Квантование `docs/AIOS_Colab_GGUF_Quantize.ipynb`:
   - Конвертация слитой модели в **GGUF** (llama.cpp) и/или **AWQ/EXL2**.
   - Оптимизация для инференса на VPS без GPU.
4. Инференс обновлённой модели:
   - Вариант A: поднять в Colab (vLLM/Ollama) через `colab_automation_runner.py` → туннель → реестр → LLMBalancer.
   - Вариант B: сконвертировать в GGUF и запустить `llama.cpp`/Ollama на VPS (Ollama уже есть, порт 11434).

---

### ЭТАП 4 — Векторные базы и RAG (раздел 4)

**Цель:** генерация эмбеддингов для всей базы AIOS (исходники, доки, логи, база знаний) → FAISS/ChromaDB, используемые VPS.

**Артефакты:**
1. `docs/AIOS_Colab_Embeddings_Build.ipynb` (GPU):
   - Модели: **BAAI/bge-m3** и **nomic-embed-text** (оба бесплатные).
   - Чанкинг кода/доков/логов, генерация эмбеддингов большими батчами на GPU.
   - Сохранение векторного индекса → **FAISS** (`.index`) и **ChromaDB** → публикация в облако (R2).
2. `aios_core/rag/index_builder.py` — на VPS: подготовка и экспорт корпуса для Colab (что индексировать: `aios_core/`, `docs/`, README, `data/knowledge/`, `Calls/` и т.д.).
3. `scripts/import_colab_index.py` — загрузка готового индекса из облака в VPS (ChromaDB уже используется: папка `chroma_db/`).
4. Интеграция с RAG-поиском: VPS делает эмбеддинг запроса (лёгкая модель или Colab-эмбеддинг-сервис через туннель) и ищет в импортированном индексе.

---

### ЭТАП 5 — Высокоскоростной парсинг и сбор данных (раздел 5)

**Цель:** гигабитный канал и чистые IP Google для крупного скрапинга без нагрузки на VPS.

**Артефакты:**
1. `docs/AIOS_Colab_Scraper_Farm.ipynb` (Playwright/Selenium):
   - Мониторинг: аирдропы, CryptoPanic, Freelancehunt, DEX-пулы.
   - Парсинг крупных датасетов/архивов/репозиториев.
   - Результаты сохраняются в облако (R2) → VPS забирает.
2. `aios_core/scraping/job_spec.py` — описание задач скрапинга (очередь заданий).
3. `aios_core/scraping/result_ingest.py` — приём/нормализация результатов скрапинга на VPS.
4. `scripts/dispatch_colab_scrape.py` — отправка задания в Colab-ферму и забор результата.

---

### ЭТАП 6 — Colab Multi-Node Cluster (раздел, где сообщение оборвалось)

**Дочитаю/уточню архитектуру. Исходное предложение: «многонодовая схема (Colab Multi-Node Cluster)».**

Концепция:
- Несколько бесплатных Colab-инстансов (каждый = отдельная сессия Chrome CDP) = «ноды».
- Координатор на VPS: `aios_core/colab/cluster.py` — управляет жизненным циклом нод (запуск/остановка/регистрация).
- **Роли нод:** LLM-нода, Whisper-нода, Quant-ML-нода, Embeddings-нода, Scraper-нода.
- **Планировщик задач:** `aios_core/colab/scheduler.py` — распределяет задачи по свободным нодам (очередь, приоритеты, heartbeat).
- **Федерация:** т.к. каждая нода имеет свой trycloudflare-URL, кластер хранит в реестре `service_discovery` карту `kind → [URL1, URL2, ...]` и делает load-balancing/fallback.
- Управление: панель в `dashboard_v3.py` + CLI `aios_cli.py colab ...`.

**Требуется согласование:** какую модель оркестрации предпочитаете — (а) простой «каждой ноде — своя статичная роль», или (б) полный планировщик задач с очередью. См. «Открытые вопросы».

---

## 3. Инфраструктура хранения (облако для обмена с Colab)

Colab и VPS общаются **не напрямую файлами**, а через облако (R2/Drive/HF). Рекомендация:

| Что | Куда | Кто кладёт | Кто забирает |
|---|---|---|---|
| Обученные модели / LoRA / GGUF | R2 или HF Hub | Colab | VPS (инференс) |
| Датасеты | R2 | VPS (сборщик) | Colab (обучение) |
| Векторные индексы (FAISS/Chroma) | R2 | Colab | VPS (RAG) |
| Результаты скрапинга | R2 | Colab | VPS (ingest) |

Уже есть ключи `CLOUDFLARE_R2_*` в `.env` — используем их. Для RAG можно также HF Datasets.

---

## 4. Порядок внедрения (приоритет)

1. **Этап 1** (реестр) — фундамент, без него нельзя ферму. **~0.5–1 день.**
2. **Этап 2** (Quant ML) — самый ценный по вашей формуле «Quant-Tрейдинг + ML». **~2–3 дня.**
3. **Этап 4** (RAG/эмбеддинги) — даёт быстрый выигрыш для всей базы знаний. **~1–2 дня.**
4. **Этап 3** (LoRA) — данные уже частично есть (фриланс). **~2 дня.**
5. **Этап 5** (скрапинг) — отдельно, можно параллельно. **~1–2 дня.**
6. **Этап 6** (мульти-нода) — поверх всего, оркестрация. **~2–3 дня.**

**Итого: ~9–13 рабочих дней** при последовательном выполнении.

---

## 5. Риски и ограничения

- **Бесплатный Colab:** GPU T4 (~16GB VRAM), таймауты сессий (~12ч/одна сессия, до 90 мин простоя). «Вочдог» в `colab_automation_runner.py` уже снижает риск отключения, но **гарантий непрерывности нет** — обучение должно быть чекпоинтировано и возобновляемо.
- **vLLM на 7B в бесплатном Colab:** возможно с `--max-model-len` ограниченным (уже так в ноутбуке). Llama-3.1-8B вплотную к лимиту T4 → для LLM предпочтительны Qwen2.5-7B / модели 7B.
- **TryCloudflare-URL меняется** при каждом перезапуске → реестр должен обновлять URL по heartbeat (заложено в Этап 1).
- **ToS Colab/Google:** интенсивные GPU-нагрузки без подписки могут приводить к ограничениям. Это бизнес-риск, не технический.
- **Безопасность:** туннели публичны → обязательно проверять, что сервисы не светят ключами; закрывать/перезапускать туннели.

---

## 6. Открытые вопросы (нужно ваше решение)

1. **Оркестрация мульти-ноды:** статичные роли нод или полноценный планировщик задач с очередью? (влияет на объём Этапа 6)
2. **Хранилище для моделей/датасетов:** R2 (уже есть ключи) или HF Hub, или Google Drive? 
3. **LLM для LoRA:** какая целевая модель — Llama-3.1-8B или Qwen2.5-7B? И какие домены датасета важнее всего (Freelancehunt, юридические договоры, рефакторинг кода)?
4. **Quant-ML:** сигналы моделей должны быть **консультирующими** (подсказки для человека/существующего движка) или **автоматически торгующими**?
5. **Масштаб:** начинать с одного приоритетного модуля или делать все по порядку?

---

*Это план-черновик. После ваших ответов я зафиксирую этапы, и мы начнём реализацию на VPS в `/root/AIOS`.*

---

## СТАТУС РЕАЛИЗАЦИИ (обновляется)

| Этап | Статус | Созданные артефакты на VPS `/root/AIOS` |
|---|---|---|
| **1. Фундамент (реестр)** | ✅ Выполнен | `aios_core/colab/colab_registry.py`, `service_discovery.py`, `scripts/register_colab_service.py`, `run_colab_heartbeat.py` (systemd `aios-colab-heartbeat.service`), миграция `colab_llm`, интеграция в `colab_automation_runner.py` |
| **2. Quant ML Engine** | ✅ Выполнен | `aios_core/quant/data_collector.py` (4 CEX), `uniswap_v3.py` (DefiLlama), `ml_predictor.py`, `run_market_data_collector.py` (systemd `aios-market-data.service`), `run_quant_ml_inference.py` (systemd `aios-quant-ml-inference.service`), ноутбуки `docs/AIOS_Colab_Quant_ML_Training.ipynb`, `Quant_RL_Training.ipynb`, `Quant_Clustering.ipynb`, `scripts/import_colab_models.py`. Демон собрал 24 актива × 4 биржи; CatBoost обучена (acc≈0.575), сигналы по 24 активам в `data/quant/ml_signals.json` |
| **3. LoRA Fine-Tuning** | ✅ Выполнен | `docs/AIOS_Colab_LoRA_FineTune.ipynb` (Unsloth), `docs/AIOS_Colab_GGUF_Quantize.ipynb`, `scripts/export_lora_dataset.py` (собран `data/finetune/lora_commercial.jsonl`, 124 примера). Существующие датасеты `aios_coder_hf.jsonl`, `Modelfile` переиспользованы |
| **4. RAG/Эмбеддинги** | ✅ Выполнен | `aios_core/rag/index_builder.py` (корпус: 3332 док. / 6011 чанков), `embeddings_store.py` (ChromaDB-поиск, протестирован), `scripts/import_colab_index.py`, `build_local_embedding_index.py`, `docs/AIOS_Colab_Embeddings_Build.ipynb`. Полный индекс строится на VPS (ONNX) |
| **5. Скрапинг** | ✅ Выполнен | `aios_core/scraping/job_spec.py`, `result_ingest.py`, `scripts/dispatch_colab_scrape.py` (create/run), `docs/AIOS_Colab_Scraper_Farm.ipynb`. Локальный скрапер (Playwright) протестирован, результат ингестится в RAG |
| **6. Multi-Node Cluster** | ✅ Выполнен | `aios_core/colab/cluster.py` (регистрация нод по ролям), `scheduler.py` (планировщик задач по нодам). Тест: quant_ml→node-1, scraper→node-2, embeddings ждёт ноду |

### Открытые вопросы — принятые решения по умолчанию
- **Оркестрация мульти-ноды:** начать со статичных ролей нод, задел под планировщик задач.
- **Хранилище моделей/датасетов:** R2 (ключи есть) + опционально HF Hub.
- **LLM для LoRA:** Qwen2.5-7B, датасет — Freelancehunt-заказы + коммерческие ответы.
- **Quant-ML сигналы:** консультирующие (не автоторговля).
- **Uniswap V3:** legacy The Graph subgraph выключен → данные через DefiLlama API (бесплатно, без ключей).
