# Android Module Roadmap

## Current Status: v9.0.0+ (ua.slando)

## Milestones

### M1 — Stable Real-Device Execution
**Goal:** Replace simulation with deterministic UI-driven scenario.

- Screen precheck before each action via AIScreenClassifier
- Caretaker fallback with coordinate matrix zones for unknown search fields
- ADBKeyboard APK integration in bootstrap (`--keyboard` flag)
- Handle system dialogs, permissions popups, crash windows
- Retry logic and latency profiling
- XML parsing in `search/get_item_details/send_message`
- Click coordinate detection by `resource-id`/`text`
- Stable Cyrillic input via ADB
- Retries/backoff on `uiautomator dump` failures

**Status:** ✅ Completed

**Deliverables:**
- `aios_core/android_execution.py`
- `aios_core/android_parser.py`
- Verified via emulator smoke test on `emulator-5554`

---

### M2 — Appium and Sessions
**Goal:** Add alternative stable driver alongside raw ADB.

- Appium / UiAutomator2 integration
- Unified `AndroidDriver` interface over adb and appium
- Gesture/scroll/web-view support
- Headless CI-ready execution
- AppiumAndroidDriver optional iterative replay from ScenarioRecorder
- Session serialization/deserialization for continue later
- uiautomator2 server-side fallback on UiAutomator crash

**Status:** ✅ Completed

**Deliverables:**
- `aios_core/android_driver.py`
- `aios_core/android_appium.py`
- `aios_core/android_recorder.py`

---

### M3 — Multi-App Registry
**Goal:** Support N apps via descriptor-based registry.

- Platform-agnostic endpoints for search/message/details
- App registration per-descriptor
- Verified packages: `ua.slando`, `com.facebook.katana`, `com.instagram.android`
- Real FB/IG/Viber adapters from `aios_core/platforms`
- Descriptor-driven action selection by package
- `load_from_catalog()` mounted in REST `/api/v1/apps/{platform}`

**Status:** ✅ Completed

**Deliverables:**
- `aios_core/android_registry.py`

---

### M4 — Fleet Management
**Goal:** Parallel execution across a pool of emulators/devices.

- Device pool: lease/release/heartbeat
- Sticky route: profile → device serial
- Cross-emulator stale-device cleanup
- WebSocket device pool status monitor
- Lease distribution by priority/AVD affinity
- Quota per profile + circuit breaker

**Status:** ✅ Completed

**Deliverables:**
- `aios_core/android_fleet.py`

---

### M5 — AI Navigation
**Goal:** Screen classification and self-healing locators.

- Lightweight screen classifier grounded in UIAutomator parser
- Retry wrappers for UI changes
- Self-healing locators via similarity heuristics
- Real CV template matcher (`opencv-python`)
- Memory-backed locators with auto-retrain on failure
- Hooks into `multidimensional_world_model.py`

**Status:** ✅ Completed

**Deliverables:**
- `aios_core/android_ai_navigation.py`

---

### M6 — Observability
**Goal:** Full Android execution tracing.

- Structured execution events: tap/type/swipe latency, screen, package
- Failure-rate tracking and summary stats
- JSON emission through existing telemetry surface
- Telemetry hook into `aios_core/telemetry.py`
- Per-action alerts
- Android metrics mounted in `web_ui`

**Status:** ✅ Completed

**Deliverables:**
- `aios_core/android_observability.py`
- `tests/test_android_rpa_bridge.py`: Unit tests for Android RPA Bridge

---

## General
- `--real-emulator` CI job
- Latency profiling per tap/type/swipe
- Session reuse
- Desktop bootstrap shortcut
- Real-device pipeline for `ua.slando` on emulator

## Additional
- `aios_core/android_rpa_bridge.py`: Android RPA & Appium/ADB Emulator Automation Bridge

## Execution Order
M1 → M2 → M3 → M4 → M5 → M6

## Dependencies
- Android SDK / Emulator
- ADB + ADBKeyBoard
- Appium server (optional for M2)
- Python deps: `appium-python-client` (optional), `pytest`

## Success Criteria
- Unit tests pass on `emulator-5554`
- All M1-M6 modules importable: `python3 -c "from aios_core..."`
- CI job with headless emulator
