# AIOS v22.6 Autonomous Agent Loop

## New Layer

Agent Runtime Loop connects planning, execution state and reflection.

Flow:

```text
Goal
 ↓
Context
 ↓
Reasoning Engine
 ↓
Action Planner
 ↓
Execution Engine
 ↓
Agent Runtime Loop
 ↓
Reflection
```

## Principles

- Keep runtime boundaries isolated.
- Preserve cognitive service modularity.
- Allow future persistent memory integration.
