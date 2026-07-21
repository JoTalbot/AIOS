# AIOS Official Release Notes — Version 9.0.0-alpha.2

**Release Tag:** `v9.0.0-alpha.2`  
**Release Date:** July 21, 2026  
**Repository:** `JoTalbot/AIOS`  
**Constitutional Compliance:** 100% (67 Articles Validated via `tula`)  
**Automated Test Coverage:** 603 / 603 Tests Passing (100% Green)

---

## 🌟 Executive Summary

`v9.0.0-alpha.2` extends the OLX Parser Agent from a library into an
always-on data service: periodic scheduled collection in the background and
a full REST control surface. All OLX pipelines now run unattended and are
exposed through the standard authenticated AIOS REST API.

---

## 🚀 What's New

### ⏱ OLX Collection Scheduler (`aios_core/modules/olx/scheduler.py`)

- Thread-based periodic collection over a query list with configurable
  interval and card budget.
- Run history with `parsed` / `inserted` / `total` counters per query.
- Idempotent `start()` / `stop()`; safe to embed in the REST API or CLI.

### 🌐 OLX REST endpoints (`/api/v1/modules/olx/*`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/modules/olx/ads` | Stored ads (query filter, bounded limit) |
| GET | `/api/v1/modules/olx/stats` | Competitor market statistics per query |
| POST | `/api/v1/modules/olx/recommendations` | Listing advice for a draft ad |
| POST | `/api/v1/modules/olx/collect` | One-off ADB collection run |
| POST | `/api/v1/modules/olx/schedule` | Start periodic background collection (`interval_s >= 10`) |
| DELETE | `/api/v1/modules/olx/schedule` | Stop collection, returns recent run history |

### 🔧 Improvements

- `OLXStorage` is now thread-safe (`check_same_thread=False` + write lock),
  serving the HTTP loop and the scheduler thread from one connection.
- `AdCard.fingerprint` includes the search query: the same ad surfaced by
  different queries is now tracked once per query, keeping per-query market
  reports consistent (fixes cross-query dedupe collisions).
- 14 new tests (scheduler + REST API) — total suite: **603 passed**.

---

## ✅ Verification

```bash
python -m pip install -r requirements.txt
python -m pytest -q        # 603 passed
python -m build            # dist/aios-9.0.0a2-*.{whl,tar.gz}
```

Base platform notes: [RELEASE_NOTES_9.0.md](RELEASE_NOTES_9.0.md).
Full delta: [CHANGELOG.md](CHANGELOG.md).
