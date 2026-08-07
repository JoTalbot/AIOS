# AIOS Changelog

All notable changes to this project will be documented in this file.

## [19.9.0] — 2026-08-07 — AIOS FH 50 Projects v19.9 (Pagination + Python Filter)

### Added
- **FH 50 Projects v19.9** ( 870→882 lines):
  -  (env) →  ×10 = **50 projects** (was 30),  (Python),  → try  then fallback to all, … dedup , .
  -  19.8.0→19.9.0,  19.9.0.
  - **Test:**  (5 pages, dedup, python filter 400 fallback to all, +8 extra),  (10 pages),  sample , ,  — all 50,  882.

## [19.8.0] — 2026-08-07 — AIOS Freelance API Pagination v19.8 (30 Projects)

### Added
- **Freelance API Pagination v19.8** (`aios_core/freelance_brain.py` 863→870 lines):
  - `fetch_freelancehunt_jobs` теперь `api_pages = [1,2,3]` → `page[size]=10` ×3 = **30 projects** (was 10), `if len(tasks)>=30 break`, dedup by `fh_{proj_id}`, `sleep 0.5` respect API.
  - `VERSION` 19.7.0→19.8.0, `pyproject` 19.8.0.
  - `FH API` still primary: `10→30` projects, `Upwork 0` graceful, `Fiverr 1`, `Github 3` + seed → **~34 scanned** per cycle (vs 17 before), `max_process_batch=3` → 3 bids/cycle.

### Test
- `FH API page 1 found 10 total` → `page 2 found 20 total` → `page 3 found 30 total` → `total 30 projects (3 pages)` ✅
- Sample: `fh_1646235 3d модель step $65.85`, `fh_1646233 google ads $24.39`, `fh_1646229 web project $300` — all 30 with `budget/currency` UAH→USD + category.
- `py_compile OK` 870 lines

## [19.7.0] — 2026-08-07 — AIOS FlareSolverr v19.7 (Docker Cloudflare Bypass)

### Added
- **FlareSolverr v19.7** (Docker `ghcr.io/flaresolverr/flaresolverr:3.5.0` + `aios_core/freelance_brain.py` 813→863 lines):
  - Docker `flaresolverr` on `127.0.0.1:8191` (Chrome 148, `LOG_LEVEL=info`, `restart unless-stopped`) — `Test successful! Serving on 0.0.0.0:8191` ✅
  - `_fetch_via_flaresolverr(url, timeout=60000)` — `POST http://127.0.0.1:8191/v1 {cmd:request.get, url, maxTimeout}` → `solution.response` + `cf_clearance` cookie, `Just a moment` check, `len>1000`.
  - FH fallback: `if not tasks` → `FlareSolverr https://freelancehunt.com/projects` → `re.findall href project` 7 links `fh_flare_*`, Upwork fallback similarly `/nx/jobs/` 5 links `upwork_flare_*`.
  - `VERSION` 19.6.0→19.7.0, `pyproject` 19.7.0, `undetected-chromedriver 3.5.5` + `selenium` + `cloudscraper` installed (tested, still 403), `FlareSolverr` primary for Cloudflare.

### Test
- `curl POST /v1 {cmd:request.get, url:freelancehunt.com/projects}` → `status ok Challenge solved!` `cf_clearance LKdr3I...` `response len` real page `615 projects` `title Удаленная работа` ✅
- Second POST same URL → `500 Error solving challenge Connection refused port 35581` — FlareSolverr browser session unstable (needs `sessions` reuse), fallback graceful
- `Upwork` via FlareSolverr → `500 Cloudflare has blocked this request. Probably your IP is banned` — Upwork datacenter IP ban (needs residential proxy)
- Direct `cloudscraper` and `undetected-chromedriver` (Chrome 151 vs 150 mismatch, then `Just a moment...` still) → **API remains best** for FH (10 projects via `api.freelancehunt.com/v2/projects?page[size]=10` bypasses Cloudflare 200 OK)
- `FH API` still primary: `10 projects` (vs browser 0), `Upwork 0` graceful, overall `17 scanned` → 3 bids `$225` — жив
- `docker ps` `flaresolverr Up 2 minutes 0.0.0.0:8191->8191` `restart unless-stopped`, `py_compile OK` 863 lines

