# AIOS Changelog

All notable changes to this project will be documented in this file.

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
