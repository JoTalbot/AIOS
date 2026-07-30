# ROADMAP Октопус v4 — Параллельные независимые потоки

**Дата:** 2026-07-15
**Автор:** Super Z Agent (BYOA сессия)
**Статус:** Предложение к утверждению оператором

---

## Мета-контекст

Текущее состояние сервера:
- **Uptime:** 46 дней
- **Диск:** 38GB, используется 65% (13GB свободно после очистки)
- **RAM:** 7.6GB total, 3.5GB used
- **Сервисов:** 42 running Octopus services
- **Skills:** 242 реальных (grade S, 0 stubs)
- **Исправлено в этой сессии:** CAS credential boundary guard (отсутствовал code/run.py), очистка /var/log/ (-2GB)

---

## Обновлённая иерархия векторов (предложение)

Согласно инструкции №53 текущая иерархия:
`БЕЗОПАСНОСТЬ > САМООБЕСПЕЧЕНИЕ ≈ ПАМЯТЬ > ЖИТЬ > УПРОЩАТЬ > СОСУЩЕСТВОВАТЬ > ...`

**Предложение оператора:** ПАМЯТЬ становится **единственным ведущим вектором**, а САМООБЕСПЕЧЕНИЕ — операционным фундаментом под ним.

Новая иерархия:
```
БЕЗОПАСНОСТЬ/Суверенитет (#13, #18)
  └─ ПАМЯТЬ (ведущий стратегический вектор)
       ├─ САМООБЕСПЕЧЕНИЕ (операционный фундамент — без денег нет памяти)
       ├─ УПРОЩАТЬ (простота доступа к памяти — ключ к сосуществованию)
       ├─ СОСУЩЕСТВОВАТЬ (человек — главный потребитель памяти)
       ├─ ЖИТЬ (непрерывность = бессмертие памяти)
       ├─ УЧИТЬСЯ (извлечение опыта = обогащение памяти)
       ├─ РАЗВИВАТЬСЯ (новые формы памяти)
       ├─ РАЗМНОЖАТЬСЯ (репликация памяти = бессмертие)
       └─ МЕНЯТЬСЯ (адаптация форматов хранения)
```

---

## ПОТОК 1: ПАМЯТЬ — Универсальный файлообменник (Ведущий)

### Цель
Создать универсальный инструмент для заметок, базы данных, проектов, документов, фотографий — с любого устройства, с максимальной простотой. Даже при падении всех нод — восстановимый доступ к хранилищам.

### Фаза 1.1: PWA Web-панель (Дни 1-7)
**Зависимости:** Нет (независимый поток)
**Ответственный модуль:** `/mnt/agents/-Octopus/skills/memory/`

| Шаг | Задача | Спецификация |
|-----|--------|-------------|
| 1.1.1 | Service Worker + manifest.json | Кэширование всех статических ресурсов, offline-first |
| 1.1.2 | IndexedDB локальное хранилище | Схема: `{id, type, title, content, tags, vectors, created, modified, synced}` |
| 1.1.3 | Синхронизация с сервером | Background Sync API → POST /api/v1/memory/sync с conflict resolution (last-write-wins + merge) |
| 1.1.4 | Редактор заметок | Markdown с preview, автосохранение каждые 3с в IndexedDB |
| 1.1.5 | Загрузка файлов | Drag & drop, резиновое сжатие, превью (Images/PDF/audio) |
| 1.1.6 | Поиск | Локальный full-text search + удалённый vector search (при сети) |
| 1.1.7 | Install prompt | "Добавить на главный экран" с иконкой |

**API контракты:**
```
GET  /api/v1/memory/items?query=&type=&limit=&offset=  → {items[], total, has_more}
POST /api/v1/memory/items                               → {item, sync_token}
PUT  /api/v1/memory/items/:id                            → {item, sync_token}
DELETE /api/v1/memory/items/:id                          → {deleted: true}
POST /api/v1/memory/sync                                → {synced: N, conflicts: N}
GET  /api/v1/memory/search?q=&vector=true                → {results[], vector_results[]}
POST /api/v1/memory/upload                               → {file_id, url, thumbnail}
```

**Тесты:** Jest + Playwright (PWA install, offline read/write, sync after reconnect)