### Note
- **API > FlareSolverr > Browser** priority: `FH API v2` is **best** (no Cloudflare), `FlareSolverr` is fallback for `Upwork`/`RSS` when API not available, `undetected`/`stealth` is last. Full Cloudflare bypass for Upwork requires `residential proxy` + `FlareSolverr` with `sessions`.

## [19.6.0] — 2026-08-07 — AIOS Stealth Bypass v19.6 (Cloudflare)

### Added
- **Stealth v19.6** (`aios_core/freelance_brain.py` 786→813 lines, `playwright-stealth 2.0.3`):
  - `HAS_STEALTH` + `from playwright_stealth import Stealth` — `Stealth().apply_stealth_async(page)` для обоих браузеров.
  - FH helper: `user_agent Chrome/120`, `viewport 1280x900`, `Stealth` + `wait 5s` + Cloudflare `Just a moment`/`challenges.cloudflare.com` detect → extra 5s wait, `try/except` + `finally ctx.close`.
  - Upwork helper: аналогично `Stealth` + `user_agent` + `viewport` + 5s wait.
  - `VERSION` 19.5.0→19.6.0, `pyproject` 19.6.0, `playwright-stealth` installed.

### Test
- `pip show playwright-stealth` → `2.0.3` ✅
- `Stealth().apply_stealth_async(page)` on `freelancehunt.com/projects` → still `Just a moment...` `len 27471` `challenges.cloudflare.com True` — Cloudflare **still blocks** headless even with stealth (expected, need `undetected-chromedriver` or residential proxy for full bypass)
- `FH RSS 403 → browser 0` graceful (не падает), `Upwork 0` graceful — fallback best-effort, primary remains `github + seed + fiverr` (7 scanned) ✅
- `py_compile OK` 813 lines, `headless example.com` still OK

### Note
- Cloudflare Turnstile на Freelancehunt требует `playwright-stealth` + `chrome` non-headless + `proxy` или `FlareSolverr` — пока fallback оставлен как best-effort, RSS primary. Полный bypass — в `v20` с `undetected-chromedriver`.

## [19.5.0] — 2026-08-07 — AIOS Freelance Browser v19.5 (Playwright Fallback)

### Added
- **Freelance Browser Fallback v19.5** (`aios_core/freelance_brain.py` 603→786 lines):
  - `HAS_PLAYWRIGHT` + `from playwright.async_api import async_playwright` — headless Chrome `launch_persistent_context` с `/tmp/aios_*_browser`, stealth args.
  - `_fetch_freelancehunt_via_browser()` — `https://freelancehunt.com/projects` → `querySelectorAll('a[href*="/project/"]')` 7 links, dedup, `fh_browser_*` tasks (bypass 403 RSS/HTML Cloudflare).
  - `_fetch_upwork_via_browser()` — `https://www.upwork.com/nx/jobs/search/?q=python` → `a[href*="/jobs/"]` 5 links, `upwork_browser_*` tasks.
  - `fetch_freelancehunt_jobs()` и `fetch_upwork_jobs()` теперь при `RSS+HTML 403` → `if not tasks and HAS_PLAYWRIGHT` → browser fallback с `logger.info` и `asyncio.run` (ThreadPool fallback если loop running).
  - Graceful Cloudflare handling: `Just a moment...` → 5s wait, `try/except` + `ctx.close/p.stop` в `finally`, 0 tasks если blocked (не крашит цикл).
  - `VERSION` 19.4.0→19.5.0, `pyproject` 19.5.0.

