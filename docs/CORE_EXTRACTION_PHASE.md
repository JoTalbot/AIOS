# Core Extraction Phase

## Goal
Extract the production runtime core from infrastructure-dependent layers.

## Steps

1. Identify runtime primitives.
2. Move shared contracts into core interfaces.
3. Remove infrastructure imports from core.
4. Migrate services to depend on contracts.
5. Validate with tests.

## Target Architecture

```text
Core Runtime
  |
  +-- Contracts
  +-- Domain Logic
  +-- Execution Engine

Services
  |
  +-- Agents
  +-- Orchestration
  +-- Memory

Infrastructure
  |
  +-- Storage
  +-- External APIs
  +-- Deployment
```

## Safety Rules

- Small isolated changes.
- Preserve execution flow.
- No hidden infrastructure dependencies.
- Every migration requires validation.
