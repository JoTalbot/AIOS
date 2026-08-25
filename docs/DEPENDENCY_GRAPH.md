# AIOS Dependency Graph Baseline

Branch: clean-code-production

## Target architecture

```
Core Runtime
    |
    +-- Orchestration
    |       |
    |       +-- Agents
    |       +-- Workflows
    |
    +-- Memory
    |       |
    |       +-- Storage
    |       +-- Retrieval
    |
    +-- Tools
    |
    +-- Infrastructure
            |
            +-- Deployment
            +-- Observability
```

## Audit rules

- Core must not import infrastructure.
- Agents depend on interfaces, not implementations.
- Tools are isolated behind adapters.
- Memory access goes through defined contracts.
- Circular dependencies must be removed.

## Refactoring order

1. Map imports.
2. Detect cycles.
3. Extract interfaces.
4. Move infrastructure boundaries.
5. Validate tests.
