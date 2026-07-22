# AIOS Android Applications Roadmap

## Current Status: v9.0.0+ (ua.slando)

### Completed
- `aios_core/android_rpa_bridge.py`: Android RPA & Appium/ADB Emulator Automation Bridge
- `aios_core/android_execution.py`: Real Device Execution (M1) — UIAutomator XML parsing, ADB actions, retry logic
- `aios_core/android_driver.py`: Unified AndroidDriver ABC and data models (UIElement, SearchResult, ItemDetails)
- `aios_core/android_appium.py`: Appium Android Driver (M2) satisfying shared AndroidDriver interface
- `aios_core/android_parser.py`: Focused UIAutomator parser submodule (M1)
- `aios_core/android_registry.py`: Multi-App Abstraction / AppRegistry per-package (M3)
- `aios_core/android_fleet.py`: Device Fleet / Pool with lease/release/heartbeat (M4)
- `aios_core/android_ai_navigation.py`: AI Powered UI Navigation, screen classification, self-healing locators (M5)
- `aios_core/android_observability.py`: Observability & Analytics, structured execution events (M6)
- `tests/test_android_rpa_bridge.py`: Unit tests for Android RPA Bridge
- Real-device pipeline for `ua.slando` on emulator

---

## Milestones

### M1: Stable Real-Device Execution
**Goal:** Replace simulation with deterministic UI-driven scenario.

- XML parsing in `search/get_item_details/send_message`
- Click coordinate detection by `resource-id`/`text`
- Stable Cyrillic input via ADB
- Retries/backoff on `uiautomator dump` failures

**Status:** Completed
**Deliverables:**
- `aios_core/android_execution.py`
- `aios_core/android_parser.py`
- Verified via emulator smoke test on `emulator-5554`

---

### M2: Appium Integration
**Goal:** Add alternative stable driver alongside raw ADB.

- Appium / UiAutomator2 integration
- Unified `AndroidDriver` interface over adb and appium
- Gesture/scroll/web-view support
- Headless CI-ready execution

**Status:** Completed
**Deliverables:**
- `aios_core/android_driver.py`
- `aios_core/android_appium.py`

---

### M3: Multi-App Abstraction
**Goal:** Support N apps via descriptor-based registry.

- Platform-agnostic endpoints for search/message/details
- App registration per-descriptor
- Verified packages: `ua.slando`, `com.facebook.katana`, `com.instagram.android`

**Status:** Completed
**Deliverables:**
- `aios_core/android_registry.py`

---

### M4: Device Fleet Management
**Goal:** Parallel execution across a pool of emulators/devices.

- Device pool: lease/release/heartbeat
- Sticky route: profile → device serial
- Cross-emulator stale-device cleanup

**Status:** Completed
**Deliverables:**
- `aios_core/android_fleet.py`

---

### M5: AI-Powered UI Navigation
**Goal:** Screen classification and self-healing locators.

- Lightweight screen classifier grounded in UIAutomator parser
- Retry wrappers for UI changes
- Self-healing locators via similarity heuristics

**Status:** Completed
**Deliverables:**
- `aios_core/android_ai_navigation.py`

---

### M6: Observability & Analytics
**Goal:** Full Android execution tracing.

- Structured execution events: tap/type/swipe latency, screen, package
- Failure-rate tracking and summary stats
- JSON emission through existing telemetry surface

**Status:** Completed
**Deliverables:**
- `aios_core/android_observability.py`

---

## Execution Order
M1 → M2 → M3 → M4 → M5 → M6

## Dependencies
- Android SDK / Emulator
- ADB + ADBKeyBoard
- Appium server (optional for M2 IM2)
- Python deps: `appium-python-client` (optional), `pytest`

## Success Criteria
- Unit tests pass on `emulator-5554`
- All M1-M6 modules importable: `python3 -c "from aios_core..."`
- CI job with headless emulator
