# Dependency Graph Build Plan

## Goal
Create a clear dependency map for the clean production baseline.

## Steps

1. Collect module imports.
2. Build dependency graph.
3. Detect circular dependencies.
4. Identify high-coupling modules.
5. Separate core runtime from infrastructure.
6. Prepare refactoring targets.

## Target architecture

```text
Core Runtime
    |
Services
    |
Agents
    |
Tools
    |
Infrastructure
```

## Validation

- import checks
- test suite
- architecture review
- CI validation
