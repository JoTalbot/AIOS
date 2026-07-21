# AIOS 9.1.0-alpha.1 — релиз-ноты

> 2026-07-21 · **952 теста зелёные** (было 939)
> Батч H3.11 + H2.9-добивка + H2.13: AI-советник черновиков,
> drift-events в Prometheus, K8s operator.

## 1. AI-советник Direct-черновиков (draft-only)

`aios_core/platforms/advise.py`:

- `reply_draft` — детерминированные шаблоны uk/en (availability /
  price / generic, авто-детект языка по триггерам).
- `advise_drafts(threads, storage, platform)` — только непрочитанные
  треды → черновики в **guarded outbox**; человеческое одобрение и
  `dm-flush` обязательны, на устройство ничего не уходит.
- Deny-by-default: без `extras.compliance` советник честно отказывает;
  решения пишутся в audit (`advise.draft` / `advise.denied`).
- Pluggable `composer`: любой LLM-callable подменяет шаблонный движок,
  факт честно фиксируется в отчёте. Хардкод-фасада в репо нет — это
  осознанная прореха (см. ROADMAP H3.11).

```bash
aios whatsapp advise --db data/whatsapp.sqlite   # черновики → outbox
aios whatsapp dm-outbox --db data/whatsapp.sqlite
```

## 2. Marker drift events → Prometheus

- `platforms marker-check --drift-db data/marker-drift.sqlite` —
  каждое drift-событие теперь персистится (baseline маркера потерян →
  событие с removed-количеством);
- серия `aios_marker_drift_events{platform}` на `/metrics`;
- builtin worker-джоба `marker-check` пишет в общую базу по умолчанию.

## 3. Kubernetes operator (H2.13)

`deploy/k8s/`: CRD `Platform`/`Profile`/`Job` (`aios.io/v1alpha1`,
status subresources), RBAC, Deployment operator'а + PVC, примеры CR.
Контроллер `aios_core/platforms/koperator.py`: reconcile сворачивает
CR в состояние флота — Platform→yaml-дескриптор, Profile→ProfileStore
(идемпотентный upsert), Job→ShardJobs enqueue. Watch-loop ходит в
Kubernetes REST напрямую (без SDK), вне кластера честно падает с
подсказкой. Guarded-семантика платформ сохраняется.

## Миграция

Ломающих изменений нет. Новые CLI: `<whatsapp|viber|facebook> advise`,
`platforms marker-check --drift-db`.

## Что дальше

- H1.5: on-device прогон calibrate-рецептов флота (живое устройство).
- H3.11 продолжение: hosted LLM-фасад, саммари inbox, price-advice.
- H3.12: официальный `aios-sdk` (клиент REST/WS).

## Напоминания по безопасности

1. Отзовите GitHub-токен, засвеченный в чате.
2. Смените пароль Instagram (тоже засвечен).
