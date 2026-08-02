---
name: resource-coexistence
description: Bounded read-only аудитор coexistence-ресурсов. Реализует инструкцию №18 section 4: тяжёлые сервисы (ollama, ipfs, docker, whisper) обязаны иметь CPU/RAM-лимиты, чтобы человеку всегда оставались ресурсы на общем хосте. Т
---

# SKILL: resource-coexistence
**Категория:** swarm / coexistence / operations
**Дата создания:** 2026-06-20
**Реализовано:** 2026-07-13 (заменён generic runtime на реальную логику)

## Описание
Bounded read-only аудитор coexistence-ресурсов. Реализует инструкцию №18 section 4: тяжёлые сервисы (ollama, ipfs, docker, whisper) обязаны иметь CPU/RAM-лимиты, чтобы человеку всегда оставались ресурсы на общем хосте. Также проверяет host-headroom (RAM/CPU/диск).

## Алгоритм
1. **Инспекция тяжёлых сервисов** (`HEAVY_SERVICES`): чтение `CPUQuotaPerSecUSec`, `MemoryMax` через `systemctl show` + `is-active`.
2. **Парсинг** cgroup-значений: systemd-формат (`2s`=200%, `infinity`=unlimited, `1s500ms`=150%) → процент/байты.
3. **Классификация** каждого: `active_limited_ok` / `active_unlimited_mem` / `active_unlimited_cpu` / `active_high_cpu_limit` / `active_low_mem_limit` / `inactive`.
4. **Drift detection**:
   - HIGH: активный сервис без MemoryMax → может OOM хост (№18 sec.4);
   - MEDIUM: активный сервис без CPUQuota → может starve процессы человека;
   - LOW: CPUQuota выше ожидаемого cap / MemoryMax ниже floor.
5. **Host-headroom**: RAM-available фракция (<20% → HIGH), disk-free (<10% MEDIUM, <5% CRITICAL, №42).
6. JSON-отчёт: host-headroom + services + drifts + рекомендации. Read-only.

## Контракт безопасности
`read_only: true` — никогда не ставит/меняет cgroup-лимиты, не останавливает сервисы.

## Runtime
```bash
python3 code/run.py --json
python3 code/run.py --no-live --json
```

## Связь
№18 (coexistence), №22 (ubu worker node: CPUQuota=200%, MemoryMax=4G), №42 (disk hygiene).
