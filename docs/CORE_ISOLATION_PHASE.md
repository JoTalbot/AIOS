# Core Isolation Phase

## Goal
Create a clean production baseline by separating the AIOS runtime core from infrastructure concerns.

## Target boundaries

```
Core Runtime
    |
    +-- Contracts
    +-- Domain Logic
    +-- Execution Engine

Services
    |
    +-- Orchestration
    +-- Agents
    +-- Memory

Infrastructure
    |
    +-- Storage
    +-- Deployment
    +-- Observability
```

## Rules

- Core must not import infrastructure.
- External integrations must use interfaces.
- Agents depend on contracts, not implementations.
- Refactoring is performed in small validated batches.

## Migration steps

1. Identify core candidates.
2. Move shared interfaces.
3. Remove infrastructure leakage.
4. Add regression tests.
5. Validate production baseline.
