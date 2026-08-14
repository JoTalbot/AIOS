# Политика версий AIOS

## Источник истины

Каноническая версия основного продукта хранится в корневом файле `VERSION` в формате SemVer.

Некоторые инструменты требуют статические зеркала версии:

- `pyproject.toml` → `project.version`;
- `aios_core/__init__.py` → `__version__`;
- FastAPI metadata получает значение из `aios_core.__version__`;
- workflow документации читает `VERSION` во время публикации.

Зеркала не являются независимыми источниками. Их согласованность блокируется тестом `tests/test_release_version.py`.

## Отдельные версии

Версии самостоятельных поставляемых компонентов могут отличаться от версии основного продукта:

- Python SDK: `sdk/pyproject.toml` и `sdk/__init__.py`;
- внутренние API protocol versions;
- названия/описания отдельных systemd-сервисов и rollout-контуров.

Метка `v20` или `v21` в имени сервиса не означает автоматический bump основного package release.

## Release checklist

1. Создать отдельную release-сессию и claim согласно `coordination/README.md`.
2. Обновить `VERSION`, `pyproject.toml` и `aios_core.__version__` одним release-коммитом.
3. Так как `aios_core/__init__.py` защищён, выполнять изменение только как явно разрешённую ручную release-операцию и затем создать selfguard snapshot по `AGENTS.md`.
4. Обновить `CHANGELOG.md` и release notes.
5. Выполнить:

   ```bash
   source /opt/aios/.venv/bin/activate
   pytest tests/test_release_version.py -q
   python -m py_compile main.py aios_core/__init__.py
   git diff --check
   ```

6. Не заменять номера в исторических audit/release документах. Добавлять явную пометку, что это snapshot.
7. Не выводить новую общую версию из названия одного сервиса или незавершённого roadmap milestone.

## Документация

- Актуальная package version: `VERSION`.
- История релизов: `CHANGELOG.md` и `docs/releases/`.
- Текущая рабочая точка: `coordination/PROJECT_CONTEXT.md`.
- Документы с пометкой «исторический снимок» сохраняют цифры соответствующего аудита и не используются как текущий status.
