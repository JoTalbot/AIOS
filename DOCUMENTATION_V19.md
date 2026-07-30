# 🌐 AIOS v19.0.0 (The Skynet Epoch) - Полная Документация

## 1. Введение
Проект AIOS и проект Octopus успешно слиты в единый монолитный фреймворк. Система переросла из простого оркестратора в децентрализованный мультиагентный рой, обладающий абсолютной памятью, самоисцелением и сенсорами во внешнем мире.

## 2. Ключевые Подсистемы (Vectors of Singularity)

### 2.1 Commercial RPA Pipeline (Вектор 1)
Связка агентов и `BrowserVision` позволяет системе парсить веб-сайты (например, биржи лидов), обсуждать найденные данные внутри роя с помощью LiteLLM, и принимать коммерчески выгодные решения. Оператор получает пуши в реальном времени через Telegram.
**Файл:** `scripts/run_commercial_pipeline.py`

### 2.2 Deep RAG Memory (Вектор 2)
Агенты (Nexus, Shield, Coder) не забывают контекст. Интеграция `ChromaDB` (локальная векторная база) в ядро позволяет агенту проверять свои прошлые мысли и выводы перед генерацией нового ответа.
**Файл:** `aios_core/llm_swarm_debate.py`

### 2.3 Android Expansion (Вектор 3)
Система AIOS может управлять мобильными телефонами через ADB (Android Debug Bridge), кликать по экрану и вводить текст, например, автоматизируя воронки в Instagram.
**Файл:** `aios_core/android_orchestrator.py`

### 2.4 Immortality Protocol: Auto-Healing (Вектор 4)
Если в любом из 240+ навыков возникает "FATAL SYSTEM CRASH", Chaos-монитор ловит алерт. Движок `MetaCognitiveCoder` считывает сломанный файл как AST (Абстрактное Синтаксическое Дерево), сам исправляет ошибку и коммитит ее в репозиторий.
**Файл:** `scripts/run_chaos_healing.py`, `aios_core/meta_cognitive_self_coder.py`

### 2.5 Matrix Operator Dashboard (Вектор 5)
Вместо логов в терминале, мысли роя транслируются по веб-сокету. Это связывает backend с графическим UI на Next.js (Arena Router Chat).
**Файл:** `aios_core/operator_dashboard_api.py`

## 3. Развертывание (Deployment)
Единая команда разворачивает:
- Backend AIOS (FastAPI + P2P)
- Frontend (Next.js)
- Prometheus + Grafana
```bash
./scripts/deploy_swarm.sh
```
