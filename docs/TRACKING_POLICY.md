# Политика отслеживания source/config и runtime-данных

## Основной принцип

Исходный код, manifests, dashboards, примеры и воспроизводимая конфигурация должны отслеживаться Git. Runtime state, backups, credentials, персональные и бизнес-данные должны игнорироваться по **конкретному пути или назначению**, а не по глобальному расширению.

Запрещены глобальные правила наподобие:

```gitignore
*.json
*.yaml
```

Они скрывают новые конфигурационные файлы от `git status`, и агент ошибочно считает локальный файл сохранённым в репозитории.

## JSON

Отслеживаются:

- Grafana dashboards и monitoring configuration;
- plugin/package manifests;
- небольшие обезличенные fixtures/examples;
- schema и API assets без credentials.

Игнорируются точечно:

- `data/`, `Calls/`, mutable runtime databases/state;
- backup snapshots и key-cleanup directories;
- coverage/CatBoost output;
- `docs/warehouse_pricelist.json` как генерируемый business inventory snapshot;
- любые `.llm_keys.json`, vault, token и credential files.

Перед добавлением нового JSON:

1. Проверить, почему он был создан и кто его обновляет.
2. Не добавлять значения secrets/PII.
3. Выполнить Gitleaks или эквивалентный redacted scan.
4. Если файл runtime — добавить узкий ignore pattern и тест.
5. Если файл source/config — добавить в Git и при необходимости в tracking contract.

## Каталоги с именем build

Общее `build/` остаётся правилом для артефактов, но `skills/stitch/build/` — название исходной категории Stitch skills, а не build output. Для него есть явное исключение:

```gitignore
!/skills/stitch/build/
!/skills/stitch/build/**
```

Android `app/build/` и остальные реальные build outputs остаются ignored.

## Автоматическая проверка

```bash
source /opt/aios/.venv/bin/activate
python scripts/check_tracking_policy.py --strict
pytest tests/test_tracking_policy.py -q
```

Checker гарантирует:

- отсутствие глобального `*.json`;
- наличие необходимых manifests в Git;
- полноту `skills/stitch/build/`;
- игнорирование synthetic runtime/sensitive paths;
- отсутствие tracked ключей/vault/private-key extensions.

## Запрет массового добавления

Даже после удаления глобального ignore запрещено использовать `git add -A` в общем worktree. Агент сначала просматривает список новых файлов, сканирует безопасный scope и добавляет только явные пути.
