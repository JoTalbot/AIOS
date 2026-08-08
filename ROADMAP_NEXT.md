# AIOS Roadmap — Next Milestones (актуализировано 2026-08-08)

> Текущая версия: **v19.9.0** | Инфраструктура: 23 systemd-сервиса активны, 0 failed | Docker-стек: healthy
> Документ заменяет устаревший роадмап (все пункты v18.x–v19.x закрыты).

---

## ✅ Завершено: v18.0.0 → v19.9.0 (2026-08-06 — 2026-08-08)

### v18.0.0 — Autonomous Treasury, Web3 & Multi-Agent Swarm
- ✅ Autonomous Crypto Treasury & 4-Way Split (25%×4: Dev / Investor / Personnel / System)
- ✅ DeFi Lending APY & Yield Sweeper (Aave V3 Polygon, Compound V3 Base)
- ✅ Live Binance Spot Fiat Dispatcher (USDT/UAH → Visa/Mastercard)
- ✅ Kraken Exchange Client (HMAC-SHA512, тикеры, ордера)
- ✅ Quant Trading Engine & Paper Trading (SMA/RSI; BTC, ETH, SOL)
- ✅ Gitcoin & Algora Bounty Auto-Solver
- ✅ SRE Self-Reflective Healer (автопатчинг по трейсбекам)
- ✅ Multi-Modal Vision Cascade (Gemini → Pixtral → Ollama qwen2.5vl:3b)
- ✅ Interactive Telegram Operator Dashboard (Казначейство/Трейдинг/Склад/НП)

### v19.0 → v19.4 — Chrome Twin, Liquidity, Flash-Loan, Mesh
- ✅ **v19.0** Autonomous Freelance Chrome Twin (Freelancehunt/Upwork/Fiverr, safe autopilot)
- ✅ **v19.1** Smart Liquidity Router (4 сети: Polygon/Base/Arbitrum/Solana, bridge dry-run)
- ✅ **v19.2** Flash-Loan Arbitrage (cross-DEX/CEX сканер + Aave V3 симуляция)
- ✅ **v19.3** Android Mesh Fleet v1 (регистрация устройств, lease/release, heartbeat)
- ✅ **v19.4** Telegram Control — кнопки Liquidity/Flash/Mesh в боте

### v19.5 → v19.9 — Freelancehunt Anti-Block & Scale
- ✅ **v19.5** Freelance Browser Fallback (Playwright bypass 403)
- ✅ **v19.6** Stealth mode для Cloudflare
- ✅ **v19.7** FlareSolverr в Docker (127.0.0.1:8191)
- ✅ **v19.8** FH API пагинация ×3 = 30 проектов/цикл
- ✅ **v19.9** FH пагинация до 50 (`AIOS_FH_PAGES`) + Python-фильтр

---

## 🚀 v20.0.0 — «Activation»: от кода к деньгам (ГЛАВНЫЙ ПРИОРИТЕТ)

> Проблема: v19.1–v19.3 собраны и протестированы, но работают только в scan/dry-run — демонами не запущены, реальных сделок нет. v20.0 = включение построенного в боевой контур.

- 🔲 **Flash-Loan Arbitrage → Live**: запуск `--daemon` с порогом spread ≥1.5% (сейчас рынок даёт ~0.13% — виабельных сделок 0; нужен алертинг при появлении окна, а не постоянный скан)
- 🔲 **Smart Liquidity Router → Daemon**: ежедневный ребаланс-скан 4 сетей + TG-отчёт в утренний бриф; auto-execute только при ΔAPY > 2% и сумме < лимита безопасности
- 🔲 **Android Mesh → 2-е устройство**: подключение второго телефона в fleet, распределение OLX-чатов и банк-мониторинга по устройствам (разгрузка единственной точки отказа)
- 🔲 **Freelance → First Win**: из 50 проектов/цикл и BID_SUBMITTED — трекинг конверсии bid→win, A/B тест текстов ставок, фокус на 3-5 нишах с наибольшим win-rate
- 🔲 **Treasury наполнение**: первый реальный incoming revenue через live on-chain listener → автоматический 4-way split

## 🔧 v20.5.0 — «Hygiene»: технический долг

- 🔲 **Разбор монолита** `run_telegram_bot.py` (511 КБ, 8700+ строк) → модули `tg/handlers/*`
- ✅ **Чистка `.bak` файлов** → единый attic/bak_cleanup_20260808 (19 файлов, 1.6 МБ перенесено; .bak в .gitignore)
- ✅ **Диск 76% → 74%**: старые backups (1.4 ГБ) удалены по ротации; swap 4G + swappiness=10; health-check OK 18/18
- 🟡 **Тесты**: покрытие run_*.py раннеров — добавлены test_phone_sync_status (7) и test_run_swarm_backtester (2); всего покрыто ~30 из 105 раннеров
- ✅ **Dependabot**: 18 осиротевших remote-веток вычищены (git remote prune origin), открытых PR — 0

## 📈 v21.0.0 — «Scale»: масштабирование работающего

- 🔲 **OLX вертикаль**: авто-выставление объявлений по инвентарю (run_olx_ad_gen уже есть → полный цикл inventory→ad→sale→TTN)
- 🔲 **Multi-niche freelance**: расширение с Python-скрапинга на data-engineering и TG-ботов (готовые компетенции системы)
- 🔲 **Mesh 3+ устройств**: тарифные планы, отдельные SIM/аккаунты на устройство
- 🔲 **DeFi стратегии**: leveraged yield (осторожно, constitutional REVIEW-гейт обязателен)

## 🌐 v22.0.0 — «Platform»: продукт наружу

- 🔲 **SaaS-пилот**: AIOS-как-сервис для 1-2 внешних клиентов (multi-tenancy из aios_core/multitenancy.py)
- 🟡 **API-монетизация**: groundwork 2026-08-08 — /api/v2/mon/* (olx-price $0.10 live, audit, summarize, balance), key store + bearer allowlist; Phase B пилот за approve владельца
- 🟡 **White-label OLX-автоматизация** для автоназборок: groundwork 2026-08-08 — tenant-конфиги брендов + изолированные черновики (markup/квота), публикация за approve

---

### Принципы роадмапа
1. **Revenue first** — фича считается done только когда приносит или измеримо экономит.
2. **Constitutional gates** — всё финансово-рискованное идёт через REVIEW, лимиты в .env.
3. **No new skeletons** — новый модуль только под конкретный работающий раннер, без «витринных» заглушек.
