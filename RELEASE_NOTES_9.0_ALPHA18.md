# AIOS 9.0.0-alpha.18 — автокалибровка вкладки, own-posts в autopilot, ShardExec

**Дата:** 2026-07-21 · **Тесты:** 879/879 зелёные

Три пункта дорожной карты в параллельных батчах: автокалибровка
navigation, own-posts шаг автопилота и pull-модель джобов для
multi-host запуска.

## Что нового

### 🧭 Автокалибровка navigation (reels_tab)
`DetailCalibrationAdvisor.analyze_navigation` по дампу домашнего
экрана сам находит tab-bar и видео-вкладку → секция
`navigation.reels_tab` дескриптора (питает ReelsTabDriver): ручная
разметка маркеров больше не нужна. Честные диагнозы: видео-вкладка
не распознана / tab-bar не найден (→ дефолтные маркеры драйва).

```bash
aios platforms calibrate --navigation home.xml --dump feed.xml --write
```

### 📸 Own-posts в autopilot
Флаг `--own` добавляет шаг снапшота собственных постов в цикл
автопилота (та же схема own_ads, счётчики/дельты). Алёрт `own-posts`
в webhook при новых постах и **негативных дельтах счётчиков**
(views/favorites упали — сигнал теневого бана или удаления):

```bash
aios instagram autopilot --login --own --own-dump grid.xml \
    --webhook https://hooks.example/in
```

### 🛰 ShardExec — pull-модель джобов
Замена crontab в multi-host: оператор вешает джобу на профиль, ноды
сами забирают **свои** джобы по sticky HRW-маршруту (та же
AIOS_SHARDS_DB) — двойной запуск профиля на двух хостах исключён,
чужая нода получает честный idle. `ShardJobWorker` изолирует ошибки
обработчика; встроенный вид `autopilot` — guarded shell-out в
`aios instagram autopilot --login` (очереди/подтверждения guarded-
контура сохранены).

```bash
aios shards enqueue --profile instagram:main --kind autopilot
aios shards work --host worker-1 --once      # на каждой ноде
aios shards jobs --status pending
```

## Проверка
- **879 автотестов** (865 + 14 новых: analyze_navigation, merge/CLI
  calibrate --navigation, own-шаг autopilot с алёртами, ShardJobs/
  Worker/CLI, subprocess-handler).
- Документация: `docs/PLATFORMS_SCALING.md`,
  `docs/modules/instagram/ONBOARDING.md`, `CHANGELOG.md`.

## Артефакты
- `aios-9.0.0a18-py3-none-any.whl`
- `aios-9.0.0a18.tar.gz`
