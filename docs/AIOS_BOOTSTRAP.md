# AIOS Bootstrap Protocol

## Purpose

Define the first steps for any new AIOS agent session.

The GitHub repository is the source of truth. Chat history is temporary execution context.

## Rule

Do not read the entire repository during startup.

Use the recovery chain:

```
BOOTSTRAP
    ↓
PROJECT_STATE
    ↓
DOCUMENT_INDEX
    ↓
Required Documentation
    ↓
Implementation
```

## Startup Procedure

1. Read this file.
2. Read `docs/AIOS_PROJECT_STATE.md`.
3. Read `docs/AIOS_DOCUMENT_INDEX.md`.
4. Determine current phase and active task.
5. Open only documents required for the current task.

## Agent Behavior

The agent must:

- minimize unnecessary reading;
- preserve project direction;
- update state after significant changes;
- prefer existing architecture over creating duplicates;
- record new knowledge in documentation.

## Objective

Restore working context quickly while maintaining AIOS as a self-documenting system.
