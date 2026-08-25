# AIOS Import Dependency Map Baseline

## Purpose

Track module relationships before production refactoring.

## Target dependency direction

```
Core Runtime
    ↓
Orchestration
    ↓
Agents
    ↓
Tools
    ↓
Infrastructure
```

## Rules

- Core must not import infrastructure.
- Agents communicate through stable interfaces.
- Tools remain replaceable adapters.
- Memory access goes through contracts.
- External services stay isolated.

## Analysis Steps

1. Collect imports.
2. Build dependency graph.
3. Detect cycles.
4. Identify high-coupling modules.
5. Move unstable dependencies outward.
6. Re-run validation.

## Cleanup Output

The result should become the production dependency baseline for AIOS.