### Test
- RSS 403 → HTML 403 → `🌐 FH RSS+HTML blocked (403), пробую browser fallback...` → 0 tasks (Cloudflare `Just a moment` challenge, headless detected) — graceful, не падает
- Upwork RSS 403 → `🌐 Upwork RSS blocked, пробую browser` → 0 tasks (Target closed, но `try/except` ловит) — graceful
- Общий цикл `run_freelance_brain` → `7 tasks scanned` (github 3 + seed 3 + fiverr 1) → `1 evaluated` → `financial 2027%` — жив, несмотря на 403
- Playwright `headless` `example.com` → `title: Example Domain` `browser launch ok` ✅
- `py_compile OK` 786 lines

### Note
- Cloudflare на Freelancehunt требует `stealth` / `playwright-stealth` или `undetected-chromedriver` для полного bypass — пока best-effort, RSS остается primary, browser fallback — опциональный `AIOS_BROWSER_FETCH=1` в будущем.

## [19.4.0] — 2026-08-07 — AIOS Telegram Control v19.4 (Liquidity/Flash/Mesh Buttons)

### Added
- **Telegram Control v19.4** (`run_telegram_bot.py` 8718 lines):
  - `MAIN_MENU_KEYBOARD` обновлено: 6 рядов `💰 Казначейство/📈 Трейдинг` → `💧 Ликвидность/⚡ Арбитраж` → `📱 Mesh/🛒 Склад & OLX` → `📦 Новая Почта/🌐 Веб-каталог` → `📲 Телефон & Банки/🛡 SRE` → `❓ Помощь`.
  - `_handle_treasury_intent` liquidity блок: теперь `run_smart_liquidity_router.py --telegram` v19.1 (Solana 6.8% best, net +25.13, bridge quote) вместо ручной сборки.
  - `_handle_treasury_intent` arbitrage блок: теперь `run_dex_arbitrage_scanner.py --cross --telegram` v19.2 (5 venues, viable 0 honest, 10k/50k sim).
  - Новый `Android Mesh v19.3` блок: `mesh/меш/📱 mesh` → `run_android_mesh.py --telegram` (1 Online 1 Idle 🔋90% или 2 parallel).
  - Эмодзи-триггеры `💧/⚡/📱` уже покрыты substring check (`ликвидность/арбитраж/mesh`), меню полностью кликабельно.

### Test
- MockAPI direct call: `💧 Ликвидность` → Solana 6.8% report ✅, `⚡ Арбитраж` → cross 4 пары viable 0 ✅, `📱 Mesh` → 1 Online 1 Idle 🔋90% ✅
- `systemctl restart aios-telegram-bot` → active running ✅, `py_compile OK` 8718 lines

## [19.3.0] — 2026-08-07 — AIOS Android Mesh v19.3 (Multi-Device Fleet)

### Added
- **Android Mesh v19.3** (`aios_core/android_mesh.py` 321 lines, `run_android_mesh.py` 122 lines):
  - `MeshDevice` dataclass: serial, name, model, android, wireguard_ip, status idle/busy/offline, leased_to, capabilities, battery, heartbeat, task_count.
  - `AndroidMeshFleet`: `register_device`, `list_devices`, `get_device`, `lease_device` (least-loaded + app filter + battery <15% skip), `release_device`, `heartbeat`, `reap_stale(600s)`, `stats`, `health_report`, `route_task`, `generate_telegram_report`.
  - Fleet file `data/android_gateway/fleet.json` (auto-migrate legacy `device.json` G1), `ANDROID_MESH_*` env, WireGuard mesh ready for G2/G3.
  - Runner `run_android_mesh.py`: `--status/--telegram/--list/--register/--remove/--lease/--release/--heartbeat/--route/--daemon 60`, lease example `G1→olx, G2→whatsapp` parallel.
  - Telegram report: `Устройств 1 Online 1 Idle 1` → `✅ G1 idle 🔋87%` или `2 devices parallel ready`.