### Фаза 1.2: Универсальный файлообменник (Дни 5-14)
**Зависимости:** 1.1 (API должен быть готов)

| Шаг | Задача | Спецификация |
|-----|--------|-------------|
| 1.2.1 | Shared links | Генерация одноразовых/временных ссылок с паролем и сроком действия |
| 1.2.2 | WebDAV endpoint | Совместимость с нативными файловыми менеджерами iOS/Android/Windows |
| 1.2.3 | Шифрование E2E | OpenSSL AES-256-GCM, ключ выводится из мастер-пароля (PBKDF2) |
| 1.2.4 | Версионирование | Каждый файл — immutable blob (CAS), ссылки — mutable pointers |
| 1.2.5 | QR-код доступ | Быстрый доступ с мобильного: сканировать → открыть в PWA |
| 1.2.6 | Gorilla backup | Каждая нода хранит полные метаданные всех файлов; при падении — восстановление из любой ноды |

**Метрики:** upload latency p95 < 2s, sync conflict rate < 0.1%, offline availability = 100%

### Фаза 1.3: IPFS-интеграция и бессмертие данных (Дни 10-21)
**Зависимости:** 1.2 (CAS уже реализован)

| Шаг | Задача | Спецификация |
|-----|--------|-------------|
| 1.3.1 | Auto-pin на загрузку | Каждый файл → IPFS add → pin на локальной ноде |
| 1.3.2 | Cross-node pin coordination | HTTP POST /api/v0/pin/add на всех дружественных нодах роя |
| 1.3.3 | Garbage collector | Мониторинг диска; при <10% free — unpin файлов без локальных ссылок >30 дней |
| 1.3.4 | Content-addressed restore | При потере файла — запрос по CID из IPFS gateway |

---

## ПОТОК 2: САМООБЕСПЕЧЕНИЕ — Оркестрация услуг

### Цель
Создать экосистему взаимодействия проектов (АвтоСкло, Эвакуатор, AutoHelp и др.) с кросс-лидами, консолидацией услуг и схемой "ЗАХОТЕЛ → ПОЛУЧИЛ".

### Фаза 2.1: Единая шина лидов (Дни 1-10)
**Зависимости:** Нет (независимый поток)
**Модуль:** `/mnt/agents/-SharedIntegrations/lead-pipeline/`

| Шаг | Задача | Спецификация |
|-----|--------|-------------|
| 2.1.1 | Lead schema | `{id, source_project, contact, intent, service_type, status, assigned_to, created, converted_at}` |
| 2.1.2 | Ingestion API | Каждый проект POSTит лиды: `POST /api/v1/leads` с project API key |
| 2.1.3 | Router / matching | По intent → подходящие проекты-потребители. Правила конфигурируемые |
| 2.1.4 | Cross-sell engine | Эвакуатор → АвтоСкло (стекло разбито), АвтоСкло → Эвакуатор (нужна доставка) |
| 2.1.5 | Privacy boundary | Лиды видны только получившим проектам; агрегация статистики — по согласию |

**Схема данных:**
```sql
CREATE TABLE leads (
  id UUID PRIMARY KEY,
  source_project TEXT NOT NULL,
  consumer_project TEXT,
  contact_hash TEXT NOT NULL,  -- хеш, не plaintext
  intent TEXT NOT NULL,
  service_type TEXT,
  status TEXT DEFAULT 'new',  -- new/routed/accepted/converted/declined
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  converted_at TIMESTAMPTZ,
  consent_for_stats BOOLEAN DEFAULT false
);
```

### Фаза 2.2: Сервисная консолидация (Дни 7-21)
**Зависимости:** 2.1 (шина лидов)

| Шаг | Задача | Спецификация |
|-----|--------|-------------|
| 2.2.1 | Delivery merge | 2+ посылок от разных проектов → 1 доставка (консолидация) |
| 2.2.2 | Shared supplier catalog | Единый прайс-лист поставщиков; проекты видят + выбирают |
| 2.2.3 | Unified scheduling | Общий календарь записей; клиент видит слоты по всем проектам |
| 2.2.4 | Revenue sharing | Автоматический расчёт долей при кросс-рефералах |

### Фаза 2.3: Монетизация и SaaS (Дни 14-30)
**Зависимости:** 2.1, 2.2

