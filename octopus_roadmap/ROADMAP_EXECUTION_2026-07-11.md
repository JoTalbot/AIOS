# Octopus — исполнение roadmap, storage/reconciliation wave

Дата: 2026-07-11T19:58:33Z
Статус: **APPLIED / VERIFIED**

## Закрытый пункт
Vector B — Storage / Disk / IPFS / Garage:
- выполнена archive-verified reconciliation для воскресших strict ITER-файлов;
- источник parent: disk 86% -> 69%;
- worker ubu: disk 80% -> 74%;
- на каждой ноде удалено 1,516,020 воскресших файлов, уже сохранённых в проверенных tar.gz архивах;
- логический объём удалённых файлов на ноду: 400,236,347 bytes; основной выигрыш — освобождение блоков/inodes от миллионов мелких файлов;
- SUMMARY/SMOKE/STATUS/MANIFEST/board/marker не удалялись;
- IPFS/CAS/Docker GC не выполнялся.

## Новый reusable skill
`skills/core/archived-report-resurrection-reconciler`
- full archive SHA256 gate;
- archive member-count gate;
- exact membership gate;
- restore-smoke SHA256;
- dry-run/apply режимы;
- удаление только `ITER_[0-9]{2,3}.md` внутри exact marked run directory;
- tests: 2/2 локально; server `py_compile` pass;
- добавлен в skills index: 238 total, 238 real, 0 stubs.

## Проверка
- Octopus failed services: 0.
- restart loops: 0.
- all-vectors: 916.67/A.
- СОСУЩЕСТВОВАТЬ: 650/yellow до wave -> 850/green.
- РАЗВИВАТЬСЯ: 1000/green, 238 real skills.

## Оставшийся bounded backlog
1. Разобрать 100,214 strict ITER-файлов из старых unmarked runs: сначала создать отдельные verified archives/markers, затем применять тот же skill.
2. Добавить marker-aware reconciliation dry-run после multisync, без автоматического удаления до отдельного apply gate.
3. Продолжить Batch 2 roadmap: CAS proof sample, GraphRAG citations, MCP read-only ops и trace_id chain.

## Wave 2 — archive-first legacy runs
Статус: **APPLIED / VERIFIED**

- Обнаружено 18 завершённых unmarked `parallel_*` runs.
- Созданы 18 tar.gz архивов для 100,200 strict ITER-файлов.
- Для каждого архива проверены exact membership, count, SHA256 и restore-smoke.
- Только после marker commit выполнен reconciliation на parent и ubu.
- Удалено по 100,200 архивированных файлов на каждой ноде.
- Осталось 14 strict ITER-файлов: это контрольные restore-smoke samples внутри compaction gate reports, они не относятся к wave-run payload и сохранены.
- Новый skill: `strict-iter-archive-gate`.
- Skills index: 239 total / 239 real / 0 stubs.
- parent disk: 68%; ubu disk: 74%.

Следующий roadmap batch: CAS proof sample + GraphRAG exact citations + MCP read-only ops + trace_id propagation.

## Wave 3 — Batch 2 foundation: proof + citations + MCP + trace
Статус: **APPLIED / VERIFIED**
Trace-ID proof chain: `octo-20260711T201121Z-batch2-proof-ec604361`

### Реализовано
- MCP read-only methods: `ops/status`, `storage/proof`, `graphrag/search`.
- `tools/list` публикует safety annotations: readOnly=true, destructive=false, idempotent=true, openWorld=false.
- Storage proof принимает только allowlisted project/storage paths; secrets, SSH и credential paths блокируются.
- GraphRAG `/search` возвращает exact source path, indexed SHA256, size/mtime, excerpt и trace ID.
- MCP передаёт единый trace ID в GraphRAG без разрыва корреляции.
- Выполнен end-to-end proof: GraphRAG citation -> live full-file read -> SHA256 match.

### Проверка
- Citation/storage proof chain: ok=true, full_read=true, hash_match=true.
- MCP direct smoke: status + storage proof pass.
- MCP TCP smoke: GraphRAG exact citations pass.
- Unit/integration tests: 4/4 pass.
- Services after bounded restart: active, NRestarts=0.
- Skills: 240 total / 240 real / 0 stubs.
- All-vectors: 916.67/A.

