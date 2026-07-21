# AIOS — Полный роадмап (линейка 9.0.0-alpha → 9.0 GA)

> Статус на **v9.0.0-alpha.18** (2026-07-21, 879 тестов зелёные).
> Принципы, которые действуют на всём роадмапе: **guarded-действия**
> (ничего не трогает внешний мир молча: outbox/DRY-RUN/confirm),
> **платформенность** (любая механика сразу generic, платформенный код
> только в `modules/<platform>`), **честные ошибки** (нет silently-
> фолбэков), **секреты только в env**.

## Горизонт H0 — фундамент ✅ ГОТОВО

- Ядро AIOS (конституция, оркестратор, эволюция, API, WS, маркетплейс).
- OLX-агент полного цикла (коллектор, детали, мессенджер, свои
  объявления, конкуренты, советник, autowatch, REST/CLI).
- **Платформенная архитектура «10000+ приложений»**
  (`aios_core/platforms/`): descriptor-registry, профили/аккаунты
  (ProfileStore + resolver precedence), storage/adb per-profile,
  device pool с lease/waitlist/квотами, scaffold/codegen/bootup
  (APK → модуль → калибровка → verify), apkfetch (apkeep), secrets
  (per-profile env), каталог YAML, sharding (HRW sticky) + gateway,
  marker-regression, runtime-hints, pointdrive, videocards,
  generic autowatch + FleetScheduler, ReelsCollector + receipts,
  ShardExec (pull-джобы).
- **Instagram как вторая платформа полного стека**: login-wall driver,
  коллектор, детали, guarded Direct, doctor, own-posts/composer,
  Reels (коллектор + tab-driver + алёрты), autopilot-цикл, cron-plan,
  multi-account e2e через waitlist.

## Горизонт H1 — операционная закалка мультиаккаунтности (alpha.19–22)

**Тема: автопилот и очереди должны переживать реальную эксплуатацию.**

1. **Job-lease TTL** (ShardExec): heartbeat исполнителя, requeue
   «зависших» claimed-джоб умерших нод, метрики глубины очереди,
   CLI `shards jobs --stale`, `shards requeue-stale`. *(alpha.19)*
2. **Встроенные виды джоб** в `default_handlers`: `reels`,
   `dm-flush`, `marker-check` (+ `bootup`) по образцу `autopilot`;
   cron-plan умеет генерировать enqueue-строки вместо shell-cron.
   *(alpha.19)*
3. **Own-promote → autopilot**: stagnant-анализ своих постов/объявлений
   → DRY-RUN план продвижения (бюджет/действия), исполнение только с
   confirm; webhook-предложения «стоит продвинуть». *(alpha.20)*
4. **Human-like pacing**: рандомизированные паузы/лимиты действий в
   коллекторах/мессенджерах (per-profile квоты: actions/hour,
   session length, jitter) — антибан-профилирование как часть pool
   limits. *(alpha.20)*
5. **On-device Instagram bootstrapping**: прогон `ONBOARDING.md` на
   реальной машине с Android SDK — fetch APK, login (env-секреты),
   калибровка feed/detail/Direct/navigation, `marker-check` baseline,
   занесение откалиброванных hints в `platforms/instagram.yaml`.
   *(ops-эпик, кода почти нет — тур через doctor)*

## Горизонт H2 — масштабирование до флота платформ (alpha.23–30)

**Тема: «ещё N приложений» = конфигурация, а не код.**

6. **Onboarding wizard**: `aios onboard <apk-or-package>` — единая
   команда: fetch → bootup → login-driver (если стена) → doctor →
   первый autowatch-цикл; печатает «паспорт платформы» (готовность
   по чек-листу). Минимум ручных шагов = 0 в happy path. *(alpha.23)*
7. **Новые платформы-мишени** (доказательство generic'ности): TikTok
   (video-first: videocards+reelscout уже есть), Facebook Marketplace
   (OLX-подобный), 1–2 региональные площадки по запросу. Каждая —
   YAML + login-driver + документированный онбординг. *(alpha.24–26)*
8. **Pull-first автоматизация по умолчанию**: pull-модель джобов как
   основной способ эксплуатации (cron-plan → `shards enqueue`/
   supervisor), web-pane очереди джобов и пула устройств в dashboard
   (dashboard API уже есть — добить вкладками). *(alpha.26)*
9. **Метрики/наблюдаемость**: Prometheus-экспортер (jobs done/failed,
   cards/cycle, drift events, pool utilization, per-profile health);
   alert-правила (drift, failed> N, queue depth). *(alpha.27)*
10. **Compliance-контур**: per-platform robots/ToS-флаги в дескрипторе
    (`extras.compliance`), принудительные rate-limits и запреты
    (например, no-autopost для платформы) на уровне resolver —
    guarded не только технически, но и правово. Audit-log действий
    в storage. *(alpha.28)*

## Горизонт H3 — продуктовое ядро и GA (alpha.31+ → 9.0)

11. **AI-советник поверх платформ**: генеративные ответы Direct по
    шаблонам (draft-only в outbox, human-approve обязателен),
    саммари inbox, price-advice из истории (LLM-фасад AIOS уже есть —
    прикрутить платформенные контексты). *(alpha.31–32)*
12. **Официальный SDK** (`aios-sdk`): питон-клиент REST/WS + типы;
    примеры: «свой агент за 30 строк». *(alpha.33; см. веху v4.1)*
13. **Kubernetes operator** (веха v4.1): CRD Platform/Profile/Job,
    device-farm как daemonset эмуляторов, шард-контроллер.
    *(alpha.34)*
14. **Marketplace плагинов платформ**: публикация onboarding-пакетов
    (descriptor + hints + drivers) в marketplace-модуль ядра.
    *(alpha.35)*
15. **9.0 GA-критерии**: ≥1000 тестов зелёные; 3+ production-профиля
    Instagram под autopilot ≥2 недели без банов (pacing-метрики);
    онбординг новой платформы ≤ 30 минут по чек-листу; документация
    — PDF/сайт; API стабилизировано (deprecation-политика).

## Открытые риски / вопросы владельцу

- **Безопасность**: отозвать засвеченный GitHub-токен; сменить пароль
  Instagram (засвечен в чате дважды) — блокеры для любого on-device.
- **Право**: автопостинг/скрапинг по ToS каждой площадки —
  compliance-флаги (п.10) ждут решений по платформам.
- **Инфраструктура**: device-farm (сколько эмуляторов/машин,
  какие хосты шардов) — влияет на п.6–8.

*Правило дорожной карты: пункт берётся в работу только с тестами и
релизом в конце батча («+» = следующий батч целиком).*
