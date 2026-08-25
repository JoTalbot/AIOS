# Execution Engine Isolation Phase

## Goal

Create a clean execution kernel separated from services and infrastructure.

## Objectives

- isolate runtime loop;
- define execution boundaries;
- remove infrastructure coupling;
- keep agents and tools behind contracts.

## Target Flow

```
Request
  |
Execution Kernel
  |
Contracts
  |
Agents / Tools
  |
Infrastructure Adapters
```

## Rules

- Core runtime owns execution contracts.
- Infrastructure provides implementations.
- External services are accessed through adapters.
- Changes must remain testable and reversible.

## Next Tasks

- extract execution primitives;
- migrate interfaces;
- validate imports;
- add regression tests.
