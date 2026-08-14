# Политика зависимостей AIOS

## Роли файлов

Зависимости разделены по назначению; разные размеры файлов не являются drift сами по себе.

| Файл/секция | Роль |
|---|---|
| `pyproject.toml [project.dependencies]` | Минимальная устанавливаемая библиотека/API-основа |
| `requirements.txt` | Полный список прямых production-зависимостей всех runtime-контуров |
| `requirements.lock` | Точное разрешение direct + transitive для production Docker image |
| `pyproject.toml [project.optional-dependencies].dev` | Инструменты локальной разработки и тестирования |
| `requirements-fly.txt` | Отдельный минимальный Fly.io профиль |

Обязательный инвариант:

```text
minimal project dependencies ⊆ production direct input ⊆ exact production lock
```

Все constraints из minimal/direct должны удовлетворяться версиями lock. Проверка:

```bash
source /opt/aios/.venv/bin/activate
python scripts/check_dependency_contract.py --strict
pytest tests/test_dependency_contract.py -q
```

## Найденный и устранённый конфликт 2026-08-14

`pyproject.toml` требовал `websockets>=16.1.1`, но production использует `web3==7.16.0`, который требует `websockets>=10,<16`. Docker не устанавливает AIOS как package и поэтому этот конфликт metadata не обнаруживался обычным `pip check` внутри runtime.

Согласованный диапазон — `websockets>=15.0,<16.0`; текущий lock `15.0.1` удовлетворяет и AIOS, и Web3.

## Обновление direct dependencies

1. Создать отдельную session/claim.
2. Добавить или изменить direct constraint в `requirements.txt`.
3. Если зависимость входит в минимальную библиотечную основу, синхронизировать `pyproject.toml`.
4. Пересобрать lock **без массового upgrade** в Python версии production image:

   ```bash
   python -m pip install pip-tools
   pip-compile \
     --no-annotate \
     --no-header \
     --strip-extras \
     --no-emit-index-url \
     --extra-index-url=https://download.pytorch.org/whl/cpu \
     --output-file=requirements.lock \
     requirements.txt
   ```

   При существующем output pip-tools использует текущие pins как предпочтительные и меняет только необходимое. Для планового массового upgrade применяется отдельная задача и флаг `--upgrade`.

5. Проверить contract, `pip check` в новой среде и целевые тесты.
6. Не генерировать production lock через `pip freeze`: он захватывает случайные пакеты текущего venv и не сохраняет dependency provenance.

## Production и CI

- `Dockerfile` устанавливает только `requirements.lock`.
- CI может устанавливать `requirements.txt`, чтобы проверить свежую разрешимость direct input, но release image должен использовать lock.
- Docker build и lock generation должны использовать совместимую Python minor version. Production Dockerfile сейчас основан на Python 3.11; хостовый venv использует 3.12 и не является источником lock.
- Любое изменение lock рассматривается как supply-chain изменение и требует diff/review.

## Отдельные профили

Heavy dependencies (`torch`, Qiskit, Web3, ChromaDB) входят в full production profile, но не обязаны входить в minimal package metadata. Их нельзя механически переносить в базовые `[project.dependencies]`, иначе минимальная установка превратится в полный runtime image.
