AIOS — Autonomous Intelligence Operating System
=================================================

.. image:: https://img.shields.io/badge/version-9.2.0--production-blue
   :target: https://github.com/JoTalbot/AIOS

.. image:: https://img.shields.io/badge/tests-1010%20passing-green
   :target: https://github.com/JoTalbot/AIOS/actions

.. image:: https://img.shields.io/badge/python-3.10%2B-blue
   :target: https://www.python.org/

**Версия 9.2.0-production** | 23 июля 2026

AIOS — саморазвивающаяся распределённая операционная система для интеллекта приложений,
автоматизированного тестирования, генерации API, эволюции навыков и коллективного обучения.
Работает на **Octopus Runtime**.

.. note::
   AIOS v9.2.0-production — GA-релиз: 1010 тестов, 3 IG профиля ≥2 недели без банов
   в симуляции, 143 API маршрута, SDK v4.2.0, Marketplace v2.

Содержание
----------

.. toctree::
   :maxdepth: 3
   :caption: Документация:

   architecture
   api
   modules
   platforms
   production

Быстрые ссылки
--------------

- `GitHub Repository <https://github.com/JoTalbot/AIOS>`_
- `Production Exploitation Guide <PRODUCTION.html>`_
- `Security & Secrets Rotation <SECURITY.html>`_
- `Constitution (67 Articles) <constitution.html>`_

Компоненты
----------

1. **Конституция и политики** — 67 статей, загрузка правил, runtime decision pipeline
2. **Оркестратор** — последовательное выполнение задач с конституционной оценкой
3. **SQLite-персистентность** — аудит, одобрения, память, граф знаний, эволюция
4. **MCP Gateway** — JSON-RPC 2.0 tools/resources/prompts
5. **REST API** — 143 маршрута, Starlette, bearer auth
6. **Production Autopilot** — compliance, pacing, predictive risk, 3 IG profiles
7. **AI Advisor** — draft-only, human-approve, template registry per platform
8. **SDK v4.2.0** — async/sync Python client, 25+ методов
9. **Marketplace v2** — capability + platform plugins, install/verify

Индексы
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
