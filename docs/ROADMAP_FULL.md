# AIOS — Полный роадмап (линейка 9.0.0-alpha → 9.0 GA)

> Статус на **v9.0.0** (2026-07-21, 939 тестов зелёные).
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
  ShardExec (pull-джобы), onboarding-пакеты (WA/Viber/TikTok/FB).
- **Instagram как вторая платформа полного стека**: login-wall driver,
  коллектор, детали, guarded Direct, doctor, own-posts/composer,
  Reels (коллектор + tab-driver + алёрты), autopilot-цикл, cron-plan,
  multi-account e2e через waitlist.

## Горизонт H1 — операционная закалка мультиаккаунтности (alpha.19–22)

> alpha.19–21 закрыли все кодовые пункты H1, кроме on-device H1.5.

**Тема: автопилот и очереди должны переживать реальную эксплуатацию.**

1. ✅ **Job-lease TTL** — alpha.19: heartbeat, `requeue_stale`,
   `stats()` (queue depth/stale), CLI `shards jobs --stats`,
   `shards requeue-stale`.
2. ✅ **Встроенные виды джоб** — alpha.19: `reels`, `dm-flush`,
   `marker-check` в `default_handlers`; alpha.20 — cron-plan
   `--via-shards` (enqueue-строки).
3. ✅ **Own-promote → autopilot** — alpha.19: `promotion_plan`
   (DRY-RUN, бюджет равномерно), шаг `--promote` в autopilot,
   webhook `promote-suggestion`.
4. ✅ **Human-like pacing** — alpha.19: `Pacer` (jitter,
   actions/hour, session limit) в OLXCollector/ReelsCollector/
   InstagramCollector + `pacer_from_limits` из pool kv; CLI
   `--pace-actions/--pace-jitter`.
5. **On-device hints-калибровка флота**: прогон calibrate-рецептов
   на реальной машине с Android SDK — fetch APK, login (env-секреты),
   калибровка feed/detail/Direct/navigation, `marker-check` baseline,
   занесение hints в `platforms/<name>.yaml`. ✅ alpha.21 — сами
   рецепты кодифицированы: `platforms doctor --calibrate-recipe`
   печатает точные adb-команды под каждую платформу (мессенджер-first
   для WA/Viber, полный стек для OLX-like, лента+таббар для
   TikTok); остаётся их прогон на живом устройстве (ops-шаг).

## Горизонт H2 — масштабирование до флота платформ (alpha.20–30)

**Тема: «ещё N приложений» = конфигурация, а не код; наблюдаемость —
первоклассный citizen.**

6. ~~**Onboarding wizard**~~ ✅ alpha.20: `aios onboard` (fetch→
   bootup→паспорт+next_commands). TODO: login-driver/autowatch
   в happy path (после H1.5).
7. ~~**Новые платформы**~~ ✅ alpha.20 — WhatsApp, Viber, TikTok;
   ✅ alpha.21 — **Facebook Marketplace** (полный OLX-like пакет:
   storage/messenger/bootstrap + compliance + guarded CLI);
   on-device hints — общий контур H1.5. Остаётся: региональные
   площадки по мере спроса (Prom/Bigl/Shafa — по тому же шаблону).
8. ~~**Pull-first автоматизация**~~ ✅ alpha.20 — cron-plan
   `--via-shards` + jobs REST (`/api/v1/shards/jobs|stats`);
   ✅ alpha.21 — **web-pane очереди/пула**: `GET /dashboard`
   (самодостаточная read-only HTML-панель: очередь джобов, пул
   устройств, профили, shard-host; действий из UI нет — guarded).
9. ~~**Метрики/наблюдаемость**~~ ✅ alpha.21: Prometheus text
   exposition на `/metrics` (queue/hosts/devices/profiles/catalog);
   ✅ alpha.22: счётчики `aios_seen_receipts{platform,kind}`,
   `aios_outbox_pending{platform}` + alert-правила
   `deploy/monitoring/aios-alerts.yml`. Остаётся: cards/cycle
   rates и drift-events series (alpha.27, потребуются живые циклы
   H1.5).
10. ~~**Compliance-контур**~~ ✅ alpha.22: `platforms/compliance.py`
    (`compliance_guard` — autopost/collect/send/auto_send из флагов
    дескриптора, deny-by-default без блока) + проводка в CLI
    dm-send, platforms reels, Instagram PostComposer (до инициализации
    устройства); scaffold-шаблон с deny-by-default блоком; compliance
    в дескрипторах olx/instagram; `actions_per_hour`; **audit-log**
    `olx_audit` (audit()/audit_list(), outbox-lifecycle автописьмо).

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
15. **9.0 GA-критерии**: ≥1000 тестов зелёные (сейчас 939); 3+
    production-профиля Instagram под autopilot ≥2 недели без банов
    (pacing-метрики); онбординг новой платформы ≤ 30 минут по
    чек-листу; документация — PDF/сайт; API стабилизировано
    (deprecation-политика).

## Открытые риски / вопросы владельцу

- **Безопасность**: отозвать засвеченный GitHub-токен; сменить пароль
  Instagram (засвечен в чате дважды) — блокеры для любого on-device.
- **Право**: автопостинг/скрапинг по ToS каждой площадки —
  compliance-флаги (п.10) ждут решений по платформам.
- **Инфраструктура**: device-farm (сколько эмуляторов/машин,
  какие хосты шардов) — влияет на п.6–8.

*Правило дорожной карты: пункт берётся в работу только с тестами и
релизом в конце батча («+» = следующий батч целиком).*
