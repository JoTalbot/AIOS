---
name: pytest-path-hermeticity
version: 1.0
description: Устраняет machine-specific repository paths и mutable production-state reads в pytest без изменения production logic.
triggers: [pytest, permission-error, root-aios, hermetic-tests]
dependencies: [pytest]
llm_required: false
mcp_tools: []
---

# Pytest Path Hermeticity

## Описание

Применять, когда тесты проходят на production host `/root/AIOS`, но падают в CI или
не-root sandbox с PermissionError/ModuleNotFoundError.

## Алгоритм

1. Корень tracked repo вычислять как `Path(__file__).resolve().parents[1]`.
2. Mutable data перенаправлять в `tmp_path`; патчить не только `PROJECT_ROOT`, но и
   импортированные module-level path constants в модулях-владельцах функций.
3. Scripts импортировать через derived `<root>/scripts`, никогда через `/root/AIOS/scripts`.
4. Тест wiring/report rendering отделять от production snapshot reads: monkeypatch
   builder/formatter на минимальный валидный payload.
5. Aggregation/render tests снабжать детерминированными section providers, не читать live
   ledger/funnel/Kraken.
6. Запустить все затронутые файлы вместе, затем changed-file hard gate
   `ruff --select E,F --ignore E402` и py_compile.
7. Для legacy test files с большим количеством исторических длинных fixtures допустим
   узкий file-level `# ruff: noqa: E501`; остальные E/F остаются активны.

## Контроль и развитие

- [x] 8 test files / 100 tests passed вне `/root/AIOS`.
- [x] Changed-file E/F hard gate и py_compile clean.
- [ ] Отдельно сделать live-network tests opt-in integration suite.