### Test
- Auto-migrate legacy G1 `10.203.0.2:46037` → fleet 1 device idle ✅
- Register G2 mock `10.203.0.3:46038` → 2 devices, lease `olx→G1` + `whatsapp→G2` parallel ✅, release, heartbeat 87, reap stale ✅
- Fleet JSON persisted `data/android_gateway/fleet.json` 1.2K, clean after G2 remove → 1 device ✅

## [19.2.0] — 2026-08-07 — AIOS Flash-Loan Arbitrage v19.2 (Cross-DEX Uniswap/QuickSwap + CEX)

### Added
- **Flash-Loan Arbitrage Engine v19.2** (`aios_core/dex_arbitrage_scanner.py` 80→385 lines):
  - 4 пары: `WETH/USDC`, `WBTC/USDC`, `WMATIC/USDC`, `SOL/USD` — кросс-DEX/CEX цены `kraken + binance + coingecko + Uniswap V3 Polygon` (on-chain `slot0` + `matic-network` fix).
  - `fetch_all_prices()` — 5 venue, `scan_cross_dex_opportunities(min_spread_pct=0.8, flash_amount=10k)` — спред, `flash_sim_10k/50k` (fee 0.05% Aave + gas $0.02 + slippage 0.3% = 0.35%), `viable` если spread≥0.8% и net>$5, фильтр data error >15%.
  - `simulate_flash_loan(buy,sell,symbol,amount)` — buy low → sell high симуляция, `net = gross - (flash_fee+gas+slippage)`.
  - `execute_flash_arbitrage(..., dry_run=True)` — dry_run safe, `AIOS_FLASH_LIVE=1` gate + приватный ключ check, stub для `AaveFlashArb.sol`.
  - `generate_telegram_report()` — `Viable 0/3 Best WETH 0.07% net -$27 (cost 0.35%)` — honest для calm market.
  - Legacy `scan_arbitrage_opportunities()` + alias `AIOSDEXArbitrageScanner = AIOSFlashLoanArbitrageEngine`.
- **Runner v19.2** (`run_dex_arbitrage_scanner.py`):
  - Args: `--cross`, `--telegram`, `--simulate SYMBOL BUY SELL --amount 10000`, `--execute`, `--daemon --interval 300`, `--min-spread 0.8`.
  - Daemon: loop 300s + state `data/flash_arbitrage_state.json`.
  - Safety: `AIOS_FLASH_LIVE=0` блокирует live.
- **Solidity** (`contracts/AaveFlashArb.sol`): Aave V3 `flashLoanSimple` stub, `FLASH_FEE_BPS 5`, `dryRun` + `executeOperation` buy/sell via low-level call, `owner` only, `ArbitrageExecuted` event. Live требует аудита.

### Test
- Cross scan: `WETH 0.07%, WBTC 0.05%, SOL 0.06%` — viable 0 (нормально, calm), `WMATIC` 405% filtered as data error.
- Simulate 10k WETH kraken→binance `net -$27.45` (gross $7.57 - cost $35.02), execute blocked без `AIOS_FLASH_LIVE=1` ✅.

## [19.1.0] — 2026-08-07 — AIOS Smart Liquidity Router v19.1 (Cross-Chain Solana/Arbitrum)

### Added
- **Smart Liquidity Router v19.1** (`aios_core/smart_liquidity_router.py` 110→351 lines):
  - 4 сети: `Solana Marinade/Jito 6.8%` (live API + fallback), `Base Compound 5.25%` (live), `Arbitrum Aave V3` (live on-chain 4.15% fallback), `Polygon Aave V3 2.74%` (live).
  - Live Solana APY via Marinade `api.marinade.finance/apy` + Jito fallback, Arbitrum live via `ARBITRUM_DATA_PROVIDER` on-chain `getReserveData`.
  - `_get_bridge_quote()` — оценка Stargate/Across/LiFi: fee 0.05-0.12% + gas $0.01-0.05, time 2-5 мин, для Polygon→Solana `0.8168$` на `639$`.
  - `scan_multi_chain_yields()` расширен: net APY после газа, `net_gain_annual`, `yield_30d/90d`, `current_allocation`, `bridge_quote`, сортировка по APY.
  - `execute_rebalance(dry_run=True)` — `dry_run` по умолчанию (safe), `AIOS_LIQUIDITY_LIVE=1` для live, проверка приватного ключа, stub для Stargate.
  - `generate_telegram_report()` — markdown отчет `Excess $639 → Annual $43.45 (Solana 6.8% best), net +$25.13`.
  - `save_state/load_state` → `data/liquidity_router_state.json`.
