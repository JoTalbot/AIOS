Platforms
=========

AIOS supports 9+ platforms through a descriptor-based architecture.

Supported Platforms
-------------------

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Platform
     - Package
     - Status
   * - OLX.ua
     - ua.slando
     - Full stack: collector, detail, messenger, own, competitor, advisor, autowatch
   * - Instagram
     - com.instagram.android
     - Full stack: login-wall, collector, detail, guarded Direct, Reels, autopilot
   * - Facebook Marketplace
     - com.facebook.katana
     - OLX-like marketplace scaffold
   * - TikTok
     - com.zhiliaoapp.musically
     - Collector, onboarding
   * - Viber
     - com.viber.voip
     - Messaging, onboarding
   * - WhatsApp
     - com.whatsapp
     - Messaging, onboarding
   * - Prom.ua
     - com.prom.ua
     - Marketplace scaffold
   * - Bigl.ua
     - com.bigl.ua
     - Marketplace scaffold
   * - Shafa.ua
     - com.shafa.ua
     - Marketplace scaffold

Architecture
------------

All platforms follow the same pattern:

1. **Descriptor YAML** — Platform metadata, package name, UI hints, compliance flags
2. **Registry** — ``android_registry.py`` loads descriptors and resolves capabilities
3. **ProfileStore** — Resolves platform-specific profile configuration
4. **DevicePool** — Lease/release devices with sticky routing
5. **Scaffold** — Auto-generates platform code from templates
6. **Codegen** — Generates UI interaction code from calibration data
7. **Bootup** — Verifies platform readiness

Onboarding a New Platform (≤30 min)
------------------------------------

.. code-block:: bash

   # 1. Create scaffold
   aios platforms scaffold --platform prom --package com.prom.ua --type marketplace

   # 2. Get calibration recipe (ADB commands)
   aios platforms doctor --platform prom --calibrate-recipe

   # 3. On device: dump UI and calibrate
   aios platforms calibrate --platform prom --dump /tmp/ui.xml --write

   # 4. Generate code
   aios platforms codegen --platform prom --force

   # 5. Verify boot
   aios platforms bootup --verify

Compliance
----------

Each platform descriptor includes compliance flags:

.. code-block:: yaml

   # platforms/instagram.yaml
   extras:
     compliance:
       autopost: false      # deny by default
       collect: false       # deny by default
       send: false          # deny by default
       auto_send: false     # deny by default
       note: "Requires manual approval per ToS"

The ``compliance_guard`` in ``platforms/compliance.py`` enforces deny-by-default
for all actions unless explicitly allowed.

Pacing
------

Human-like pacing is enforced via ``platforms/pacing.py``:

.. code-block:: python

   from platforms.pacing import Pacer

   pacer = Pacer(
       actions_per_hour=45,
       jitter_range=(0.8, 2.5),
       session_max_minutes=30,
   )
   pacer.before_action()  # blocks or raises if limit exceeded

Production Profiles
-------------------

Instagram production profiles (v9.2.0):

.. code-block:: python

   profiles = [
       {"name": "ig_shop_1", "aph": 45, "session_max": 30, "jitter": (0.8, 2.5)},
       {"name": "ig_shop_2", "aph": 50, "session_max": 30, "jitter": (0.8, 2.5)},
       {"name": "ig_shop_3", "aph": 40, "session_max": 25, "jitter": (0.8, 2.5)},
   ]

See :doc:`production` for full exploitation guide.
