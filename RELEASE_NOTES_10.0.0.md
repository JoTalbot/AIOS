# RELEASE_NOTES — AIOS v10.0.0

**Release Date:** 2026-07-24
**Test Suite:** 1514 tests passing, 0 failures

## 🚀 Major New Features

### 1. Price Prediction ML Engine (`aios_core/price_prediction_ml.py`)
Full-featured ML-style price prediction without external dependencies:

- **Polynomial Regression** — degree 1 (linear), 2 (quadratic), 3 (cubic) via least-squares fitting
- **Moving Average Models** — SMA, WMA, EMA with configurable windows
- **Ensemble Predictor** — averages multiple models weighted by confidence
- **Trend Detection** — UP, DOWN, STABLE, VOLATILE with automatic detection
- **PricePredictionEngine** — high-level API: `predict()`, `predict_best()`, `predict_all()`
- **Gaussian Elimination** — pure Python solver for normal equations
- **Confidence Scoring** — based on MSE, data points, model fit quality
- **Negative Price Clamping** — predicted prices never go below 0

### 2. Product Image Comparison (`aios_core/image_comparison.py`)
Perceptual hashing for cross-platform duplicate detection:

- **Average Hash (aHash)** — fastest, coarse similarity (8×8 → 64-bit)
- **Difference Hash (dHash)** — gradient-based, better edge detection (9×8 → 64-bit)
- **Perceptual Hash (pHash)** — DCT-based, best accuracy (32×32 → low-frequency 64-bit)
- **Color Histogram Comparison** — RGB binning with intersection similarity
- **ImageComparisonEngine** — composite scoring (hash + color), duplicate detection, best-match search
- **Pixel Resampling** — block averaging for arbitrary-size images
- **2D DCT** — pure Python Discrete Cosine Transform for pHash

### 3. Fleet Scheduler (`aios_core/fleet_scheduler.py`)
Multi-device orchestration for parallel scraping:

- **Device Management** — register, heartbeat, health monitoring, auto-offline detection
- **Task Scheduling** — 4 policies: round-robin, least-busy, priority-first, random
- **Priority System** — CRITICAL → LOW → MAINTENANCE with queue ordering
- **Automatic Retry** — failed tasks re-queued with configurable max retries
- **Cooldown Mechanism** — 3+ failures → device cooldown (configurable duration)
- **Queue Processing** — pending tasks auto-assigned when devices become available
- **Load Balancing** — rebalance from overloaded (>80%) to underloaded (<30%) devices
- **Fleet Statistics** — utilization, reliability, queue depth, success/fail counts

## 📋 CLI Subcommands

- `price-predict predict --fingerprint FP --prices 100 110 120 --model ensemble`
- `price-predict best --fingerprint FP --prices ...`
- `price-predict all --fingerprint FP --prices ...`
- `image-compare hash --pixels ... --algorithm ahash`
- `image-compare compare --source ... --target ... --threshold 0.85`
- `fleet stats` / `fleet register --device-id dev1` / `fleet schedule --platform olx --action collect`

## 🧪 Tests

- `test_price_prediction_ml.py` — 45 tests (polynomial fit, trend detection, SMA/WMA/EMA, ensemble, engine)
- `test_image_comparison.py` — 30 tests (aHash/dHash/pHash, color histograms, engine, duplicates)
- `test_fleet_scheduler.py` — 35 tests (device lifecycle, scheduling policies, retry, cooldown, integration)

## 📊 Version Bump

- v9.9.0 → **v10.0.0** (major version: new ML engine, new CV module, new fleet scheduler)

## 🔧 Bug Fixes

- Fixed `list[float]` typo in `price_prediction_ml.py` (extra `]`)
- Fixed `PredictionModel.LINEAR` not being set for degree=1 polynomial predictor

## 📁 New Files

- `aios_core/price_prediction_ml.py`
- `aios_core/image_comparison.py`
- `aios_core/fleet_scheduler.py`
- `aios_cli/v10.py`
- `tests/test_price_prediction_ml.py`
- `tests/test_image_comparison.py`
- `tests/test_fleet_scheduler.py`