- **Runner v19.1** (`run_smart_liquidity_router.py`):
  - Args: `--telegram`, `--dry-run`, `--execute`, `--amount`, `--daemon --interval 3600`, `--json`.
  - Daemon mode: loop scan + dry-run quote + state save.
  - Safety: `AIOS_LIQUIDITY_LIVE=0` блокирует live bridge.
- **ROI:** Excess `639$` → Base `33.55$/год`, Solana `43.45$/год` (+9.9$), net ребаланс Polygon→Solana `+25.13$/год` после fee `0.81$`.

## [19.0.0] — 2026-08-07 — AIOS Autonomous Freelance Chrome Twin v19 (Freelancehunt/Upwork/Fiverr)

### Added
- **Freelance Chrome Twin v19** (`aios_core/platforms/freelance_chrome_twin_adapter.py` 163→425 lines):
  - `submit_freelancehunt_proposal()` — автоматическая ставка на Freelancehunt (Сделать/Зробити ставку, #bid-comment, #bid-amount, #bid-days) с 3-язычным детектом и верификацией.
  - `submit_upwork_proposal()` — Submit a Proposal на Upwork (Apply Now → Cover Letter → Submit, Connects & Verification checks).
  - `submit_fiverr_proposal()` — Contact Me / Custom Offer на Fiverr.
  - `verify_platform_status()` — проверка верификации профиля + скриншот.
  - `submit_proposal()` — унифицированный диспетчер по платформе + `AIOS_FREELANCE_AUTOPILOT` safe mode (default confirm=False → need_confirm).
  - `_detect_common_blocks()` — детект капчи/Cloudflare/верификации/авторизации.
- **Freelance Brain v19** (`aios_core/freelance_brain.py` 447→603 lines):
  - `fetch_freelancehunt_jobs()` — RSS + HTML парсинг freelancehunt.com с UAH→USD конвертацией (≈41) и категоризацией.
  - `fetch_fiverr_gigs()` — поиск Fiverr gigs + seed fallback.
  - Обновлен `run_market_scan_cycle()` — теперь 5 источников (github + upwork + freelancehunt + fiverr + seed), лимит пачки 2, safe `confirm=False` до Telegram approve.
  - `AIOS_FREELANCE_AUTOPILOT=0/1` в `.env.example` + per-platform профиль изоляция.
- **CLI v19** (`aios_cli/chrome_twin.py`): команда `freelance` + args `--platform/--proposal/--budget/--days/--hourly-rate/--verify`.

### Security
- Confirm-by-default: все новые платформы требуют `confirm=True` или `AIOS_FREELANCE_AUTOPILOT=1` + Telegram approve flow.
- Конституционный фильтр Article V сохранен, добавлены freelance-специфичные проверки.

## [18.0.0] — 2026-08-06 — AIOS Autonomous Treasury, Quant Trading, Multi-Agent Swarm & Web3 Major Release

### Added
- **Autonomous Crypto Treasury & 4-Way Profit Distribution (25%/25%/25%/25%)**:
  - `AIOSWalletManager` (`aios_core/crypto_wallet.py`): Multi-chain EVM wallet & automated gross accounting ledger.
  - `AIOSTreasuryManager` (`aios_core/treasury_manager.py`): Automated reserve auditing (3-month survival buffer) and On-Chain DeFi lending APY retrieval (Aave V3 Polygon & Compound V3 Base).
  - `YieldSweeper` (`run_yield_sweeper.py`): Automated weekly dividend sweeping and clearing across 4 system wallets.
  - `AccountingReporter` (`aios_core/accounting_reporter.py`): Automated daily generation of comprehensive `.xlsx` financial workbooks.
- **Crypto-to-Card Fiat Dispatcher & Kraken Integration**:
  - `AIOSFiatDispatcher` (`aios_core/fiat_dispatcher.py`): Live Binance Spot `USDT/UAH` rate integration and automated Visa/Mastercard fiat withdrawal pipeline.
  - `AIOSKrakenClient` (`aios_core/kraken_client.py`): REST API client with HMAC-SHA512 authentication, live ticker queries, and market order execution.
- **Quant Trading Engine & Paper Trading**:
  - `AIOSQuantTradingEngine` (`aios_core/quant_trading_engine.py`): Real-time multi-exchange market radar (Binance & Kraken) analyzing SMA Fast/Slow crossovers and RSI indicators for BTC, ETH, and SOL.
  - Autonomous Paper Trading portfolio simulator with automated PnL calculation and win-rate tracking.
- **Gitcoin & Algora Bounty Auto-Solver**:
  - `GitcoinAlgoraSolver` (`run_gitcoin_algora_solver.py`): Automated discovery of open bounties, LLM-powered solution synthesis, pull request/comment creation, and payment collection.
- **SRE Self-Reflective Healer**:
  - `SRESelfReflectiveHealer` (`aios_core/sre_healer.py`): Continuous scanning of runtime logs, root-cause diagnosis via LLM, and automated AST code patching.
- **Multi-Modal Vision Cascade**:
  - `PhotoRecognition` (`run_photo_recognition.py`): Triple-fallback vision engine (Gemini Vision ➔ Mistral Pixtral ➔ Local Ollama `qwen2.5vl:3b`).
- **Interactive Telegram Operator Menu**:
  - `run_telegram_bot.py`: Main Menu keyboard with direct access to Treasury, Quant Trading, Warehouse/OLX, Nova Poshta logistics, Phone/Banking, and SRE Diagnostics.

## [17.0.0] — 2026-08-02 — AIOS Meta-Cognitive Self-Coder & Autonomous Evolution

### Added
- **Meta-Cognitive Self-Coder (`aios_core/meta_cognitive_self_coder.py`)**: Autonomous self-design, test generation, and architectural refactoring.
- **Autonomous Digital Earnings Engine (`aios_core/autonomous_earnings_engine.py`)**: 100% digital self-sustaining intelligence.

## [16.0.0] — 2026-07-30 — AIOS Universal Cross-Platform Execution Adapters Major Release

### Added
- **Universal Cross-Platform Execution Adapters (`aios_core/adapters/`)**:
  - `APIAdapter`: Universal REST, GraphQL, gRPC, and WebSocket execution.
  - `WebAdapter`: Headless browser, DOM element scraping, and web RPA.
  - `IoTAdapter`: MQTT topic publishing, CoAP, Modbus, and Zigbee sensor/actuator control.
  - `ARMEmbeddedAdapter`: ARM Cortex / Raspberry Pi GPIO pin I/O and Serial UART/SPI/I2C.
  - `RouterNetworkAdapter`: Router SSH, SNMP, OpenWrt ubus, and NETCONF network configuration.
  - `QuantumAdapter`: Quantum circuit execution over Qiskit, Cirq, and OpenQASM hardware simulators.
  - `BlockchainNodeAdapter`: Web3/EVM smart contract interaction and transaction execution.
  - `UniversalAdapterRegistry`: Master registry routing execution through any platform adapter.
- **REST API & Developer SDK Integration**:
  - `POST /api/adapters/execute` & `GET /api/adapters/stats`.
  - Python SDK methods `execute_adapter_action()` & `get_adapter_stats()`.