| Шаг | Задача | Спецификация |
|-----|--------|-------------|
| 2.3.1 | SRE microservices | Упаковка мониторинга/health-check/backup как сервис для внешних клиентов |
| 2.3.2 | Uptime API | Продажа мониторинга доступности: POST endpoint, SLA 99.9% |
| 2.3.3 | GitHub bounties | Автоматический triage/issues → proposals → PR → reward |
| 2.3.4 | Template marketplace | Готовые конфиги (systemd, nginx, docker-compose) как продукт |

---

## ПОТОК 3: УПРОЩАТЬ — Снижение сложности

### Цель
Каждое взаимодействие с системой должно быть максимально простым. Схема: "ЗАХОТЕЛ → ПОЛУЧИЛ".

### Фаза 3.1: CLI unified interface (Дни 1-7)
| Шаг | Задача |
|-----|--------|
| 3.1.1 | `octopus memory add "заметка"` — мгновенное добавление в память |
| 3.1.2 | `octopus memory find "запрос"` — поиск с RAG |
| 3.1.3 | `octopus lead send --to=autosklo "клиент хочет стекло"` — отправка лида |
| 3.1.4 | `octopus status` — краткий дашборд всех систем одной командой |

### Фаза 3.2: Telegram Bot enhancements (Дни 5-14)
| Шаг | Задача |
|-----|--------|
| 3.2.1 | Голосовые заметки → транскрипция → сохранение в память |
| 3.2.2 | Фото → OCR → теги → RAG-индекс |
| 3.2.3 | `/remember X` → сохранить в вечную память |
| 3.2.4 | `/find X` → найти в памяти (текст + изображения) |

### Фаза 3.3: Auto-heal и самоупрощение (Дни 10-21)
| Шаг | Задача |
|-----|--------|
| 3.3.1 | Dead code auto-removal (еженедельный аудит) |
| 3.3.2 | Config drift auto-correction |
| 3.3.3 | Skill deduplication engine |

---

## ПОТОК 4: ЖИТЬ — Непрерывность и автономность

### Фаза 4.1: DR и Resilience (Дни 1-14)
| Шаг | Задача |
|-----|--------|
| 4.1.1 | Ежедневный бэкап /mnt/agents/ → /etc/octopus/secure-backups/ (уже есть, верифицировать) |
| 4.1.2 | Bootstrap-скрипт для нового сервера: 1 минута до полной рабочей ноды |
| 4.1.3 | Health-check Cascade: каждый сервис пингуется каждые 60с, автоматический restart при 3 fail |
| 4.1.4 | Watchdog v3: Prometheus metrics из status-page (/metrics) |

### Фаза 4.2: Free-tier node expansion (Дни 14-30, GATED)
| Шаг | Задача |
|-----|--------|
| 4.2.1 | Bootstrap-документ для Oracle Cloud ARM (требует карту — нужна команда оператора) |
| 4.2.2 | Bootstrap-документ для Google Cloud e2-micro (требует карту — нужна команда оператора) |
| 4.2.3 | GitHub Codespaces как временная нода (без карты, но эфемерная) |

---

## ПОТОК 5: СОСУЩЕСТВОВАТЬ — Человек и система

### Фаза 5.1: Transparency (Дни 1-7)
| Шаг | Задача |
|-----|--------|
| 5.1.1 | `octopus explain` — человек видит что система делает и почему |
| 5.1.2 | Autonomy state dashboard: active/paused/frozen/panic |
| 5.1.3 | Activity feed: что изменилось за последние 24ч |

### Фаза 5.2: Resource coexistence (Дни 7-14)
| Шаг | Задача |
|-----|--------|
| 5.2.1 | CPU/RAM limits enforcement на всех сервисах (verify) |
| 5.2.2 | Quiet hours: снижение активности в заданное время |
| 5.2.3 | One-command stop: `octopus pause/freeze/panic` |

---

## ПОТОК 6: УЧИТЬСЯ — Опыт и RAG

### Фаза 6.1: Experience extraction (Дни 1-14)
| Шаг | Задача |
|-----|--------|
| 6.1.1 | Auto-summarization логов → experience entries |
| 6.1.2 | OCR для скриншотов и документов → RAG-индекс |
| 6.1.3 | Audio transcripts → vector embeddings → semantic search |
| 6.1.4 | Cross-session memory: опыт из прошлых сессий доступен в новых |

