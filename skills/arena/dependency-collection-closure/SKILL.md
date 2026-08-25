---
name: dependency-collection-closure
version: 1.0
description: Закрывает missing-import CI collection failures через direct dependencies и минимальный exact-lock diff без массового upgrade.
triggers: [dependency-contract, pytest-collection, requirements-lock, missing-module]
dependencies: [pip-tools]
llm_required: false
mcp_tools: []
---

# Dependency Collection Closure

## Описание

Применять, когда production/CI tests импортируют пакет, отсутствующий в
`requirements.txt` и `requirements.lock`. Сохраняет контракт minimal ⊆ direct ⊆ lock и
не принимает массовый resolver diff.

## Алгоритм

1. Воспроизвести `pytest tests --collect-only` в Python версии production.
2. Подтвердить, что импорт относится к production runtime, а не только dev tooling.
3. Добавить bounded direct constraint в `requirements.txt`; minimal `pyproject.toml`
   менять только для библиотечной основы.
4. Сначала выполнить канонический pip-compile без `--upgrade`. Если внешний index
   недоступен, остановить процесс и убедиться, что lock не изменён.
5. Для точечной диагностики создать временный input с `-c requirements.lock` и новыми
   direct deps. Исключить из временного constraint только пакеты, которые новый wheel
   требует точными несовместимыми pins; получить resolver-approved минимальный набор.
6. В lock изменить только этот набор, сохраняя алфавитный exact-pin формат.
7. Проверить `check_dependency_contract --strict`, dependency unit test, `pip check`,
   полный collect и тесты ранее падавших модулей.
8. Если dependency-count test использует точные числа, синхронизировать его с фактическим
   отчётом checker.

## Контроль и развитие

- [x] pandas/ccxt collection gap закрыт.
- [x] CCXT exact transitive pins получены resolver'ом, не угаданы вручную.
- [x] Full collection и 36 целевых tests прошли.
- [ ] Канонический full pip-compile повторить в среде с доступным PyTorch CPU index.
