/root/AIOS
├── android-bootstrap.sh
├── android-emulator-run.sh
├── setup
│   └── android-emulator-env.sh
├── test_real_android_app.py
└── tests
    └── test_android_rpa_bridge.py

# Quick Start

1) Setup AVD and env:
   bash setup/android-emulator-env.sh

2) Full bootstrap from clean checkout:
   bash android-bootstrap.sh

3) Run only real-app test:
   python3 test_real_android_app.py --package ua.slando --device emulator-5554

# Notes
- Default AVD: AIOS_Slando
- Default device: emulator-5554
- Package: ua.slando