AIOS Modules
============

Core Modules
------------

The AIOS core consists of the following modules:

aios_core/
├── __init__.py
├── orchestrator.py            # Sequential task execution with constitutional evaluation
├── constitution_engine.py     # 67-article constitution loading and runtime decision pipeline
├── autonomy_manager.py        # Autonomy levels 1-5 regulation
├── ai_advisor.py              # AI Advisor — draft-only, human-approve, template registry
├── marketplace.py             # Marketplace v2 — capabilities + platform plugins
├── production_autopilot.py    # Production exploitation — compliance, pacing, predictive
├── memory.py                  # Personal memory with subject-scoped isolation
├── knowledge_graph.py         # Knowledge graph persistence and querying
├── evolution.py               # Evolution state transitions
├── privacy.py                 # Privacy controls and data isolation
├── event_bus.py               # Event bus for inter-component communication
├── planner.py                 # ML planner scorer and plan optimization
├── capability.py              # Capability engine and registry
├── formal_code_verifier.py    # AST-based formal code verification
├── substrate_convergence.py   # Substrate routing (Silicon/Photonic/Quantum/Bio)
├── ai_safety.py               # AI safety and alignment
├── ai_safety_constitutional.py # Constitutional AI safety
├── agent_swarm.py             # Multi-agent swarm coordination
├── active_learning.py         # Active learning engine
├── advanced_security.py       # Advanced security controls
├── ab_testing.py              # A/B testing framework
└── modules/                   # Platform-specific modules
    ├── olx/                   # OLX.ua full stack
    ├── instagram/             # Instagram full stack
    ├── facebook/              # Facebook Marketplace
    ├── tiktok/                # TikTok integration
    ├── viber/                 # Viber integration
    ├── whatsapp/              # WhatsApp integration
    ├── prom/                  # Prom.ua marketplace
    ├── bigl/                  # Bigl marketplace
    └── shafa/                 # Shafa marketplace

Platform Modules (aios_core/modules/)
--------------------------------------

OLX
^^^

Full stack for OLX.ua marketplace:

- ``collector.py`` — Card collection and listing scraping
- ``detail.py`` — Detailed card information extraction
- ``messenger.py`` — Guarded messaging with compliance
- ``own_ads.py`` — Own ads management
- ``competitive.py`` — Competitor analysis
- ``advisor.py`` — AI-powered pricing and reply advice
- ``autowatch.py`` — Automatic watch/favorites
- ``subscriptions.py`` — Subscription management
- ``analytics.py`` — OLX analytics and reporting
- ``storage.py`` — SQLite persistence for OLX data
- ``card_parser.py`` — Card HTML/JSON parsing
- ``ui_parser.py`` — UI element parsing for automation
- ``adb.py`` — ADB device control
- ``bootstrap.py`` — OLX platform initialization
- ``scheduler.py`` — Task scheduling
- ``promotion.py`` — Ad promotion management
- ``profile.py`` — Profile management
- ``notifier.py`` — Notification dispatch
- ``text_utils.py`` — Text processing utilities
- ``models.py`` — Data models

Instagram
^^^^^^^^^

Full stack for Instagram:

- Login-wall driver for authentication
- Collector and detail extraction
- Guarded Direct messaging
- Own posts composer
- Reels collector with receipts
- Autopilot integration
- Cron-plan scheduling
- Multi-account waitlist management
- Doctor for platform health checks

Other Platforms
^^^^^^^^^^^^^^^

Each platform module follows a similar structure:

- ``__init__.py`` — Module initialization
- Platform-specific collectors and parsers
- Compliance guard integration
- Scaffold template for new platforms

Android Modules
---------------

Located in the project root and ``aios_core/``:

- ``android_execution.py`` — Deterministic UI-driven execution
- ``android_parser.py`` — XML/Accessibility parsing
- ``android_driver.py`` — Unified ADB/Appium driver
- ``android_appium.py`` — Appium session management
- ``android_recorder.py`` — Session recording and serialization
- ``android_registry.py`` — Multi-app descriptor-based registry
- ``android_fleet.py`` — Device pool management (lease/release/heartbeat)
- ``android_ai_navigation.py`` — AI-powered navigation (64-dim embeddings)
- ``android_observability.py`` — Latency/failure metrics, Prometheus
- ``android_cross_app.py`` — Cross-app workflow engine (OLX→Viber)
- ``android_predictive.py`` — Predictive positioning and trend analysis
- ``android_test_generator.py`` — Auto test generation from recorder flows

SDK
---

``sdk/aios_sdk.py`` — Official Python SDK v4.2.0:

- ``AIOSClient`` — Async client with 25+ methods
- ``AIOSClientSync`` — Synchronous wrapper
- Methods: health, ready, stats, metrics, tasks, evaluate, evolution, memory, kg, android, marketplace, advisor, watch_events (WebSocket)
- Timeout: 30s default
- Example agent in 30 lines