### Research baseline
- MCP tool annotations: Model Context Protocol official blog/spec semantics.
- Trace identity: W3C Trace Context / OpenTelemetry 16-byte trace ID principles; Octopus retains its human-readable correlation ID contract.
- Graph provenance: Microsoft GraphRAG source-grounding model; exact source linkage is returned explicitly.

### Следующий bounded шаг
Security K: миграция CAS tokens из systemd drop-in с inline Environment в root-only EnvironmentFile с controlled rotation/canary; до отдельного compatibility gate значения не менять.

## Wave 4 — Security Vector K: CAS credential boundary
Статус: **APPLIED / VERIFIED**
Trace-ID: `octo-20260711T202235Z-security-k-e279918d`

### Найденный дефект
CAS credentials находились в inline systemd Environment, но приложение эти переменные не использовало. При отсутствии ожидаемых token files `_auth_ok()` переходил в compatibility fail-open, поэтому protected CAS routes на parent фактически принимали anonymous запросы.

### Исправление
- Значения удалены из systemd drop-in и process environment.
- Создан root-only client env с mode 0600.
- Создан root-only scoped token map с mode 0600.
- Scope separation: read; read+write; read+write+admin.
- CAS настроен на scoped token map вне project/multisync/Git.
- Sensitive rollback backups хранятся только в `/etc/octopus/secure-backups/`.

### Проверка
- protected anonymous -> HTTP 401;
- valid read credential -> HTTP 200;
- invalid credential -> HTTP 401;
- public `/healthz` -> HTTP 200;
- inline token names in systemd: 0;
- token names in CAS process environment: 0;
- loopback bind: 127.0.0.1:9540;
- service active, NRestarts=0;
- guard checks: 11/11 pass, secret values emitted=false.

### Новый skill
`skills/core/cas-credential-boundary-guard` — fail-closed drift guard без вывода секретов.

### Следующий bounded шаг
Подключить guard как read-only timer с redacted report и без Telegram noise; затем выполнить tunnel exposure inventory и проверить, что внешний доступ к CAS проходит через auth boundary.

### Wave 4 addendum — continuous drift guard
- Installed `octopus-cas-credential-guard.service` and `.timer` on parent.
- Interval: bounded 15 minutes with randomized delay.
- Redacted atomic state: `/run/octopus/cas_credential_guard.json`.
- Hardening: NoNewPrivileges, PrivateTmp, ProtectSystem=strict, ProtectHome=read-only, CPUQuota=20%, MemoryMax=128M.
- Timer active+enabled; last result success; NRestarts=0; 11/11 checks pass.

## Wave 5 — Security K: tunnel exposure and gateway auth
Статус: **APPLIED / VERIFIED WITH ROTATION BLOCKER**
Trace-ID: `octo-20260711T204949Z-tunnel-exposure-4442ea91`

### Инвентаризация
- CAS listens only on 127.0.0.1:9540.
- Octopus nginx gateway listens only on 127.0.0.1:9088.
- Quick tunnels targeting 9540/9088: 0.
- Named Cloudflare tunnel exposes `api.autosklo.org.ua` to local autopilot :8787, not CAS.
- External `/cas/stats` returns 404; CAS is not routed through the public named tunnel.

### Исправления
- Named tunnel credential removed from process argv and systemd unit.
- Credential moved to root-only `--token-file`, mode 0600.
- Active nginx CAS prefix route repaired: `/cas/stats` and `/cas/slo` now reach the intended protected upstream routes.
- Legacy double-prefix route no longer succeeds.
- Guard extended from 11 to 21 redacted checks.

### External negative canary
- public `/health` -> 200;
- anonymous `/system/status` -> 401;
- anonymous POST `/system/shell` -> 401;
- anonymous POST `/system/cleanup` -> 401;
- public `/cas/stats` -> 404.

### Manual blocker
Cloudflare named tunnel credential must be rotated from the Cloudflare account because it historically appeared in process argv. Local server changes have stopped further argv/unit exposure, but cannot invalidate the old credential without account-side rotation.

