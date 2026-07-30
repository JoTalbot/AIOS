---
name: money-earner-orchestrator
version: "1.0"
description: "Вектор САМООБЕСПЕЧЕНИЕ — автоматический заработок всеми доступными способами (от бесплатных сатоши с кранов до торговли на биржах). Zero-cost first; реальные средства за consent gate; торговля только paper-trading."
triggers:
  - self_sufficiency
  - заработок денег
  - earn money
  - satoshi faucet
  - paper trading
  - self_sustain
dependencies:
  - core/all-vectors-orchestrator
llm_required: false
---

# SKILL: money-earner-orchestrator
**Категория:** core
**Вектор:** САМООБЕСПЕЧЕНИЕ (`self_sustain`) — ведущий операционный/стратегический вектор Octopus.
**Дата создания:** 2026-07-09

## Описание
Навык-оркестратор вектора САМООБЕСПЕЧЕНИЕ: catalogue, probe и bounded-развитие всех
способов автоматического заработка — от сбора бесплатных сатоши с кранов и airdrop-мониторинга
до paper-trading и (за consent gate) реальной торговли на биржах. По умолчанию полностью
безопасен: zero-cost, read-only, без приватных ключей и без реальных ордеров.

## Принципы безопасности (обязательно)
- **Zero-cost first.** Сначала только бесплатные методы (faucets, learn-and-earn, airdrops,
  free-tier перепродажа при разрешении ToS, контент/данные/баунти, paper-trading).
- **Consent gate (многоуровневый).** Реальные средства / биржи / API-ключи разрешены ТОЛЬКО
  после явной отдельной команды человека. Gate разделяет два уровня:
  - *Санкция* (`real_funds_unlocked`, `exchange_trading_allowed`) — стоячее разрешение пользователя.
  - *Готовность исполнить* (`approved_exchanges`, `api_keys_present`, `execution_armed`) —
    должны быть все true; `execution_armed` — доп. ручной рычаг, чтобы автономные агенты
    (см. `13_no_unsupervised_autoloops.txt`) НЕ могли торговать реальными деньгами сами.
  Реальный ордер отправляется только при `can_trade_live()` = все условия И kill-switch не сработал.
- **Kill-switch.** При суммарном реализованном убытке >= `max_loss_usd` торговля останавливается
  (`kill_switch_tripped=true`, персистится в ledger); сброс — только командой человека.
- **Live коннектор.** `code/exchange_live.py` (ccxt, ленивая зависимость). Реальные ордера — только
  при полном consent; иначе dry-run/paper. Ключи read+trade (БЕЗ вывода), из `~/agents/-Octopus/secrets/exchange.env`, не логируются (маскируются).
- **Faucet-коллектор (L0).** `code/faucet_collector.py` — сбор бесплатных сатоши с Lightning-кранов.
  Deep-probe через headless chromium (точное обнаружение JS-капчи hCaptcha/reCAPTCHA), каталог реальных
  кранов (`config/faucet_catalog.json`), классификация claimable/captcha/testnet/dead, ledger клеймов.
  Принимает Lightning Address (публичный, без приватных ключей). Честно: captcha-free mainnet-кранов
  почти нет (анти-абус обязателен), поэтому при политике captcha_free_only claimable≈0.
- **Bounded.** Один безопасный шаг за цикл; таймауты на сети; без uncontrolled loops.
- **Секреты.** Ключи/токены не запрашиваются и не логируются этим навыком.
- **Платные ресурсы.** Запрещены без отдельной команды человека (`09_free_servers_only.txt`).

## Инструкции
1. Загрузить каталог методов (`config/earnings_methods.json` или встроенный default).
2. Проверить consent gate (`config/consent.json`).
3. Выполнить read-only probe методов: классифицировать готовность, оценить сатоши/награды,
   НЕ клеймить и НЕ тратить.
4. Paper-trade шаг: получить BTC/USD (best-effort, offline-safe), обновить SMA-сигнал и
   симулированную позицию.
