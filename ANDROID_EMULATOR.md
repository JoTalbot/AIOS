# AIOS: мобильный стенд из коробки

Для повторяемого запуска на `ua.slando`/OLX-инфраструктуре используются:
- `python3`, `pytest`, `httpx`, `graphql-core`, `websockets`, `grpcio`
- Android SDK (`adb`, `emulator`, `avdmanager`)
- AVD `AIOS_Slando` (Android API 35, x86_64)

# Быстрый старт

```bash
bash setup/android-emulator-env.sh
bash android-bootstrap.sh
```

# Makefile

```makefile
.PHONY: android-setup android-emulator android-test

android-setup:
	bash setup/android-emulator-env.sh

android-emulator:
	bash android-emulator-run.sh

android-test:
	python3 test_real_android_app.py --package ua.slando --device emulator-5554
```