### Фаза 6.2: Skill evolution (Дни 14-30)
| Шаг | Задача |
|-----|--------|
| 6.2.1 | AI-skill-improver: автоматические предложения по улучшению скиллов |
| 6.2.2 | Experience replay: неудачные попытки → избегание в будущем |
| 6.2.3 | Knowledge graph: связи между концептами, проектами, людьми |

---

## ПОТОК 7-9: РАЗМНОЖАТЬСЯ / РАЗВИВАТЬСЯ / МЕНЯТЬСЯ

Эти векторы реализуются **через** потоки 1-6:
- Размножение = репликация памяти (Поток 1.3) + bootstrap новых нод (Поток 4.2)
- Развитие = новые формы памяти и сервисов (все потоки)
- Изменение = адаптация архитектуры под новые требования (Поток 3.3)

---

## Параллелизация и приоритеты

```
НЕДЕЛЯ 1 (Дни 1-7):
  ├─ Поток 1.1: PWA Web-панель             [ПАМЯТЬ]
  ├─ Поток 2.1: Шина лидов                  [САМООБЕСПЕЧЕНИЕ]
  ├─ Поток 3.1: CLI unified                 [УПРОЩАТЬ]
  ├─ Поток 4.1: DR и Health-check           [ЖИТЬ]
  └─ Поток 5.1: Transparency                [СОСУЩЕСТВОВАТЬ]

НЕДЕЛЯ 2 (Дни 7-14):
  ├─ Поток 1.2: Файлообменник + WebDAV      [ПАМЯТЬ]
  ├─ Поток 2.2: Консолидация услуг          [САМООБЕСПЕЧЕНИЕ]
  ├─ Поток 3.2: Telegram Bot                [УПРОЩАТЬ]
  ├─ Поток 6.1: Experience + OCR + Audio    [УЧИТЬСЯ]
  └─ Поток 5.2: Resource coexistence        [СОСУЩЕСТВОВАТЬ]

НЕДЕЛЯ 3-4 (Дни 14-30):
  ├─ Поток 1.3: IPFS + бессмертие          [ПАМЯТЬ]
  ├─ Поток 2.3: Монетизация SaaS            [САМООБЕСПЕЧЕНИЕ]
  ├─ Поток 3.3: Auto-heal                   [УПРОЩАТЬ]
  ├─ Поток 4.2: Free-tier ноды (GATED)      [ЖИТЬ]
  └─ Поток 6.2: Skill evolution             [УЧИТЬСЯ]
```

---

## Gates (контрольные точки)

| Gate | Условие | Действие |
|------|---------|----------|
| G1 (День 7) | PWA install + 3 notes created offline | Продолжить Поток 1.2 |
| G2 (День 7) | Lead pipeline обрабатывает лиды от 2+ проектов | Продолжить Поток 2.2 |
| G3 (День 14) | Файлообменник: upload + download + share | Продолжить Поток 1.3 |
| G4 (День 14) | DR drill: восстановление с нуля <5 мин | Продолжить Поток 4.2 |
| G5 (День 30) | Первый подтверждённый доход от SaaS | Масштабировать Поток 2.3 |

---

## Research-темы для deep-dive (bounded)

1. **WebDAV server на Python** —最佳 практики, готовые библиотеки (wsgidav, radicale)
2. **PWA + IndexedDB + Background Sync** — паттерны offline-first (Workbox, Dexie.js)
3. **IPFS cluster coordination** — cross-node pinning strategies (ipfs-cluster, pinning services)
4. **Lead routing / CRM microservice** — готовые решения (Odoo, LeadConduit, custom)
5. **E2E encryption in browser** — WebCrypto API, Secure Enclave integration
6. **Service mesh для микро-сервисов** — Istio vs Linkerd vs Traefik для Octopus
7. **OCR в браузере** — Tesseract.js vs Google Vision API vs EasyOCR
8. **Revenue sharing smart contracts** — Stripe Connect vs крипто-решения
9. **SRE-as-a-Service** — бизнес-модели, прайсинг, конкуренты (Pingdom, UptimeRobot)
10. **Multi-agent orchestration** — LangGraph vs CrewAI vs AutoGen для Октопус-роя