5. Сформировать JSON-отчёт: методы, paper-trade PnL, предложения (proposals) для gated-действий,
   `next_bounded_step`.
6. Любое действие с реальными средствами → proposal + ждать consent gate; автоприменение запрещено.

### Airdrop eligibility checker
- `code/airdrop_checker.py <address> --json` — read-only проверка незаявленных airdrop.
- Поддерживает EVM (0x...), Cosmos (cosmos1.../osmo1...), Solana.
- Требует `BANKLESS_API_KEY` для Bankless Claimables API (заголовок `X-BANKLESS-TOKEN`); без ключа выдаёт manual-ссылки.
- Приватные ключи/seed не запрашиваются и не используются.

## Алгоритм
1. `consent = consent_state()` (читаем `config/consent.json`; default — всё закрыто).
2. `methods = method_catalog()` (zero-cost каталог по риск-уровням L0…L3).
3. `probe = probe_methods(methods, consent)`:
   - `discovered_count`, `ready_count`, `needs_wallet_or_account_count`;
   - `gated_behind_consent` — методы L2/L3, заблокированные пока `real_funds_unlocked=false`;
   - `satoshis_estimated_per_cycle` — сумма оценок сатоши-методов.
4. `price = fetch_price()` — приоритет: `OCTOPUS_ME_PRICE` > CoinMarketCap Pro API (`CMC_API_KEY`/`~/agents/-Octopus/secrets/cmc_api_key.txt`)
   > бесплатные публичные источники (CoinGecko/Bitstamp/blockchain.info). Offline-safe, таймаут, fallback;
   env `OCTOPUS_ME_OFFLINE=1` / `OCTOPUS_ME_PRICE=` для тестов.
5. `paper = paper_trade_cycle(price, history, position)`:
   - `signal(history)` = пересечение `sma(fast=2)` и `sma(slow=3)`;
   - `apply_paper_trade()` меняет симулированную позицию (`cash`/`btc`/`pnl_usd`), реализованный PnL;
   - `warming_up=True` пока `len(history) < MIN_HISTORY(3)`.
6. `build_report()`: если `--apply` — persist в `data/earnings_ledger.json` (история, позиция, entries,
   methods_discovered, satoshis_estimated_total); иначе read-only.
7. Вывод: `--json` (машино-читаемый) или человеко-читаемая сводка.

## Риск-лестница (tiers)
- **L0 — zero-cost, сейчас:** faucets, learn-and-earn, airdrops, free-tier перепродажа (ToS!), контент/SEO, баунти за данные.
- **L1 — zero-cost, симуляция:** paper-trading на реальных ценах.
- **L2 — real funds, gated:** реальная торговля маленьким размером, paper-first, с `max_loss_usd` и `approved_exchanges`.
- **L3 — real funds, gated, продвинуто:** арбитраж/маркет-мейкинг/мульти-биржа — только после устойчивой L2 и явной команды.
Подробности: `references/zero_cost_methods_and_risk_ladder.md`.

## Контроль и развитие
- Runtime: `python3 code/run.py --json` (read-only) / `code/run.py --apply` (локальный ledger) / `code/run.py --live` (попытка bounded live-ордера; только при полном consent, иначе dry-run).
- Live trading: `code/exchange_live.py` (`can_trade_live()`, `live_blockers()`, `live_trade_step()`, kill-switch).
- Contract tests: `python3 -m unittest discover -v tests` (offline, без сети; 34 теста).
- Интеграция: `scripts/all_vectors_development_cycle.py` читает `data/earnings_ledger.json`
  и `config/consent.json` для вектора `self_sustain` в `ALL_VECTORS_STATUS.md`.
- Мониторинг: `scripts/skill_evolution_cycle.py` пересчитывает health/coverage навыка.
- Развитие (bounded): расширять zero-cost каталог; накапливать price-history; добавлять
  bounded claim-probes для ready-методов (без приватных ключей); после команды человека —
  открывать L2 с paper-first и лимитом потерь.
- Telegram: прямые push-запрещены, кроме `skill-notification` и отчётов автономного агента.
