# Сессия: paper-контур — диагностика блокировок входа

---
session_id: "20260814T160500Z-aios-arena-paper-fix"
status: "DONE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T16:05:00Z"
updated_utc: "2026-08-14T16:15:00Z"
branch: "agent/20260814-paper-fix"
base_commit: "9d5dbd7b"
claim: "coordination/claims/paper-fix--20260814T160500Z-aios-arena-paper-fix.md"
---

## Цель

Разобраться, почему owner-approved paper-контур (aios-quant-trading) не открывает позиции, и починить так, чтобы paper-вход реально работал без изменения owner-профиля риска. Live запрещён.

## Диагноз

- `exchange_not_allowed` 96/цикл — by design: owner-профиль ограничивает kucoin,bitstamp,mexc (7 из 10 бирж вне allowlist). Не баг.
- `ml_not_confirmed` 17/цикл — корневой блокер: развёрнутая CatBoost-модель (Colab, 2026-08-12) деградирована — prob_up=0.433 ровно для 30/35 активов, AUC 0.504, на OOS ни разу >=0.60. Гейт 0.65 физически недостижим.
- Причина деградации: обучение на сырых абсолютных ценах (BTC 95000 vs PEPE 2.7e-6) в одном пуле без нормализации + финальный fit на всех данных без честного OOS.

## Решение

1. Новый `scripts/quant_ml_eval_train.py`: строгий per-symbol walk-forward (train 70% / test 30%, gap 48 бар), масштаб-инвариантные признаки (ret1..24, rsi, bb_pos, macd_norm, ema_gap, vol_ratio, vol_z, bar_range_pct, hl_pos), label = направление следующего 1h бара.
2. Кандидат `catboost_price_dir_v2.cbm` (AUC 0.533) валидирован на двух независимых OOS-окнах:
   - среднее окно (train 55%): hit@0.65=81.3%, 32 сделки, win 68.8%, avg +0.59% net, итог +18.9%
   - последнее окно (train 70%): hit@0.65=83.3%, 36 сделок, win 75.0%, avg +0.74% net, итог +26.5%
   - симуляция по правилам движка (TP+2%/SL-1%/trail, комиссии 0.5% round-trip, исполнение по триггерному уровню)
3. `aios_core/quant/ml_predictor.py`: DEFAULT_FEATURES → 13 scale-free признаков (1:1 формулы), приоритет загрузки catboost_price_dir_v2.cbm; старая модель остаётся fallback'ом (откат = удалить v2).
4. Признаки предиктора сверены с тренировочным скриптом — совпадение 1:1 (abs diff < 1e-9).

## Проверки

- [PASS] python -m py_compile aios_core/quant/ml_predictor.py, scripts/quant_ml_eval_train.py
- [PASS] pytest quant-набор: 18 passed (directional_v2, run_quant_trading_v2, v2_gate, walkforward_v2, signal_product, signal_api, directional_policy)
- [PASS] feature parity: тренировочный скрипт vs предиктор (BTC CSV) — 1:1
- [PASS] run_quant_ml_inference.py: ml_signals.json перегенерирован моделью v2, prob_up 0.38-0.60 (различаются), 1 актив >=0.60
- [PASS] gate-проверка с owner-профилем: ML=0.70 conf=0.90 → вход разрешён (None); ML=0.45 → ml_not_confirmed; binance → exchange_not_allowed
- [NOT RUN] полный pytest suite (5 198 тестов) — затронуты только quant/ml пути, покрыты выше

## Изменённые файлы

- `scripts/quant_ml_eval_train.py` — новый: диагностика + обучение кандидата + симуляция paper-сделок
- `aios_core/quant/ml_predictor.py` — scale-free признаки v2, приоритет модели v2
- `data/quant/models/catboost_price_dir_v2.cbm/.pkl` — runtime-артефакт (git-ignored), старый .cbm сохранён

## Git

- Branch `agent/20260814-paper-fix`, commit `8d668f03` (2 файла, +336/-7). Не закоммичены: coordination/sessions, claims, PROJECT_CONTEXT (следующий коммит).

## Handoff

- Paper-вход Directional v2 структурно разблокирован: гейт ML=0.65 теперь достижим реальной моделью; сделки будут открываться при появлении prob_up>=0.65 (редкие, ~1-2/мес — селективность гейта).
- Следующий шаг: наблюдать циклы демона (полный скан на границе часа); при появлении WATCH/сделки — сверить PnL с симуляцией.
- Известные ограничения: (1) RL-мост деградирован — onehot-баг (все активы получают индекс BTC) → все 10 мажоров FLAT → rl_veto блокирует вход по BTC/ETH/SOL/BNB/XRP/ADA/DOGE/LINK/DOT/MATIC; 25 активов вне RL-карты не затронуты. Требует отдельного решения владельца (фикс onehot + переобучение PPO в Colab). (2) MATIC/RNDR — мёртвые тикеры (переименованы в POL/RENDER), засоряют universe сигнального продукта.
- Что нельзя делать без повторной проверки: включать live (гейт walk-forward отрицательный), менять пороги owner-профиля, удалять старую модель до подтверждения работы v2.
