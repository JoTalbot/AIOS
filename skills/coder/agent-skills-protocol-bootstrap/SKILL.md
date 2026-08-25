---
name: agent-skills-protocol-bootstrap
description: "Как ИИ-агенту вести сессию в AIOS по протоколу скиллов/исследований/видимости статуса: старт, текущий шаг, поиск скиллов, deep research, дистилляция лога в скилл, закрытие."
---

# Agent Skills Protocol Bootstrap

Сессия-дистилляция: `coordination/sessions/20260825T074311Z-openhands-skills-protocol.md`.

## Описание

Проверенный на этой сессии рабочий цикл ИИ-агента в AIOS по протоколу
`docs/AGENT_SKILLS_PROTOCOL_RU.md`: как стартовать, держать видимым текущий шаг,
искать и применять скиллы, исследовать перед шагом и превращать лог в скилл.

## Алгоритм

1. Старт: прочитать `AGENTS.md`, `coordination/README.md`, `PROJECT_CONTEXT.md`,
   claims и `git status`. Чужие незакоммиченные изменения — не чужие (не трогать).
2. Изолированная работа: в грязном общем worktree ветки не переключать —
   `git worktree add <path> -b agent/<session-id>/<task> HEAD`.
3. Claim `coordination/claims/<scope>--<session-id>.md` до правок файлов.
4. Журнал `coordination/sessions/<session-id>.md` по шаблону; блок
   «Текущий шаг (виден другим агентам)» обновлять на каждом рубеже.
5. Поиск скилла: локально (`skills/`, SKILLS_INDEX.md) + интернет; применить,
   либо записать в журнал явный отказ с причиной.
6. Перед шагом кода/конфига — deep research (доки/issues/PR + сверка с кодом/runtime);
   итог 1-3 строки в журнал.
7. Правки: минимальные diff-вставки; якорь проверять на единственность
   (`s.count(anchor) == 1`).
8. Проверка: для AGENTS.md — маркеры `Protected`/`Золотые правила` + загрузка через
   `AutocoderV3._load_agents_md` с repo_path на worktree + `scripts/test_agents_md.py` (4/4).
9. Закрытие: журнал → DONE (файлы, проверки, git, handoff), claim удалить по протоколу,
   коммит только своих путей (`git add -- <paths>`), отдельный коммит на задачу.

## Контроль и развитие

- [x] Протокол задокументирован (AGENTS.md секция + docs/AGENT_SKILLS_PROTOCOL_RU.md)
- [x] Шаблон журнала получил блок «Текущий шаг»
- [ ] Автогенерация skills/<agent>/ из coordination/sessions/ (скрипт по аналогии memory_to_skills)
- [ ] Публикация в origin решена владельцем (push не выполнен)
