# AIOS Android RPA Emulator Quickstart

End-to-end one-liner from a clean checkout. Completely local test
with the existing headless AVD.

```bash
bash android-bootstrap.sh
```

## Manual steps

```bash
bash setup/android-emulator-env.sh
bash android-emulator-run.sh
python3 test_real_android_app.py --package ua.slando --device emulator-5554
```

## What it does
- Installs Python dependencies
- Creates/validates the `AIOS_Slando` AVD
- Launches headless emulator
- Waits for Android boot
- Runs real app interaction tests for package `ua.slando`