## Wave 6 — Reliability: autopilot runtime durability and orphan cleanup
Статус: **APPLIED / VERIFIED**
Trace-ID: `octo-20260711T210125Z-autopilot-durability-b3227840`

### Найдено
- Public autopilot :8787 работал неделю как unmanaged process в abandoned user session.
- Canonical `autopilot/server.py` и token file отсутствовали на parent filesystem; следующий restart был бы невосстановим.
- В том же abandoned scope оставались 17 orphan-процессов. Один `python3 -` потреблял около 100% CPU более 13 часов; остальные были зависшими grep/head searches.

### Исправлено
- Восстановлен canonical source из surviving worker copy.
- Token path переведён на root-only `/etc/octopus/autopilot.token`, mode 0600, без смены credential.
- Source прошёл canary на отдельном loopback port: health 200, anonymous 401, valid 200, wrong 401.
- Live process мигрирован в enabled `octopus-autopilot-api.service`.
- Установлен `octopus-autopilot-runtime-guard.timer` каждые 15 минут.
- Завершены 17 подтверждённых abandoned orphan-процессов; scope исчез, remaining=0.

### Проверка
- local auth contract: 200/401/200/401;
- external health/auth: 200/401;
- service active+enabled, NRestarts=0;
- runtime cgroup: managed system.slice;
- guard: 12/12 pass, secret values emitted=false;
- skills: 242 total / 242 real / 0 stubs.

### Следующий bounded шаг
Сделать общий orphan/session drift guard с age+CPU thresholds и fail-closed quarantine proposal; не убивать неизвестные процессы автоматически без строгой классификации.

## Wave 7 — Reliability: orphan/session drift guard
Статус: **APPLIED / VERIFIED**
Trace-ID: `octo-20260711T212850Z-orphan-drift-30e8cef5`

### Реализовано
- Новый read-only `orphan-session-drift-guard` исследует systemd session scopes через cgroup membership.
- Кандидат требует одновременно: SubState=abandoned, PPid=1, age>=1h и known-stale scanner либо CPU>=90%.
- Guard не отправляет сигналы и не выводит argv/environment: `actions_taken=0`.
- Установлен bounded timer каждые 10 минут с redacted state в `/run/octopus/orphan_session_guard.json`.

### Найдено и исправлено
После предыдущей очистки обнаружен ещё один изолированный stale `grep`: abandoned scope, PPid=1, age>8 дней, sole process. Перед действием все признаки повторно проверены; процесс завершён, scope исчез.

### Проверка
- abandoned candidates: 0;
- errors: 0;
- timer active, last result success, NRestarts=0;
- skills: 243 total / 243 real / 0 stubs.

### Политика
Глобальный `KillUserProcesses` не изменялся: это может сломать tmux/screen и легитимные persistent root workloads. Постоянные процессы должны мигрировать в system/user services; guard остаётся proposal-only.

## Wave 8 — CI/QA Release Safety Manifest + nginx canonicalization
Статус: **PASS WITH ONE MANUAL BLOCKER**
Trace-ID: `octo-20260711T215722Z-release-verify-49f49596`

### Реализовано
- Расширен skill `integration-testing`: добавлен bounded `code/release_verify.py`.
- Release gate проверяет source hashes/existence, py_compile, targeted systemd verify, active/NRestarts, failed units, nginx syntax/routes, runtime guard states и local/gateway/external auth contracts.
- Manifest не выводит credentials и включает trace ID.

### Устранён config drift
`sites-enabled/octopus-api` был отдельной активной копией, а `sites-available/octopus-api` содержал другое dormant содержимое. Активная конфигурация принята как source of truth; available синхронизирован, enabled заменён стандартным symlink. Runtime route не изменён.

### Проверка
- release checks: 16/16 pass;
- nginx files equal=true, symlink canonical;
- CAS gateway anonymous/auth=401/200;
- all selected units active, NRestarts=0;
- secret_values_emitted=false.

### Единственный warning
Account-side rotation Cloudflare named tunnel token остаётся ручным блокером.
